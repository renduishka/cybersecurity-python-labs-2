import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from shared.student import (  # noqa: E402
    GROUP_NAME,
    STUDENT_NAME,
    VARIANT_NUMBER,
)

USERS = {
    "ai_security_expert": {
        "role": "ai_security",
        "clearance": 4,
        "department": "AI Security",
        "active": True,
    },
    "ml_engineer": {
        "role": "ml_engineer",
        "clearance": 3,
        "department": "Machine Learning",
        "active": True,
    },
    "data_engineer": {
        "role": "data_engineer",
        "clearance": 2,
        "department": "Data Engineering",
        "active": True,
    },
    "research_assistant": {
        "role": "researcher",
        "clearance": 2,
        "department": "Research",
        "active": True,
    },
    "training_bot": {
        "role": "bot_account",
        "clearance": 1,
        "department": "Automation",
        "active": False,
    },
}
RESOURCES = [
    ("ai_models", 4),
    ("training_datasets", 3),
    ("data_pipelines", 2),
    ("research_notebooks", 2),
    ("model_artifacts", 4),
    ("synthetic_data", 1),
    ("adversarial_tests", 3),
    ("model_registry", 4),
    ("feature_stores", 2),
    ("public_models", 1),
]
SECURITY_LEVELS = (
    "1",
    "2",
    "3",
    "4",
)
BLOCKED_USERS = {"training_bot", "model_theft", "data_poisoning_acc"}

USERS_TO_CHECK = [*USERS, "unknown_user"]


def level_name(level):
    return SECURITY_LEVELS[level - 1]


def print_resources(resources):
    print("Ресурси системи:")
    for name, level in resources:
        print(f"  {name:<20} {level_name(level)}")
    print()


def check_access(username, resource_level):
    user = USERS.get(username)
    if user is None:
        return False, "User not found"
    if username in BLOCKED_USERS:
        return False, "User is blocked"
    if not user["active"]:
        return False, "Account inactive"
    if user["clearance"] >= resource_level:
        return True, ""
    return False, "Insufficient clearance"


def main():
    print("Завдання 2")
    print(f"Студент: {STUDENT_NAME}")
    print(f"Група: {GROUP_NAME}, варіант: {VARIANT_NUMBER}\n")

    print_resources(RESOURCES)

    for username in USERS_TO_CHECK:
        for resource, level in RESOURCES:
            allowed, reason = check_access(username, level)
            if allowed:
                result = "ALLOW"
            else:
                result = f"DENY ({reason})"
            print(f"user={username} resource={resource} -> {result}")
        print()


if __name__ == "__main__":
    main()
