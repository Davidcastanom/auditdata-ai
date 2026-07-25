"""Domain rules for auto-detecting column types by name pattern and value analysis.

This module enables the system to work with ANY dataset without prior context,
by inferring what each column represents from its name and predominant values.
"""

from __future__ import annotations

from typing import Any


DOMAIN_PATTERNS: list[dict[str, Any]] = [
    {
        "domain": "age",
        "name_hints": ["edad", "age", "antiguedad", "anios", "años", "years", "experiencia"],
        "range": [0, 120],
        "expected_type": "number",
        "description": "Edad humana o antigüedad",
    },
    {
        "domain": "currency",
        "name_hints": ["precio", "price", "valor", "monto", "costo", "salario", "salary",
                        "sueldo", "ingreso", "presupuesto", "total", "importe", "tarifa"],
        "range": [0, None],
        "expected_type": "number",
        "description": "Valor monetario o precio",
    },
    {
        "domain": "quantity",
        "name_hints": ["cantidad", "quantity", "units", "unidades", "stock", "inventario",
                        "disponible", "num", "numero"],
        "range": [0, None],
        "expected_type": "number",
        "description": "Cantidad o unidades",
    },
    {
        "domain": "percentage",
        "name_hints": ["porcentaje", "percentage", "rate", "tasa", "proporcion",
                        "pct", "%", "comision"],
        "range": [0, 100],
        "expected_type": "number",
        "description": "Porcentaje o tasa",
    },
    {
        "domain": "date",
        "name_hints": ["fecha", "date", "created_at", "updated_at", "timestamp",
                        "dia", "mes", "ano", "año", "year", "month", "day",
                        "inicio", "fin", "nacimiento", "registro"],
        "range": None,
        "expected_type": "date",
        "description": "Fecha o marca de tiempo",
    },
    {
        "domain": "email",
        "name_hints": ["email", "correo", "mail", "e-mail", "correo_electronico"],
        "range": None,
        "expected_type": "text",
        "pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        "description": "Direccion de correo electronico",
    },
    {
        "domain": "phone",
        "name_hints": ["telefono", "phone", "cel", "celular", "movil", "fax",
                        "tel", "contacto"],
        "range": None,
        "expected_type": "text",
        "description": "Numero de telefono",
    },
    {
        "domain": "country",
        "name_hints": ["pais", "country", "nation", "nacionalidad", "paiz"],
        "range": None,
        "expected_type": "text",
        "description": "Pais (ISO 3166)",
    },
    {
        "domain": "city",
        "name_hints": ["ciudad", "city", "municipio", "localidad", "lugar",
                        "ubicacion", "distrito", "barrio"],
        "range": None,
        "expected_type": "text",
        "description": "Ciudad o municipio",
    },
    {
        "domain": "gender",
        "name_hints": ["genero", "gender", "sexo", "sex"],
        "range": None,
        "expected_type": "text",
        "description": "Genero o sexo",
    },
    {
        "domain": "id",
        "name_hints": ["id", "identificacion", "cedula", "dni", "passport",
                        "codigo", "code", "key", "llave", "consecutivo"],
        "range": None,
        "expected_type": "any",
        "description": "Identificador unico",
    },
    {
        "domain": "name",
        "name_hints": ["nombre", "name", "apellido", "last_name", "first_name",
                        "razon_social", "denominacion"],
        "range": None,
        "expected_type": "text",
        "description": "Nombre o apellido",
    },
    {
        "domain": "address",
        "name_hints": ["direccion", "address", "calle", "avenida", "barrio",
                        "numero_direccion", "domicilio"],
        "range": None,
        "expected_type": "text",
        "description": "Direccion postal",
    },
    {
        "domain": "latitude",
        "name_hints": ["lat", "latitude", "latitud"],
        "range": [-90, 90],
        "expected_type": "number",
        "description": "Coordenada de latitud",
    },
    {
        "domain": "longitude",
        "name_hints": ["lon", "lng", "longitude", "longitud"],
        "range": [-180, 180],
        "expected_type": "number",
        "description": "Coordenada de longitud",
    },
    {
        "domain": "boolean",
        "name_hints": ["activo", "active", "enabled", "completo", "completed",
                        "acepta", "aceptado", "verificado", "verified"],
        "range": None,
        "expected_type": "boolean",
        "description": "Valor booleano (si/no, true/false)",
    },
    {
        "domain": "score",
        "name_hints": ["calificacion", "score", "rating", "puntuacion", "nota",
                        "ranking", "nivel"],
        "range": [0, 10],
        "expected_type": "number",
        "description": "Calificacion o puntuacion",
    },
    {
        "domain": "duration",
        "name_hints": ["duracion", "duration", "tiempo", "time", "minutos",
                        "horas", "seconds", "segundos"],
        "range": [0, None],
        "expected_type": "number",
        "description": "Duracion o tiempo",
    },
    {
        "domain": "weight",
        "name_hints": ["peso", "weight", "kg", "lbs", "gramos"],
        "range": [0, None],
        "expected_type": "number",
        "description": "Peso",
    },
    {
        "domain": "distance",
        "name_hints": ["distancia", "distance", "km", "millas", "metros"],
        "range": [0, None],
        "expected_type": "number",
        "description": "Distancia",
    },
]


COUNTRY_SYNONYMS: dict[str, str] = {
    "col": "Colombia", "co": "Colombia", "republica de colombia": "Colombia",
    "rep. de colombia": "Colombia", "rep colombia": "Colombia",
    "usa": "Estados Unidos", "us": "Estados Unidos",
    "united states": "Estados Unidos", "united states of america": "Estados Unidos",
    "ee uu": "Estados Unidos", "ee.uu.": "Estados Unidos",
    "brasil": "Brasil", "br": "Brasil", "brazil": "Brasil",
    "mexico": "Mexico", "mx": "Mexico", "méxico": "Mexico",
    "argentina": "Argentina", "ar": "Argentina",
    "peru": "Peru", "pe": "Peru", "perú": "Peru",
    "chile": "Chile", "cl": "Chile",
    "ecuador": "Ecuador", "ec": "Ecuador",
    "venezuela": "Venezuela", "ve": "Venezuela",
    "bolivia": "Bolivia", "bo": "Bolivia",
    "paraguay": "Paraguay", "py": "Paraguay",
    "uruguay": "Uruguay", "uy": "Uruguay",
    "espana": "Espana", "españa": "Espana", "es": "Espana", "spain": "Espana",
    "portugal": "Portugal", "pt": "Portugal",
    "brasil": "Brasil", "brazil": "Brasil",
    "china": "China", "cn": "China",
    "japon": "Japon", "japón": "Japon", "jp": "Japon",
    "alemania": "Alemania", "de": "Alemania", "germany": "Alemania",
    "francia": "Francia", "fr": "Francia", "france": "Francia",
    "italia": "Italia", "it": "Italia", "italy": "Italia",
    "reino unido": "Reino Unido", "uk": "Reino Unido",
    "canada": "Canada", "ca": "Canada",
    "australia": "Australia", "au": "Australia",
}

GENDER_SYNONYMS: dict[str, str] = {
    "m": "Masculino", "masculino": "Masculino", "hombre": "Masculino",
    "h": "Masculino", "male": "Masculino", "man": "Masculino",
    "f": "Femenino", "femenino": "Femenino", "mujer": "Femenino",
    "female": "Femenino", "woman": "Femenino",
}

BOOLEAN_SYNONYMS: dict[str, bool] = {
    "si": True, "sí": True, "s": True, "true": True, "1": True,
    "yes": True, "verdadero": True, "activo": True, "completo": True,
    "no": False, "n": False, "false": False, "0": False,
    "falso": False, "inactivo": False, "pendiente": False,
}

DATE_FORMATS: list[str] = [
    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
    "%d-%m-%Y", "%m-%d-%Y", "%d.%m.%Y",
    "%d %m %Y", "%Y%m%d",
    "%d/%m/%y", "%m/%d/%y", "%y/%m/%d",
    "%B %d, %Y", "%b %d, %Y",
    "%d de %B de %Y", "%d de %b de %Y",
]

MISSING_TOKENS_EXTENDED: set[str] = {
    "", "na", "n/a", "null", "none", "nan", "-", "n/d", "nd",
    "sin dato", "sin datos", "no aplica", "no disponible",
    "desconocido", "pendiente", "no reportado", "missing",
    "?", "9999", "-1", "--", "n/a", "na",
    "s/d", "s/dato", "no aplica", "n/r",
    " ", "  ", "\t", "\n",
}


def match_column_name(header: str) -> dict[str, Any] | None:
    """Match a column header against known domain patterns.

    Returns the matched domain dict or None if no pattern matches.
    """
    normalized = header.lower().strip()
    normalized = normalized.replace(" ", "_").replace("-", "_")

    for pattern in DOMAIN_PATTERNS:
        for hint in pattern["name_hints"]:
            if hint in normalized or normalized in hint:
                return pattern

    return None


def get_country_synonym(value: str) -> str:
    """Return the standardized country name for a given variant."""
    return COUNTRY_SYNONYMS.get(value.lower().strip(), value)


def get_gender_synonym(value: str) -> str:
    """Return the standardized gender for a given variant."""
    return GENDER_SYNONYMS.get(value.lower().strip(), value)


def is_boolean_synonym(value: str) -> bool | None:
    """Return True/False if value matches a boolean synonym, None otherwise."""
    return BOOLEAN_SYNONYMS.get(value.lower().strip())


def is_hidden_missing(value: str) -> bool:
    """Check if a value is a placeholder that hides a missing value."""
    if value is None:
        return True
    normalized = str(value).strip().lower()
    return normalized in MISSING_TOKENS_EXTENDED


def detect_date_format(value: str) -> str | None:
    """Try to parse a date string against known formats.

    Returns the format string if successful, None otherwise.
    """
    import re
    cleaned = value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", cleaned):
        return "%Y-%m-%d"
    if re.match(r"^\d{2}/\d{2}/\d{4}", cleaned):
        return "%d/%m/%Y"
    if re.match(r"^\d{2}-\d{2}-\d{4}", cleaned):
        return "%d-%m-%Y"
    if re.match(r"^\d{2}/\d{2}/\d{2}$", cleaned):
        return "%d/%m/%y"
    if re.match(r"^\d{8}$", cleaned):
        return "%Y%m%d"
    return None


def is_valid_calendar_date(value: str) -> bool:
    """Check if a date string represents a valid calendar date."""
    import re
    cleaned = value.strip()

    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", cleaned)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False
        if month in (4, 6, 9, 11) and day > 30:
            return False
        if month == 2:
            is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            if day > 29 or (not is_leap and day > 28):
                return False
        return True

    m2 = re.match(r"^(\d{2})/(\d{2})/(\d{4})", cleaned)
    if m2:
        day, month, year = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False
        if month in (4, 6, 9, 11) and day > 30:
            return False
        if month == 2:
            is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            if day > 29 or (not is_leap and day > 28):
                return False
        return True

    return False


EXCEL_FORMULA_ERRORS: set[str] = {
    "#REF!", "#DIV/0!", "#N/A", "#VALUE!", "#NAME?",
    "#NULL!", "#NUM!", "#NOMBRE?", "#ERROR!", "#¡REF!",
}

MULTIVALUE_SEPARATORS: list[str] = [",", ";", "/", "|"]
