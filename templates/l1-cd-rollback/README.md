# L1 — Post-Deploy Auto-Rollback Templates

Canonical, battle-tested workflows for the L1 layer of `autonomous-cd-business-agents`:
after each deploy to a customer-facing property, run its live customer-path E2E and,
on red, restore the previous good deployment. Zero model calls — pure CI config.

## Pick the topology by how the property deploys

| Property deploys via… | Rollback mechanism | Template | Proven on |
|---|---|---|---|
| **Netlify git integration** (push → Netlify builds & publishes, outside Actions) | Netlify **restore API** (`POST /sites/{id}/deploys/{id}/restore`) — republish a prior build, no rebuild | `netlify-restore.cd-rollback.yml` (here) | green-collar-landscaping #4 |
| **Cloudflare Pages/Workers** (deploy runs *inside* GitHub Actions via `wrangler`) | **Redeploy-from-SHA** — check out the previous good commit and re-run `wrangler deploy` (CF Pages has no restore verb) | see `immortalvibes-store` `.github/workflows/deploy.yml` (verify-live + rollback jobs) | immortalvibes-store #3/#5 |

The two share the same contract; only the "how do I put the old version back" step differs.

## The contract (both topologies)

1. **Deploy** (existing — Netlify auto, or the CF deploy jobs).
2. **Verify** — run the property's live customer-path suite against the public URL.
3. **On red → rollback** — restore/redeploy the previous known-good.
4. **On red → notify** — best-effort ntfy + Telegram (secret-guarded).
5. **Record evidence** — restored id/sha + run URL in the job summary (STOP 9).

A green deploy does nothing extra. No false rollbacks.

## Wiring a new Netlify property

1. Copy `netlify-restore.cd-rollback.yml` → the property repo's `.github/workflows/cd-rollback.yml`.
2. Replace `<PROD_BRANCH>`, `<PROD_URL>`, `<PROJECT_NAME>`.
3. Ensure the repo already has a Playwright suite under `e2e/` + `playwright.config.*`
   whose `baseURL` reads `E2E_BASE_URL` (reuse the property's weekly `e2e.yml` suite —
   do **not** duplicate it; Playwright stays `--no-save`, never in `package.json`).
4. Add GH secrets `NETLIFY_AUTH_TOKEN` + `NETLIFY_SITE_ID` (scope the token to the site).
   Optional notify: `NTFY_URL`, `NTFY_TOPIC`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
5. **Prove it (STOP 9):** after merge, run the drill —
   `gh workflow run cd-rollback.yml -f rollback_drill=true` — it restores the *current*
   live deploy (no revert) and exercises auth → list → restore → notify end-to-end.
   Capture the run URL + restored id.

## Design invariants — do not regress (each cost a real bug or gate finding)

- **Rollback fires only on the SMOKE step's own `failure` outcome** (exposed as a job
  output), never on the verify *job* result. Otherwise a transient Netlify API blip
  during the poll, or an npm/browser-install failure, reverts a *healthy* deploy.
  (GCL Opus gate, finding #1.)
- **The poll curl is fault-tolerant** (`|| true`, jq `… || echo none`) and re-polls
  within the deadline — an API hiccup is not a rollback trigger.
- **Rollback target is anchored to `github.sha`** (restore the deploy *after* the bad
  one), not a positional index — robust if a newer deploy lands mid-run. (GCL gate, #2.)
- **Refuse (exit 1) if there's no prior deploy**; the post-restore health check runs
  once and never loops.
- **Drill restores the CURRENT deploy** = a no-op that proves the machinery without
  reverting. (CF variant redeploys current HEAD for the same reason.)
- **STOP 21:** secret *names* only in these files — they live in public repos.

## Lessons banked (from building these)

- **Exercise the failure path before you need it.** The IV rollback drill's *first*
  run failed on a real bug (a doubled `web/` path → ENOENT) — a happy-path-only drill
  would have hidden it. Run the drill as part of shipping, not later.
- **Confirm the deploy branch before wiring.** GCL's L1 was first built against a
  stale `master`; the live branch was `main`. Check `default_branch` + which branch
  actually has recent commits + what the platform (Netlify/CF) is configured to build.
- **Reuse the existing E2E suite; don't duplicate it.** The gate is only as good as
  the suite it runs — point at the property's real customer-path specs.
