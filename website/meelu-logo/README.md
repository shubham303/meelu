# Meelu logo files

Colors: ink `#1f2d3d`, blue `#2563eb`, cream `#f8f5eb`, blue on dark `#6b9bff`.
The wordmark is Fraunces Light, converted to outlines, so no font needs to be loaded.

## Which file to use

| Use | File |
| --- | --- |
| Header logo, light background | `svg/meelu-logo.svg` |
| Header logo, dark background | `svg/meelu-logo-dark.svg` |
| Mark only (nav, loaders, avatars) | `svg/meelu-mark.svg` / `svg/meelu-mark-dark.svg` |
| Mark below ~32px | `svg/meelu-mark-small.svg` (thicker ring) |
| Wordmark only | `svg/meelu-wordmark.svg` / `svg/meelu-wordmark-dark.svg` |
| Desktop app icon | `svg/meelu-app-icon.svg`, `png/meelu-app-icon-1024.png` |
| Social / OG / email | `png/meelu-logo@4x.png`, `png/meelu-mark-1024.png` |

## Favicon setup

Copy `favicon.ico` to your public root and the rest to `/public`, then:

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
```

`favicon.svg` switches the ring to cream when the browser is in dark mode.

In Next.js App Router you can instead drop `favicon.ico`, `icon.svg` (rename `favicon.svg`)
and `apple-icon.png` (rename `apple-touch-icon.png`) into `app/`.

`site.webmanifest` icons:

```json
"icons": [
  { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
  { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
  { "src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
]
```

## Clear space and minimum size

Keep clear space around the logo equal to the ring's inner diameter.
Don't use the full lockup below 100px wide; use the mark instead.
Don't recolor the ring and disk the same color, since the overlap is the idea.
