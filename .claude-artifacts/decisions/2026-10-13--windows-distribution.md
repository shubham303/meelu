# Windows distribution: Microsoft Store first, unsigned .exe as fallback

Decided 2026-10-13.

## Goal

A new Windows user installs Meelu without any security warning. A SmartScreen
"Windows protected your PC" screen makes people turn back, so avoiding it on
the first download matters more than saving the Store review time.

## Decision

- **Main path: Microsoft Store (MSIX).** Meelu is published as an MSIX package
  built by electron-builder's `appx` target. Microsoft re-signs MSIX packages,
  so Store installs show no SmartScreen warning from day one, and the Store
  installs updates by itself.
- **Website:** the "Download for Windows" button on meelu.tech opens Meelu's
  listing on apps.microsoft.com (Get button, or Microsoft's signed web
  installer for the Store version).
- **Fallback:** the current unsigned NSIS `.exe` stays on downloads.meelu.tech
  as a secondary "Direct download (.exe)" link, for machines where the Store is
  disabled. It keeps showing SmartScreen and keeps updating through the in-app
  update notice and the Settings update card.
- **Account:** Partner Center, registered as an Individual developer
  (Shubham Randive). Registration is free for individuals since September 2025
  (ID + selfie check).

## Options rejected

| Option | Why not |
|---|---|
| Azure Artifact Signing (Trusted Signing) | Individuals only in the US and Canada; India not eligible as individual or organization. |
| Paid OV/IV certificate for the .exe (Certum ~$115–139/yr, Sectigo ~$216/yr + cloud signing, SSL.com eSigner from ~$180/yr + cert) | SmartScreen still warns until download reputation builds, so it does not meet the no-warning goal. Certum cloud signing cannot run in GitHub Actions. Revisit only if many users need a signed direct .exe. |
| EV certificate | Microsoft removed the instant SmartScreen reputation benefit in 2024. |
| SignPath Foundation / Certum open-source certificate | Require a public open-source repository; the repo is private. |
| Win32 .exe submitted to the Store as-is | Microsoft does not re-sign it; it needs its own trusted signature. |

## Risks to check on the Store build

- MSIX runs with full trust but redirects some AppData writes. Verify the agent
  (Claude Agent SDK CLI), crawling, renders, the embedding models and the
  Google OAuth loopback sign-in (127.0.0.1 callback) all work in the packaged
  Store build before submitting.
- Each version goes through Store certification (usually a few days), so a
  hotfix reaches Store users later than the direct .exe.
- The in-app update notice must not tell Store users to download the .exe;
  Store installs update through the Store.

## Steps

1. [x] Register in Partner Center as an Individual developer (ID verification was still in progress when the name was reserved; it did not block).
2. [x] Reserve the app name "Meelu" (Apps and games → New product → MSIX or PWA app).
3. [x] Product identity: `ShubhamRandive.Meelu`, publisher `CN=62EA4499-A8A4-4A51-BF17-4B19F01B3EF1`, display name "Shubham Randive".
4. [x] `appx` config in `app/package.json`, tile images in `app/build/appx/`, `npm run dist:store` (prod only), and an App build step that uploads the package as the `store` workflow artifact (not to R2).
5. [ ] Test the Store package: submit it to Partner Center with a private audience first (it cannot be built or sideloaded on a Mac), install from the private Store link on a Windows PC, check the agent, crawl, GSC/GA sign-in.
6. [x] Store installs (`process.windowsStore`) skip Meelu's own update check; the Settings card says the Store keeps Meelu up to date.
7. [ ] Submit to Store certification (listing text, screenshots, privacy policy URL https://meelu.tech/privacy, age rating).
8. [ ] Point the website's Windows button at the Store listing; keep the .exe as a secondary link.
9. [ ] Update website and beta-banner copy that says Windows shows security warnings.

## Related

- Mac: Apple Developer Program, individual enrollment in progress; signed and
  notarized builds remove the Gatekeeper warning.
- Google: OAuth verification in progress for `webmasters.readonly` and
  `analytics.readonly`.
