# Dashboard MVP Notes

This dashboard provides live release-pipeline monitoring plus first-pass visual asset browsing.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File .\run_dashboard.ps1 -Port 8787
```

Open `http://127.0.0.1:8787`.

## MVP Features Implemented

- Live pipeline state, progress, control actions, checkpoint timeline, and logs.
- QA report summaries for preflight, quality gate, and release readiness.
- Latest preview player that loads the newest rendered video artifact.
- Format layout summary cards from export presets and current output files.
- Asset browser grouped by output folder with preview/download actions.
- Safe download endpoint with path traversal protection and URL encoding.

## New API Endpoints

- `GET /api/artifact-browser`
- `GET /api/layouts`
- `GET /api/preview/default`
- `GET /api/files/download?path=<workspace-relative-path>`

## Notes

- The dashboard is read-first for assets in this MVP phase.
- Timeline editing, preset CRUD, and export/share assistant are planned next.
