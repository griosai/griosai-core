import json
import shutil
import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def local_manifests(path: Path) -> list[dict]:
    # --local bypasses API discovery and cluster contact; kubectl only parses
    # the YAML and applies an empty local patch so stdlib can inspect JSON.
    result = subprocess.run(
        ["kubectl", "patch", "--local=true", "--type=merge", "--patch={}",
         "-f", str(path), "-o", "json"],
        capture_output=True, text=True, check=True, timeout=10,
    )
    objects = []
    remaining = result.stdout.lstrip()
    while remaining:
        item, end = json.JSONDecoder().raw_decode(remaining)
        objects.extend(item["items"] if item.get("kind") == "List" else [item])
        remaining = remaining[end:].lstrip()
    return objects


class KubernetesManifestTests(unittest.TestCase):
    def test_griosai_manifests_keep_cluster_private_and_hardened(self) -> None:
        deployment = (REPO / "deploy/kubernetes/base/deployment.yaml").read_text(encoding="utf-8")
        service = (REPO / "deploy/kubernetes/base/service.yaml").read_text(encoding="utf-8")
        config = (REPO / "deploy/kubernetes/base/configmap.yaml").read_text(encoding="utf-8")
        policy = (REPO / "deploy/kubernetes/base/networkpolicy.yaml").read_text(encoding="utf-8")
        kustomization = (REPO / "deploy/kubernetes/base/kustomization.yaml").read_text(encoding="utf-8")

        self.assertIn("type: ClusterIP", service)
        self.assertNotIn("type: LoadBalancer", service)
        self.assertNotIn("type: NodePort", service)
        self.assertIn("runAsNonRoot: true", deployment)
        self.assertIn("readOnlyRootFilesystem: true", deployment)
        self.assertIn("automountServiceAccountToken: false", deployment)
        self.assertIn("drop:\n                - ALL", deployment)
        self.assertIn("value: localhost", deployment)
        self.assertIn("GRIOSAI_MLFLOW_TRACKING_URI: http://mlflow-tracking:5000", config)
        self.assertIn('GRIOSAI_MLFLOW_ALLOW_REMOTE: "true"', config)
        self.assertIn("kind: NetworkPolicy", policy)
        self.assertIn("policyTypes:\n    - Ingress\n    - Egress", policy)
        self.assertIn("port: 8765", policy)
        self.assertIn("port: 5000", policy)
        self.assertIn("port: 11434", policy)
        self.assertIn("networkpolicy.yaml", kustomization)

    def test_mlflow_manifests_are_private_and_persistent(self) -> None:
        deployment = (REPO / "deploy/kubernetes/mlflow/deployment.yaml").read_text(encoding="utf-8")
        service = (REPO / "deploy/kubernetes/mlflow/service.yaml").read_text(encoding="utf-8")
        pvc = (REPO / "deploy/kubernetes/mlflow/pvc.yaml").read_text(encoding="utf-8")
        policy = (REPO / "deploy/kubernetes/mlflow/networkpolicy.yaml").read_text(encoding="utf-8")
        kustomization = (REPO / "deploy/kubernetes/mlflow/kustomization.yaml").read_text(encoding="utf-8")
        backup = (REPO / "deploy/kubernetes/mlflow/backup-cronjob.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("type: ClusterIP", service)
        self.assertNotIn("type: LoadBalancer", service)
        self.assertIn("readOnlyRootFilesystem: true", deployment)
        self.assertIn("claimName: mlflow-tracking", deployment)
        self.assertIn("storage: 10Gi", pvc)
        self.assertIn("kind: NetworkPolicy", policy)
        self.assertIn("port: 5000", policy)
        self.assertIn("egress: []", policy)
        self.assertIn("app.kubernetes.io/name: griosai", policy)
        self.assertIn("networkpolicy.yaml", kustomization)
        self.assertNotIn("backup-cronjob.yaml", kustomization)
        self.assertIn("kind: PersistentVolumeClaim", backup)
        self.assertIn("name: mlflow-backups", backup)
        self.assertIn("kind: CronJob", backup)
        self.assertIn("name: mlflow-backup", backup)
        self.assertIn('schedule: "17 3 * * *"', backup)
        self.assertIn("concurrencyPolicy: Forbid", backup)
        self.assertIn("claimName: mlflow-tracking", backup)
        self.assertIn("claimName: mlflow-backups", backup)
        self.assertIn("automountServiceAccountToken: false", backup)
        self.assertIn("readOnlyRootFilesystem: true", backup)
        self.assertIn("allowPrivilegeEscalation: false", backup)

    @unittest.skipUnless(shutil.which("kubectl"), "Optional Kubernetes check requires kubectl")
    def test_backup_requires_actual_tracker_node_and_excludes_backup_pods(self) -> None:
        tracker = local_manifests(REPO / "deploy/kubernetes/mlflow/deployment.yaml")[0]
        resources = local_manifests(REPO / "deploy/kubernetes/mlflow/backup-cronjob.yaml")
        backup = next(item for item in resources if item["kind"] == "CronJob")
        template = backup["spec"]["jobTemplate"]["spec"]["template"]
        terms = template["spec"]["affinity"]["podAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
        self.assertEqual(len(terms), 1)
        term = terms[0]
        self.assertEqual(term["topologyKey"], "kubernetes.io/hostname")
        self.assertEqual(term["namespaces"], [tracker["metadata"]["namespace"]])
        selector = term["labelSelector"]
        self.assertEqual(selector["matchLabels"], {
            "app.kubernetes.io/name": tracker["metadata"]["name"],
            "app.kubernetes.io/part-of": "griosai",
        })
        self.assertEqual(selector["matchExpressions"], [{
            "key": "app.kubernetes.io/component", "operator": "NotIn", "values": ["backup"],
        }])

        def matches(labels):
            return all(labels.get(key) == value for key, value in selector["matchLabels"].items()) and all(
                labels.get(expression["key"]) not in expression["values"]
                for expression in selector["matchExpressions"]
            )

        self.assertTrue(matches(tracker["spec"]["template"]["metadata"]["labels"]))
        self.assertFalse(matches(template["metadata"]["labels"]))
        self.assertFalse(matches({"app.kubernetes.io/name": "unrelated", "app.kubernetes.io/part-of": "griosai"}))

    def test_containerfiles_use_non_root_users(self) -> None:
        app = (REPO / "Containerfile").read_text(encoding="utf-8")
        mlflow = (REPO / "deploy/kubernetes/mlflow/Containerfile").read_text(encoding="utf-8")

        self.assertIn("USER 10001:10001", app)
        self.assertIn("USER 10001:10001", mlflow)
        self.assertIn("ENV GRIOSAI_HOST=127.0.0.1", app)
        self.assertIn('CMD ["--help"]', app)
        self.assertNotIn("ENV GRIOSAI_HOST=0.0.0.0", app)
        self.assertIn("mlflow==${MLFLOW_VERSION}", mlflow)


class BackupScriptTests(unittest.TestCase):
    def _run(self, python_body: str) -> tuple[int, Path]:
        import os
        import tempfile
        import textwrap

        text = (REPO / "deploy/kubernetes/mlflow/backup-cronjob.yaml").read_text(
            encoding="utf-8"
        )
        block = text.split("- |\n", 1)[1].split("              env:", 1)[0]
        script = textwrap.dedent(block)
        tmp = Path(tempfile.mkdtemp())
        (tmp / "backups" / "old").mkdir(parents=True)
        os.utime(tmp / "backups" / "old", (1, 1))
        (tmp / "mlflow").mkdir()
        (tmp / "bin").mkdir()
        py = tmp / "bin" / "python"
        py.write_text(python_body)
        py.chmod(0o755)
        script = script.replace("/backups", str(tmp / "backups")).replace(
            "/mlflow", str(tmp / "mlflow")
        )
        env = {"PATH": f"{tmp / 'bin'}:/usr/bin:/bin", "BACKUP_RETENTION_DAYS": "1"}
        proc = subprocess.run(
            ["/bin/sh", "-c", script], env=env, capture_output=True, text=True
        )
        return proc.returncode, tmp / "backups"

    def test_failed_backup_still_prunes_cleans_partial_and_exits_nonzero(self) -> None:
        rc, backups = self._run("#!/bin/sh\nexit 1\n")
        self.assertNotEqual(rc, 0)
        self.assertEqual([p.name for p in backups.iterdir()], [])

    def test_successful_backup_prunes_old_and_exits_zero(self) -> None:
        rc, backups = self._run("#!/bin/sh\nexit 0\n")
        self.assertEqual(rc, 0)
        self.assertEqual(len(list(backups.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
