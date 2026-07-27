#!/usr/bin/env bash
# Deploy do Relatório Fin. Rode como o usuário `deploy`, dentro da pasta do projeto:
#     bash deploy/deploy.sh
# É idempotente: serve tanto para a primeira instalação quanto para atualizar.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$RAIZ/backend"
FRONTEND="$RAIZ/frontend"

echo "==> Projeto em $RAIZ"

echo "==> Backend: virtualenv e dependências"
if [ ! -d "$BACKEND/.venv" ]; then
  python3 -m venv "$BACKEND/.venv"
fi
"$BACKEND/.venv/bin/pip" install --upgrade pip --quiet
"$BACKEND/.venv/bin/pip" install -r "$BACKEND/requirements.txt" --quiet

echo "==> Backend: testes"
(cd "$BACKEND" && "$BACKEND/.venv/bin/python" -m pytest -q)

echo "==> Frontend: dependências e build"
(cd "$FRONTEND" && npm ci --no-audit --no-fund 2>/dev/null || npm install --no-audit --no-fund)
(cd "$FRONTEND" && npm run build)

echo
echo "==> Pronto. Para (re)iniciar os serviços:"
echo "    sudo systemctl restart relatorio-fin-api relatorio-fin-web"
