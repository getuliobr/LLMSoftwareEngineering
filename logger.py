import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent
# Diretório de logs
LOGS_DIR = BASE_DIR / "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuração do logger
logger = logging.getLogger("tools.info")

if not logger.handlers:
    logger.setLevel(logging.INFO)

    fmt = (
        "Data: %(asctime)s\n"
        "Tipo: [%(levelname)s]\n"
        "Module: %(module)s\n"
        "Role: %(role)s\n"
        "Tool: %(tool_name)s\n"
        "Resposta: %(message)s\n"
        "----------------------------------------"
    )
    # Formatter padrão
    formatter = logging.Formatter(
        fmt=fmt,
        datefmt="%d/%m/%Y %H:%M:%S"
    )

    # Handler para arquivo (com rotação)
    file_handler = RotatingFileHandler(
        LOGS_DIR / "tools.log", maxBytes=5_000_000, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Adiciona handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Evita propagação para o logger raiz
    logger.propagate = False

__all__ = ["logger"]
