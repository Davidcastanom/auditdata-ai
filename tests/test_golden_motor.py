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

import pytest

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
@pytest.mark.xfail(reason="DM-01: 'nivel' matchea dominio 'score' por substring", strict=True)
def test_nivel_estudios_dominio_no_confirmado():
    """DM-01: 'nivel' hace substring-match con dominio 'score' (rango 0-10)
    pero los valores (bachiller/universitario) no confirman un puntaje numérico.
    El dominio no debe quedar confirmado con confidence 0.95."""
    diag = diagnose_column("nivel_estudios", ["bachiller", "universitario", "bachiller", "tecnico", "universitario"], 5)
    assert diag.inferred_domain != "score"
    assert "TYPE_VALIDATION" not in codes(diag)


@pytest.mark.xfail(reason="DM-01: match_column_name usa substring", strict=True)
def test_nivel_estudios_match_column_name_no_falso_positivo():
    """DM-01: match_column_name no debe confirmar dominio por substring."""
    assert match_column_name("nivel_estudios") is None


# ── Caso 3: "validacion" (si/no) ──────────────────────────────────────────────
@pytest.mark.xfail(reason="DM-01: 'validacion' matchea dominio 'id' por substring", strict=True)
def test_validacion_dominio_no_id():
    """DM-01: 'validacion' contiene 'id' como substring pero NO es identificador."""
    diag = diagnose_column("validacion", ["si", "no", "si", "no", "si", "no", "si"], 7)
    assert diag.inferred_domain != "id"


def test_validacion_sin_duplicate():
    """Columna si/no NO es ID → nunca se reporta DUPLICATE (regresión)."""
    diag = diagnose_column("validacion", ["si", "no", "si", "no", "si", "no", "si"], 7)
    assert "DUPLICATE" not in codes(diag)


@pytest.mark.xfail(reason="DM-01: match_column_name usa substring", strict=True)
def test_validacion_match_column_name_no_id():
    """DM-01: match_column_name('validacion') no debe devolver dominio 'id'."""
    info = match_column_name("validacion")
    assert info is None or info["domain"] != "id"


# ── Caso 4: fecha única ───────────────────────────────────────────────────────
@pytest.mark.xfail(reason="DG-02: fecha única clasifica IDENTIFICADOR/TEXTO_LIBRE y salta chequeos", strict=True)
def test_fecha_unica_ejecuta_chequeos_de_fecha():
    """DG-02: una columna de fechas con alta cardinalidad NO se salta los
    chequeos DATE_INVALID/DATE_FORMAT por clasificarse IDENTIFICADOR/TEXTO_LIBRE."""
    values = [f"2020-01-{d:02d}" for d in range(1, 31)] + ["2020-13-01"]
    diag = diagnose_column("fecha", values, len(values))
    assert "DATE_INVALID" in codes(diag)


# ── Caso 5: "activo" solo "activo"/"inactivo" ─────────────────────────────────
@pytest.mark.xfail(reason="DG-04: BOOL_INCONSISTENCY marca booleanos bien formados", strict=True)
def test_activo_bien_formado_sin_bool_inconsistency():
    """DG-04: dos etiquetas booleanas limpias (activo/inactivo) no son
    BOOL_INCONSISTENCY. Solo debe señalarse cuando un mismo significado tiene
    varias representaciones."""
    diag = diagnose_column("activo", ["activo", "inactivo", "activo", "inactivo", "activo"], 5)
    assert "BOOL_INCONSISTENCY" not in codes(diag)


# ── Caso 6: "ciudad" minúscula uniforme ───────────────────────────────────────
@pytest.mark.xfail(reason="DG-05: TEXT_ERROR marca minúsculas uniformes", strict=True)
def test_ciudad_minuscula_uniforme_sin_text_error():
    """DG-05: texto uniforme en minúsculas no es TEXT_ERROR. Solo se señalan
    grafías MIXTAS con el mismo contenido."""
    diag = diagnose_column("ciudad", ["bogota", "medellin", "bogota", "cali", "medellin", "bogota"], 6)
    assert "TEXT_ERROR" not in codes(diag)


# ── Caso 7: fechas no son MULTI_VALUE ─────────────────────────────────────────
@pytest.mark.xfail(reason="DG-06: MULTI_VALUE marca fechas (12/03/2020)", strict=True)
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
@pytest.mark.xfail(reason="DG-05: variantes de case no generan CATEGORICAL", strict=True)
def test_ciudad_variantes_case_categorical():
    """DG-05/DG-11: variantes de case/acento del mismo valor son CATEGORICAL
    (A_REVISAR), no TEXT_ERROR."""
    diag = diagnose_column(
        "ciudad", ["bogota", "Bogotá", "MEDELLIN", "medellin", "bogota", "Bogota", "medellin"], 7
    )
    assert "CATEGORICAL" in codes(diag)
