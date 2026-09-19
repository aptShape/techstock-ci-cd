# TechStock frontend

React + Vite interface for **TechStock - IT Equipment Inventory Manager**.
It preserves item names, prices, quantities, CRUD operations, and quantity adjustment.

See the [project README](../README.md) for Docker Compose, credentials, CI, and Kubernetes deployment.

For local frontend development, run `npm ci`, then `npm run dev`.
The Vite development server forwards `/api` to FastAPI at `http://127.0.0.1:8000`.

`VITE_API_URL` defaults to `/api`. It accepts an API base or origin; the client
normalizes the trailing `/api` prefix and appends `/items`. It is a build-time
setting, not a runtime container setting. Do not put credentials in Vite variables.

Commands: `npm test`, `npm run lint`, `npm run build`.
