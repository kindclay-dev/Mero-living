# new-products — drop new planter photography here

Put a zip (or loose image files) in this folder, then tell me to update and
I'll unpack it, work out which products the photos belong to, and rebuild the
site.

```
new-products/
  planters.zip
```

Anything works — one zip, several zips, or loose images. Folder names inside
the zip help me match photos to products, but if there aren't any I'll go by
filenames and, where it's ambiguous, ask before guessing.

## What I'll need to know

For photos of a planter **already in the store**, nothing — I'll match it and
the new shots will lead its gallery.

For a **new planter**, the Shopify feed has no entry for it, so tell me:

- name
- price
- colours it comes in
- sizes, if more than one
- the description for the DETAILS section
- SKU, if there is one

## Notes

- Originals can be full size; they're resized to 1100px on build.
- JPG, PNG and WebP all work.
- Nothing here is published directly — the build writes to
  `site/assets/products/`, and what you put here stays untouched.
