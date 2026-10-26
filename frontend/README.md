# AuditDDI frontend

The DDI prediction panel calls the FastAPI service through the Express server. The browser never receives the backend URL's API key.

## Local development

1. Copy a compatible trained checkpoint and its matching seven-branch feature bundle from Drive into a local artifact directory. In a PowerShell window at the repository root, set `AUDITDDI_CHECKPOINT_DIR` to that directory, `PXDDI_CHECKPOINT_PATH` to the checkpoint filename, and `AUDITDDI_SEVEN_BRANCH_FEATURE_BUNDLE` to the matching `.npz` path. Keep local research authentication disabled, then start FastAPI with `python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`. Check `http://127.0.0.1:8000/health` before starting the UI.
2. In a second PowerShell window, go to `frontend`, install dependencies with `npm install`, and copy `.env.example` to `.env`. Keep `AUDITDDI_BACKEND_URL=http://127.0.0.1:8000`.
3. Start the frontend with `npm run dev`, then open the local URL printed by Vite.

The UI displays “DDI model unavailable” when FastAPI is unreachable, has no compatible checkpoint, or cannot load its feature bundle; it does not invent a replacement score. `GET /api/backend/health` helps inspect backend readiness.

The other dashboard sections still contain demo or fixture content and are not evidence-backed prediction APIs. The DDI output itself represents reported TWOSIDES pairs versus sampled unreported pairs; an unreported pair is not known to be safe. This research system is not clinical advice.
