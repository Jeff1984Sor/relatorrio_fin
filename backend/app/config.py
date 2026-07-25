"""Configuração da aplicação, lida do ambiente."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", DATA_DIR / "arquivos"))

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'relatorio_fin.db'}")

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

EXTENSOES_ACEITAS = {".xlsx", ".xls", ".xlsm", ".csv"}

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

# Enquanto não há autenticação integrada, todo processamento é atribuído a este usuário.
USUARIO_PADRAO = os.getenv("USUARIO_PADRAO", "sistema")


def garantir_diretorios() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
