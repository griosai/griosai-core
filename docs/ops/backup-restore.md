# Backup And Restore

GriosAI stores the brain as plain files. The `backup` and `restore` commands
turn that vault into a portable zip archive with a signed-by-hash manifest, then
restore it without allowing path traversal, symlink entries, or accidental
clobbering.

## Create A Backup

```bash
griosai backup --vault ~/GriosAI-vault --output ~/Backups
```

If `--output` is a directory, GriosAI writes a timestamped
`griosai-vault-<timestamp>.zip` inside it. If the exact output file already
exists, the command allocates a unique filename unless `--overwrite` is set.
The output archive must be outside the selected vault.

The archive includes files under the standard vault directories:

- `notes/`
- `dashboards/`
- `images/`
- `inbox/`
- `lineage/`
- `notebook-packets/`
- `agent-runs/`

Symlinks are skipped so a backup cannot silently capture files outside the
selected vault.

## Restore A Backup

Verify an archive without restoring it:

```bash
griosai verify-backup ~/Backups/griosai-vault-20260530T120000Z.zip
```

The command reads every archived file and verifies the manifest hashes.

```bash
griosai restore ~/Backups/griosai-vault-20260530T120000Z.zip \
  --vault ~/GriosAI-vault-restored
```

Restore fails if a target file already exists. To replace existing files:

```bash
griosai restore ~/Backups/griosai-vault-20260530T120000Z.zip \
  --vault ~/GriosAI-vault-restored \
  --overwrite
```

## Safety Checks

During restore, GriosAI verifies:

- the backup manifest schema
- every file path is relative and inside the expected vault layout
- no zip entry is a symlink
- no unexpected zip entries exist
- every file size matches the manifest
- every file SHA-256 digest matches the manifest
- existing files are not replaced unless `--overwrite` is set

`griosai verify-backup` performs the archive and digest checks without writing
to a vault.

Backups can contain private notes, images, dashboards, lineage metadata, and
agent experiment metadata. Keep backup archives out of git, cloud sync folders,
and public issue attachments unless they are explicitly reviewed and sanitized.

## MLflow Tracker State

The `griosai backup`/`restore` commands cover the GriosAI vault only. They do
not back up the optional Kubernetes MLflow tracker, which keeps its own durable
state on the `mlflow-tracking` PVC:

- `/mlflow/mlflow.db` — the SQLite backend store (experiments, runs, metrics,
  params, tags)
- `/mlflow/artifacts/` — run artifacts under the default artifact root

Both must be backed up together; a `mlflow.db` snapshot without its matching
artifacts (or vice versa) restores an inconsistent tracker.

### Scheduled Backup CronJob

The recommended path is the opt-in CronJob at
`deploy/kubernetes/mlflow/backup-cronjob.yaml` (see
[kubernetes-mlflow.md](kubernetes-mlflow.md)). Apply it after the tracker is up:

```bash
kubectl apply -f deploy/kubernetes/mlflow/backup-cronjob.yaml
```

It writes timestamped backups to a separate `mlflow-backups` PVC: a consistent
`mlflow.db` (via the SQLite `.backup` command) plus an `artifacts.tar.gz`. To
copy a backup off-cluster, stream it from the PVC, for example:

```bash
POD="$(kubectl -n griosai get pods \
  -l app.kubernetes.io/component=backup -o name | head -n1)"
# Or run a short-lived pod that mounts the mlflow-backups PVC, then:
kubectl -n griosai cp "<backup-pod>:/backups/<timestamp>" ./mlflow-backup
```

### Manual Online Backup

Without the CronJob you can take a one-off backup against the running tracker by
running a short-lived pod (or `kubectl exec` into the tracker) that reads the
PVC:

```bash
# Inside a pod that mounts the mlflow-tracking PVC read-write at /mlflow
# (python and its sqlite3 module ship in the tracker image):
python -c 'import sqlite3; s=sqlite3.connect("/mlflow/mlflow.db"); o=sqlite3.connect("/backups/mlflow.db"); s.backup(o); o.close(); s.close()'
tar -czf /backups/artifacts.tar.gz -C /mlflow artifacts
```

The SQLite online backup API yields a single consistent file even while MLflow
keeps writing. MLflow runs the database in WAL mode, so the source must be
opened read-write (the backup touches the `-wal`/`-shm` sidecars); it only reads
committed state and does not modify MLflow data. Do not copy `mlflow.db` with
`cp` while the server is running; that can capture a torn write, and copying the
main DB file without its WAL loses the most recent committed transactions.

### Restore

1. Scale the tracker down so nothing writes during the restore:
   `kubectl -n griosai scale deployment/mlflow-tracking --replicas=0`.
2. Mount the `mlflow-tracking` PVC in a short-lived pod and replace state:
   copy the backed-up `mlflow.db` to `/mlflow/mlflow.db` and extract
   `artifacts.tar.gz` into `/mlflow` (restoring the `artifacts/` tree).
3. Scale the tracker back up:
   `kubectl -n griosai scale deployment/mlflow-tracking --replicas=1`.

Restore `mlflow.db` and `artifacts/` from the same backup timestamp so run rows
and their artifact paths stay consistent.

### VolumeSnapshot Alternative

If your storage class supports the CSI snapshot API, you can schedule
`VolumeSnapshot` resources against the `mlflow-tracking` PVC instead of the
file-level CronJob. Snapshots are crash-consistent at the block level; for an
application-consistent SQLite snapshot, briefly scale the tracker to zero (or
quiesce writes) before taking the snapshot. Restore by provisioning a new PVC
from the `VolumeSnapshot` and pointing the tracker at it.

MLflow backups can contain experiment names, run metadata, and any logged
artifacts. Treat them with the same handling rules as vault backups above:
keep them out of git, cloud sync folders, and public attachments unless
reviewed and sanitized.
