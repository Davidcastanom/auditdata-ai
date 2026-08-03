"""Contrato de carga de archivos (F1) — FE-01/02/03/04.

Valida de extremo a extremo que el motor, el preview (detect_file_settings) y la
API producen resultados coherentes para delimitador, comillas, header y encoding.
Regla del plan R3: no romper el contrato del frontend.
"""

import base64
import unittest

from fastapi.testclient import TestClient

from backend.app.main import app
from data_engine.analyzer import (
    _load_csv,
    analyze_dataset,
    detect_file_settings,
)

client = TestClient(app)


def _encode(payload: bytes) -> str:
    return base64.b64encode(payload).decode("ascii")


# ── FE-01: delimitador real ──────────────────────────────────────────────────
def test_preview_detecta_delimitador_semicolon():
    assert detect_file_settings("v.csv", b"a;b;c\n1;2;3\n")["delimiter"] == "semicolon"


def test_preview_detecta_delimitador_tab():
    assert detect_file_settings("v.csv", b"a\tb\tc\n1\t2\t3\n")["delimiter"] == "tab"


def test_preview_detecta_delimitador_pipe():
    assert detect_file_settings("v.csv", b"a|b|c\n1|2|3\n")["delimiter"] == "pipe"


def test_preview_detecta_delimitador_comma():
    assert detect_file_settings("v.csv", b"a,b,c\n1,2,3\n")["delimiter"] == "comma"


def test_analisis_con_delimitador_tab():
    analysis = analyze_dataset("v.csv", b"a\tb\tc\n1\t2\t3\n", delimiter="tab")
    assert analysis["column_count"] == 3
    assert analysis["headers"] == ["a", "b", "c"]


def test_analisis_con_delimitador_pipe():
    analysis = analyze_dataset("v.csv", b"a|b|c\n1|2|3\n", delimiter="pipe")
    assert analysis["column_count"] == 3


def test_analisis_autodetecta_pipe_sin_preferencia():
    analysis = analyze_dataset("v.csv", b"a|b|c\n1|2|3\n")
    assert analysis["column_count"] == 3


def test_header_row_explicito_se_respeta():
    payload = b"Reporte\na,b\n1,2\n"
    _, _, header_idx = _load_csv(payload, header_row=1)
    assert header_idx == 1


def test_detect_file_settings_con_header_row_explicito():
    settings = detect_file_settings("v.csv", b"a,b,c\n1,2,3\n")
    assert settings["detected_header_row"] == 0
    assert settings["headers"] == ["a", "b", "c"]


# ── FE-02: comillas ──────────────────────────────────────────────────────────
def test_preview_no_confunde_punto_y_coma_entre_comillas():
    payload = b'id,nombre,nota\n1,Ana,"a;b;c;d;e"\n2,Luis,media\n'
    settings = detect_file_settings("v.csv", payload)
    assert settings["delimiter"] == "comma"
    assert settings["headers"] == ["id", "nombre", "nota"]
    assert settings["preview"][0]["nota"] == "a;b;c;d;e"


def test_preview_no_confunde_coma_entre_comillas():
    payload = b'id,frase\n1,"hola, mundo"\n'
    settings = detect_file_settings("v.csv", payload)
    assert settings["delimiter"] == "comma"
    assert settings["preview"][0]["frase"] == "hola, mundo"


def test_comillas_escapadas_dobles():
    payload = b'id,frase\n1,"dijo ""hola"""\n'
    settings = detect_file_settings("v.csv", payload)
    assert settings["preview"][0]["frase"] == 'dijo "hola"'


def test_campo_multilinea_entre_comillas_no_rompe_deteccion():
    payload = b'id,nombre,nota\n1,Ana,"a;b;c\nd;e"\n2,Luis,media\n'
    settings = detect_file_settings("v.csv", payload)
    assert settings["delimiter"] == "comma"
    analysis = analyze_dataset("v.csv", payload)
    assert analysis["column_count"] == 3


# ── FE-03: consistencia preview == análisis ──────────────────────────────────
CASES = [
    ("semicolon", b"id;nombre;edad\n1;Ana;25\n2;Luis;30\n"),
    ("quoted", b'id,nombre,nota\n1,Ana,"a;b;c"\n2,Luis,media\n'),
    ("tab", b"id\tnombre\n1\tAna\n"),
    ("pipe", b"id|nombre\n1|Ana\n"),
]


def test_preview_y_analisis_coinciden_en_todos_los_casos():
    for _label, payload in CASES:
        settings = detect_file_settings("v.csv", payload)
        analysis = analyze_dataset("v.csv", payload)
        assert analysis["headers"] == settings["headers"], settings["delimiter"]
        assert analysis["column_count"] == len(settings["headers"])
        preview_headers = list(settings["preview"][0]) if settings["preview"] else []
        assert preview_headers == settings["headers"]


def test_analisis_usa_el_encoding_detectado_en_preview():
    payload = "id,nombre\n1,María José\n2,José\n".encode("latin-1")
    settings = detect_file_settings("v.csv", payload)
    analysis = analyze_dataset("v.csv", payload, encoding=settings["encoding"])
    nombre = next(c for c in analysis["columns"] if c["name"] == "nombre")
    assert settings["encoding"] == "latin-1"
    assert nombre["examples"] == ["María José", "José"]


def test_utf8_bom_se_limpia_y_encoding_es_utf8():
    payload = b"\xef\xbb\xbfid,nombre\n1,Ana\n"
    settings = detect_file_settings("v.csv", payload)
    assert settings["encoding"] == "utf-8"
    assert settings["headers"] == ["id", "nombre"]


# ── API (R3: contrato) ───────────────────────────────────────────────────────
class TestFileContractAPI(unittest.TestCase):
    def test_analyze_auto_detecta_delimitador_sin_preferencia(self):
        payload = b'id,nombre,nota\n1,Ana,"a;b;c;d;e"\n2,Luis,media\n'
        response = client.post(
            "/api/analyze",
            json={"filename": "v.csv", "content_base64": _encode(payload)},
        )
        self.assertEqual(response.status_code, 200)
        analysis = response.json()["analysis"]
        self.assertEqual(analysis["column_count"], 3)
        self.assertEqual(analysis["headers"], ["id", "nombre", "nota"])
        nota = next(c for c in analysis["columns"] if c["name"] == "nota")
        self.assertEqual(nota["examples"], ["a;b;c;d;e", "media"])

    def test_analyze_respeta_header_row_explicito(self):
        payload = b"Reporte\nGenerado: hoy\nid,nombre\n1,Ana\n"
        response = client.post(
            "/api/analyze",
            json={"filename": "v.csv", "content_base64": _encode(payload), "header_row": 2},
        )
        self.assertEqual(response.status_code, 200)
        analysis = response.json()["analysis"]
        self.assertEqual(analysis["headers"], ["id", "nombre"])
        self.assertEqual(analysis["row_count"], 1)

    def test_analyze_respeta_encoding_explicito(self):
        payload = "id,nombre\n1,María\n".encode("latin-1")
        response = client.post(
            "/api/analyze",
            json={"filename": "v.csv", "content_base64": _encode(payload), "encoding": "latin-1"},
        )
        self.assertEqual(response.status_code, 200)
        analysis = response.json()["analysis"]
        nombre = next(c for c in analysis["columns"] if c["name"] == "nombre")
        self.assertEqual(nombre["examples"], ["María"])

    def test_clean_con_archivo_comillas(self):
        payload = b'id,nombre,nota\n1,Ana,"a;b;c"\n2,Luis,media\n'
        response = client.post(
            "/api/clean",
            json={
                "filename": "v.csv",
                "content_base64": _encode(payload),
                "actions": [{"kind": "delete_column", "column": "nota", "reason": "Prueba"}],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cleaning"]["after"]["headers"], ["id", "nombre"])

    def test_preview_endpoint_devuelve_mismas_headers_que_analisis(self):
        payload = b'id;nombre\n1;Ana\n2;Luis\n'
        resp_preview = client.post(
            "/api/file/preview",
            json={"filename": "v.csv", "content_base64": _encode(payload)},
        )
        self.assertEqual(resp_preview.status_code, 200)
        settings = resp_preview.json()
        resp_analyze = client.post(
            "/api/analyze",
            json={"filename": "v.csv", "content_base64": _encode(payload), "delimiter": settings["delimiter"], "encoding": settings["encoding"], "header_row": settings["detected_header_row"]},
        )
        analysis = resp_analyze.json()["analysis"]
        self.assertEqual(analysis["headers"], settings["headers"])


if __name__ == "__main__":
    unittest.main()
