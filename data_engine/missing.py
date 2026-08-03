"""Tabla única de tokens de valor faltante (AP-04 / X1).

Todos los módulos (analyzer, diagnostic, domain_rules) usan esta única
definición para que el Paso 1 (perfilado) y el Paso 3 (diagnóstico) cuenten
missing de la misma forma.

DM-03/A4: "pendiente", "9999" y "-1" son valores LEGÍTIMOS en la práctica y NO
están en la lista base. Para datasets con sentinelas específicos se puede usar
`EXTENDED_MISSING_TOKENS` (lista opcional configurable por dataset), pero por
defecto esos valores se consideran datos reales.
"""

from __future__ import annotations

from typing import Any

MISSING_TOKENS: set[str] = {
    "", "na", "n/a", "null", "none", "nan", "-",
    "n/d", "nd", "sin dato", "sin datos", "no aplica", "no disponible",
    "desconocido", "no reportado", "missing", "?", "--", "s/d", "s/dato", "n/r",
    " ", "  ", "\t", "\n",
}

# Sentinelas opcionales por dataset; vacío por defecto.
EXTENDED_MISSING_TOKENS: set[str] = set()


def is_missing(value: Any) -> bool:
    """Return True if a value is a missing token (None or in the unified table)."""
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_TOKENS or str(value).strip().lower() in EXTENDED_MISSING_TOKENS
