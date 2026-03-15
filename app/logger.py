# ============================================================
# APP/LOGGER.PY — Structured JSON logging
# ============================================================
# Outputs JSON lines in production so Railway / Datadog /
# Logtail can parse and filter them easily.
# In development, outputs plain human-readable logs.
# ============================================================
import os
import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        obj = {
            "ts"      : datetime.now(timezone.utc).isoformat(),
            "level"   : record.levelname,
            "logger"  : record.name,
            "msg"     : record.getMessage(),
        }
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj)


def init_logging(app):
    env = os.environ.get("FLASK_ENV", "production")

    handler = logging.StreamHandler(sys.stdout)
    if env == "production":
        handler.setFormatter(_JsonFormatter())
        level = logging.INFO
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S"
        ))
        level = logging.DEBUG

    # Root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quieten noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app.logger.setLevel(level)
    app.logger.info(f"Logging initialised (env={env})")
