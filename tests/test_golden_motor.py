"""Golden tests — Motor de diagnóstico de 28 categorías (TS-01).

Especificación del comportamiento OBJETIVO definido en
`docs/DIAGNOSTICO_MEJORA_MOTOR_28CATEGORIAS.md` (sección 7, tabla de regresión).

Convención (ver docs/PLAN_REFACTOR_MOTOR.md, regla R2):
- Cada test que aún NO se cumple está marcado `xfail(strict=True)` con el ID del
  hallazgo en `reason`. La suite permanece verde (XFAIL) y, cuando el fix
  implementa el comportamiento, el test pasa y pytest lo reporta como XPASS
  STRICT → señal para quitar el marcador.
- Los tests sin marcador son comportamiento correcto actual que debe conservarse
  (regresión de verdaderos positivos).
"""

from data_engine.diagnostic import (
    _check_multivalue_cells,
    diagnose_column,
    match_column_name,
)


def codes(diag) -> set[str]:
    return {i.category_code for i in diag.issues}


# ── Caso 1: "estado" con "pendiente"/"activo" ─────────────────────────────────
def test_estado_pendiente_activo_sin_hidden_missing():
    """DM-03: 'pendiente' es un valor legítimo de estado, no un placeholder."""
    diag = diagnose_column("estado", ["pendiente", "activo", "activo", "pendiente", "activo"], 5)
    assert "HIDDEN_MISSING" not in codes(diag)


def test_sentinelas_9999_y_menos_uno_no_son_missing():
    """DM-03: '9999' y '-1' son valores legítimos, no placeholders de missing."""
    from data_engine.domain_rules import is_hidden_missing

    assert not is_hidden_missing("9999")
    assert not is_hidden_missing("-1")


# ── Caso 2: "nivel_estudios" ──────────────────────────────────────────────────
def test_nivel_estudios_dominio_no_confirmado():
    """DM-01: 'nivel' hace substring-match con dominio 'score' (rango 0-10)
    pero los valores (bachiller/universitario) no confirman un puntaje numérico.
    El dominio no debe quedar confirmado con confidence 0.95."""
    diag = diagnose_column("nivel_estudios", ["bachiller", "universitario", "bachiller", "tecnico", "universitario"], 5)
    assert diag.inferred_domain != "score"
    assert "TYPE_VALIDATION" not in codes(diag)


def test_nivel_estudios_match_column_name_no_falso_positivo():
    """DM-01: match_column_name no matchea 'nivel_estudios' como 'score'
    (matching por token completo, sin substring)."""
    assert match_column_name("nivel_estudios") is None


# ── Caso 3: "validacion" (si/no) ──────────────────────────────────────────────
def test_validacion_dominio_no_id():
    """DM-01: 'validacion' contiene 'id' como substring pero NO es identificador."""
    diag = diagnose_column("validacion", ["si", "no", "si", "no", "si", "no", "si"], 7)
    assert diag.inferred_domain != "id"


def test_validacion_sin_duplicate():
    """Columna si/no NO es ID → nunca se reporta DUPLICATE (regresión)."""
    diag = diagnose_column("validacion", ["si", "no", "si", "no", "si", "no", "si"], 7)
    assert "DUPLICATE" not in codes(diag)


def test_validacion_match_column_name_no_id():
    """DM-01: match_column_name('validacion') no debe devolver dominio 'id'."""
    info = match_column_name("validacion")
    assert info is None or info["domain"] != "id"


def test_id_cliente_match_por_token():
    """DM-01: el matcher por tokens SÍ reconoce 'id_cliente' como id
    (token 'id' coincide con hint de dominio id, sin substring)."""
    info = match_column_name("id_cliente")
    assert info is not None and info["domain"] == "id"


def test_fecha_nacimiento_match_por_token():
    """DM-01: 'fecha_nacimiento' matchea date por 2 tokens ('fecha' + 'nacimiento')."""
    info = match_column_name("fecha_nacimiento")
    assert info is not None and info["domain"] == "date"


def test_correo_sin_confirmacion_por_valores():
    """DM-01: 'correo_electronico' matchea por nombre pero los valores no-email
    no confirman el dominio (spec 4.2 paso 3)."""
    diag = diagnose_column("correo_electronico", ["hola", "mundo", "hola", "mundo", "hola"], 5)
    assert diag.inferred_domain != "email"


# ── Caso 4: fecha única ───────────────────────────────────────────────────────
def test_fecha_unica_ejecuta_chequeos_de_fecha():
    """DG-02: una columna de fechas con alta cardinalidad NO se salta los
    chequeos DATE_INVALID/DATE_FORMAT por clasificarse IDENTIFICADOR/TEXTO_LIBRE."""
    values = [f"2020-01-{d:02d}" for d in range(1, 31)] + ["2020-13-01"]
    diag = diagnose_column("fecha", values, len(values))
    assert "DATE_INVALID" in codes(diag)


# ── DM-02: fecha US 12/25/2020 no es "fecha imposible" ────────────────────────
def test_fecha_us_no_date_invalid():
    """DM-02 (A3): '12/25/2020' es una fecha válida en formato US (mm/dd/yyyy).
    No debe marcarse DATE_INVALID por asumir día-primero."""
    diag = diagnose_column(
        "fecha_ingreso",
        ["12/25/2020", "12/25/2020", "12/26/2020", "01/15/2021", "11/30/2021"],
        5,
    )
    assert "DATE_INVALID" not in codes(diag)


# ── DG-01: ID requiere nombre match AND (cardinalidad o patrón) ───────────────
def test_codigo_postal_repetido_no_duplicate():
    """DG-01 (B1): 'codigo_postal' matchea ID por nombre pero los códigos
    postales se repiten legítimamente → NO debe reportarse DUPLICATE."""
    diag = diagnose_column(
        "codigo_postal",
        ["110111", "110111", "050001", "050001", "110111", "080001", "080001", "110111", "050001", "110111"],
        10,
    )
    assert "DUPLICATE" not in codes(diag)


def test_nombre_casi_unico_no_duplicate():
    """DG-01 (B3): columna 'nombre' con alta cardinalidad NO es ID → las
    repeticiones de 'Ana' no son DUPLICATE."""
    diag = diagnose_column(
        "nombre",
        ["Ana", "Juan", "Maria", "Carlos", "Luis", "Pedro", "Sofia", "Diego", "Laura",
         "Jorge", "Andres", "Paula", "Hugo", "Ivan", "Rosa", "Marta", "Nora", "Cesar",
         "Pablo", "Ana"],
        20,
    )
    assert "DUPLICATE" not in codes(diag)


def test_id_real_repetido_sigue_duplicate():
    """Regresión DG-01: una columna 'id' con cardinalidad ≥95% y un repetido
    SÍ es identificador → DUPLICATE."""
    ids = [f"{1000 + i}" for i in range(1, 21)]
    ids[19] = "1001"
    diag = diagnose_column("id", ids, 20)
    assert "DUPLICATE" in codes(diag)


def test_identificador_repetido_sigue_duplicate():
    """Regresión DG-01: 'identificador' (header común, no estaba en los
    patrones) con alta cardinalidad y un repetido sigue siendo ID → DUPLICATE."""
    ids = [f"{2000 + i}" for i in range(1, 21)]
    ids[19] = "2001"
    diag = diagnose_column("identificador", ids, 20)
    assert "DUPLICATE" in codes(diag)


# ── Caso 5: "activo" solo "activo"/"inactivo" ─────────────────────────────────
def test_activo_bien_formado_sin_bool_inconsistency():
    """DG-04: dos etiquetas booleanas limpias (activo/inactivo) no son
    BOOL_INCONSISTENCY. Solo debe señalarse cuando un mismo significado tiene
    varias representaciones."""
    diag = diagnose_column("activo", ["activo", "inactivo", "activo", "inactivo", "activo"], 5)
    assert "BOOL_INCONSISTENCY" not in codes(diag)


# ── Caso 6: "ciudad" minúscula uniforme ───────────────────────────────────────
def test_ciudad_minuscula_uniforme_sin_text_error():
    """DG-05: texto uniforme en minúsculas no es TEXT_ERROR. Solo se señalan
    grafías MIXTAS con el mismo contenido."""
    diag = diagnose_column("ciudad", ["bogota", "medellin", "bogota", "cali", "medellin", "bogota"], 6)
    assert "TEXT_ERROR" not in codes(diag)


# ── Caso 7: fechas no son MULTI_VALUE ─────────────────────────────────────────
def test_fechas_no_multivalue():
    """DG-06: '12/03/2020' no es una celda multivaluada por contener '/'."""
    issues = _check_multivalue_cells(
        ["12/03/2020", "15/08/2021", "01/01/2020", "22/12/2019"], 4
    )
    assert all(i.category_code != "MULTI_VALUE" for i in issues)


# ── Caso 8: booleano mezclado si/sí/true → CONFIRMADO (regresión) ────────────
def test_boolean_mixto_detecta_inconsistencia():
    """Verdadero positivo que debe conservarse: si/sí/true/verdadero son
    múltiples representaciones del mismo significado."""
    diag = diagnose_column(
        "estado_respuesta", ["si", "sí", "true", "no", "verdadero", "no", "si"], 7
    )
    assert "BOOL_INCONSISTENCY" in codes(diag)


# ── Caso 9: edad 450 → NUMERIC_DOMAIN CRITICA (regresión) ─────────────────────
def test_edad_450_violacion_dominio_critica():
    """Verdadero positivo que debe conservarse: 450 años excede el rango humano."""
    diag = diagnose_column("edad", ["18", "25", "30", "45", "450", "30", "25"], 7)
    num_domain = [i for i in diag.issues if i.category_code == "NUMERIC_DOMAIN"]
    assert num_domain, "NUMERIC_DOMAIN debe detectarse"
    assert num_domain[0].severity == "CRITICA"


# ── Caso 10: "bogota"/"Bogotá" → CATEGORICAL A_REVISAR ───────────────────────
def test_ciudad_variantes_case_categorical():
    """DG-05/DG-11: variantes de case/acento del mismo valor son CATEGORICAL
    (A_REVISAR), no TEXT_ERROR."""
    diag = diagnose_column(
        "ciudad", ["bogota", "Bogotá", "MEDELLIN", "medellin", "bogota", "Bogota", "medellin"], 7
    )
    assert "CATEGORICAL" in codes(diag)
