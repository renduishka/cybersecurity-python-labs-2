import os
import random
import string
import sys
from collections import Counter

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from shared.student import (
    GROUP_NAME,
    STUDENT_NAME,
    VARIANT_NUMBER,
)

PASSWORDS = [
    "Compli4nc3@Check",
    "weak",
    "Risk@Ass3ssment",
    "guest",
    "Vulner4bility@Scan",
    "temp",
    "P3netration@Test",
    "demo",
    "S3curity@Audit",
    "trial",
    "okaeksdbdj",
    "password1",
]
CRITERIA = {
    "min_length": 8,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}
FORBIDDEN_PASSWORDS = {"weak", "guest", "temp", "demo", "trial", "password"}

DUPLICATES_COUNT = 3
EXTRA_LENGTH = 4


def add_duplicates(passwords, count=DUPLICATES_COUNT):
    indexes = random.sample(range(len(passwords)), count)
    result = list(passwords)
    for index in indexes:
        result.append(passwords[index])
    return result, indexes


def get_char_groups(password):
    return {
        "digits": any(char.isdigit() for char in password),
        "upper": any(char.isupper() for char in password),
        "lower": any(char.islower() for char in password),
        "special": any(char in string.punctuation for char in password),
    }


def meets_all_criteria(password, groups, criteria):
    if len(password) < criteria["min_length"]:
        return False
    required = [
        group
        for group in ("digits", "upper", "special")
        if criteria.get(f"require_{group}")
    ]
    return all(groups[group] for group in required)


def evaluate_password(password, counts, criteria, forbidden):
    min_length = criteria["min_length"]

    if password.lower() in forbidden or len(password) < min_length:
        return "Недоступний"

    groups = get_char_groups(password)

    if meets_all_criteria(password, groups, criteria):
        if len(password) < min_length + EXTRA_LENGTH:
            return "Сильний"
        if counts[password] == 1:
            return "Дуже сильний"
        return "Сильний"

    if sum(groups.values()) >= 2:
        return "Середній"
    return "Слабкий"


def print_table(passwords, counts, criteria, forbidden):
    header = f"{'№':<3} {'Пароль':<20} {'Довж.':>5} {'Повт.':>5}  Оцінка"
    print(header)
    print(" " * len(header))
    for number, password in enumerate(passwords, start=1):
        rating = evaluate_password(password, counts, criteria, forbidden)
        print(
            f"{number:<3} {password:<20} {len(password):>5} "
            f"{counts[password]:>5}  {rating}"
        )


def main():
    print("Завдання 1")
    print(f"Студент: {STUDENT_NAME}")
    print(f"Група: {GROUP_NAME}, варіант: {VARIANT_NUMBER}\n")

    passwords, indexes = add_duplicates(PASSWORDS)
    duplicated = [PASSWORDS[index] for index in indexes]
    print(f"Додано дублікати паролів: {', '.join(duplicated)}\n")

    counts = Counter(passwords)
    print_table(passwords, counts, CRITERIA, FORBIDDEN_PASSWORDS)
    print()


if __name__ == "__main__":
    main()
