# Kubernetes And MLflow Ops

This is the open-source ops lane for GriosAI. It keeps the default app private,
containerized, persistent, and observable without making Kubernetes or MLflow a
hard requirement for local development.

## Design

- GriosAI runs from `Containerfile` as UID/GID `10001`.
- The vault lives on a PVC mounted at `/data/vault`.
- The app service is `ClusterIP` only.
- The app pod uses non-root execution, read-only root filesystem, dropped Linux
  capabilities, no service-account token mount, and HTTP health probes.
- NetworkPolicies keep GriosAI ingress namespace-private and restrict egress to
  DNS plus same-namespace MLflow/Ollama ports when the cluster CNI enforces
  NetworkPolicy.
- MLflow tracking uses the REST API through `src/griosai/mlflow_client.py`.
- MLflow payloads are metadata-only: counts, slug, model label, timestamps, and
  safe source image basename.

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
