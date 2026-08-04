"""Golden tests — Algoritmo de análisis y limpieza (TS-02).

Especificación del comportamiento OBJETIVO definido en
`docs/DIAGNOSTICO_ALGORITMO_ANALISIS_LIMPIEZA.md` (sección 9, tabla de casos).

Misma convención que test_golden_motor.py: `xfail(strict=True)` con ID de
hallazgo en `reason`; los tests sin marcador son regresión de comportamiento
correcto actual.
"""

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


# ── Caso 2b: fecha compacta no se pierde como número (AP-02) ─────────────────
def test_fecha_compacta_no_es_numero():
    """AP-02: 20240101 es fecha (YYYYMMDD), no número."""
    rows = [{"fecha": "20240101"}, {"fecha": "20240102"}, {"fecha": "20240103"}, {"fecha": "20240104"}]
    profile = _profile_column("fecha", rows)
    assert profile.detected_type == "date"


def test_anios_siguen_siendo_numeros():
    """AP-02: una columna de años (2024) no debe clasificarse como fecha."""
    rows = [{"anio": "2024"}, {"anio": "2025"}, {"anio": "2023"}]
    profile = _profile_column("anio", rows)
    assert profile.detected_type == "number"


# ── Caso 2c: umbral configurable y exactitud estructural (AP-03) ─────────────
def test_columna_70_por_ciento_numerica_es_number():
    """AP-03: 3 de 4 valores numéricos (75%) y 1 texto -> number con umbral 70%."""
    rows = [{"valor": "34"}, {"valor": "29"}, {"valor": "45"}, {"valor": "treinta"}]
    profile = _profile_column("valor", rows)
    assert profile.detected_type == "number"
    assert profile.invalid_type_count == 1


def test_exactitud_incluye_errores_de_tipo():
    """AP-03: errores de tipo reducen la exactitud estructural, no solo outliers."""
    result = analyze_dataset("v.csv", b"valor\n34\n29\n45\ntreinta\n")
    column = next(c for c in result["columns"] if c["name"] == "valor")
    accuracy = result["scores"]["accuracy"]
    expected = 100 - ((column["outliers"] + column["invalid_type_count"]) / 4 * 100)
    assert accuracy == round(expected, 2)


# ── Caso 2d: outliers, format_issues y overall (AP-05/06/07) ─────────────────
def test_iqr_cero_es_explicito():
    """AP-05: valores idénticos (IQR=0) marcan outlier_analysis_skipped."""
    rows = [{"nota": "5"}, {"nota": "5"}, {"nota": "5"}, {"nota": "5"}]
    profile = _profile_column("nota", rows)
    assert profile.outlier_analysis_skipped
    assert profile.outliers == 0


def test_format_issues_cuenta_filas_afectadas():
    """AP-06: 2 'bogota' + 1 'Bogota' -> 1 fila afectada, no 2 variantes."""
    payload = b"ciudad\nbogota\nBogota\nbogota\nMedellin\n"
    analysis = analyze_dataset("t.csv", payload)
    ciudad = next(c for c in analysis["columns"] if c["name"] == "ciudad")
    assert ciudad["format_issues"] == 1


def test_overall_es_ponderado():
    """AP-07: completitud (75) pesa menos que en la media simple (92.5)."""
    payload = b"edad\n25\n30\nNA\n31\n"
    analysis = analyze_dataset("t.csv", payload)
    s = analysis["scores"]
    assert s["overall"] == 92.5
    assert s["overall"] != round((s["completeness"] + s["consistency"] + s["accuracy"] + s["uniqueness"]) / 4, 2)


# ── Caso 3: encabezado en fila 3 → target_rows apuntan a la fila correcta ────
def test_target_rows_con_encabezado_en_fila_3():
    """CL-05: con metadatos arriba (header en fila 3), la fila Excel 5 es el
    segundo dato. fill_missing debe rellenar exactamente esa fila (id=2)."""
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
    assert _clean_values(result, "nombre") == ["Ana", "Ana", "Carlos"]


# ── Caso 4: change_type boolean con sinónimos ─────────────────────────────────
def test_change_type_boolean_con_sinonimos():
    """CL-01: 'activo'/'yes'/'verdadero' -> 'si' (no 'no'); 'no' -> 'no'."""
    payload = b"estado\nactivo\nyes\nverdadero\nno\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "change_type", "column": "estado", "value": "boolean"}],
    )
    assert _clean_values(result, "estado") == ["si", "si", "si", "no"]


def test_change_type_boolean_sinonimos_falsos_y_default():
    """CL-01: sinónimos falsos (falso/inactivo/0) -> 'no'; token desconocido
    mantiene el default actual ('no')."""
    payload = b"estado\nfalso\ninactivo\n0\n1\nNA\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "change_type", "column": "estado", "value": "boolean"}],
    )
    assert _clean_values(result, "estado") == ["no", "no", "no", "si", "no"]


# ── Caso 5: duplicados por key_columns se eliminan exactamente ───────────────
def test_remove_duplicate_rows_respeta_key_columns():
    """DU-02: '1,Ana' vs '1,ANA' son duplicados por la clave 'id' -> 2 filas."""
    payload = b"id,nombre\n1,Ana\n1,ANA\n2,Luis\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "remove_duplicate_rows"}],
        duplicate_key_columns=["id"],
    )
    assert result["after"]["row_count"] == 2


def test_duplicados_misma_firma_analyzer_y_diagnostic():
    """DU-01: la definición de duplicado es idéntica entre analyzer (_count_duplicate_rows)
    y diagnostic (_check_row_duplicates) usando strip + lower + sin acentos."""
    payload = b"id,nombre,ciudad\n1,Ana,Medellin\n1,ana,medellin\n2,Luis,Bogota\n"
    analysis = analyze_dataset("t.csv", payload)
    assert analysis["duplicate_rows"] == 1

    from data_engine.diagnostic import _check_row_duplicates

    headers, rows, _ = load_dataset("t.csv", payload)
    issues = _check_row_duplicates(headers, rows)
    assert sum(i.count for i in issues) == 1


def test_remove_duplicate_rows_full_row_con_acentos():
    """DU-02: full-row con acentos/case colapsa a la misma fila normalizada.
    El perfil 'after' queda sin duplicados y el changelog registra la fila."""
    payload = b"id,nombre\n1,Ana\n1,ana\n2,Luis\n"
    before = analyze_dataset("t.csv", payload)
    assert before["duplicate_rows"] == 1

    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "remove_duplicate_rows"}],
    )
    assert result["after"]["row_count"] == 2
    assert result["after"]["duplicate_rows"] == 0
    dedup_entries = [e for e in result["changelog"] if e["action"] == "Eliminar duplicado"]
    assert len(dedup_entries) == before["duplicate_rows"] == 1




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


# ── Caso 8: fill_empty respeta target_rows (filas Excel) ──────────────────────
def test_fill_empty_respeta_target_rows():
    """CL-02: fill_empty solo rellena las filas seleccionadas (Excel row 3 = índice 1)."""
    payload = b"id,valor\n1,10\n2,\n3,30\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "fill_empty", "column": "valor", "value": "NULL", "rows": [3]}],
    )
    assert _clean_values(result, "valor") == ["10", "NULL", "30"]


def test_fill_empty_sin_target_rows_rellena_todas():
    """CL-02: sin 'rows', fill_empty rellena todos los vacíos (comportamiento previo)."""
    payload = b"id,valor\n1,10\n2,\n3,\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "fill_empty", "column": "valor", "value": "NULL"}],
    )
    assert _clean_values(result, "valor") == ["10", "NULL", "NULL"]


# ── Caso 9: flag_outliers registra filas reales en el changelog ───────────────
def test_flag_outliers_con_filas_seleccionadas():
    """CL-03: con 'rows', el changelog registra exactamente esas filas (Excel row 3 = id 2)."""
    payload = b"id,valor\n1,10\n2,20\n3,30\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "flag_outliers", "column": "valor", "rows": [3]}],
    )
    entries = [e for e in result["changelog"] if e["action"] == "Marcar outlier"]
    assert len(entries) == 1
    assert entries[0]["changes"][0]["row"] == "2"


def test_flag_outliers_detecta_filas_atipicas():
    """CL-03: sin 'rows', calcula los outliers reales (misma IQR del perfilado)
    y los registra en el changelog."""
    payload = b"valor\n1\n2\n3\n4\n5\n100\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "flag_outliers", "column": "valor"}],
    )
    entries = [e for e in result["changelog"] if e["action"] == "Marcar outlier"]
    assert len(entries) == 1
    assert entries[0]["changes"][0]["old"] == "100"


# ── Caso 10: fill_missing / impute_missing consolidados (CL-06) ──────────────
def test_impute_y_fill_missing_comparten_semantica():
    """CL-06: fill_missing (mode) e impute_missing (mode) producen el mismo resultado."""
    payload = b"id,valor\n1,10\n2,\n3,20\n4,\n"
    a = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "fill_missing", "column": "valor", "method": "mode"}],
    )
    b = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "impute_missing", "column": "valor", "method": "mode"}],
    )
    assert _clean_values(a, "valor") == _clean_values(b, "valor")


def test_fill_missing_null_y_fill_empty_respetan_missing():
    """CL-06: fill_missing con method=null rellena tokens missing (N/A), no solo vacíos."""
    payload = b"id,valor\n1,10\n2,N/A\n3,\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "fill_missing", "column": "valor", "method": "null"}],
    )
    assert _clean_values(result, "valor") == ["10", "NULL", "NULL"]


# ── Caso 11: after se re-perfila en memoria sin re-parsear CSV (CL-08) ────────
def test_after_reperfilado_en_memoria():
    """CL-08: tras change_type a number, el perfil 'after' refleja el cambio."""
    payload = b"id,valor\n1,10\n2,20\n3,30\n"
    result = apply_cleaning_actions(
        "t.csv", payload,
        [{"kind": "change_type", "column": "valor", "value": "number"}],
    )
    after_valor = next(c for c in result["after"]["columns"] if c["name"] == "valor")
    assert after_valor["detected_type"] == "number"
    assert result["after"]["row_count"] == 3


# ── CL-07: justificaciones batch llegan al changelog ─────────────────────────
def test_cl07_changelog_tiene_justificaciones_reales():
    """CL-07: batch Groq genera justificaciones para cada accion en changelog."""
    payload = (
        b"id,nombre,edad\n"
        b"1,,25\n"
        b"2,Carlos,30\n"
        b"3,,35\n"
    )
    actions = [
        {"kind": "delete_column", "column": "edad", "reason": "Columna no necesaria"},
        {"kind": "fill_missing", "column": "nombre", "method": "mode"},
    ]
    result = apply_cleaning_actions("t.csv", payload, actions)
    changelog = result["changelog"]
    assert len(changelog) == 3, f"expected 3 changelog entries (1 delete + 2 fills), got {len(changelog)}: {changelog}"
    for entry in changelog:
        assert "reason" in entry
        assert len(entry["reason"]) > 10, f"justificacion demasiado corta: {entry['reason']!r}"
        assert "Gemini" not in entry["reason"], "justificacion no debe mencionar Gemini"


def test_cl07_changelog_acciones_multiples():
    """CL-07: 3 acciones en batch -> 3+ justificaciones en changelog."""
    payload = (
        b"id,ciudad,edad\n"
        b"1,bogota,25\n"
        b"2,medellin,30\n"
        b"3,bogota,35\n"
    )
    actions = [
        {"kind": "standardize_text", "column": "ciudad", "method": "title", "reason": "Unificar capitalizacion"},
        {"kind": "fill_missing", "column": "edad", "method": "mode"},
        {"kind": "remove_duplicate_rows", "reason": "Filas repetidas"},
    ]
    result = apply_cleaning_actions("t.csv", payload, actions)
    changelog = result["changelog"]
    assert len(changelog) >= 3
    reasons = [e["reason"] for e in changelog]
    assert all(len(r) > 10 for r in reasons), "todas las justificaciones deben tener contenido real"
