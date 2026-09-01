"""
Scraper de grupos do Telegram para extrair Produto e Cupom.

Usa Telethon (biblioteca de cliente Telegram) para ler mensagens de grupos
dos quais você já é membro, tenta identificar se cada mensagem é um Produto
ou um Cupom com base em heurísticas simples (regex), e envia o resultado
para a API FastAPI já existente (endpoints /produtos e /cupons).

Instalação:
    pip install telethon requests python-dotenv

Configuração:
    1. Crie uma aplicação em https://my.telegram.org -> "API development tools"
    2. Copie TELEGRAM_API_ID e TELEGRAM_API_HASH para um arquivo .env
       (veja .env.example)
    3. Defina TELEGRAM_GRUPOS com os grupos/canais que quer escutar
       (username público, ex: "promocoesbrasil", ou o ID numérico do grupo)

Uso:
    python telegram_scraper.py                 # escuta mensagens novas em tempo real
    python telegram_scraper.py --historico      # varre mensagens antigas dos grupos
    python telegram_scraper.py --historico --limite 500
"""

import argparse
import asyncio
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

load_dotenv()

# --------------------------------------------------------------------------
# Configuração
# --------------------------------------------------------------------------
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "")
SESSION_NAME = os.getenv("SESSION", "scraper_session")
_SESSION = StringSession(TELEGRAM_SESSION_STRING) if TELEGRAM_SESSION_STRING else SESSION_NAME

TELEGRAM_GRUPOS = [g.strip() for g in os.getenv("TELEGRAM_GRUPOS", "").split(",") if g.strip()]
TELEGRAM_GRUPOS = [int(g) if re.fullmatch(r"-?\d+", g) else g for g in TELEGRAM_GRUPOS]

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DOWNLOAD_IMAGENS = os.getenv("DOWNLOAD_IMAGENS", "false").lower() == "true"
PASTA_IMAGENS = "imagens_baixadas"

client = TelegramClient(_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)

# Trava para impedir que dois disparos do scraper rodem ao mesmo tempo
_scraper_lock = asyncio.Lock()


# --------------------------------------------------------------------------
# Extração de dados (heurísticas via regex)
# --------------------------------------------------------------------------
PRICE_TOKEN = r"[\d.]+,\d{2}|\d+"
PRICE_RE = re.compile(rf"r\$\s*({PRICE_TOKEN})", re.IGNORECASE)
POR_RE = re.compile(rf"por\s*(?:apenas\s*)?r\$\s*({PRICE_TOKEN})", re.IGNORECASE)
PARCELADO_RE = re.compile(rf"r\$\s*({PRICE_TOKEN})\s*(?:em\s*)?\d{{1,2}}\s*x", re.IGNORECASE)
LINK_RE = re.compile(r"(https?://\S+)")
CODIGO_RE = re.compile(r"c[oó]digo[:\s]*(.+)", re.IGNORECASE)
CUPOM_RE = re.compile(r"cupom[:\s]*(.+)", re.IGNORECASE)
DESCONTO_RE = re.compile(r"(\d{1,3}\s?%\s?(?:off|de desconto)?)", re.IGNORECASE)
LIMITE_MINIMO_RE = re.compile(
    rf"(?:m[ií]nimo|acima de)[:\s]*r\$\s*({PRICE_TOKEN})", re.IGNORECASE
)

PALAVRAS_CUPOM = ["cupom", "código promocional", "code:"]


def _to_decimal(valor_str: str | None) -> Decimal | None:
    if not valor_str:
        return None
    limpo = valor_str.replace(".", "").replace(",", ".")
    try:
        return Decimal(limpo)
    except InvalidOperation:
        return None


def extrair_nome(texto: str) -> str:
    linhas = [l.strip() for l in texto.split("\n") if l.strip()]
    for linha in linhas:
        if LINK_RE.fullmatch(linha):
            continue
        if PRICE_RE.fullmatch(linha):
            continue
        return linha[:255]
    return "Produto sem nome"


def extrair_link(texto: str) -> str | None:
    m = LINK_RE.search(texto)
    return m.group(1) if m else None


def extrair_precos(texto: str) -> tuple[Decimal | None, Decimal | None]:
    preco: Decimal | None = None
    preco_parcelado: Decimal | None = None

    if m_por := POR_RE.search(texto):
        preco = _to_decimal(m_por.group(1))

    if m_parcelado := PARCELADO_RE.search(texto):
        preco_parcelado = _to_decimal(m_parcelado.group(1))

    if preco is None:
        todos = [_to_decimal(p) for p in PRICE_RE.findall(texto)]
        if todos := [
            p for p in todos if p is not None and p != preco_parcelado
        ]:
            preco = todos[0]

    return preco, preco_parcelado


def extrair_cupom_codigo(texto: str) -> str | None:
    m = CODIGO_RE.search(texto)
    if m:
        return m.group(1).upper()
    m = CUPOM_RE.search(texto)
    return m.group(1).upper() if m else None


def extrair_desconto(texto: str) -> str | None:
    m = DESCONTO_RE.search(texto)
    return m.group(1).strip() if m else None


def extrair_limite_minimo(texto: str) -> Decimal | None:
    m = LIMITE_MINIMO_RE.search(texto)
    return _to_decimal(m.group(1)) if m else None


def eh_mensagem_de_cupom(texto: str) -> bool:
    texto_lower = texto.lower()
    tem_palavra_cupom = any(p in texto_lower for p in PALAVRAS_CUPOM)
    tem_preco_de_produto = POR_RE.search(texto) is not None
    return tem_palavra_cupom and not tem_preco_de_produto


def parse_mensagem(texto: str) -> dict[str, Any]:
    nome = extrair_nome(texto)
    if eh_mensagem_de_cupom(nome):
        return {
            "tipo": "cupom",
            "payload": {
                "nome": nome,
                "codigo": extrair_cupom_codigo(texto),
                "desconto": extrair_desconto(texto),
                "limite_minimo": extrair_limite_minimo(texto),
                "link": extrair_link(texto),
                "imagem": None,
                "publicado": True,
            },
        }

    preco, preco_parcelado = extrair_precos(texto)
    return {
        "tipo": "produto",
        "payload": {
            "nome": nome,
            "preco": preco,
            "preco_parcelado": preco_parcelado,
            "link": extrair_link(texto),
            "cupom": extrair_cupom_codigo(texto),
            "imagem": None,
            "publicado": True,
        },
    }


# --------------------------------------------------------------------------
# Envio para a API (main.py / FastAPI)
# --------------------------------------------------------------------------
def enviar_para_api(tipo: str, payload: dict[str, Any]) -> None:
    endpoint = "/produtos" if tipo == "produto" else "/cupons"

    if not payload.get("nome"):
        print(f"[SKIP] sem nome identificado: {payload}")
        return
    if tipo == "cupom" and not payload.get("codigo"):
        print(f"[SKIP] cupom sem código identificado: {payload}")
        return
    if (
        tipo == "produto"
        and payload.get("preco") is None
        and payload.get("preco_parcelado") is None
        and not payload.get("cupom")
    ):
        print(f"[SKIP] produto sem preço nem cupom (só nome/link): {payload['nome']}")
        return

    payload_json = {
        k: (str(v) if isinstance(v, Decimal) else v) for k, v in payload.items()
    }

    try:
        resp = requests.post(f"{BACKEND_URL}{endpoint}", json=payload_json, timeout=10)
        if resp.status_code == 201:
            print(f"[OK] {tipo} criado: {payload['nome']}")
        else:
            print(f"[ERRO {resp.status_code}] {resp.text}")
    except requests.RequestException as e:
        print(f"[ERRO DE CONEXÃO] {e}")


# --------------------------------------------------------------------------
# Download opcional de imagem
# --------------------------------------------------------------------------
async def baixar_imagem(message) -> str | None:
    if not DOWNLOAD_IMAGENS:
        return None
    if not message.media or not isinstance(message.media, MessageMediaPhoto):
        return None
    os.makedirs(PASTA_IMAGENS, exist_ok=True)
    return await message.download_media(file=PASTA_IMAGENS)


# --------------------------------------------------------------------------
# Modo tempo real: escuta mensagens novas
# --------------------------------------------------------------------------
@client.on(events.NewMessage(chats=TELEGRAM_GRUPOS or None))
async def handler(event):
    texto = event.raw_text
    if not texto or len(texto.strip()) < 5:
        return

    resultado = parse_mensagem(texto)

    imagem_path = await baixar_imagem(event.message)
    if imagem_path:
        resultado["payload"]["imagem"] = imagem_path

    print("=" * 60)
    print(f"Novo post detectado ({resultado['tipo']}): {resultado['payload']}")

    enviar_para_api(resultado["tipo"], resultado["payload"])


# --------------------------------------------------------------------------
# Modo histórico: varre mensagens antigas de cada grupo
# --------------------------------------------------------------------------
async def escanear_historico(grupo, limite: int) -> None:
    print(f"Escaneando histórico de '{grupo}' (últimas {limite} mensagens)...")
    async for message in client.iter_messages(grupo, limit=limite):
        texto = message.raw_text
        if not texto or len(texto.strip()) < 5:
            continue

        resultado = parse_mensagem(texto)

        imagem_path = await baixar_imagem(message)
        if imagem_path:
            resultado["payload"]["imagem"] = imagem_path

        print(f"[{resultado['tipo']}] {resultado['payload']['nome']}")
        enviar_para_api(resultado["tipo"], resultado["payload"])


def _validar_configuracao() -> None:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise RuntimeError(
            "Defina TELEGRAM_API_ID e TELEGRAM_API_HASH no .env "
            "(gere em https://my.telegram.org)"
        )
    if not TELEGRAM_GRUPOS:
        raise RuntimeError("Defina TELEGRAM_GRUPOS no .env (lista separada por vírgula)")


async def _conectar_se_necessario() -> None:
    if not client.is_connected():
        await client.start()


async def executar_historico(limite: int = 200) -> dict[str, Any]:
    if _scraper_lock.locked():
        return {"status": "ja_em_execucao"}

    async with _scraper_lock:
        _validar_configuracao()
        await _conectar_se_necessario()
        for grupo in TELEGRAM_GRUPOS:
            await escanear_historico(grupo, limite)
        print("Escaneamento de histórico concluído.")
        return {"status": "concluido", "grupos": TELEGRAM_GRUPOS, "limite": limite}


async def executar_tempo_real() -> None:
    _validar_configuracao()
    await _conectar_se_necessario()
    print("Cliente conectado. Escutando grupos em tempo real:", TELEGRAM_GRUPOS)
    await client.run_until_disconnected()


# --------------------------------------------------------------------------
# Entrypoint (CLI)
# --------------------------------------------------------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--historico",
        action="store_true",
        help="Varre mensagens antigas em vez de escutar em tempo real",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=200,
        help="Quantidade de mensagens antigas a buscar (usado com --historico)",
    )
    args = parser.parse_args()

    try:
        if args.historico:
            resultado = await executar_historico(args.limite)
            print(resultado)
        else:
            await executar_tempo_real()
    except RuntimeError as e:
        raise SystemExit(str(e)) from e


if __name__ == "__main__":
    asyncio.run(main())