# Sito GitHub Pages — ISTAT MCP Server

## Obiettivo
Single page IT + single page EN che descrive il progetto, stile Airbnb (DESIGN.md), Astro, deploy su GitHub Pages.

## Fase 1 — Scaffolding
- [x] Creare directory `site/` alla root del repo (isolata, non interferisce col progetto Python)
- [x] Init Astro minimale: `package.json`, `astro.config.mjs`, `tsconfig.json`
- [x] Config `base` e `site` in `astro.config.mjs` per GitHub Pages (`/istat_mcp_server/`)
- [x] `.gitignore` per `node_modules`, `dist`, `.astro`

## Fase 2 — Design system (DESIGN.md → CSS)
- [x] `src/styles/global.css` con token CSS: colori (#ff385c, #222222, #f2f2f2), radius (8/14/20/32), shadow 3-layer, font-stack Cereal→fallback system
- [x] Layout base `src/layouts/Base.astro`: header sticky bianco, footer
- [x] Componenti riutilizzabili: `Hero.astro`, `FeatureCard.astro`, `ToolCard.astro`, `CTAButton.astro`, `LangSwitch.astro`

## Fase 3 — Contenuti
- [x] `src/pages/index.astro` (EN): hero + overview + 8 tools grid + workflow + install + link GitHub
- [x] `src/pages/it.astro` (IT): stessa struttura, contenuti da `README_IT.md`
- [x] Language switch EN ⇄ IT in header
- [x] Badge newsletter + deepwiki + GitHub

## Fase 4 — Deploy GitHub Pages
- [x] `.github/workflows/deploy-site.yml` con action ufficiale Astro (`withastro/action@v3`)
- [x] Trigger: push su `main` con path filter `site/**`
- [x] Permissions: `pages: write`, `id-token: write`

## Fase 5 — Guida utente (config repo)
Istruzioni per te:
1. Settings → Pages → Source = **GitHub Actions**
2. Merge PR → workflow parte → sito live su `https://ondata.github.io/istat_mcp_server/`
3. (Opz.) Settings → Pages → Custom domain

## Domande aperte
- URL finale: `ondata.github.io/istat_mcp_server/` ok? oppure custom domain?
- Contenuti: riassumo README o riporto tutto?
- Screenshot/immagini del tool in azione? (per ora solo testo/icone)
- Logo ISTAT/ondata da includere?

## Review

- Scaffolding Astro minimale in `site/` (package.json, astro.config.mjs con `base: /istat_mcp_server`, tsconfig strict, .gitignore)
- Design system in `src/styles/global.css`: token colori (Rausch #ff385c, near-black #222), radius 8/14/20/32, shadow 3-layer, font-stack Cereal→system
- Layout `Base.astro` con header sticky, lang-switch EN⇄IT, footer
- Pagine `index.astro` (EN) e `it.astro` (IT): hero + "perché esiste" + grid 8 tool + workflow 3 step + install block
- Contenuti concisi: concetti base + curiosità, link al README per approfondire
- Workflow `.github/workflows/deploy-site.yml` con `withastro/action@v3`, filtro path `site/**`
- Build locale OK: 2 pagine in `site/dist/`

**Config repo da fare a mano (una volta sola):**
1. Settings → Pages → Source = **GitHub Actions**
2. Merge PR → workflow gira → sito live su `https://ondata.github.io/istat_mcp_server/`

**Note:**
- Branch `docs/newsletter-badge` cancellato (locale + remoto) perché già mergeato
- Font "Airbnb Cereal VF" non è open: il CSS cade su Circular / system-ui, mantenendo il feel

