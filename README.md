<div align="center">

# 🛍️ Promogram Backend

**API REST + scraper de promoções do Telegram para o Promogram**

Coleta automaticamente ofertas e cupons publicados em grupos/canais do Telegram, estrutura os dados e os expõe através de uma API REST para consumo por um frontend.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Telethon](https://img.shields.io/badge/Telethon-Telegram_API-26A5E4?logo=telegram&logoColor=white)](https://docs.telethon.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📑 Sumário

- [Sobre o projeto](#-sobre-o-projeto)
- [Como funciona](#️-como-funciona)
- [Funcionalidades](#-funcionalidades)
- [Tecnologias](#-tecnologias)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Modelos de dados](#️-modelos-de-dados)
- [Endpoints da API](#-endpoints-da-api)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Variáveis de ambiente](#-variáveis-de-ambiente)
- [Executando localmente](#️-executando-localmente)
- [Sessão do Telegram em produção](#-sessão-do-telegram-em-produção)
- [Deploy](#️-deploy)
- [Possíveis melhorias](#-possíveis-melhorias)
- [Licença](#-licença)
- [Autor](#-autor)

---

## 📖 Sobre o projeto

O **Promogram Backend** é o serviço que dá suporte ao Promogram, um agregador de promoções e cupons. O sistema é composto por duas partes que trabalham juntas:

1. Um **scraper** (`scraper.py`) que se conecta a grupos e canais do Telegram usando [Telethon](https://docs.telethon.dev/) e interpreta as mensagens publicadas para identificar se tratam de um **Produto** em oferta ou de um **Cupom** de desconto;
2. Uma **API REST** (`main.py`), construída com [FastAPI](https://fastapi.tiangolo.com/), que recebe esses dados, persiste em um banco **PostgreSQL** e os disponibiliza para um frontend consumir.

O nome remete à junção de **Promoção + Telegram** — a origem das ofertas que o sistema coleta.

## ⚙️ Como funciona

```mermaid
flowchart LR
    A["Grupos/Canais no Telegram"] -->|"Telethon"| B["scraper.py"]
    B -->|"heurísticas via regex"| C{"Produto ou Cupom?"}
    C -->|"Produto"| D["POST /produtos"]
    C -->|"Cupom"| E["POST /cupons"]
    D --> F[("PostgreSQL")]
    E --> F
    F --> G["API FastAPI"]
    G --> H["Frontend / clientes"]
```

1. O scraper escuta mensagens novas em tempo real **ou** varre o histórico de mensagens de cada grupo configurado.
2. Cada texto é analisado por expressões regulares para extrair nome, preço, preço parcelado, link, código de cupom, percentual de desconto e valor mínimo de compra.
3. O resultado é classificado como `produto` ou `cupom` e enviado via HTTP para a API (`/produtos` ou `/cupons`).
4. A API valida os dados com **Pydantic**, persiste com **SQLAlchemy** e os deixa disponíveis via endpoints REST paginados.
5. A própria API expõe um endpoint (`/scraper/executar`) para disparar o scraper remotamente em background, com trava para impedir execuções concorrentes.

## ✨ Funcionalidades

- CRUD completo de **produtos** e **cupons** promocionais.
- Scraper de mensagens do Telegram em **modo tempo real** e **modo histórico** (com limite configurável).
- Extração automática por regex de preço, preço parcelado, cupom, percentual de desconto, valor mínimo de compra e link.
- Download opcional das imagens anexadas às mensagens (`DOWNLOAD_IMAGENS`).
- Endpoint para disparar o scraper remotamente e consultar seu status (`em_execucao`, `modo`, `ultimo_resultado`).
- Trava em memória que impede duas execuções simultâneas do scraper.
- CORS configurável por variável de ambiente.
- Suporte a **StringSession** do Telethon, permitindo rodar o scraper em ambientes sem disco persistente (Vercel, Lambda, containers efêmeros etc.).

## 🧱 Tecnologias

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| Banco de dados | PostgreSQL |
| ORM | SQLAlchemy |
| Validação de dados | Pydantic |
| Cliente Telegram | Telethon |
| Configuração | python-dotenv |
| HTTP client (scraper → API) | requests |

## 📁 Estrutura do projeto

```
promogram-backend/
├── db/
│   ├── __init__.py
│   ├── database.py      # engine, sessão e Base do SQLAlchemy
│   ├── models.py        # modelos ORM (Produto, Cupom)
│   └── schemas.py       # schemas Pydantic de entrada/saída
├── gerar_sessao.py      # gera uma StringSession do Telethon para produção
├── scraper.py           # scraper de grupos/canais do Telegram
├── main.py              # aplicação FastAPI (rotas da API)
├── requirements.txt
├── Procfile             # comando de start do worker do scraper
├── Render.yml           # configuração de deploy da API no Render
└── LICENSE
```

## 🗃️ Modelos de dados

**Produto**

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int | Identificador |
| `nome` | string | Nome do produto |
| `preco` | decimal | Preço à vista |
| `preco_parcelado` | decimal | Preço parcelado, se houver |
| `link` | string | Link para a oferta |
| `cupom` | string | Código de cupom associado, se houver |
| `imagem` | string | Caminho/URL da imagem |
| `publicado` | bool | Se o item deve ser exibido (padrão `true`) |
| `created_at` | timestamp | Data de criação |

**Cupom**

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | int | Identificador |
| `nome` | string | Nome/descrição do cupom |
| `codigo` | string | Código promocional |
| `desconto` | string | Percentual/descrição do desconto |
| `limite_minimo` | decimal | Valor mínimo de compra exigido |
| `link` | string | Link relacionado |
| `imagem` | string | Caminho/URL da imagem |
| `publicado` | bool | Se o item deve ser exibido (padrão `true`) |
| `created_at` | timestamp | Data de criação |

## 🔌 Endpoints da API

| Método | Rota | Descrição | Sucesso |
|---|---|---|---|
| `POST` | `/produtos` | Cria um produto | `201` |
| `GET` | `/produtos` | Lista produtos (`skip`, `limit`) | `200` |
| `PUT` | `/produtos/{produto_id}` | Atualiza um produto | `200` / `404` |
| `DELETE` | `/produtos/{produto_id}` | Remove um produto | `204` / `404` |
| `POST` | `/cupons` | Cria um cupom | `201` |
| `GET` | `/cupons` | Lista cupons (`skip`, `limit`) | `200` |
| `PUT` | `/cupons/{cupom_id}` | Atualiza um cupom | `200` / `404` |
| `DELETE` | `/cupons/{cupom_id}` | Remove um cupom | `204` / `404` |
| `POST` | `/scraper/executar` | Dispara o scraper em background (`modo=historico\|tempo_real`, `limite`) | `202` / `409` se já em execução |
| `GET` | `/scraper/status` | Consulta o status atual do scraper | `200` |

Com a API rodando, a documentação interativa (Swagger) fica disponível em `/docs` e o esquema OpenAPI em `/openapi.json`.

> ⚠️ Atualmente as rotas de escrita (`POST`/`PUT`/`DELETE`) não possuem autenticação — veja [Possíveis melhorias](#-possíveis-melhorias).

## ✅ Pré-requisitos

- Python 3.11 ou superior
- Um banco **PostgreSQL** (local ou hospedado — Render, Supabase, Neon etc.)
- Credenciais de API do Telegram em [my.telegram.org](https://my.telegram.org) (necessárias apenas para usar o scraper)

## 🚀 Instalação

```bash
git clone https://github.com/Victor-Gabriel-Barbosa/promogram-backend.git
cd promogram-backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## 🔐 Variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
# Obrigatório para a API
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco
CORS_ORIGINS=http://localhost:3000

# Obrigatório apenas para usar o scraper
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=sua_api_hash_aqui
TELEGRAM_GRUPOS=nome_do_grupo,-1001234567890

# Opcionais
TELEGRAM_SESSION_STRING=
SESSION=scraper_session
BACKEND_URL=http://localhost:8000
DOWNLOAD_IMAGENS=false
```

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `DATABASE_URL` | Sim (API) | — | String de conexão do PostgreSQL |
| `CORS_ORIGINS` | Não | `http://localhost:3000` | Origens permitidas, separadas por vírgula |
| `TELEGRAM_API_ID` | Sim (scraper) | — | ID gerado em my.telegram.org |
| `TELEGRAM_API_HASH` | Sim (scraper) | — | Hash gerado em my.telegram.org |
| `TELEGRAM_GRUPOS` | Sim (scraper) | — | Grupos/canais a monitorar (username público ou ID numérico), separados por vírgula |
| `TELEGRAM_SESSION_STRING` | Não | vazio | StringSession do Telethon, para ambientes sem disco persistente |
| `SESSION` | Não | `scraper_session` | Nome do arquivo de sessão local (usado se `TELEGRAM_SESSION_STRING` não estiver definida) |
| `BACKEND_URL` | Não | `http://localhost:8000` | URL da API para onde o scraper envia os dados |
| `DOWNLOAD_IMAGENS` | Não | `false` | Baixa localmente as imagens anexadas às mensagens |

## ▶️ Executando localmente

**API**

```bash
uvicorn main:app --reload
```

A API sobe em `http://localhost:8000` e a documentação interativa em `http://localhost:8000/docs`.

**Scraper**

```bash
python scraper.py                       # escuta mensagens novas em tempo real
python scraper.py --historico            # varre as últimas 200 mensagens de cada grupo
python scraper.py --historico --limite 500
```

## 🔑 Sessão do Telegram em produção

Em ambientes sem disco persistente (Vercel, Lambda, containers efêmeros), o Telethon precisa de uma **StringSession** em vez de um arquivo de sessão local. Para gerar uma:

```bash
python gerar_sessao.py
```

O script solicita seu número de telefone e o código enviado pelo Telegram e, ao final, imprime uma string. Copie-a e defina como a variável de ambiente `TELEGRAM_SESSION_STRING` no seu provedor de hospedagem (marcada como secreta).

> ⚠️ Trate essa string como uma senha: quem a possuir consegue autenticar na sua conta do Telegram sem precisar do código de verificação.

## ☁️ Deploy

O projeto inclui um `Render.yml` para deploy da API no [Render](https://render.com/):

```yaml
services:
  - type: web
    name: api-promogram
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: CORS_ORIGINS
        sync: false
```

Há também um `Procfile`, tipicamente usado por plataformas como Heroku/Railway para subir o scraper como um *worker* separado — nesse caso, garanta que o comando aponte para o nome atual do arquivo (`scraper.py`).

O repositório também lista uma instância publicada em `promogram-backend.vercel.app`. Vale lembrar que ambientes serverless como a Vercel são adequados para a **API** (funções de curta duração), mas não sustentam o **modo tempo real** do scraper, que precisa de um processo contínuo — para isso, prefira um *worker* dedicado (Render, VPS) ou dispare execuções pontuais via `POST /scraper/executar`.

## 📄 Licença

Distribuído sob a licença **MIT**. Veja [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

**Victor Gabriel Barbosa**
GitHub: [@Victor-Gabriel-Barbosa](https://github.com/Victor-Gabriel-Barbosa)
