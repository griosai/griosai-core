from datetime import datetime, timezone
import unittest

from griosai.broker import CredentialBroker, CredentialBrokerError


class BrokerTests(unittest.TestCase):
    def test_issue_env_lease_redacts_audit_and_repr(self) -> None:
        token = "super-" + "secret-token"
        broker = CredentialBroker(environ={"SERVICE_TOKEN": token})
        lease = broker.issue_env_lease(
            secret_name="service",
            env_var="SERVICE_TOKEN",
            scopes=("service:read",),
            client_id="agent-1",
            ttl_seconds=60,
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(lease.token, token)
        self.assertNotIn(token, repr(lease))
        self.assertEqual(lease.audit_record(now=lease.issued_at)["token"], "[redacted]")
        self.assertFalse(lease.is_expired(now=lease.issued_at))

    def test_revoke_marks_lease_without_losing_metadata(self) -> None:
        broker = CredentialBroker(environ={"SERVICE_TOKEN": "super-" + "secret-token"})
        lease = broker.issue_env_lease(
            secret_name="service",
            env_var="SERVICE_TOKEN",
            scopes=("service:read",),
            client_id="agent-1",
        )

        revoked = broker.revoke(lease.lease_id)
        self.assertTrue(revoked.revoked)
        self.assertEqual(revoked.scopes, ("service:read",))

    def test_rejects_missing_secret_and_bad_ttl(self) -> None:
        broker = CredentialBroker(environ={})
        with self.assertRaises(CredentialBrokerError):
            broker.issue_env_lease(
                secret_name="service",
                env_var="SERVICE_TOKEN",
                scopes=("service:read",),
                client_id="agent-1",
            )
        with self.assertRaises(CredentialBrokerError):
            CredentialBroker(environ={"SERVICE_TOKEN": "super-" + "secret-token"}).issue_env_lease(
                secret_name="service",
                env_var="SERVICE_TOKEN",
                scopes=("service:read",),
                client_id="agent-1",
                ttl_seconds=999_999,
            )


if __name__ == "__main__":
    unittest.main()
