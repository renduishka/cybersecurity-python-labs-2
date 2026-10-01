import csv
import functools
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from shared.student import (  # noqa: E402
    GROUP_NAME,
    STUDENT_NAME,
    VARIANT_NUMBER,
)

HASH_ALGORITHM = "sha3_256"
MIN_PASSWORD_LENGTH = 14
SALT = str(VARIANT_NUMBER).zfill(5)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
LOG_JSON = os.path.join(DATA_DIR, "log.json")

users_db = []


class ValidationError(Exception):
    pass


def generate_hash(password: str, salt: str = "00000") -> str:
    if not password or not salt:
        raise ValueError("Пароль і сіль не можуть бути порожніми")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Пароль має бути не коротший за {MIN_PASSWORD_LENGTH} символів"
        )
    data = (password + salt).encode("utf-8")
    return hashlib.new(HASH_ALGORITHM, data).hexdigest()


def create_user(username, password):
    if not username:
        raise ValueError("Логін не може бути порожнім")
    hash_value = generate_hash(password, SALT)
    return username, hash_value


def create_users(users_list):
    os.makedirs(DATA_DIR, exist_ok=True)
    records = []
    for username, password in users_list:
        try:
            records.append(create_user(username, password))
        except (ValueError, ValidationError) as error:
            name = username if username else "<порожній>"
            print(f"Користувача {name} пропущено: {error}")

    with open(USERS_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["username", "password_hash"])
        writer.writerows(records)
    print(f"Записано: {len(records)}\n")


def load_users_db():
    users_db.clear()
    with open(USERS_CSV, newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)
        for row in reader:
            users_db.append((row[0], row[1]))


def print_users_db():
    print(f"{'':<3} {'Логін':<10} Хеш пароля")
    for number, (username, hash_value) in enumerate(users_db, start=1):
        print(f"{number:<3} {username:<10} {hash_value}")
    print()


def write_log(entry):
    os.makedirs(DATA_DIR, exist_ok=True)
    events = []
    if os.path.exists(LOG_JSON):
        try:
            with open(LOG_JSON, encoding="utf-8") as file:
                events = json.load(file)
        except json.JSONDecodeError:
            events = []
    events.append(entry)
    with open(LOG_JSON, "w", encoding="utf-8") as file:
        json.dump(events, file, ensure_ascii=False, indent=4)


def log_event(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        success = False
        try:
            success = func(*args, **kwargs)
            return success
        finally:
            if args:
                username = args[0]
            else:
                username = kwargs.get("username", "")
            # пароль у лог не пишемо
            safe_args = [username] + ["***"] * (len(args) - 1)
            safe_kwargs = {}
            for key, value in kwargs.items():
                safe_kwargs[key] = "***" if key == "password" else value
            write_log(
                {
                    "event": func.__name__,
                    "user": username,
                    "result": "success" if success else "failure",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "args": safe_args if args else [],
                    "kwargs": safe_kwargs,
                }
            )

    return wrapper


@log_event
def login(username: str, password: str) -> bool:
    if not username or not password:
        raise ValueError("Логін і пароль не можуть бути порожніми")

    saved_hash = None
    for db_username, db_hash in users_db:
        if db_username == username:
            saved_hash = db_hash
            break
    if saved_hash is None:
        return False

    try:
        entered_hash = generate_hash(password, SALT)
    except ValidationError:
        return False
    return hmac.compare_digest(entered_hash, saved_hash)


def test_hash_errors():
    print("Перевірка помилок ")
    for password in ("", "short"):
        try:
            generate_hash(password, SALT)
        except ValidationError as error:
            print(f"  ValidationError: {error}")
        except ValueError as error:
            print(f"  ValueError: {error}")
    print()


def test_logins():
    attempts = (
        ("alice", "Al1ce@SecurePass"),
        ("alice", "Wrong@Password123"),
        ("unknown", "Some@Password123"),
        ("bob", "short"),
        ("", "Anything@12345678"),
    )
    print("Спроби входу:")
    for username, password in attempts:
        name = username if username else "<порожній>"
        try:
            if login(username, password):
                print(f"  {name:<10}  успіх")
            else:
                print(f"  {name:<10}  відмова")
        except ValueError as error:
            print(f"  {name:<10}  помилка: {error}")
    print("\nЗаписано у log.json\n")


def main():
    print("Завдання 3")
    print(f"Студент: {STUDENT_NAME}")
    print(f"Група: {GROUP_NAME}, варіант: {VARIANT_NUMBER}")
    print(f"Алгоритм: {HASH_ALGORITHM}, сіль: {SALT}\n")

    users_to_register = (
        ("alice", "Al1ce@SecurePass"),
        ("bob", "B0b#Strong_Key2026"),
        ("charlie", "Ch@rlie_Passw0rd"),
        ("diana", "D1ana$Secret_Key"),
        ("eve", "Ev3!Crypto_Phrase"),
        ("frank", "Fr@nk_H4sh_Test1"),
        ("grace", "Gr4ce%Long_Pass!"),
        ("henry", "H3nry&Salt_Pepper"),
        ("irene", "Ir3ne*Secure_2026"),
        ("jack", "J4ck^Quantum_Key"), 
        ("Yummy", "Ababalamaga!hsjfnf"),
    )

    try:
        create_users(users_to_register)
        load_users_db()
        print_users_db()
        test_hash_errors()
        test_logins()
    except FileNotFoundError:
        print("Помилка: файл не знайдено")
    except PermissionError:
        print("Помилка: немає доступу до файлу")
    except IOError as error:
        print(f"Помилка роботи з файлом: {error}")
    except ValidationError as error:
        print(f"Помилка валідації: {error}")
    except ValueError as error:
        print(f"Помилка: {error}")


if __name__ == "__main__":
    main()
