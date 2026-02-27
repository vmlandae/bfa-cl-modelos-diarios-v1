"""
Logging estructurado para BFA-CL Modelos Diarios.

Reemplaza ``print()`` por ``logging`` estándar de Python con dos handlers:

- **Consola**: formato legible (preserva estilo visual actual con emojis).
- **Archivo**: JSONL estructurado (``logs/{fecha}/modelos.jsonl``).

Uso básico::

    # Al inicio del programa (main.py):
    from core.logger import setup_logging
    setup_logging(fecha_proceso="20260227")

    # En cada módulo:
    from core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Mensaje")

Con contexto de modelo (automático en JSONL)::

    from core.logger import contexto_modelo

    with contexto_modelo("mr_prepago_consumo"):
        logger.info("Ejecutando...")
        # → {"modelo": "mr_prepago_consumo", "msg": "Ejecutando..."} en JSONL

Compatibilidad GUI:
    ``DynamicStdoutHandler`` resuelve ``sys.stdout`` en cada ``emit()``,
    por lo que funciona correctamente incluso si ``StdoutRedirector`` de
    tkinter redirige stdout *después* de ``setup_logging()``.
"""

import builtins
import json
import logging
import sys
import contextvars
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Nombre base del logger del proyecto
# ---------------------------------------------------------------------------

_LOGGER_NAME = "bfa_modelos"

# Prevenir warning "No handler found" si se usa antes de setup_logging()
logging.getLogger(_LOGGER_NAME).addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Contexto de modelo (thread-safe via contextvars)
# ---------------------------------------------------------------------------

_modelo_actual: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "modelo_actual", default=None
)


@contextmanager
def contexto_modelo(nombre_modelo: str):
    """Context manager que asocia un nombre de modelo al hilo actual.

    Todos los log records emitidos dentro del bloque incluirán
    ``"modelo": "<nombre>"`` en el output JSONL automáticamente.

    Funciona correctamente con ``ThreadPoolExecutor``: cada hilo
    tiene su propio contexto independiente.

    Ejemplo::

        with contexto_modelo("mr_prepago_consumo"):
            logger.info("Iniciando modelo...")
    """
    token = _modelo_actual.set(nombre_modelo)
    try:
        yield
    finally:
        _modelo_actual.reset(token)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


class ConsoleFormatter(logging.Formatter):
    """Formatter de consola: solo el mensaje, sin prefijos de nivel/timestamp.

    Preserva el estilo visual actual del proyecto (emojis, indentación,
    separadores ``=``).  Incluye tracebacks si los hay.
    """

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                if msg and msg[-1] != "\n":
                    msg += "\n"
                msg += record.exc_text
        if record.stack_info:
            if msg and msg[-1] != "\n":
                msg += "\n"
            msg += self.formatStack(record.stack_info)
        return msg


class JsonlFormatter(logging.Formatter):
    """Formatter JSONL: una línea JSON por registro de log.

    Campos emitidos::

        ts        — ISO-8601 con milisegundos
        level     — DEBUG / INFO / WARNING / ERROR / CRITICAL
        logger    — nombre del logger (e.g. ``core.orquestador``)
        modelo    — nombre del modelo si hay contexto activo, o ``null``
        msg       — mensaje formateado
        exception — traceback completo (solo si hay excepción)
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.fromtimestamp(record.created).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "modelo": _modelo_actual.get(),
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class DynamicStdoutHandler(logging.StreamHandler):
    """StreamHandler que resuelve ``sys.stdout`` en cada ``emit()``.

    Garantiza compatibilidad con la GUI de tkinter: si ``sys.stdout``
    es redirigido por ``StdoutRedirector`` *después* de ``setup_logging()``,
    este handler usará el stdout redirigido automáticamente.
    """

    def __init__(self) -> None:
        # Inicializar con stdout actual (será re-resuelto en emit)
        super().__init__(sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


# ---------------------------------------------------------------------------
# Interceptor de print() → JSONL  (solución rápida F11)
# ---------------------------------------------------------------------------
#
# Monkey-patch de ``builtins.print`` para capturar los ~200+ ``print()``
# de los modelos individuales en el archivo JSONL, **sin necesidad de
# migrarlos uno por uno**.
#
# Estrategia:
#   - Solución rápida (esta): interceptar ``print()`` globalmente.
#     Ventaja: cobertura inmediata al 100 %.  Limitación: todos los
#     mensajes se registran como INFO y el texto es libre (no
#     estructurado).
#   - Solución robusta (mediano plazo): migrar cada ``print()`` a
#     ``logger.info/warning/error()`` con niveles y campos adecuados.
#     Permite filtrar por severidad, agregar campos extra, etc.
# ---------------------------------------------------------------------------

_original_print = builtins.print
_interceptor_guard = threading.local()


def _setup_print_interceptor(file_handler: logging.FileHandler) -> None:
    """Activa la captura de ``print()`` hacia el archivo JSONL.

    Crea un logger dedicado (``bfa_modelos._print_capture``) que **solo**
    tiene el ``FileHandler`` JSONL — sin handler de consola — para evitar
    duplicar la salida por pantalla.

    El ``print()`` original sigue funcionando con normalidad (consola y/o
    ``StdoutRedirector`` de la GUI).

    Se usa un guard *thread-local* para evitar re-entrada si algún
    handler escribe a stdout.
    """
    capture_logger = logging.getLogger(f"{_LOGGER_NAME}._print_capture")
    capture_logger.propagate = False
    capture_logger.setLevel(logging.DEBUG)
    capture_logger.addHandler(file_handler)

    def _intercepted_print(*args, **kwargs):
        # Ejecutar el print original (consola / GUI StdoutRedirector)
        _original_print(*args, **kwargs)

        # Si el print redirige a un file explícito, no capturar
        if kwargs.get("file") is not None:
            return

        # Guard contra re-entrada (thread-local)
        if getattr(_interceptor_guard, "active", False):
            return
        _interceptor_guard.active = True
        try:
            message = kwargs.get("sep", " ").join(str(a) for a in args)
            if message.strip():
                capture_logger.info(message)
        finally:
            _interceptor_guard.active = False

    builtins.print = _intercepted_print


# ---------------------------------------------------------------------------
# Setup público
# ---------------------------------------------------------------------------

_setup_done = False


def setup_logging(
    fecha_proceso: Optional[str] = None,
    nivel_consola: int = logging.INFO,
    nivel_archivo: int = logging.DEBUG,
) -> None:
    """Configura el logging del proyecto con handler de consola y archivo JSONL.

    Debe llamarse **una vez** al inicio del programa (en ``main.py``).
    Llamadas adicionales son no-op.

    Args:
        fecha_proceso: Fecha ``YYYYMMDD`` para organizar los logs en
                       ``logs/{fecha}/modelos.jsonl``.  Si ``None``, usa
                       la fecha actual.
        nivel_consola: Nivel mínimo para output a consola (default: INFO).
        nivel_archivo: Nivel mínimo para output a JSONL (default: DEBUG).
    """
    global _setup_done
    if _setup_done:
        return

    root = logging.getLogger(_LOGGER_NAME)
    root.setLevel(logging.DEBUG)
    root.propagate = False

    # Eliminar NullHandler de seguridad (ya no es necesario)
    root.handlers = [
        h for h in root.handlers if not isinstance(h, logging.NullHandler)
    ]

    # --- Handler consola (siempre) ---
    console_handler = DynamicStdoutHandler()
    console_handler.setLevel(nivel_consola)
    console_handler.setFormatter(ConsoleFormatter())
    root.addHandler(console_handler)

    # --- Handler archivo JSONL ---
    if fecha_proceso is None:
        fecha_proceso = datetime.now().strftime("%Y%m%d")

    base_dir = Path(__file__).resolve().parent.parent
    log_dir = base_dir / "logs" / fecha_proceso
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "modelos.jsonl"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(nivel_archivo)
    file_handler.setFormatter(JsonlFormatter())
    root.addHandler(file_handler)

    # --- Interceptor de print() → JSONL ---
    _setup_print_interceptor(file_handler)

    _setup_done = True


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger hijo del logger del proyecto.

    Args:
        name: Nombre del logger (típicamente ``__name__``).

    Returns:
        ``logging.Logger`` bajo ``bfa_modelos.{name}``.

    El logger hereda los handlers configurados por ``setup_logging()``.
    """
    return logging.getLogger(f"{_LOGGER_NAME}.{name}")
