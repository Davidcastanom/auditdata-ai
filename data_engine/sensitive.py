"""Detección de posibles datos sensibles o personales de alto riesgo.

El copiloto de IA envía columnas, preguntas y valores de ejemplo a un proveedor
externo (Groq). Antes de que eso ocurra, la app detecta si el dataset parece
contener datos sensibles (salud, biometría, religión, vida sexual, menores,
identidad, contacto personal, financiero) y exige una autorización explícita.

Es una heurística por nombre de columna: puede tener falsos positivos o negativos,
por eso el aviso dice "parece contener" y la decisión final siempre es del usuario.
"""

import re
import unicodedata

SENSITIVE_GROUPS: dict[str, list[str]] = {
    "identidad": [
        "documento",
        "cedula",
        "identificacion",
        "identificacion completa",
        "dni",
        "pasaporte",
        "seguridad social",
        "social security",
        "ssn",
        "tax id",
        "licencia de conducir",
    ],
    "contacto personal": [
        "email",
        "correo",
        "correo electronico",
        "e-mail",
        "mail",
        "telefono",
        "celular",
        "movil",
        "whatsapp",
        "direccion",
        "domicilio",
    ],
    "salud y biometria": [
        "salud",
        "diagnostico",
        "enfermedad",
        "historia clinica",
        "condicion medica",
        "medico",
        "health",
        "medical",
        "biometri",
        "huella",
        "iris",
        "facial",
        "adn",
        "dna",
    ],
    "religion o ideologia": [
        "religion",
        "creencia",
        "ideologia",
        "partido politico",
        "sindical",
        "afiliacion sindical",
    ],
    "vida privada": [
        "orientacion sexual",
        "vida sexual",
        "sexual",
    ],
    "menores": [
        "menor de edad",
        "menor",
        "nino",
        "nino y adolescente",
    ],
    "financiero o patrimonial": [
        "salario",
        "ingreso",
        "sueldo",
        "tarjeta",
        "cuenta bancaria",
        "numero de cuenta",
        "iban",
        "patrimonio",
        "deuda",
        "credito",
        "credit card",
    ],
}

def _normalize(text: str) -> str:
    """Minusculas y sin acentos: 'Cédula' -> 'cedula', 'TELÉFONO' -> 'telefono'."""
    decomposed = unicodedata.normalize("NFD", str(text))
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.lower()


# Patrones ya compilados y normalizados (minusculas, sin acentos).
_SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = []
for group, keywords in SENSITIVE_GROUPS.items():
    for keyword in keywords:
        escaped = re.escape(_normalize(keyword))
        pattern = re.compile(rf"(?<!\w){escaped}(?!\w)")
        _SENSITIVE_PATTERNS.append((group, pattern))


def detect_sensitive_columns(headers: list[str]) -> list[str]:
    """Devuelve las columnas cuyo nombre sugiere datos sensibles o de alto riesgo.

    Excluye identificadores tecnicos genericos como 'id' (fila/registro).
    """
    found: list[str] = []
    for header in headers:
        if header is None:
            continue
        name = str(header)
        if name.strip().lower() == "id":
            continue
        normalized = _normalize(name)
        if any(pattern.search(normalized) for _, pattern in _SENSITIVE_PATTERNS):
            found.append(name)
    return found


def sensitive_groups_for(headers: list[str]) -> list[str]:
    """Devuelve las categorias presentes (para el mensaje del modal)."""
    groups: list[str] = []
    for header in headers:
        if header is None:
            continue
        if str(header).strip().lower() == "id":
            continue
        normalized = _normalize(str(header))
        for group, pattern in _SENSITIVE_PATTERNS:
            if pattern.search(normalized) and group not in groups:
                groups.append(group)
    return groups
