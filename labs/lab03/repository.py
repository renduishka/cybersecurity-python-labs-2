"""Параметризовані SQL-запити; цей модуль не залежить від FastAPI."""

import sqlite3
from contextlib import closing
from typing import Any

from labs.lab03.database import get_connection

SELECT_RECORD = (
    "SELECT r.id, r.code, r.title, r.category_id, r.value, r.status, "
    "c.name AS category_name FROM records AS r "
    "JOIN categories AS c ON c.id = r.category_id"
)
INSERT_RECORD = (
    "INSERT INTO records (code, title, category_id, value, status) "
    "VALUES (?, ?, ?, ?, ?)"
)


class NotFoundError(Exception):
    """Ресурс або потрібна категорія не існує."""


def _require_category(
    connection: sqlite3.Connection, category_id: int
) -> None:
    if (
        connection.execute(
            "SELECT id FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        is None
    ):
        raise NotFoundError("Категорію не знайдено")


def _read_record(
    connection: sqlite3.Connection, record_id: int
) -> dict[str, Any]:
    row = connection.execute(
        SELECT_RECORD + " WHERE r.id = ?", (record_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError("Запис не знайдено")
    return dict(row)


def _values(record: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(
        record[key]
        for key in ("code", "title", "category_id", "value", "status")
    )


def list_categories() -> list[dict[str, Any]]:
    """Отримати категорії у стабільному порядку."""
    with closing(get_connection()) as connection:
        return [
            dict(row)
            for row in connection.execute(
                "SELECT id, name FROM categories ORDER BY id"
            )
        ]


def create_category(name: str) -> dict[str, Any]:
    """Додати категорію та підтвердити транзакцію."""
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO categories (name) VALUES (?)", (name,)
        )
        return dict(
            connection.execute(
                "SELECT id, name FROM categories WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        )


def delete_category(category_id: int) -> None:
    """Видалити порожню категорію; зовнішній ключ захищає непорожню."""
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM categories WHERE id = ?", (category_id,)
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Категорію не знайдено")


def get_record(record_id: int) -> dict[str, Any]:
    """Прочитати одну знахідку з назвою напряму аудиту."""
    with closing(get_connection()) as connection:
        return _read_record(connection, record_id)


def list_records(
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Застосувати AND-фільтри, буквальний пошук та пагінацію."""
    clauses: list[str] = []
    params: list[Any] = []
    for clause, value in [
        ("r.category_id = ?", category_id),
        ("r.status = ?", status),
        ("r.value >= ?", min_value),
        ("instr(r.title, ?) > 0", q),
    ]:
        if value is not None:
            clauses.append(clause)
            params.append(value)
    # Структура SQL складається лише з фіксованих фрагментів коду.
    query = SELECT_RECORD
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend((limit, offset))
    with closing(get_connection()) as connection:
        return [dict(row) for row in connection.execute(query, params)]


def create_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Вставити весь пакет в одній транзакції або скасувати всі вставки."""
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN")
        result = []
        for record in records:
            _require_category(connection, record["category_id"])
            cursor = connection.execute(INSERT_RECORD, _values(record))
            result.append(_read_record(connection, cursor.lastrowid))
        return result


def create_record(record: dict[str, Any]) -> dict[str, Any]:
    """Створити одну знахідку через спільну транзакційну операцію."""
    return create_records([record])[0]


def replace_record(record_id: int, record: dict[str, Any]) -> dict[str, Any]:
    """Замінити змінювані поля, зберігши id."""
    with closing(get_connection()) as connection, connection:
        connection.execute("BEGIN")
        _read_record(connection, record_id)
        _require_category(connection, record["category_id"])
        connection.execute(
            "UPDATE records SET code = ?, title = ?, category_id = ?, "
            "value = ?, status = ? WHERE id = ?",
            (*_values(record), record_id),
        )
        return _read_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити знахідку або повідомити про відсутній id."""
    with closing(get_connection()) as connection, connection:
        cursor = connection.execute(
            "DELETE FROM records WHERE id = ?", (record_id,)
        )
        if cursor.rowcount == 0:
            raise NotFoundError("Запис не знайдено")
