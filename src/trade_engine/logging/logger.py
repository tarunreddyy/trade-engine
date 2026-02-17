import json
import logging
from datetime import datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _build_logger() -> logging.Logger:
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"trade_engine_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"

    logger_instance = logging.getLogger("TradeEngine")
    logger_instance.setLevel(logging.INFO)
    logger_instance.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())
    logger_instance.addHandler(file_handler)
    logger_instance.propagate = False
    return logger_instance


logger = _build_logger()

# Backward compatibility for existing imports:
# `from trade_engine.logging.logger import logging`
