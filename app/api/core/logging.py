import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.api.core.config import settings

# Context variable for request ID tracking
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add request ID to log context if available.
    """
    request_id = request_id_var.get("")
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to every log entry.
    """
    event_dict["app_name"] = settings.app_name
    event_dict["app_version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Remove color_message key from event dict (used by ConsoleRenderer).
    """
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging() -> None:
    """
    Configure structured logging using structlog.

    Features:
    - JSON output in production
    - Pretty-printed console output in development
    - Request ID tracking
    - Consistent log levels
    - Timestamped entries
    """

    # Determine log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors for all configurations
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_request_id,
        add_app_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_development:
        # Development: pretty console output with colors
        processors = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            drop_color_message_key,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured structlog logger

    Example:
        logger = get_logger(__name__)
        logger.info("user_registered", user_id=123, email="user@example.com")
    """
    return structlog.get_logger(name)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.

    Args:
        request_id: Unique request identifier
    """
    request_id_var.set(request_id)


def get_request_id() -> str:
    """
    Get the current request ID from context.

    Returns:
        Current request ID or empty string if not set
    """
    return request_id_var.get("")


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.

    Usage:
        class MyService(LoggerMixin):
            def do_something(self):
                self.logger.info("doing_something", param="value")
    """

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger bound to the class name."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


# Example usage and helper functions
def log_function_call(func_name: str, **kwargs: Any) -> None:
    """
    Helper to log function calls with parameters.

    Args:
        func_name: Name of the function being called
        **kwargs: Function parameters to log
    """
    logger = get_logger("function_call")
    logger.debug("function_called", function=func_name, **kwargs)


def log_error(error: Exception, context: dict[str, Any] | None = None) -> None:
    """
    Helper to log errors with context.

    Args:
        error: Exception that occurred
        context: Additional context about the error
    """
    logger = get_logger("error")
    log_context = context or {}
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        **log_context,
        exc_info=True,
    )
