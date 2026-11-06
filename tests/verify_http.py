"""Відтворювана перевірка 14 сценаріїв через справжній HTTP-сервер.

Запуск: python -m tests.verify_http. Використовує тимчасову копію даних;
робочу data/lab3.sqlite3 не змінює. Порт 8013 має бути вільним.
"""

import json
import os
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8013"


def run_checks() -> None:
    """Запустити сервер двічі, виконати HTTP-запити й зберегти протокол."""
    output = ROOT / "output" / "evidence"
    output.mkdir(parents=True, exist_ok=True)
    evidence = []
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "lab3.sqlite3"
        # Окремий процес імпортує застосунок із тимчасовим шляхом до SQLite.
        launch = (
            "from pathlib import Path; from labs.lab03 import database; "
            f"database.DATABASE_PATH = Path({str(db_path)!r}); "
            "import uvicorn; uvicorn.run('labs.lab03.main:app', "
            "host='127.0.0.1', port=8013, log_level='warning')"
        )
        from labs.lab03 import database, seed

        previous_path = database.DATABASE_PATH
        database.DATABASE_PATH = db_path
        try:
            first = seed.seed_database()
            second = seed.seed_database()
            assert first is True and second is False
            with sqlite3.connect(db_path) as connection:
                category_count = connection.execute(
                    "SELECT COUNT(*) FROM categories"
                ).fetchone()[0]
                record_count = connection.execute(
                    "SELECT COUNT(*) FROM records"
                ).fetchone()[0]
            assert category_count == 3 and record_count == 8
            evidence.append(
                {
                    "scenario": 1,
                    "label": "Початкове та повторне заповнення",
                    "result": {
                        "first_inserted": first,
                        "second_inserted": second,
                        "categories": category_count,
                        "records": record_count,
                    },
                }
            )
        finally:
            database.DATABASE_PATH = previous_path

        log = (output / "server.log").open("w", encoding="utf-8")
        process = None
        client = httpx.Client(base_url=BASE_URL, timeout=10, trust_env=False)

        def start():
            proc = subprocess.Popen(
                [sys.executable, "-c", launch],
                cwd=ROOT,
                stdout=log,
                stderr=log,
                env=os.environ.copy(),
            )
            for _ in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("Сервер не запустився; див. server.log")
                try:
                    if client.get("/ping").status_code == 200:
                        return proc
                except httpx.ConnectError:
                    pass
                time.sleep(0.05)
            proc.terminate()
            proc.wait(timeout=10)
            raise RuntimeError("Сервер не відповідає")

        def stop(proc):
            proc.terminate()
            proc.wait(timeout=10)

        def request(
            scenario, label, method, path, expected, body=None, raw=None
        ):
            command = [
                "curl",
                "--silent",
                "--show-error",
                "--include",
                "--noproxy",
                "127.0.0.1",
                "--request",
                method,
            ]
            if body is not None or raw is not None:
                payload = (
                    raw
                    if raw is not None
                    else json.dumps(body, ensure_ascii=False)
                )
                command += [
                    "--header",
                    "Content-Type: application/json",
                    "--data-raw",
                    payload,
                ]
            command.append(BASE_URL + quote(path, safe="/?=&%"))
            executed = subprocess.run(command, capture_output=True, check=True)
            raw_response = executed.stdout.decode("utf-8")
            headers, _, content = raw_response.partition("\r\n\r\n")
            status_code = int(headers.splitlines()[0].split()[1])
            response = httpx.Response(status_code, content=content)
            assert response.status_code == expected, (
                label,
                response.status_code,
                response.text,
            )
            result = response.json() if response.content else None
            evidence.append(
                {
                    "scenario": scenario,
                    "label": label,
                    "method": method,
                    "path": path,
                    "request": body if raw is None else raw,
                    "status": response.status_code,
                    "response": result,
                    "curl_command": shlex.join(command),
                    "raw_response": raw_response,
                }
            )
            return result

        def record(code, **updates):
            return {
                "code": code,
                "title": "Навчальна знахідка",
                "category_id": 1,
                "value": 7.5,
                "status": "new",
            } | updates

        def snapshot():
            return client.get("/records?limit=100").json()

        try:
            process = start()
            request(2, "Перевірка доступності", "GET", "/ping", 200)
            request(2, "Дані студента", "GET", "/student", 200)
            request(2, "Напрями аудиту", "GET", "/categories", 200)
            request(
                1, "Початкові 8 знахідок", "GET", "/records?limit=100", 200
            )
            row = request(
                3,
                "Створення знахідки",
                "POST",
                "/records",
                201,
                record("V13-TEST"),
            )
            rid = row["id"]
            request(3, "Читання знахідки", "GET", f"/records/{rid}", 200)
            request(
                3,
                "Повна заміна",
                "PUT",
                f"/records/{rid}",
                200,
                record("V13-TEST", value=2, status="done"),
            )
            request(3, "Видалення без тіла", "DELETE", f"/records/{rid}", 204)
            for path in [
                "/records?category_id=1",
                "/records?min_value=7",
                "/records?category_id=1&status=new",
                "/records?limit=2&offset=2",
                "/records?q=аудиту%2002",
                "/records?category_id=999",
            ]:
                request(4, "Фільтрація та пагінація", "GET", path, 200)
            before = snapshot()
            for updates in [
                dict(value=-1),
                dict(title="   "),
                dict(status="invalid"),
            ]:
                request(
                    5,
                    "Невалідні поля",
                    "POST",
                    "/records",
                    422,
                    record("V13-BAD", **updates),
                )
            request(5, "Невалідний limit", "GET", "/records?limit=0", 422)
            request(
                6,
                "Перевищення верхньої межі",
                "POST",
                "/records",
                422,
                record("V13-BAD", value=10.1),
            )
            raw = json.dumps(record("V13-INF")).replace("7.5", "1e309")
            request(
                6, "Нескінченне число у JSON", "POST", "/records", 422, raw=raw
            )
            assert snapshot() == before
            request(7, "Відсутній запис", "GET", "/records/999", 404)
            request(
                7,
                "Відсутня категорія",
                "POST",
                "/records",
                404,
                record("V13-NOCAT", category_id=999),
            )
            request(
                8, "Повторний code", "POST", "/records", 409, record("V13-01")
            )
            request(
                8,
                "Повторна назва категорії",
                "POST",
                "/categories",
                409,
                {"name": "iam"},
            )
            request(
                9,
                "Захист непорожньої категорії",
                "DELETE",
                "/categories/1",
                409,
            )
            cat = request(
                9,
                "Створення порожньої категорії",
                "POST",
                "/categories",
                201,
                {"name": "temporary"},
            )
            request(
                9,
                "Видалення порожньої категорії",
                "DELETE",
                f"/categories/{cat['id']}",
                204,
            )
            request(
                10,
                "Коректний пакет",
                "POST",
                "/records/bulk",
                201,
                [
                    record("V13-BULK1"),
                    record("V13-BULK2", category_id=2, value=5),
                ],
            )
            for number, second_item, code in [
                (11, record("V13-01"), 409),
                (12, record("V13-NOCAT", category_id=999), 404),
            ]:
                before = snapshot()
                with sqlite3.connect(db_path) as connection:
                    count_before = connection.execute(
                        "SELECT COUNT(*) FROM records"
                    ).fetchone()[0]
                first_code = f"V13-ROLLBACK{number}"
                request(
                    number,
                    "Скасування всього пакета",
                    "POST",
                    "/records/bulk",
                    code,
                    [record(first_code), second_item],
                )
                after = snapshot()
                with sqlite3.connect(db_path) as connection:
                    count_after = connection.execute(
                        "SELECT COUNT(*) FROM records"
                    ).fetchone()[0]
                    first_code_count = connection.execute(
                        "SELECT COUNT(*) FROM records WHERE code = ?",
                        (first_code,),
                    ).fetchone()[0]
                assert count_before == count_after and first_code_count == 0
                assert before == after
                assert all(row["code"] != first_code for row in after)
                evidence.append(
                    {
                        "scenario": number,
                        "label": "Стан після rollback",
                        "result": {
                            "count_before": count_before,
                            "count_after": count_after,
                            "first_code": first_code,
                            "first_code_exists": bool(first_code_count),
                            "first_code_count": first_code_count,
                            "count_query": "SELECT COUNT(*) FROM records",
                            "code_query": (
                                "SELECT COUNT(*) FROM records WHERE code = ?"
                            ),
                        },
                    }
                )
            request(
                13,
                "SQL-ін'єкція як буквальний підрядок",
                "GET",
                "/records?q=%27%20OR%201%3D1%20--",
                200,
            )
            persistent = request(
                14,
                "Збереження перед перезапуском",
                "POST",
                "/records",
                201,
                record("V13-PERSIST", category_id=3),
            )
            previous_pid = process.pid
            stop(process)
            process = None
            process = start()
            evidence.append(
                {
                    "scenario": 14,
                    "label": "Перезапуск процесу uvicorn",
                    "result": {
                        "stopped_pid": previous_pid,
                        "started_pid": process.pid,
                        "same_database_file": True,
                    },
                }
            )
            restored = request(
                14,
                "Читання після перезапуску процесу",
                "GET",
                f"/records/{persistent['id']}",
                200,
            )
            assert restored == persistent
            request(14, "Підсумкові дані", "GET", "/records?limit=100", 200)
            assert client.get("/docs").status_code == 200
            schema = client.get("/openapi.json").json()
            (output / "openapi.json").write_text(
                json.dumps(schema, ensure_ascii=False, indent=2)
            )
        finally:
            if process is not None:
                stop(process)
            client.close()
            log.close()
    (output / "http-results.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2)
    )
    lines = []
    for item in evidence:
        lines.append(f"Сценарій {item['scenario']}: {item['label']}")
        if "method" in item:
            lines.append(
                f"{item['method']} {item['path']} -> HTTP {item['status']}"
            )
        lines.append(
            json.dumps(
                item.get("response", item.get("result")), ensure_ascii=False
            )
        )
        lines.append("")
    (output / "http-transcript.txt").write_text("\n".join(lines))
    print(
        f"PASS: 14 сценаріїв, {len(evidence)} кроків. "
        "Перезапуск процесу перевірено."
    )


if __name__ == "__main__":
    run_checks()
