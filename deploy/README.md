# Deploy no servidor (Ubuntu 24.04)

O app roda como o usuário `deploy`, em `/home/deploy/apps/relatorio_fin`. Os
comandos marcados com `sudo` são os únicos que precisam de privilégio.

O servidor já roda outros apps, então **confira as portas antes de subir**. O padrão
aqui é `8077` (API, só local) e `3007` (web). Se alguma estiver ocupada, troque nos
dois lugares indicados no passo 5.

## 1. Conferir as portas

```bash
sudo ss -tulpn | grep -E ':(3007|8077)\s' || echo "portas 3007 e 8077 livres"
```

Sem saída do `grep` = livre. Para ver tudo que já está ocupado:

```bash
sudo ss -tulpn | grep LISTEN
```

## 2. Conferir os pré-requisitos

```bash
python3 --version     # precisa ser 3.11 ou maior
node --version        # precisa ser 20.9 ou maior (Next 16)
npm --version
```

Se o Node for antigo:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

Se faltar o venv do Python:

```bash
sudo apt install -y python3-venv python3-pip
```

## 3. Trazer o código

```bash
su - deploy
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/Jeff1984Sor/relatorrio_fin.git relatorio_fin
cd relatorio_fin
```

Nas próximas vezes, só `git pull`.

## 4. Instalar, testar e buildar

```bash
bash deploy/deploy.sh
```

O script cria o virtualenv, instala as dependências, cria o banco SQLite, **roda os
testes** e faz o build do Next. Se os testes falharem ele para antes de publicar.

## 5. Instalar os serviços (sobem sozinhos no boot)

Se você trocou alguma porta, ajuste antes: `--port` em `relatorio-fin-api.service` e
`PORT=` / `BACKEND_URL=` em `relatorio-fin-web.service`.

```bash
sudo cp /home/deploy/apps/relatorio_fin/deploy/relatorio-fin-api.service /etc/systemd/system/
sudo cp /home/deploy/apps/relatorio_fin/deploy/relatorio-fin-web.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now relatorio-fin-api relatorio-fin-web
```

O `enable` é o que garante que os dois voltem sozinhos quando o servidor for
desligado e ligado de novo. O `Restart=always` cobre o caso de o processo morrer.

## 6. Conferir se subiu

```bash
sudo systemctl status relatorio-fin-api --no-pager
sudo systemctl status relatorio-fin-web --no-pager

curl -s http://127.0.0.1:8077/api/saude     # {"status":"ok"}
curl -sI http://127.0.0.1:3007 | head -1    # HTTP/1.1 200 OK
```

Acesse no navegador: `http://SEU_IP:3007`

Se não abrir de fora, libere a porta no firewall:

```bash
sudo ufw status
sudo ufw allow 3007/tcp
```

## Migrar de uma instalação feita em /root

Se o app já subiu uma vez como `root`, mude para o `deploy` assim:

```bash
# 1. Parar e desabilitar os serviços antigos
sudo systemctl disable --now relatorio-fin-api relatorio-fin-web

# 2. Levar o código e os dados para o deploy
sudo mkdir -p /home/deploy/apps
sudo mv /root/apps/relatorio_fin /home/deploy/apps/
sudo chown -R deploy:deploy /home/deploy/apps/relatorio_fin

# 3. O virtualenv tem caminho absoluto embutido — precisa ser refeito
sudo -u deploy rm -rf /home/deploy/apps/relatorio_fin/backend/.venv
su - deploy -c 'cd ~/apps/relatorio_fin && bash deploy/deploy.sh'

# 4. Reinstalar as units já com os caminhos novos e religar
sudo cp /home/deploy/apps/relatorio_fin/deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now relatorio-fin-api relatorio-fin-web
```

O banco e os `.xlsx` gerados vão junto no `mv` (estão em `backend/data/`).

## Comandos do dia a dia

```bash
# Ver o log ao vivo
sudo journalctl -u relatorio-fin-api -f
sudo journalctl -u relatorio-fin-web -f

# Reiniciar
sudo systemctl restart relatorio-fin-api relatorio-fin-web

# Atualizar para a última versão do código
su - deploy -c 'cd ~/apps/relatorio_fin && git pull && bash deploy/deploy.sh'
sudo systemctl restart relatorio-fin-api relatorio-fin-web
```

## Backup

Tudo que importa está em um diretório só:

```bash
tar czf ~/backup-relatorio-fin-$(date +%F).tar.gz \
  -C /home/deploy/apps/relatorio_fin/backend data
```

`data/relatorio_fin.db` é o banco e `data/arquivos/` são os `.xlsx` gerados.

## Opcional: domínio com nginx

Se quiser acessar por um domínio em vez de `IP:3007`:

```nginx
server {
    listen 80;
    server_name relatorio.seudominio.com.br;

    client_max_body_size 20M;   # o limite do app é 15 MB

    location / {
        proxy_pass http://127.0.0.1:3007;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo nano /etc/nginx/sites-available/relatorio-fin
sudo ln -s /etc/nginx/sites-available/relatorio-fin /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d relatorio.seudominio.com.br   # HTTPS
```

Com nginx na frente, feche a 3007 no firewall (`sudo ufw delete allow 3007/tcp`).

## Se der problema

| Sintoma | O que olhar |
|---|---|
| Serviço não sobe | `sudo journalctl -u relatorio-fin-api -n 50 --no-pager` |
| `Address already in use` | Outra app pegou a porta: `sudo ss -tulpn \| grep 8077` e troque a porta |
| Web abre mas a API dá erro | `BACKEND_URL` no `.service` tem que apontar para a porta real da API |
| `permission denied` no banco | `sudo chown -R deploy:deploy /home/deploy/apps/relatorio_fin/backend/data` |
| Build do Next falha | Node abaixo de 20.9 — ver passo 2 |
