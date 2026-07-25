# Deploy no servidor (Ubuntu 24.04)

Todos os comandos rodam como `root`, em `/root/apps/relatorio_fin`.

> Rodar como root deixa o app com privilégio total na máquina, e ele recebe upload
> de arquivo de fora. Se um dia quiser trocar para um usuário sem privilégio, é
> substituir `root` por `deploy` e `/root` por `/home/deploy` nos dois arquivos
> `.service`, e `chown -R deploy:deploy` na pasta do projeto.

O servidor já roda outros apps, então **confira as portas antes de subir**. O padrão
aqui é `8077` (API, só local) e `3007` (web). Se alguma estiver ocupada, troque nos
dois lugares indicados no passo 5.

## 1. Conferir as portas

```bash
ss -tulpn | grep -E ':(3007|8077)\s' || echo "portas 3007 e 8077 livres"
```

Sem saída do `grep` = livre. Para ver tudo que já está ocupado:

```bash
ss -tulpn | grep LISTEN
```

## 2. Conferir os pré-requisitos

```bash
python3 --version     # precisa ser 3.11 ou maior
node --version        # precisa ser 20.9 ou maior (Next 16)
npm --version
```

Se o Node for antigo:

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
```

Se faltar o venv do Python:

```bash
apt install -y python3-venv python3-pip
```

## 3. Trazer o código

```bash
mkdir -p /root/apps && cd /root/apps
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
cp /root/apps/relatorio_fin/deploy/relatorio-fin-api.service /etc/systemd/system/
cp /root/apps/relatorio_fin/deploy/relatorio-fin-web.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now relatorio-fin-api relatorio-fin-web
```

O `enable` é o que garante que os dois voltem sozinhos quando o servidor for
desligado e ligado de novo. O `Restart=always` cobre o caso de o processo morrer.

## 6. Conferir se subiu

```bash
systemctl status relatorio-fin-api --no-pager
systemctl status relatorio-fin-web --no-pager

curl -s http://127.0.0.1:8077/api/saude     # {"status":"ok"}
curl -sI http://127.0.0.1:3007 | head -1    # HTTP/1.1 200 OK
```

Acesse no navegador: `http://SEU_IP:3007`

Se não abrir de fora, libere a porta no firewall:

```bash
ufw status
ufw allow 3007/tcp
```

## Comandos do dia a dia

```bash
# Ver o log ao vivo
journalctl -u relatorio-fin-api -f
journalctl -u relatorio-fin-web -f

# Reiniciar
systemctl restart relatorio-fin-api relatorio-fin-web

# Atualizar para a última versão do código
cd /root/apps/relatorio_fin && git pull && bash deploy/deploy.sh
systemctl restart relatorio-fin-api relatorio-fin-web
```

## Backup

Tudo que importa está em um diretório só:

```bash
tar czf /root/backup-relatorio-fin-$(date +%F).tar.gz -C /root/apps/relatorio_fin/backend data
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
nano /etc/nginx/sites-available/relatorio-fin
ln -s /etc/nginx/sites-available/relatorio-fin /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d relatorio.seudominio.com.br   # HTTPS
```

Com nginx na frente, feche a 3007 no firewall (`ufw delete allow 3007/tcp`).

## Se der problema

| Sintoma | O que olhar |
|---|---|
| Serviço não sobe | `journalctl -u relatorio-fin-api -n 50 --no-pager` |
| `Address already in use` | Outra app pegou a porta: `ss -tulpn \| grep 8077` e troque a porta |
| Web abre mas a API dá erro | `BACKEND_URL` no `.service` tem que apontar para a porta real da API |
| Build do Next falha | Node abaixo de 20.9 — ver passo 2 |
