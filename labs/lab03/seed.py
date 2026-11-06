"""Валідація JSON та атомарне початкове заповнення SQLite."""

import logging
import sqlite3
from contextlib import closing
from pathlib import Path

from labs.lab03.database import BASE_DIR, get_connection, initialize_database
from labs.lab03.schemas import SeedData

SEED_PATH = BASE_DIR / "data" / "seed.json"


def seed_database(path: Path = SEED_PATH) -> bool:
    """Заповнити лише порожню базу; повернути False, якщо вона непорожня."""
    initialize_database()
    with closing(get_connection()) as connection, connection:
        # Блокування запису усуває гонку між перевіркою порожнечі та вставками.
        connection.execute("BEGIN IMMEDIATE")
        occupied = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM categories) "
            "OR EXISTS(SELECT 1 FROM records)"
        ).fetchone()[0]
        if occupied:
            return False
        data = SeedData.model_validate_json(path.read_text(encoding="utf-8"))
        connection.executemany(
            "INSERT INTO categories (id, name) VALUES (?, ?)",
            [(category.id, category.name) for category in data.categories],
        )
        connection.executemany(
            "INSERT INTO records (code, title, category_id, value, status) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (r.code, r.title, r.category_id, r.value, r.status)
                for r in data.records
            ],
        )
    return True


def main() -> int:
    """Надрукувати зрозумілий результат початкового заповнення."""
    try:
        inserted = seed_database()
    except (ValueError, OSError, sqlite3.Error):
        logging.exception("Помилка початкового заповнення")
        print("Початковий набір не додано. Перевірте JSON та доступ до бази.")
        return 1
    print(
        "Додано 3 категорії та 8 записів."
        if inserted
        else "База непорожня. Дані не змінено."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
