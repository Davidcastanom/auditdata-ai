"""Characterization tests — capture CURRENT behavior of the analyzer engine.

These tests document "as-is" behavior BEFORE any changes in the correction plan.
They serve as a safety net: if a future change breaks expected behavior, these fail.
"""

import unittest
from data_engine.analyzer import (
    analyze_dataset,
    _count_duplicate_rows,
    _profile_column,
    _add_numeric_stats,
    ColumnProfile,
)


class TestCharacterizationMoveupSample(unittest.TestCase):
    """Behavior snapshot for samples/moveup_sample.csv — 5 data rows."""

    @classmethod
    def setUpClass(cls):
        with open("samples/moveup_sample.csv", "rb") as f:
            cls.payload = f.read()
        cls.analysis = analyze_dataset("moveup_sample.csv", cls.payload)

    def test_row_count(self):
        self.assertEqual(self.analysis["row_count"], 5)

    def test_column_count(self):
        self.assertEqual(self.analysis["column_count"], 7)

    def test_headers(self):
        self.assertEqual(
            self.analysis["headers"],
            ["id", "nombre", "ciudad", "edad", "horas_sueno", "litros_agua", "completo_reto"],
        )

    def test_duplicate_rows_full_comparison(self):
        """Ana rows differ by ID (1 vs 3), so full-row comparison = 0 duplicates."""
        self.assertEqual(self.analysis["duplicate_rows"], 0)

    def test_scores_keys(self):
        expected = {"completeness", "consistency", "accuracy", "uniqueness", "overall"}
        self.assertEqual(set(self.analysis["scores"].keys()), expected)

    def test_scores_are_percentages(self):
        for key, val in self.analysis["scores"].items():
            self.assertGreaterEqual(val, 0, f"Score {key} < 0")
            self.assertLessEqual(val, 100, f"Score {key} > 100")

    def test_columns_count_matches_headers(self):
        self.assertEqual(len(self.analysis["columns"]), len(self.analysis["headers"]))

    def test_each_column_has_required_fields(self):
        required = {"name", "detected_type", "total_rows", "missing", "unique_values"}
        for col in self.analysis["columns"]:
            for field in required:
                self.assertIn(field, col, f"Column {col.get('name')} missing '{field}'")

    def test_id_column_type(self):
        id_col = self.analysis["columns"][0]
        self.assertEqual(id_col["name"], "id")
        self.assertEqual(id_col["detected_type"], "number")

    def test_edad_outlier(self):
        """edad=450 with only 4 numeric values: IQR range is wide, so 450 is within bounds."""
        edad_col = [c for c in self.analysis["columns"] if c["name"] == "edad"][0]
        self.assertEqual(edad_col["outliers"], 0, "Only 4 numeric values → IQR range too wide to flag 450")

    def test_preview_length(self):
        self.assertEqual(len(self.analysis["preview"]), 5)

    def test_recommendations_exist(self):
        self.assertIsInstance(self.analysis["recommendations"], list)
        self.assertGreater(len(self.analysis["recommendations"]), 0)


class TestCharacterizationDatasetSucio(unittest.TestCase):
    """Behavior snapshot for samples/dataset_sucio.csv — 25 rows."""

    @classmethod
    def setUpClass(cls):
        with open("samples/dataset_sucio.csv", "rb") as f:
            cls.payload = f.read()
        cls.analysis = analyze_dataset("dataset_sucio.csv", cls.payload)

    def test_row_count(self):
        self.assertEqual(self.analysis["row_count"], 25)

    def test_column_count(self):
        self.assertEqual(self.analysis["column_count"], 12)

    def test_duplicate_rows(self):
        """Full-row duplicates: some similar rows differ in encoding/case → 0 full-row dupes."""
        self.assertEqual(self.analysis["duplicate_rows"], 0)

    def test_nombre_format_issues(self):
        nombre_col = [c for c in self.analysis["columns"] if c["name"] == "nombre"][0]
        self.assertGreater(nombre_col["format_issues"], 0)

    def test_salario_has_outliers(self):
        salario_col = [c for c in self.analysis["columns"] if c["name"] == "salario"][0]
        self.assertGreater(salario_col["outliers"], 0)


class TestCharacterizationCountDuplicates(unittest.TestCase):
    """Document _count_duplicate_rows baseline behavior."""

    def test_full_row_comparison_returns_0_for_unique_rows(self):
        headers = ["a", "b"]
        rows = [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
        self.assertEqual(_count_duplicate_rows(headers, rows), 0)

    def test_full_row_comparison_detects_duplicates(self):
        headers = ["a", "b"]
        rows = [
            {"a": "1", "b": "x"},
            {"a": "1", "b": "x"},
            {"a": "2", "b": "y"},
        ]
        self.assertEqual(_count_duplicate_rows(headers, rows), 1)

    def test_whitespace_and_case_normalized(self):
        """Firma unificada (DU-01): strip + lower + sin acentos.
        'Hello', 'hello' y ' Hello ' normalizan a 'hello' → 2 duplicados.
        """
        headers = ["a"]
        rows = [{"a": "Hello"}, {"a": "hello"}, {"a": " Hello "}]
        self.assertEqual(_count_duplicate_rows(headers, rows), 2)

    def test_empty_values_are_duplicates(self):
        headers = ["a"]
        rows = [{"a": ""}, {"a": ""}]
        self.assertEqual(_count_duplicate_rows(headers, rows), 1)

    def test_key_columns_none_uses_full_row_normalized(self):
        """Con key_columns=None, comparación full-row normalizada (DU-01):
        'Ana' vs 'ana' ahora son duplicados (antes case-sensitive → 0).
        """
        headers = ["id", "name"]
        rows = [
            {"id": "1", "name": "Ana"},
            {"id": "1", "name": "ana"},
        ]
        self.assertEqual(_count_duplicate_rows(headers, rows), 1)
        self.assertEqual(_count_duplicate_rows(headers, rows, key_columns=None), 1)


class TestCharacterizationProfileColumn(unittest.TestCase):
    """Document _profile_column baseline behavior."""

    def test_numeric_column(self):
        rows = [{"col": "10"}, {"col": "20"}, {"col": "30"}, {"col": "40"}]
        profile = _profile_column("col", rows)
        self.assertEqual(profile.detected_type, "number")
        self.assertEqual(profile.missing, 0)
        self.assertEqual(profile.min_value, 10.0)
        self.assertEqual(profile.max_value, 40.0)

    def test_text_column_with_missing(self):
        rows = [{"col": "a"}, {"col": "b"}, {"col": ""}, {"col": "na"}]
        profile = _profile_column("col", rows)
        self.assertEqual(profile.detected_type, "text")
        self.assertEqual(profile.missing, 2)

    def test_outlier_analysis_skipped_flag_exists(self):
        """Fase 3: outlier_analysis_skipped now exists on ColumnProfile."""
        rows = [{"col": "1"}, {"col": "2"}]
        profile = _profile_column("col", rows)
        self.assertTrue(hasattr(profile, "outlier_analysis_skipped"))
        self.assertTrue(profile.outlier_analysis_skipped)

    def test_invalid_type_count_exists(self):
        """Fase 2+3: invalid_type_count now exists on ColumnProfile."""
        rows = [{"col": "1"}, {"col": "2"}, {"col": "3"}, {"col": "tres"}]
        profile = _profile_column("col", rows)
        self.assertTrue(hasattr(profile, "invalid_type_count"))
        self.assertEqual(profile.invalid_type_count, 1)


class TestCharacterizationAddNumericStats(unittest.TestCase):
    """Document _add_numeric_stats baseline behavior."""

    def test_outlier_detection_with_enough_values(self):
        profile = ColumnProfile(name="test", detected_type="number", total_rows=10, missing=0, unique_values=10)
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 100.0]
        _add_numeric_stats(profile, values)
        self.assertGreater(profile.outliers, 0)

    def test_silently_returns_with_few_values(self):
        """Fase 3: outlier_analysis_skipped=True when len < 4, outliers=0."""
        profile = ColumnProfile(name="test", detected_type="number", total_rows=2, missing=0, unique_values=2)
        values = [1.0, 2.0]
        _add_numeric_stats(profile, values)
        self.assertEqual(profile.outliers, 0)
        self.assertTrue(profile.outlier_analysis_skipped)

    def test_missing_min_max_for_empty_values(self):
        profile = ColumnProfile(name="test", detected_type="number", total_rows=0, missing=0, unique_values=0)
        _add_numeric_stats(profile, [])
        self.assertIsNone(profile.min_value)
        self.assertIsNone(profile.max_value)


class TestKeyColumnsFeature(unittest.TestCase):
    """Fase 1: key_columns for configurable duplicate detection."""

    def test_key_columns_none_preserves_legacy_behavior(self):
        headers = ["a", "b"]
        rows = [{"a": "1", "b": "x"}, {"a": "1", "b": "x"}]
        self.assertEqual(_count_duplicate_rows(headers, rows, key_columns=None), 1)

    def test_key_columns_single_column_detects_duplicates(self):
        headers = ["id", "name"]
        rows = [
            {"id": "1", "name": "Ana"},
            {"id": "1", "name": "ana"},
        ]
        self.assertEqual(_count_duplicate_rows(headers, rows, key_columns=["id"]), 1)

    def test_key_columns_normalizes_case_and_accents(self):
        headers = ["id", "name"]
        rows = [
            {"id": "1", "name": "Sofía"},
            {"id": "1", "name": "sofia"},
            {"id": "1", "name": "SOFIA"},
        ]
        self.assertEqual(_count_duplicate_rows(headers, rows, key_columns=["name"]), 2)

    def test_key_columns_different_ids_not_duplicates(self):
        headers = ["id", "name"]
        rows = [
            {"id": "1", "name": "Ana"},
            {"id": "2", "name": "Ana"},
        ]
        self.assertEqual(_count_duplicate_rows(headers, rows, key_columns=["id"]), 0)

    def test_key_columns_with_dataset_sucio(self):
        with open("samples/dataset_sucio.csv", "rb") as f:
            payload = f.read()
        from data_engine.analyzer import load_dataset
        headers, rows, _ = load_dataset("dataset_sucio.csv", payload)
        dupes_full = _count_duplicate_rows(headers, rows)
        dupes_email = _count_duplicate_rows(headers, rows, key_columns=["email"])
        self.assertGreaterEqual(dupes_email, dupes_full)

    def test_analyze_dataset_with_key_columns(self):
        with open("samples/dataset_sucio.csv", "rb") as f:
            payload = f.read()
        analysis_full = analyze_dataset("dataset_sucio.csv", payload)
        analysis_key = analyze_dataset("dataset_sucio.csv", payload, duplicate_key_columns=["email"])
        self.assertEqual(analysis_full["duplicate_rows"], 0)
        self.assertNotEqual(analysis_full["duplicate_rows"], analysis_key["duplicate_rows"])


if __name__ == "__main__":
    unittest.main()
