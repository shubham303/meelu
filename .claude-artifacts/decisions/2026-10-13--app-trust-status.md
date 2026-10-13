# App trust: Google OAuth, Apple signing, Microsoft Store (status 2026-10-13)

Goal: a new user downloads, installs and connects Meelu without a security
warning anywhere. Three separate tracks, none blocks another.

## 1. Google OAuth verification (Search Console + Analytics)

Done:
- Google Auth Platform branding: app name "Meelu", logo (120×120 made from the
  site icon), home https://meelu.tech, privacy https://meelu.tech/privacy,
  terms https://meelu.tech/terms, authorized domain meelu.tech. The app's GSC
  and GA flows share one OAuth client (`177278680529-…`), desktop loopback.
- Scopes: `webmasters.readonly`, `analytics.readonly` (both sensitive, not
  restricted, so no CASA assessment). Gmail scopes would be restricted; keep
  them out.
- App published to "In production".
- Demo video: `~/Desktop/meelu oauth demo.mp4` (1:28), cut from
  `meelu recording website.mov` + `meelu recording app.mov`: homepage, GSC
  consent showing the scope, GSC data in the app, GA consent showing the
  scope, GA connected, traffic import running. No VS Code / Finder frames.
- Verification form questions (personal / internal / dev-only / WordPress SMTP)
  all answered No.

Pending / known gaps:
- Upload the video to YouTube as Unlisted and put the link in the
  Verification Center, then submit (if not already done).
- The video never shows finished GA data, and the website clip is from
  12 Oct (old homepage, no privacy page). If Google asks, record ~15 s of the
  Traffic page with data and a few seconds of meelu.tech/privacy and append.
- Expect brand verification in 2–3 business days, scope review 1–3 weeks.

## 2. Apple (macOS signing + notarization)

Decided: enroll as **Individual** (developer name "Shubham Randive"; no
registered company, so Organization is not possible).

Status: enrollment through the Apple Developer app on the iPad; the iPad
needed a software update first. Waiting for the "Welcome to the Apple
Developer Program" email ($99/yr).

Next, once enrolled:
1. Create a **Developer ID Application** certificate (CSR from Keychain on the
   Mac), export as .p12 → GitHub secrets for electron-builder (`CSC_LINK`,
   `CSC_KEY_PASSWORD`).
2. Create an **App Store Connect API key** (.p8, key ID, issuer ID) for
   notarization → GitHub secrets.
3. Mac build config in `app/package.json`: remove `"identity": null`, enable
   hardened runtime, add entitlements Electron and the native modules need
   (JIT, unsigned executable memory, disable library validation for
   onnxruntime/sharp), turn on notarize. Do NOT change the build before the
   certificate exists or the mac job fails.
4. Release a signed build with `/app-release`.
5. After that, true auto-update on mac becomes possible (Squirrel.Mac refuses
   unsigned apps).

## 3. Microsoft Store (Windows)

Full decision and checklist: `2026-10-13--windows-distribution.md`.

Done:
- Partner Center account, Individual developer. **Verification Status: In
  Progress** (blocks only "Submit for certification").
- Product "Meelu" reserved. Identity `ShubhamRandive.Meelu`, publisher
  `CN=62EA4499-A8A4-4A51-BF17-4B19F01B3EF1`, publisher display name
  "Shubham Randive".
- App 0.1.5 (PRs #25/#26) builds `Meelu-windows-x64.appx` in the prod App
  build (artifact `store`, not uploaded to R2). Store installs skip Meelu's own
  update check (`process.windowsStore`).
- Submission 1 filled in: package 0.1.5 uploaded and validated, Pricing =
  Free with **Private audience**, properties (privacy URL), age rating,
  "digital goods" = Yes (own payment provider, Dodo; Microsoft takes 0%),
  listing text, features, search terms, screenshots, poster/box art/tiles
  (300, 150, 71), runFullTrust justification.
- Local files: `~/Desktop/meelu-store/Meelu-windows-x64.appx` and
  `~/Desktop/meelu-store/images/` (5 screenshots cropped from the OAuth
  recording with the beta banner painted out; posters, box art, tiles).

Next, once the account is verified:
1. Click **Submit for certification** (1–3 days).
2. Install from the private Store link on a Windows PC; check sign-in, crawl,
   agent, GSC/GA connect.
3. Switch visibility to **Public**.
4. Website: get the **Store ID** (Partner Center → Product identity, 12 chars
   starting with 9). Point the Windows button in
   `website/src/components/download-buttons.tsx` to
   `https://apps.microsoft.com/detail/<Store ID>`, keep the .exe as a small
   "Direct download (.exe)" link, limit the SmartScreen instructions on
   `website/src/app/(site)/download/page.tsx` to the .exe, and update the
   beta banner / homepage text about Microsoft warnings. Do this only after
   the listing is public.
5. Every later Store update: download the .appx from the App build run
   (`gh run download <run-id> -n store`), Partner Center → Update submission
   → Packages → upload → Submit. Automating via the Store submission API
   (Entra app + 4 GitHub secrets) is optional for later.

## Related changes shipped the same day

- App update check every 10 minutes and an App updates card in Settings with
  "Check for updates" (0.1.4); older apps get a fallback message.
- Beta banner can be closed (dashboard).
- Stop on a GSC/GA sync the app no longer runs now cancels it on the server.
- Skills now live in the repo: `.claude/skills/pr-workflow`, `app-release`.
- Open question: automatic install of updates. Windows is covered by the
  Store; mac waits for signing.
