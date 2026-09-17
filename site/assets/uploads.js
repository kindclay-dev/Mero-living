/* Photos dropped into the browser, kept in IndexedDB.
 *
 * Object URLs die with the page, so a folder dropped on the grid would vanish
 * the moment you opened a product. Storing the blobs instead means uploads
 * survive navigation and reloads, and both pages read from the same place.
 * Nothing leaves the browser.
 */
window.MeroUploads = (function () {
  const DB_NAME = "mero-uploads";
  const STORE = "photos";
  const VERSION = 1;

  let dbPromise = null;

  function open() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) { reject(new Error("no indexedDB")); return; }
      const req = indexedDB.open(DB_NAME, VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: "id", autoIncrement: true })
            .createIndex("slug", "slug", { unique: false });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  function tx(mode, run) {
    return open().then(db => new Promise((resolve, reject) => {
      const t = db.transaction(STORE, mode);
      const out = run(t.objectStore(STORE));
      t.oncomplete = () => resolve(out && out.value !== undefined ? out.value : out);
      t.onerror = () => reject(t.error);
      t.onabort = () => reject(t.error);
    }));
  }

  /* Store files against a product slug. */
  function put(slug, files) {
    return tx("readwrite", store => {
      [...files].forEach(file => store.add({
        slug,
        name: file.name,
        type: file.type,
        blob: file,
        added: Date.now()
      }));
    });
  }

  /* Rows for one product, oldest first, as {name, url} with live object URLs. */
  function get(slug) {
    return open().then(db => new Promise((resolve, reject) => {
      const rows = [];
      const req = db.transaction(STORE, "readonly").objectStore(STORE)
        .index("slug").openCursor(IDBKeyRange.only(slug));
      req.onsuccess = () => {
        const cursor = req.result;
        if (!cursor) {
          rows.sort((a, b) => a.added - b.added || a.name.localeCompare(b.name));
          resolve(rows.map(r => ({
            name: r.name,
            src: URL.createObjectURL(r.blob),
            uploaded: true
          })));
          return;
        }
        rows.push(cursor.value);
        cursor.continue();
      };
      req.onerror = () => reject(req.error);
    }));
  }

  /* How many photos are stored per slug: {slug: count}. */
  function counts() {
    return open().then(db => new Promise((resolve, reject) => {
      const out = {};
      const req = db.transaction(STORE, "readonly").objectStore(STORE).openCursor();
      req.onsuccess = () => {
        const cursor = req.result;
        if (!cursor) { resolve(out); return; }
        out[cursor.value.slug] = (out[cursor.value.slug] || 0) + 1;
        cursor.continue();
      };
      req.onerror = () => reject(req.error);
    }));
  }

  /* First stored photo for each slug, for grid thumbnails. */
  function covers() {
    return open().then(db => new Promise((resolve, reject) => {
      const best = {};
      const req = db.transaction(STORE, "readonly").objectStore(STORE).openCursor();
      req.onsuccess = () => {
        const cursor = req.result;
        if (!cursor) {
          const out = {};
          Object.keys(best).forEach(s => { out[s] = URL.createObjectURL(best[s].blob); });
          resolve(out);
          return;
        }
        const row = cursor.value;
        const held = best[row.slug];
        if (!held || row.added < held.added ||
            (row.added === held.added && row.name < held.name)) {
          best[row.slug] = row;
        }
        cursor.continue();
      };
      req.onerror = () => reject(req.error);
    }));
  }

  function clear(slug) {
    if (!slug) return tx("readwrite", store => store.clear());
    return open().then(db => new Promise((resolve, reject) => {
      const t = db.transaction(STORE, "readwrite");
      const req = t.objectStore(STORE).index("slug").openCursor(IDBKeyRange.only(slug));
      req.onsuccess = () => {
        const cursor = req.result;
        if (cursor) { cursor.delete(); cursor.continue(); }
      };
      t.oncomplete = resolve;
      t.onerror = () => reject(t.error);
    }));
  }

  /* --- matching dropped folders to products ------------------------ */

  const slugify = s => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  /* '20-mavi/01.jpg' -> 'mavi'. Falls back to a prefix match so
     'veeru-a' still lands on 'veeru' and 'mavi-final' on 'mavi'. */
  function matchSlug(folderName, knownSlugs) {
    const name = slugify(folderName.replace(/^\d+[-_\s]*/, ""));
    if (!name) return null;
    if (knownSlugs.includes(name)) return name;
    const near = knownSlugs.filter(s => name.startsWith(s) || s.startsWith(name));
    return near.length ? near.reduce((a, b) => (a.length >= b.length ? a : b)) : null;
  }

  const IMAGE_EXT = /\.(jpe?g|png|webp|avif|gif)$/i;
  const isImage = file =>
    (file.type ? file.type.startsWith("image/") : IMAGE_EXT.test(file.name));

  /* Group a FileList from a directory picker or a drop into {slug: [files]}. */
  function group(files, knownSlugs) {
    const byFolder = {};
    [...files].forEach(file => {
      if (!isImage(file)) return;
      const path = file.webkitRelativePath || file.relativePath || file.name;
      const parts = path.split("/").filter(Boolean);
      // the folder directly holding the file; a bare file has no folder
      const folder = parts.length > 1 ? parts[parts.length - 2] : "";
      (byFolder[folder] = byFolder[folder] || []).push(file);
    });

    const matched = {};
    const skipped = [];
    Object.keys(byFolder).forEach(folder => {
      const slug = matchSlug(folder, knownSlugs);
      if (slug) matched[slug] = (matched[slug] || []).concat(byFolder[folder]);
      else skipped.push(folder || "(loose files)");
    });
    return { matched, skipped };
  }

  /* Walk a drag-and-drop tree, which arrives as entries rather than paths. */
  function readDrop(dataTransfer) {
    const items = [...(dataTransfer.items || [])];
    const entries = items
      .map(i => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null))
      .filter(Boolean);
    if (!entries.length) return Promise.resolve([...(dataTransfer.files || [])]);

    const files = [];
    const walk = (entry, prefix) => new Promise(resolve => {
      if (entry.isFile) {
        entry.file(file => {
          file.relativePath = prefix + entry.name;
          files.push(file);
          resolve();
        }, resolve);
        return;
      }
      const reader = entry.createReader();
      const batch = () => reader.readEntries(list => {
        if (!list.length) { resolve(); return; }
        Promise.all(list.map(e => walk(e, prefix + entry.name + "/"))).then(batch);
      }, resolve);
      batch();
    });

    return Promise.all(entries.map(e => walk(e, ""))).then(() => files);
  }

  return { put, get, counts, covers, clear, group, matchSlug, readDrop, isImage };
})();
