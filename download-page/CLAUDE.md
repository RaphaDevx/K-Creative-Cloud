# Download Page — K-Advisory

## Design is FROZEN

The HTML structure and CSS in `index.html` and `advisory.html` must **never change** between sessions.
Do not redesign, refactor layouts, rename CSS classes, or touch styling. The design was finalized and is production-locked.

## How to publish a new release

1. **Only edit `releases.json`** — update the `version` and file path for the relevant product
2. Deploy (see below)

That's it. Never modify the HTML files just to bump a version.

## releases.json format

```json
{
  "r2_base": "https://pub-f8a055810aee4622b6883b39e71485fe.r2.dev",
  "products": {
    "k-creative": {
      "version": "X.Y.Z",
      "arm64": "k-creative/K-Creative Studio-X.Y.Z-arm64.dmg",
      "x64":   "k-creative/K-Creative Studio-X.Y.Z.dmg",
      "note":  "macOS 12+ · Apple Silicon + Intel · Auto-Update"
    },
    "k-daw": { ... },
    "k-dev-dashboard": { ... },
    "k-ai-dashboard": { ... }
  }
}
```

Files are stored in Cloudflare R2 bucket **`k-advisory-releases`** (public URL = `r2_base`).
Filename spaces are encoded by the page JS automatically — store readable names in the JSON.

## Deploy command

```bash
cd /home/raphael/K-Dev/Projekte/K-Creative-Cloud/download-page
CLOUDFLARE_API_TOKEN=$(grep "^CLOUDFLARE_API_TOKEN=" /home/claude/.keys/tokens.env | cut -d= -f2- | tr -d '"') \
  npx wrangler pages deploy . --project-name kaufmannadvisory
```

## Files

| File | Purpose |
|------|---------|
| `releases.json` | **Single source of truth** for all download versions and R2 paths |
| `index.html` | K-Creative Studio landing page (product cards: K-Creative, K-DAW, K-AI Dashboard) |
| `advisory.html` | K-Advisory hub — all products (Desktop + Mobile + Web) |

Both HTML files fetch `releases.json` on load and populate download links and version strings dynamically.
