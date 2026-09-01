"""
Gera uma StringSession do Telethon para usar em ambientes sem disco
persistente (Vercel, Lambda, containers efêmeros, etc.).

Rode isso UMA VEZ, na sua máquina local (nunca em produção/CI), com
TELEGRAM_API_ID e TELEGRAM_API_HASH já no seu .env. Ele vai pedir seu
número de telefone e o código que o Telegram te enviar, e no final imprime
uma string longa.

Uso:
    python gerar_sessao.py

Depois:
    1. Copie a string impressa.
    2. No painel do Vercel: Project Settings -> Environment Variables ->
       adicione TELEGRAM_SESSION_STRING com esse valor (marcada como
       secreta, não exponha no código nem em logs).
    3. Redeploy. O scraper.py vai detectar TELEGRAM_SESSION_STRING
       automaticamente e conectar sem pedir login de novo.

Trate essa string como uma senha: quem tiver ela consegue logar na sua
conta do Telegram sem precisar do código de verificação.
"""

import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")


async def main() -> None:
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        raise SystemExit(
            "Defina TELEGRAM_API_ID e TELEGRAM_API_HASH no .env antes de rodar isso."
        )

    async with TelegramClient(StringSession(), TELEGRAM_API_ID, TELEGRAM_API_HASH) as client:
        session_string = client.session.save()
        print("\n" + "=" * 70)
        print("Copie a linha abaixo para TELEGRAM_SESSION_STRING no Vercel:")
        print("=" * 70)
        print(session_string)
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
