# TechStock - IT Equipment Inventory Manager

TechStock manages IT equipment such as laptops, monitors, keyboards, routers,
switches, and accessories. Items retain the original fields: name, price, and
quantity, with create/read/update/delete and quantity increase/decrease operations.
There is no authentication, ordering, or payment system.

## Architecture

| Component | Technology | Container port |
| --- | --- | --- |
| Frontend | React + Vite, Axios; Nginx serves the production build | 80 |
| Backend | FastAPI + Uvicorn, PyMongo | 8000 |
| Database | MongoDB with persistent storage | 27017 |

The browser requests `/api/items` on the same origin as the frontend.
Docker Compose uses frontend Nginx to forward `/api/` to `backend:8000`.
Kubernetes Ingress sends `/api` directly to `backend-service:8000` and
`/` to `frontend-service:80`. The frontend Nginx image also defaults to
`backend-service`, so its API proxy works when the frontend Service is port-forwarded.

The backend uses `MONGO_DB` (default `techstock_db`) and collection `items`.
MongoDB credentials must be supplied through environment variables and are
URL-encoded when the connection URI is constructed. Connection logs omit credentials.
On an empty collection, startup seeds Dell Latitude Laptop, 24-inch Monitor,
and Mechanical Keyboard. Existing records are preserved.

| Method | Route |
| --- | --- |
| GET / POST | `/api/items` |
| PUT / DELETE | `/api/items/{item_id}` |
| PUT | `/api/items/{item_id}/quantity?action=add` or `remove` |

## Docker Compose startup

Prerequisites: Docker Engine or Docker Desktop with Compose v2.
Run these PowerShell commands from the repository root:

```powershell
Copy-Item .env.example .env
# Edit .env and replace BOTH credential placeholders with your own values.
docker compose up --build -d
docker compose ps
docker compose logs backend
```

Open **http://localhost:3000**. API documentation is at
**http://localhost:8000/docs**. Backend and MongoDB published ports are bound
to localhost for development.

`.env` is ignored by Git. Compose refuses to start if either MongoDB credential
is missing or empty. The committed `.env.example` contains placeholders only.
Use Compose dotenv quoting when a credential contains special characters
(for example, single quotes around a password containing a dollar sign).

The Compose project name is `techstock`. Containers are `techstock-mongo`,
`techstock-backend`, and `techstock-frontend`. The named volume `mongo-data`
is scoped to that project (normally `techstock_mongo-data`) and mounted at
`/data/db`.

```powershell
docker compose logs -f
docker compose down
```

Stopping with `down` preserves the volume. Do not add `--volumes` unless you
intend to delete database data. MongoDB initialization credentials apply to a
new data directory; editing environment variables does not rotate credentials
in an already initialized database. The renamed Compose project uses its own
volume; no existing volumes or records are migrated or deleted automatically.

## Local frontend development

Start the backend and database using the configured root `.env`:

```powershell
docker compose up --build -d mongo backend
Set-Location frontend
npm ci
npm run dev
```

Open the URL printed by Vite (normally http://localhost:5173).
The Vite proxy forwards `/api` to http://127.0.0.1:8000.

`VITE_API_URL` defaults to `/api`. It can also be an origin such as
`http://localhost:8000` or an API base such as `http://localhost:8000/api`.
The frontend normalizes the trailing API prefix and appends `/items` exactly
once. Production builds use `frontend/.env.production` or the Docker build
argument. This value is embedded at build time; changing an environment
variable on a running frontend container does not change its JavaScript.
No database credentials belong in frontend variables.

## CI workflow and Docker Hub

`.github/workflows/deploy.yml` runs on pushes to **main**. It:

1. Runs backend regression tests using a mocked MongoDB client.
2. Runs frontend API URL tests and ESLint.
3. Runs advisory Hadolint checks against both Dockerfiles.
4. Builds and pushes both images, tagged `latest` and the Git commit SHA.

Create your own GitHub repository and configure these Actions repository secrets:

| Secret | Value |
| --- | --- |
| `DOCKER_USERNAME` | Your Docker Hub username |
| `DOCKER_PASSWORD` | A Docker Hub access token with push permission |

Create these Docker Hub repositories under that account:

- `<DOCKER_USERNAME>/techstock-backend`
- `<DOCKER_USERNAME>/techstock-frontend`

The workflow derives the namespace from `DOCKER_USERNAME`; no personal
registry account is hardcoded. Configure your Git remote and use `main` as
the branch for CI. Public images work with the supplied Kubernetes manifests.
Private images require an image pull Secret and corresponding
`imagePullSecrets` entries in the application Deployments.

The workflow publishes images; it does **not** connect to or deploy a cluster.
Deploy explicitly using the steps below. Pushing `latest` does not restart
existing Kubernetes pods. For a repeatable release, replace `:latest` with
the published commit SHA in both application manifests before rendering them.

## Kubernetes deployment

Prerequisites:

- A working cluster and `kubectl` configured for the intended context.
- An Nginx ingress controller compatible with the manifests' `nginx` class.
- A default StorageClass with a provisioner, or a suitable pre-provisioned PV.
- Both application images published to your Docker Hub account.

All resources use namespace **techstock-ns**. Keep the generic Service,
ConfigMap, and Secret names; the references already match.

### ConfigMap and Secret

`k8s/configmap.yaml` defines `app-config`:

- `MONGO_HOST=mongo-service`
- `MONGO_DB=techstock_db`

`k8s/secrets.yaml` documents the shape of `mongo-secret`, using placeholders
under `stringData`. Both MongoDB and the backend consume its
`mongo-root-username` and `mongo-root-password` keys.

Do **not** apply `k8s/secrets.yaml` unchanged, commit real credentials to it,
or blindly apply the entire `k8s/` directory. Application image references
also contain `<DOCKER_USERNAME>`, which Kubernetes does not substitute.

Create the namespace, ConfigMap, and actual Secret explicitly. Replace the
example credential values below before running:

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl create secret generic mongo-secret --namespace techstock-ns --from-literal=mongo-root-username='YOUR_MONGO_USERNAME' --from-literal=mongo-root-password='YOUR_UNIQUE_PASSWORD' --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/mongo-statefulset.yaml
kubectl rollout status statefulset/mongo -n techstock-ns --timeout=180s
```

Supply credentials appropriate for this cluster. Changing a Secret alone
does not change a user already stored in a persistent MongoDB database.
The backend retains the original root-account connection architecture.

### Deploy application images

Replace the username below with the same account used by the workflow.
These PowerShell commands render the image placeholders in memory:

```powershell
$dockerUsername = 'YOUR_DOCKER_HUB_USERNAME'
foreach ($manifest in @('k8s/backend-deployment.yaml', 'k8s/frontend-deployment.yaml')) {
    (Get-Content -Raw $manifest).Replace('<DOCKER_USERNAME>', $dockerUsername) | kubectl apply -f -
}
kubectl apply -f k8s/ingress.yaml
kubectl rollout status deployment/backend -n techstock-ns --timeout=180s
kubectl rollout status deployment/frontend -n techstock-ns --timeout=180s
```

If you deploy a newly published `latest` image with unchanged manifests,
explicitly trigger and verify a new rollout:

```powershell
kubectl rollout restart deployment/backend deployment/frontend -n techstock-ns
kubectl rollout status deployment/backend -n techstock-ns --timeout=180s
kubectl rollout status deployment/frontend -n techstock-ns --timeout=180s
```

### Ingress

`techstock-ingress` serves **http://techstock.local**:

- `/api` -> `backend-service:8000`, preserving the path.
- `/` -> `frontend-service:80`.

Map `techstock.local` to your ingress controller's reachable address in local
DNS or your hosts file. Windows hosts file:
`C:\Windows\System32\drivers\etc\hosts`. Example entry:

```text
<INGRESS_IP> techstock.local
```

TLS is not configured. The ingress controller itself is not installed by this
repository. For a quick check without Ingress, run
`kubectl port-forward service/frontend-service 3000:80 -n techstock-ns`
and open http://localhost:3000.

### StatefulSet and persistent storage

`k8s/mongo-statefulset.yaml` contains a one-replica MongoDB StatefulSet and
the headless `mongo-service`. The `mongo-persistent-storage` claim template
requests **1Gi**, access mode **ReadWriteOnce**, mounted at `/data/db`.
The first generated PVC is `mongo-persistent-storage-mongo-0`.

No StorageClass or PV is created by these manifests. Set a suitable
`storageClassName` in the claim template if the cluster has no appropriate
default. A Pending PVC usually requires checking storage provisioning.
Persistent storage survives pod replacement; the supplied deployment does
not configure replication or backups.

### Verify resources

```powershell
kubectl get namespace techstock-ns
kubectl get deployments,statefulsets,pods,services,ingresses,pvc -n techstock-ns
kubectl get configmap app-config -n techstock-ns
kubectl get secret mongo-secret -n techstock-ns
kubectl get storageclass
kubectl get pv
kubectl describe ingress techstock-ingress -n techstock-ns
kubectl describe pvc mongo-persistent-storage-mongo-0 -n techstock-ns
kubectl logs deployment/backend -n techstock-ns
curl.exe http://techstock.local/api/items
```

## Development checks

From the repository root, with Python 3.12 available:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Set-Location frontend
npm ci
npm test
npm run lint
npm run build
```

Backend tests use a mocked MongoDB connection; they cover configuration,
credential handling, seed behavior, and existing CRUD/quantity routes.
A real Compose or Kubernetes deployment is still needed for integration checks.
