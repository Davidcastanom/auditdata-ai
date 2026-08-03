"""Golden tests — Algoritmo de análisis y limpieza (TS-02).

Especificación del comportamiento OBJETIVO definido en
`docs/DIAGNOSTICO_ALGORITMO_ANALISIS_LIMPIEZA.md` (sección 9, tabla de casos).

Misma convención que test_golden_motor.py: `xfail(strict=True)` con ID de
hallazgo en `reason`; los tests sin marcador son regresión de comportamiento
correcto actual.
"""

import pytest

from data_engine.analyzer import (
    _profile_column,
    _to_float,
    analyze_dataset,
    apply_cleaning_actions,
    load_dataset,
)


def _clean_values(result: dict, column: str) -> list:
    _headers, rows, _ = load_dataset("x.csv", result["clean_csv"].encode("utf-8"))
    return [row.get(column, "") for row in rows]


# ── Caso 1: CSV con delimitador ';' ───────────────────────────────────────────
def test_csv_punto_y_coma_se_analiza_correctamente():
    """FE-01: un CSV con ';' no debe terminar como 1 sola columna."""
    payload = b"id;nombre;edad\n1;Ana;25\n2;Luis;30\n3;Carlos;35\n"
    analysis = analyze_dataset("ventas.csv", payload)
    assert analysis["column_count"] == 3
    assert analysis["headers"] == ["id", "nombre", "edad"]


# ── Caso 1b: delimitador respetando comillas (FE-02) ─────────────────────────
def test_delimitador_respeta_campos_entre_comillas():
    """FE-02: ';' dentro de un campo entre comillas no debe elegirse como
    delimitador, y el valor debe conservarse completo."""
    payload = b'id,nombre,nota\n1,Ana,"a;b;c;d;e"\n2,Luis,media\n'
    analysis = analyze_dataset("q.csv", payload)
    assert analysis["column_count"] == 3
    assert analysis["headers"] == ["id", "nombre", "nota"]
    nota = next(c for c in analysis["columns"] if c["name"] == "nota")
    assert nota["examples"] == ["a;b;c;d;e", "media"]


# ── Caso 2: miles no se confunden con decimales ───────────────────────────────
def test_miles_no_se_confunden_con_decimales():
    """AP-01: 45,000 / 1,234 / 3,000 son miles. Media = 16411.3333."""
    rows = [{"salario": "45,000"}, {"salario": "1,234"}, {"salario": "3,000"}]
    profile = _profile_column("salario", rows)
    expected = round((45000 + 1234 + 3000) / 3, 4)
    assert profile.mean == expected


def test_decimales_con_coma_espanol():
    """AP-01: '3,5' / '12,25' usan la coma como decimal."""
    rows = [{"precio": "3,5"}, {"precio": "12,25"}, {"precio": "1,75"}]
    profile = _profile_column("precio", rows)
    assert profile.mean == round((3.5 + 12.25 + 1.75) / 3, 4)


def test_ambos_separadores_ultimo_es_decimal():
    """AP-01: '1,234.56' y '1.234,56' usan el último separador como decimal."""
    assert _to_float("1,234.56") == 1234.56
    assert _to_float("1.234,56") == 1234.56


def test_puntos_como_separador_de_miles():
    """AP-01: '1.234.567' son miles (no un número decimal)."""
    rows = [{"total": "1.234.567"}, {"total": "2.345"}]
    profile = _profile_column("total", rows)
    assert profile.mean == round((1234567 + 2345) / 2, 4)


def test_decimales_punto_de_3_digitos_siguen_siendo_decimales():
    """AP-01: '0.500' / '0.750' son decimales, no miles (riesgo de sesgo)."""
    rows = [{"prob": "0.500"}, {"prob": "0.750"}, {"prob": "0.250"}]
    profile = _profile_column("prob", rows)
    assert profile.mean == 0.5


# ── Caso 3: encabezado en fila 3 → target_rows apuntan a la fila correcta ────
@pytest.mark.xfail(reason="CL-05: target_rows-2 hardcodeado ignora header_row_index", strict=True)
def test_target_rows_con_encabezado_en_fila_3():
    """CL-05: con metadatos arriba (header en fila 3), la fila Excel 5 es el
    segundo dato. fill_missing debe rellenar exactamente esa fila."""
    payload = (
        b"Reporte de calidad\n"
        b"Generado: 2026-08-03\n"
        b"id,nombre,edad\n"
        b"1,Ana,25\n"
        b"2,,30\n"
        b"3,Carlos,35\n"
    )
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "fill_missing", "column": "nombre", "method": "mode", "rows": [5]}],
    )
    assert "2,X,30" in result["clean_csv"]


# ── Caso 4: change_type boolean con sinónimos ─────────────────────────────────
@pytest.mark.xfail(reason="CL-01: change_type boolean solo reconoce si/sí/true/1", strict=True)
def test_change_type_boolean_con_sinonimos():
    """CL-01: 'activo'/'yes'/'verdadero' -> 'si' (no 'no'); 'no' -> 'no'."""
    payload = b"estado\nactivo\nyes\nverdadero\nno\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "change_type", "column": "estado", "value": "boolean"}],
    )
    assert _clean_values(result, "estado") == ["si", "si", "si", "no"]


# ── Caso 5: duplicados por key_columns se eliminan exactamente ───────────────
@pytest.mark.xfail(reason="DU-02: remove_duplicate_rows ignora key_columns y NFKD", strict=True)
def test_remove_duplicate_rows_respeta_key_columns():
    """DU-02: '1,Ana' vs '1,ANA' son duplicados por la clave 'id' -> 2 filas."""
    payload = b"id,nombre\n1,Ana\n1,ANA\n2,Luis\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "remove_duplicate_rows"}],
        duplicate_key_columns=["id"],
    )
    assert result["after"]["row_count"] == 2


# ── Caso 6: "pendiente" no es missing (regresión) ─────────────────────────────
def test_pendiente_no_es_missing():
    """AP-04: 'pendiente' es valor legítimo. El profiler no debe contarlo como
    faltante."""
    payload = b"estado\npendiente\nactivo\nactivo\n"
    analysis = analyze_dataset("t.csv", payload)
    estado = next(c for c in analysis["columns"] if c["name"] == "estado")
    assert estado["missing"] == 0


# ── Caso 7: imputación con media es estable (regresión) ──────────────────────
def test_impute_mean_es_estable():
    """CL-06: imputar con la media no altera la media del perfilado posterior."""
    payload = b"valor\n10\n20\n30\n\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "impute_missing", "column": "valor", "method": "mean"}],
    )
    before = next(c for c in result["before"]["columns"] if c["name"] == "valor")
    after = next(c for c in result["after"]["columns"] if c["name"] == "valor")
    assert before["mean"] == after["mean"]
