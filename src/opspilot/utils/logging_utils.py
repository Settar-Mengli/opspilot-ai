import logging
from typing import Any


def configure_logging(level: int = logging.INFO) -> None:
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    if fields:
        serialized_fields = " ".join(
            f"{key}={fields[key]}" for key in sorted(fields)
        )
        logger.info("%s | %s", event, serialized_fields)
        return

    logger.info(event)
