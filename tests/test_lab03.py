"""Перевірки контракту ЛР 3 на окремій тимчасовій SQLite-базі."""

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


class Lab03Tests(unittest.TestCase):
    """Реальні HTTP-маршрути, SQL і транзакції без підміни сховища."""

    def setUp(self):
        self.assertIsNotNone(
            importlib.util.find_spec("labs.lab03.main"),
            "FastAPI-застосунок ще не реалізовано",
        )
        from fastapi.testclient import TestClient

        from labs.lab03 import database, seed
        from labs.lab03.main import app

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous = database.DATABASE_PATH
        database.DATABASE_PATH = Path(self.temp.name) / "test.sqlite3"
        self.addCleanup(setattr, database, "DATABASE_PATH", self.previous)
        self.database = database
        self.seed = seed
        database.initialize_database()
        self.assertTrue(seed.seed_database())
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def record(self, code="V13-TEST", **updates):
        data = dict(
            code=code,
            title="Навчальна знахідка",
            category_id=1,
            value=7.5,
            status="new",
        )
        return data | updates

    def all_records(self):
        return self.client.get("/records", params={"limit": 100}).json()

    def test_seed_and_identity(self):
        self.assertFalse(self.seed.seed_database())
        self.assertEqual(len(self.all_records()), 8)
        self.assertEqual(self.client.get("/ping").json(), {"status": "ok"})
        self.assertEqual(
            self.client.get("/student").json(),
            {
                "student_name": "Лозинський Ростислав Романович",
                "group_name": "КБ-202",
                "variant_number": 13,
            },
        )
        self.assertEqual(
            [c["name"] for c in self.client.get("/categories").json()],
            ["iam", "storage", "network"],
        )
        self.assertEqual(
            [r["value"] for r in self.all_records()],
            [8.0, 6.5, 4.0, 9.0, 7.5, 3.0, 7.0, 5.0],
        )

    def test_crud(self):
        created = self.client.post("/records", json=self.record())
        self.assertEqual(created.status_code, 201)
        record_id = created.json()["id"]
        self.assertEqual(created.json()["category_name"], "iam")
        self.assertEqual(
            self.client.get(f"/records/{record_id}").json(), created.json()
        )
        updated = self.client.put(
            f"/records/{record_id}", json=self.record(value=2, status="done")
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["id"], record_id)
        self.assertEqual(updated.json()["value"], 2)
        deleted = self.client.delete(f"/records/{record_id}")
        self.assertEqual((deleted.status_code, deleted.content), (204, b""))
        self.assertEqual(
            self.client.get(f"/records/{record_id}").status_code, 404
        )

    def test_filters_pagination_and_literal_search(self):
        for query, expected in [
            ({"category_id": 1}, [1, 4, 7]),
            ({"status": "new"}, [1, 4, 8]),
            ({"min_value": 7}, [1, 4, 5, 7]),
            ({"category_id": 1, "status": "new"}, [1, 4]),
            ({"limit": 2, "offset": 2}, [3, 4]),
            ({"category_id": 999}, []),
            ({"q": "аудиту 02"}, [2]),
            ({"q": "АУДИТУ"}, []),
            ({"q": "%"}, []),
            ({"q": "_"}, []),
            ({"q": "' OR 1=1 --"}, []),
        ]:
            with self.subTest(query=query):
                r = self.client.get("/records", params=query)
                self.assertEqual(r.status_code, 200)
                self.assertEqual([row["id"] for row in r.json()], expected)
        self.assertEqual(len(self.all_records()), 8)

    def test_validation_leaves_database_unchanged(self):
        for updates in [
            dict(value=-1),
            dict(value=10.1),
            dict(value="NaN"),
            dict(value="Infinity"),
            dict(value="oops"),
            dict(title="  "),
            dict(status="bad"),
            dict(category_id=0),
            dict(id=90),
            dict(code="x"),
            dict(title="x" * 121),
        ]:
            with self.subTest(updates=updates):
                self.assertEqual(
                    self.client.post(
                        "/records", json=self.record(**updates)
                    ).status_code,
                    422,
                )
        for query in [
            {"limit": 0},
            {"limit": 101},
            {"offset": -1},
            {"min_value": 11},
            {"min_value": "NaN"},
            {"status": "bad"},
            {"category_id": 0},
            {"q": ""},
        ]:
            self.assertEqual(
                self.client.get("/records", params=query).status_code, 422
            )
        self.assertEqual(
            self.client.put(
                "/records/1", json={"title": "Нова назва"}
            ).status_code,
            422,
        )
        self.assertEqual(self.client.get("/records/0").status_code, 422)
        self.assertEqual(len(self.all_records()), 8)

    def test_not_found_and_unique_conflicts(self):
        for method in ["get", "delete"]:
            self.assertEqual(
                getattr(self.client, method)("/records/999").status_code, 404
            )
        self.assertEqual(
            self.client.put("/records/999", json=self.record()).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                "/records", json=self.record(category_id=999)
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.put(
                "/records/1", json=self.record(category_id=999)
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                "/records", json=self.record("V13-01")
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.put(
                "/records/2", json=self.record("V13-01")
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post("/categories", json={"name": "iam"}).status_code,
            409,
        )
        self.assertEqual(len(self.all_records()), 8)

    def test_sqlite_integer_overflow_is_validation_error(self):
        huge = 9223372036854775808
        for path in [f"/records/{huge}", f"/categories/{huge}"]:
            method = "get" if path.startswith("/records/") else "delete"
            response = getattr(self.client, method)(path)
            self.assertEqual(response.status_code, 422)
        for params in [{"category_id": huge}, {"offset": huge}]:
            self.assertEqual(
                self.client.get("/records", params=params).status_code, 422
            )
        self.assertEqual(
            self.client.post(
                "/records", json=self.record(category_id=huge)
            ).status_code,
            422,
        )
        self.assertEqual(len(self.all_records()), 8)

    def test_categories(self):
        self.assertEqual(self.client.delete("/categories/1").status_code, 409)
        r = self.client.post("/categories", json={"name": " extra "})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["name"], "extra")
        d = self.client.delete(f"/categories/{r.json()['id']}")
        self.assertEqual((d.status_code, d.content), (204, b""))
        self.assertEqual(
            self.client.delete("/categories/999").status_code, 404
        )
        self.assertEqual(
            self.client.post("/categories", json={"name": " "}).status_code,
            422,
        )

    def test_bulk_success_and_rollback(self):
        for second, expected in [
            (self.record("V13-01"), 409),
            (self.record("V13-MISSING", category_id=999), 404),
            (self.record("V13-FIRST"), 409),
            (self.record("V13-BAD", value=-1), 422),
        ]:
            before = self.all_records()
            r = self.client.post(
                "/records/bulk", json=[self.record("V13-FIRST"), second]
            )
            self.assertEqual(r.status_code, expected)
            self.assertEqual(self.all_records(), before)
        for body in [[], [self.record(f"CODE-{i}") for i in range(101)]]:
            self.assertEqual(
                self.client.post("/records/bulk", json=body).status_code, 422
            )
        r = self.client.post(
            "/records/bulk",
            json=[
                self.record("V13-A", value=0),
                self.record("V13-B", value=10),
            ],
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.json()), 2)
        self.assertEqual(len(self.all_records()), 10)

    def test_persistence_after_lifespan_restart(self):
        from fastapi.testclient import TestClient

        from labs.lab03.main import app

        record_id = self.client.post("/records", json=self.record()).json()[
            "id"
        ]
        with TestClient(app) as restarted:
            self.assertEqual(
                restarted.get(f"/records/{record_id}").json()["code"],
                "V13-TEST",
            )
            self.assertEqual(len(restarted.get("/records").json()), 9)

    def test_foreign_keys_and_constraints(self):
        with closing(self.database.get_connection()) as conn:
            try:
                self.assertEqual(
                    conn.execute("PRAGMA foreign_keys").fetchone()[0], 1
                )
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute("DELETE FROM categories WHERE id = ?", (1,))
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(
                        "UPDATE records SET value = ? WHERE id = ?", (11, 1)
                    )
            finally:
                conn.close()

    def test_invalid_seed_rolls_back_and_nonempty_is_preserved(self):
        seed_data = json.loads(self.seed.SEED_PATH.read_text(encoding="utf-8"))
        self.database.DATABASE_PATH = Path(self.temp.name) / "bad_seed.sqlite3"
        self.database.initialize_database()
        seed_data["records"][1]["code"] = "V13-01"
        path = Path(self.temp.name) / "seed.json"
        path.write_text(json.dumps(seed_data), encoding="utf-8")
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            self.seed.seed_database(path)
        conn = self.database.get_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM records").fetchone()[0], 0
            )
            conn.execute(
                "INSERT INTO categories (name) VALUES (?)", ("existing",)
            )
            conn.commit()
        finally:
            conn.close()
        self.assertFalse(self.seed.seed_database())
        conn = self.database.get_connection()
        try:
            self.assertEqual(
                conn.execute("SELECT name FROM categories").fetchone()[0],
                "existing",
            )
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM records").fetchone()[0], 0
            )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
