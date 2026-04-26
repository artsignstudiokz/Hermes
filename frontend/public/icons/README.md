# PWA icons

Generate three PNGs from `frontend/public/hermes-emblem.svg`:

| File | Size | Purpose |
|---|---|---|
| `icon-192.png` | 192×192 | Generic any-purpose icon |
| `icon-512.png` | 512×512 | Splash screen + iOS home-screen icon |
| `icon-maskable-512.png` | 512×512 | Android adaptive icons (safe-area inside ~80% circle) |

Quick way:

```bash
# requires `inkscape` or any SVG → PNG converter
inkscape ../hermes-emblem.svg -w 192 -h 192 -o icon-192.png
inkscape ../hermes-emblem.svg -w 512 -h 512 -o icon-512.png
# For maskable: pad the SVG with a marble background so the safe-area covers
# the caduceus comfortably. Open icon-maskable-512.png in any editor and
# verify the icon stays inside the inner circle when masked.
```

Until these are added, browsers fall back to the 16×16 favicon (still works,
just less polished). The PWA install prompt requires at least the 192/512 pair.
