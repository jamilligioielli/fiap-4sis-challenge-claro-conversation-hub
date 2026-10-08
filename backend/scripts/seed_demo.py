"""Popula (ou limpa) o MongoDB com os dados de demonstração da Sprint 4.

Uso, a partir da pasta `backend/`:

    python -m scripts.seed_demo            # cria, se ainda não existir
    python -m scripts.seed_demo --clear    # remove só os dados de demonstração
    python -m scripts.seed_demo --reset    # remove e cria de novo (tempos "frescos")

Com Docker Compose:

    docker compose exec api python -m scripts.seed_demo --reset

Lê `MONGO_URL` e `MONGO_DB` do ambiente, como a API. Sem MongoDB, use
`DEMO_SEED=true` no `.env`: a API cria os mesmos dados em memória ao subir.

Só toca no que é da demonstração (`conv_demo_*`) — conversas reais ficam.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.infrastructure import seed
from app.infrastructure.demo_seed import DEMO_PREFIX, populate_demo
from app.infrastructure.persistence import mongo
from app.settings import get_settings

DEMO_FILTER = {"$regex": f"^{DEMO_PREFIX}"}


async def clear(db) -> int:
    await db.messages.delete_many({"conversation_id": DEMO_FILTER})
    result = await db.conversations.delete_many({"id": DEMO_FILTER})
    return result.deleted_count


async def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--clear", action="store_true", help="remove os dados de demonstração")
    group.add_argument("--reset", action="store_true", help="remove e cria de novo")
    args = parser.parse_args(argv)

    settings = get_settings()
    db = await mongo.connect(settings.mongo_url, settings.mongo_db)
    if db is None:
        print("MongoDB indisponível em MONGO_URL. Sem banco, suba a API com DEMO_SEED=true "
              "para ter os mesmos dados em memória.", file=sys.stderr)
        return 1

    conversations = mongo.MongoConversationRepository(db)
    customers = mongo.MongoCustomerRepository(db)
    studio = mongo.MongoStudioConfigRepository(db, seed.DEFAULT_STUDIO)

    if args.clear or args.reset:
        removed = await clear(db)
        print(f"Removidas {removed} conversas de demonstração.")
        if args.clear:
            return 0

    await seed.populate(customers, conversations, studio)
    created = await populate_demo(customers, conversations)
    print(f"Criadas {created} conversas de demonstração." if created
          else "Dados de demonstração já existiam — use --reset para recriar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
