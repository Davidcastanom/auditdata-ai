import unittest
from data_engine.analyzer import analyze_dataset, apply_cleaning_actions

class TestDataEngine(unittest.TestCase):
    def setUp(self):
        self.sample_csv = (
            "id,nombre,ciudad,edad,horas_sueno,litros_agua,completo_reto\n"
            "1,Ana,Bogota,28,7,2.1,si\n"
            "2,Juan,bogota,31,6,1.8,no\n"
            "1,Ana,Bogota,28,7,2.1,si\n"
            "4,Maria,Medellin,,8,2.4,si\n"
            "5,Luis,Medellin,450,2,,no\n"
        ).encode("utf-8")
        self.filename = "test_dataset.csv"

    def test_analyze_dataset(self):
        analysis = analyze_dataset(self.filename, self.sample_csv)
        self.assertEqual(analysis["row_count"], 5)
        self.assertEqual(analysis["column_count"], 7)
        self.assertEqual(analysis["duplicate_rows"], 1)
        self.assertIn("nombre", analysis["headers"])

    def test_cleaning_actions(self):
        actions = [
            {"kind": "remove_duplicate_rows", "reason": "Eliminar duplicados completos"},
            {"kind": "impute_missing", "column": "edad", "method": "median", "reason": "Imputar edad faltante"},
        ]
        result = apply_cleaning_actions(self.filename, self.sample_csv, actions)
        self.assertIn("before", result)
        self.assertIn("after", result)
        self.assertEqual(result["after"]["duplicate_rows"], 0)

if __name__ == "__main__":
    unittest.main()
