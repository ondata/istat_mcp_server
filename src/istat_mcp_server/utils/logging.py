"""Logging configuration for the MCP server."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level: str = 'INFO', log_dir: str = None) -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory per i file di log. Se None, usa ./log relativo al package
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Determina la directory dei log
    if log_dir is None:
        # Directory log nella root del progetto
        package_dir = Path(__file__).parent.parent.parent.parent
        log_dir = package_dir / 'log'
    else:
        log_dir = Path(log_dir)

    # Crea la directory se non esiste
    log_dir.mkdir(exist_ok=True)

    # Path del file di log
    log_file = log_dir / 'istat_mcp_server.log'

    # Configurazione formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler per file con rotazione (max 10MB, mantieni 5 file)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # Handler per stderr
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f'Logging initialized at level {level}')
    logger.info(f'Log file: {log_file.absolute()}')
