import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


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

    def test_containerfiles_use_non_root_users(self) -> None:
        app = (REPO / "Containerfile").read_text(encoding="utf-8")
        mlflow = (REPO / "deploy/kubernetes/mlflow/Containerfile").read_text(encoding="utf-8")

        self.assertIn("USER 10001:10001", app)
        self.assertIn("USER 10001:10001", mlflow)
        self.assertIn("ENV GRIOSAI_HOST=127.0.0.1", app)
        self.assertIn('CMD ["--help"]', app)
        self.assertNotIn("ENV GRIOSAI_HOST=0.0.0.0", app)
        self.assertIn("mlflow==${MLFLOW_VERSION}", mlflow)


if __name__ == "__main__":
    unittest.main()
