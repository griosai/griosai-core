# Kubernetes And MLflow Ops

This is the open-source ops lane for GriosAI. It keeps the default app private,
containerized, persistent, and observable without making Kubernetes or MLflow a
hard requirement for local development.

## Design

- GriosAI runs from `Containerfile` as UID/GID `10001`.
- The root container image prints CLI help by default. Kubernetes explicitly
  passes `serve --host 0.0.0.0` behind a private `ClusterIP` Service; local
  Docker runs should publish `127.0.0.1:8765:8765` and make any broad
  in-container bind explicit.
- The vault lives on a PVC mounted at `/data/vault`.
- The app service is `ClusterIP` only.
- The app pod uses non-root execution, read-only root filesystem, dropped Linux
  capabilities, no service-account token mount, and HTTP health probes.
- NetworkPolicies keep GriosAI ingress namespace-private and restrict egress to
  DNS plus same-namespace MLflow/Ollama ports when the cluster CNI enforces
  NetworkPolicy.
- MLflow tracking uses the REST API through `src/griosai/mlflow_client.py`.
- MLflow payloads are metadata-only: stable `analysis_id`, counts, slug, model
  label, timestamps, and safe source image basename.

## Build Images

Build the app image:

```bash
docker build -f Containerfile -t ghcr.io/gustavorios/griosai:0.1.0 .
```

Build the optional single-node OSS MLflow tracker image:

```bash
docker build \
  -f deploy/kubernetes/mlflow/Containerfile \
  -t ghcr.io/gustavorios/griosai-mlflow:3.1.0 \
  deploy/kubernetes/mlflow
```

For a remote cluster, push both images to a registry the cluster can pull from
or override the image names with `kubectl set image` after applying manifests.
For a local `kind` or `minikube` cluster, load the images directly with that
tool's image-loading command.

## App Deployment

Create a stable mutation token before deployment when you want pod restarts to
preserve the same mutation API credential:

```bash
kubectl create namespace griosai
kubectl -n griosai create secret generic griosai-api \
  --from-literal=GRIOSAI_API_TOKEN="$(openssl rand -base64 32)"
```

Apply the app manifests:

```bash
kubectl apply -k deploy/kubernetes/base
kubectl -n griosai rollout status deployment/griosai
kubectl -n griosai get pods,svc,pvc
```

Open the private service from your workstation:

```bash
kubectl -n griosai port-forward svc/griosai 8765:8765
```

Then open `http://127.0.0.1:8765`.

## Optional MLflow Tracking Server

Apply the private MLflow tracker:

```bash
kubectl apply -k deploy/kubernetes/mlflow
kubectl -n griosai rollout status deployment/mlflow-tracking
```

The base GriosAI ConfigMap points to `http://mlflow-tracking:5000` and sets
`GRIOSAI_MLFLOW_ALLOW_REMOTE=true` because cluster DNS is intentionally not a
localhost URI. The Service remains `ClusterIP`; do not expose this MLflow server
with a public LoadBalancer or public Ingress unless you add authentication,
TLS, and network policy first.

The included MLflow NetworkPolicy allows ingress only from the GriosAI dashboard
pod on TCP `5000` and denies MLflow egress by default. If you move MLflow to an
external database or object store, add reviewed egress rules for those
destinations.

### Authentication Posture

The bundled MLflow tracker runs with **no authentication**. Its `mlflow server`
process does not validate any credential, so a bearer token sent directly to
`http://mlflow-tracking:5000` is silently ignored. The only access controls are:

- the `ClusterIP`-only Service (no NodePort, LoadBalancer, or Ingress), and
- the `mlflow-tracking-private` NetworkPolicy, which permits ingress only from
  the GriosAI dashboard pod and denies MLflow egress by default.

Because the in-cluster server has no auth, the base dashboard Deployment does
**not** inject `GRIOSAI_MLFLOW_TRACKING_TOKEN`; sending a token to the bundled
server would be dead plumbing. The client-side bearer-token path
(`griosai mlflow-log --tracking-token`, or the `GRIOSAI_MLFLOW_TRACKING_TOKEN`
environment variable) is preserved only for the case where you point
`GRIOSAI_MLFLOW_TRACKING_URI` at an **external** MLflow that is fronted by an
authenticating reverse proxy. To add real auth in-cluster, put an
authenticating proxy in front of MLflow (for example an OAuth2/basic-auth
sidecar or gateway), wire the matching token into the dashboard via a
`griosai-mlflow` secret, and only then expose the proxy. Treat any such change
as a separate, reviewed step.

To inspect runs from your workstation:

```bash
kubectl -n griosai port-forward svc/mlflow-tracking 5000:5000
```

Then open `http://127.0.0.1:5000`.

To log a sample from your workstation through the port-forward:

```bash
GRIOSAI_MLFLOW_TRACKING_URI=http://127.0.0.1:5000 \
  griosai mlflow-log --json-file ./examples/sample-analysis.json
```

The returned `analysis_id` matches the local lineage manifest for the same
analysis content, so the MLflow run can be correlated with vault artifacts
without uploading raw note or dashboard content.

## Optional MLflow Backups

The bundled tracker keeps all durable state on the `mlflow-tracking` PVC: the
SQLite backend store at `/mlflow/mlflow.db` and run artifacts under
`/mlflow/artifacts`. That PVC is not backed up by default.

An opt-in backup CronJob lives at
`deploy/kubernetes/mlflow/backup-cronjob.yaml` and is intentionally left out of
the default `kustomization.yaml`. Apply it explicitly once the tracker is up:

```bash
kubectl apply -f deploy/kubernetes/mlflow/backup-cronjob.yaml
```

It runs daily, takes a consistent online copy of `mlflow.db` with the SQLite
online backup API (safe while MLflow is writing), tars `/mlflow/artifacts`, and
writes both to a separate `mlflow-backups` PVC under a timestamped directory,
pruning copies older than `BACKUP_RETENTION_DAYS`. The `mlflow-tracking` PVC is
mounted read-write in the backup pod because MLflow runs the database in WAL
mode and the online backup API must touch the WAL sidecars to read a consistent
snapshot; the backup only reads committed state and does not modify MLflow data.
Because both PVCs are `ReadWriteOnce`, the backup Job and the tracker land on
the same node; with `replicas: 1` that is the normal case.

For details on restoring `mlflow.db` and artifacts, and for the
`VolumeSnapshot` alternative when your storage class supports the CSI snapshot
API, see [backup-restore.md](backup-restore.md).

## Production Notes

The included MLflow tracker uses SQLite and a PVC-backed artifact directory.
That is fine for a private lab and early development, but it is not a highly
available production tracker. Before using it as durable shared infrastructure,
move MLflow to an external database and object store, add authentication, keep
the service private, and back up the artifact store.

Keep public exposure as a separate, reviewed change. The checked-in manifests
intentionally avoid `NodePort`, `LoadBalancer`, and public ingress resources.
NetworkPolicy enforcement depends on the cluster network plugin; verify your
cluster CNI supports it before treating policies as a boundary.
