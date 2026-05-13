"""Cuadratura input ↔ output (F29 — fase 4).

Reconcilia el ``CAPITAL`` / ``INTERES`` del INPUT del modelo (PML, Access,
Excel) con el ``SUM(AMORTIZACION)`` / ``SUM(INTERES)`` del OUTPUT cargado
a BQ. Este es el check que habría detectado el "error grueso" reciente
de desbalance entre lo que entra y lo que sale.

Estado actual: stub. Cada tipo de input (`pml_gcp`, `pml_cmr`, `access`,
`manual`) requiere su propio lector. El motor llama ``check_cuadratura``;
mientras los lectores no estén implementados, devolvemos INFO (no
alerta) para que sea visible en el dashboard sin levantar falsos
positivos.

Roadmap:
- pml_gcp / pml_cmr: reutilizar lectores de ``core/control_interfaces.py:169-178``
- access: lector parametrizable por YAML (``ruta_tabla``, ``columna_*``)
- manual: omite cuadratura (registra INFO)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING

from core.modelos_registry import tabla_dly

if TYPE_CHECKING:  # pragma: no cover
    from core.controles_outputs import CheckResultado

logger = logging.getLogger("bfa_modelos.controles_cuadratura")


def check_cuadratura(modelo: str, fecha: str, cfg_controles: dict) -> "list[CheckResultado]":
    """Retorna lista de CheckResultado para cuadratura capital + interés.

    Args:
        modelo: clave del modelo (ej ``ml_mora_consumo``).
        fecha: ISO YYYY-MM-DD.
        cfg_controles: sección ``controles`` del YAML.

    Returns:
        Lista de checks. En esta fase devolvemos INFO si el lector aún no
        está implementado, para evitar falsos positivos. Cuando se
        implemente, devolverá OK/WARNING/CRITICAL.
    """
    # Import diferido para evitar ciclo
    from core.controles_outputs import CheckResultado, _VERSION_MOTOR
    import socket
    from datetime import datetime

    cfg_input = (cfg_controles.get("cuadratura_inputs") or {}).get(modelo, {})
    tipo = cfg_input.get("tipo", "no_configurado")
    tabla = tabla_dly(modelo)

    def _info(mensaje: str, evidencia: dict | None = None) -> CheckResultado:
        return CheckResultado(
            modelo=modelo, tabla=tabla, check_id="cuadratura_capital",
            nivel="INFO", mensaje=mensaje, fecha_proceso=fecha,
            fecha_anterior=None, evidencia=evidencia or {"tipo": tipo},
            timestamp=datetime.now().isoformat(timespec="seconds"),
            hostname=socket.gethostname(), version_motor=_VERSION_MOTOR,
        )

    if tipo == "manual":
        nota = cfg_input.get("nota", "")
        return [_info(
            f"Cuadratura no aplica: modelo manual. {nota}".strip(),
        )]
    if tipo == "no_configurado":
        return [_info("Cuadratura no configurada para este modelo en YAML.")]

    # Stub: lectores reales se implementan en fase 4 del sprint S6.
    return [_info(f"Cuadratura pendiente de implementación (tipo={tipo}).")]
