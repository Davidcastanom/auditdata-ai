import base64
import unittest

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

SAMPLE_CSV = (
    "id,nombre,ciudad,edad,horas_sueno,litros_agua,completo_reto\n"
    "1,Ana,Bogota,28,7,2.1,si\n"
    "2,Juan,bogota,31,6,1.8,no\n"
    "1,Ana,Bogota,28,7,2.1,si\n"
    "4,Maria,Medellin,,8,2.4,si\n"
    "5,Luis,Medellin,450,2,,no\n"
)


def _encode(payload: str) -> str:
    return base64.b64encode(payload.encode("utf-8")).decode("ascii")


class TestHealthEndpoint(unittest.TestCase):
    def test_root_returns_html(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_docs_available(self):
        response = client.get("/docs")
        self.assertEqual(response.status_code, 200)


class TestAnalyzeEndpoint(unittest.TestCase):
    def test_analyze_valid_csv(self):
        response = client.post(
            "/api/analyze",
            json={"filename": "test.csv", "content_base64": _encode(SAMPLE_CSV)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("analysis", data)
        self.assertEqual(data["analysis"]["row_count"], 5)
        self.assertEqual(data["analysis"]["column_count"], 7)
        self.assertEqual(data["analysis"]["duplicate_rows"], 1)

    def test_analyze_invalid_format(self):
        response = client.post(
            "/api/analyze",
            json={"filename": "test.txt", "content_base64": _encode("hello")},
        )
        self.assertEqual(response.status_code, 400)

    def test_analyze_invalid_base64(self):
        response = client.post(
            "/api/analyze",
            json={"filename": "test.csv", "content_base64": "not-valid-base64!!!"},
        )
        self.assertEqual(response.status_code, 400)


class TestCleanEndpoint(unittest.TestCase):
    def test_clean_with_actions(self):
        actions = [
            {"kind": "remove_duplicate_rows", "reason": "Eliminar duplicados"},
            {"kind": "impute_missing", "column": "edad", "method": "median", "reason": "Imputar edad"},
        ]
        response = client.post(
            "/api/clean",
            json={
                "filename": "test.csv",
                "content_base64": _encode(SAMPLE_CSV),
                "actions": actions,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cleaning", data)
        self.assertEqual(data["cleaning"]["after"]["duplicate_rows"], 0)
        self.assertEqual(len(data["cleaning"]["actions"]), 2)


class TestReportEndpoint(unittest.TestCase):
    def test_markdown_report_from_analysis(self):
        analysis_response = client.post(
            "/api/analyze",
            json={"filename": "test.csv", "content_base64": _encode(SAMPLE_CSV)},
        )
        analysis = analysis_response.json()["analysis"]

        response = client.post(
            "/api/report/markdown",
            json={"analysis": analysis, "analyst": "Test Analyst", "version": "v1.0"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("content", data)
        self.assertIn("Data Cleaning Report", data["content"])

    def test_pdf_report_from_analysis(self):
        analysis_response = client.post(
            "/api/analyze",
            json={"filename": "test.csv", "content_base64": _encode(SAMPLE_CSV)},
        )
        analysis = analysis_response.json()["analysis"]

        response = client.post(
            "/api/report/pdf",
            json={"analysis": analysis, "analyst": "Test Analyst", "version": "v1.0"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("content_base64", data)
        pdf_bytes = base64.b64decode(data["content_base64"])
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
