import io
import json
import unittest
from contextlib import redirect_stdout

from griosai.cli import main
from griosai.openapi import OPENAPI_PATH, openapi_json, openapi_spec


EXPECTED_PATHS = {
    "/api/health",
    "/api/notes",
    "/api/dashboards",
    "/api/openapi.json",
    "/dashboards/{file}",
    "/api/analyze-image",
}


class OpenApiTests(unittest.TestCase):
    def test_openapi_contract_has_expected_paths_and_security(self) -> None:
        spec = openapi_spec()

        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertEqual(set(spec["paths"].keys()), EXPECTED_PATHS)
        self.assertEqual(OPENAPI_PATH, "/api/openapi.json")
        self.assertIn("bearerAuth", spec["components"]["securitySchemes"])
        self.assertEqual(
            spec["paths"]["/api/analyze-image"]["post"]["security"],
            [{"bearerAuth": []}],
        )
        self.assertIn(
            "AnalyzeImageRequest",
            spec["components"]["schemas"],
        )
        self.assertIn(
            "500",
            spec["paths"]["/api/analyze-image"]["post"]["responses"],
        )
        dashboard_schema = spec["components"]["schemas"]["DashboardSummary"]
        self.assertEqual(dashboard_schema["required"], ["name", "url"])
        self.assertIn("url", dashboard_schema["properties"])
        self.assertNotIn("updated_at", dashboard_schema["properties"])

    def test_openapi_json_is_stable_and_round_trips(self) -> None:
        encoded = openapi_json()
        parsed = json.loads(encoded)

        self.assertEqual(parsed, openapi_spec())
        self.assertEqual(encoded, openapi_json())

    def test_cli_openapi_prints_contract(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["openapi"]), 0)

        parsed = json.loads(output.getvalue())
        self.assertEqual(set(parsed["paths"].keys()), EXPECTED_PATHS)

    def test_openapi_spec_is_not_mutated_by_callers(self) -> None:
        first = openapi_spec()
        first["paths"].clear()

        self.assertEqual(set(openapi_spec()["paths"].keys()), EXPECTED_PATHS)


if __name__ == "__main__":
    unittest.main()
