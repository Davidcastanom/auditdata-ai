import unittest
from data_engine.analyzer import analyze_dataset, apply_cleaning_actions


def _column_by_name(analysis, name):
    for col in analysis["columns"]:
        if col["name"] == name:
            return col
    return None

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

    def test_cleaning_actions_with_xlsx_input(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl no instalado")

        import io

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Datos"
        ws.append(["id", "nombre", "ciudad", "edad", "completo_reto"])
        ws.append([1, "Ana", "Bogota", 28, "si"])
        ws.append([2, "Juan", "bogota", 31, "no"])
        ws.append([1, "Ana", "Bogota", 28, "si"])
        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()

        actions = [
            {"kind": "remove_duplicate_rows", "reason": "Eliminar duplicados"},
            {"kind": "standardize_values", "column": "ciudad", "method": "capitalize", "reason": "Capitalizar"},
        ]
        result = apply_cleaning_actions("test_dataset.xlsx", xlsx_bytes, actions)
        self.assertIn("before", result)
        self.assertIn("after", result)
        self.assertEqual(result["after"]["duplicate_rows"], 0)
        self.assertGreater(len(result["clean_csv"]), 0)

    def test_impute_missing_no_degrada_accuracy(self):
        """CL-10: imputar la media en 'calificacion' (IQR con pocos valores) no
        debe CONVERTIR valores normales en outliers ni bajar accuracy.
        Antes del fix el after recalculaba el IQR sobre datos ya imputados y
        el 2.9 quedaba fuera del rango (outliers 0 -> 2), restando calidad."""
        import os

        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "samples", "dataset_sucio.csv")
        with open(path, "rb") as f:
            payload = f.read()
        actions = [{"kind": "impute_missing", "column": "calificacion", "method": "mean"}]
        result = apply_cleaning_actions("dataset_sucio.csv", payload, actions)
        before = _column_by_name(result["before"], "calificacion")
        after = _column_by_name(result["after"], "calificacion")
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertGreaterEqual(after["missing"], 0)
        self.assertEqual(after["missing"], 0, "los faltantes deben imputarse")
        self.assertLessEqual(after["outliers"], before["outliers"],
                             "imputar no debe convertir valores normales en outliers")
        self.assertGreaterEqual(
            result["after"]["scores"]["accuracy"],
            result["before"]["scores"]["accuracy"],
            "una accion correctiva no debe restar exactitud estructural",
        )

    def test_impute_missing_no_degrada_accuracy_telefono(self):
        """CL-10: imputar con la moda en 'telefono' tampoco debe crear outliers."""
        import os

        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "samples", "dataset_sucio.csv")
        with open(path, "rb") as f:
            payload = f.read()
        actions = [{"kind": "impute_missing", "column": "telefono", "method": "mode"}]
        result = apply_cleaning_actions("dataset_sucio.csv", payload, actions)
        before = _column_by_name(result["before"], "telefono")
        after = _column_by_name(result["after"], "telefono")
        self.assertLessEqual(after["outliers"], before["outliers"],
                             "imputar la moda no debe crear outliers nuevos")
        self.assertGreaterEqual(
            result["after"]["scores"]["accuracy"],
            result["before"]["scores"]["accuracy"],
        )


if __name__ == "__main__":
    unittest.main()
