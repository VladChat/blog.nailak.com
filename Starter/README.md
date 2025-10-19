# blog.nailak.com — Clean Starter (from your archive)

This package contains only the **source-of-truth** and essential config for your blog:
- `blog_src/**` — Hugo source (themes, layouts, static, etc.).
- `.github/**` — your Actions (if present).
- Root configs (`config.*`, `.gitignore`, etc.).
- Icons/favicons moved to `blog_src/static/icons/` (byte-identical).
- AFF cards/images consolidated under `blog_src/static/aff/` (byte-identical).

## How to use
1. Create an empty folder `blog.nailak.com` locally.
2. Unzip this archive into that empty folder.
3. Build a **clean site** into the repository root:

```powershell
hugo -s blog_src -d . --cleanDestinationDir
```

4. Preview `index.html` locally or run the dev server (without writing to disk):
```powershell
hugo server -s blog_src
```

5. Commit & push as usual:
```powershell
git add -A
git commit -m "Clean rebuild from source"
git push
```

## Notes
- We intentionally excluded built output (`aff/`, `assets/`, `css/`, `js/`, `images/`, etc.) and backup snapshot `Last/`.
- All kept files are **byte-for-byte identical** to your originals; only their location may differ (icons/aff moved under `blog_src/static`).

