import unittest

from griosai.url_safety import is_loopback_host, is_loopback_url, parse_http_url


class UrlSafetyTests(unittest.TestCase):
    def test_parse_http_url_accepts_clean_http_urls(self) -> None:
        parsed = parse_http_url("http://127.0.0.1:8765", field_name="Test URL")

        self.assertEqual(parsed.hostname, "127.0.0.1")
        self.assertEqual(parsed.port, 8765)

    def test_parse_http_url_rejects_unsafe_components(self) -> None:
        for value in (
            "ftp://127.0.0.1:8765",
            "http://user:pass@127.0.0.1:8765",
            "http://127.0.0.1:8765?token=abc",
            "http://127.0.0.1:8765#fragment",
            "http://127.0.0.1:bad",
            "http://127.0.0.1:8765/with space",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_http_url(value, field_name="Test URL")

    def test_loopback_detection_accepts_localhost_ipv4_and_ipv6(self) -> None:
        self.assertTrue(is_loopback_host("localhost"))
        self.assertTrue(is_loopback_host("127.0.0.1"))
        self.assertTrue(is_loopback_host("::1"))
        self.assertTrue(is_loopback_url("http://[::1]:8765"))
        self.assertFalse(is_loopback_host("example.com"))


if __name__ == "__main__":
    unittest.main()
