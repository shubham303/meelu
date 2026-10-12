# website

Marketing site for Meelu: landing page with the desktop app download, free SEO tools, pricing, and a markdown blog. Built with Next.js (App Router), Tailwind CSS v4, and shadcn/ui. Self-hosted with Coolify on a Hostinger VPS.

## Develop

```bash
npm install
npm run dev
```

## Content

- **Blog posts** live in `content/blog/*.md`. Frontmatter: `title`, `description`, `date` (`YYYY-MM-DD`), optional `tags`. The filename is the URL slug. Posts appear automatically on `/blog`, the landing page, `/sitemap.xml`, and `/rss.xml`.
- **Site name, tagline, description, and social links** live in `src/lib/site.ts`.

## Environment variables

Set these in Coolify (Projects → Meelu website → production → meelu-website → Environment Variables):

- `NEXT_PUBLIC_SITE_URL` — canonical URL, `https://meelu.tech`. Used for metadata, sitemap, and RSS. Falls back to `https://meelu.tech`.
- `NEXT_PUBLIC_GA_ID` — Google Analytics measurement ID. Without it, no analytics tag is rendered.
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` — the Cloudflare R2 bucket (`meelu-website`) that holds the keyword clustering tool's daily run counter (`keyword-clusters/runs/`).
- `DATAFORSEO_AUTH` — DataForSEO credentials, already base64 (`login:password`), sent as `Authorization: Basic`. Used by the keyword clustering tool.
- `OPENROUTER_API_KEY` — OpenRouter key for the keyword clustering tool's seed relevance check and intent split.
- `OPENROUTER_LLM_MODEL` — optional, the model that splits keyword groups by intent. Defaults to `deepseek/deepseek-v4-flash`.
- `OPENROUTER_JEV_MODEL` — optional, the classifier that checks each keyword against its seed. Defaults to `~typesafe/jev-latest`.
- `KEYWORD_CLUSTER_DAILY_LIMIT` — optional, keyword clustering runs allowed per UTC day across all visitors. Defaults to 100.

`NEXT_PUBLIC_*` values are baked into the JavaScript at build time. After changing one, redeploy; a restart is not enough.

## Deploy

The site runs as a Docker container on a Hostinger VPS (`srv2048855.hstgr.cloud`, `31.220.20.109`, Ubuntu 24.04) managed by [Coolify](https://coolify.io). The image is built from `website/Dockerfile` in the `shubham303/meelu` repo (base directory `/website`) and uses Next.js `output: "standalone"`.

**Normal deploys are automatic.** Merge to `main` and a GitHub webhook tells Coolify to build and roll out the new commit. The app's watch paths are `website/**`, so changes elsewhere in the repo do not rebuild the site. The new container must pass the Dockerfile healthcheck before the old one is removed, so a broken build never replaces the running site.

Where things are:

| What | Where |
|---|---|
| Coolify dashboard | `https://coolify.meelu.tech` → Projects → Meelu website → production → meelu-website |
| Build and deploy logs | Coolify → the app → Deployments |
| Environment variables | Coolify → the app → Environment Variables |
| Domains and HTTPS | Coolify → the app → Configuration → Domains (`https://meelu.tech,https://www.meelu.tech`). Coolify's proxy gets Let's Encrypt certificates on its own and redirects all http to https with a permanent 301. |
| DNS and edge security | Cloudflare (nameservers moved from Hostinger). `@`, `www` and the app subdomains are proxied to `31.220.20.109`; SSL mode Full (strict). The Hostinger firewall only accepts ports 80/443 from Cloudflare's IP ranges, so the server can't be reached directly. |
| App downloads | R2 bucket `meelu-downloads`, served at `https://downloads.meelu.tech` and linked from `/download`. |
| Repository access | A read-only deploy key named `coolify srv2048855` (GitHub → Settings → Deploy keys) |
| Auto-deploy hook | GitHub → Settings → Webhooks → `https://coolify.meelu.tech/webhooks/source/github/events/manual`, signed with the secret stored on the Coolify app |

Manual deploy, rollback and restart are buttons on the app page in Coolify. Rollback lists the previous images by commit.

To test the image locally:

```bash
docker build -t meelu-website .
docker run --rm -p 3000:3000 --env-file .env.local meelu-website
```

### Setting it up again from scratch

1. Install Coolify on an Ubuntu VPS. Give the dashboard its own domain (Settings → Instance domain), then allow only ports 22, 80 and 443 in the Hostinger firewall.
2. In Coolify, add the deploy key under Keys & Tokens, and add its public half to this repo as a read-only deploy key.
3. Create a project, then an application from a private repository with a deploy key: repo `git@github.com:shubham303/meelu.git`, branch `main`, base directory `/website`, watch paths `website/**`, build pack Dockerfile, port 3000.
4. Set the environment variables above and the domains `https://meelu.tech,https://www.meelu.tech`.
5. Point the `@` and `www` A records at the server and deploy.
6. For auto-deploy, set a GitHub webhook secret on the app and add a GitHub webhook for push events with that secret.
