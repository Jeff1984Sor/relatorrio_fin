"""Configuração da aplicação, lida do ambiente.

Não há banco nem diretório de dados: o processamento é sem estado e o arquivo
enviado só existe na memória durante o request.
"""

import os

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

EXTENSOES_ACEITAS = {".xlsx", ".xls", ".xlsm", ".csv"}

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
