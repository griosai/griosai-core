import unittest

from griosai.privacy import SECRET_REDACTION, contains_likely_secret, redact_likely_secrets


class PrivacyTests(unittest.TestCase):
    def test_redacts_project_style_keys_assignments_and_bearer_tokens(self) -> None:
        project_key = "sk-proj-" + ("P" * 24)
        text = redact_likely_secrets(
            f"key={project_key} token={'a' * 24} Authorization: Bearer abcdefghijk"
        )

        self.assertNotIn(project_key, text)
        self.assertNotIn("a" * 24, text)
        self.assertNotIn("abcdefghijk", text)
        self.assertIn(SECRET_REDACTION, text)

    def test_detects_likely_secrets_without_flagging_plain_text(self) -> None:
        self.assertTrue(contains_likely_secret("sk-proj-" + ("K" * 24)))
        self.assertFalse(contains_likely_secret("local dashboard metadata only"))


if __name__ == "__main__":
    unittest.main()
