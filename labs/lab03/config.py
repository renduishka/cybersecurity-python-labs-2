"""Варіант 13: реєстр ризиків хмарної конфігурації."""

VARIANT_TITLE = "Реєстр ризиків хмарної конфігурації"
DOMAIN_DESCRIPTION = (
    "Облік навчальних знахідок аудиту хмарної конфігурації. "
    "Категорії: iam, storage, network. value — оцінка ризику від 0 до 10; "
    "status — стан опрацювання. Оцінки не є розрахунком за стандартом CVSS."
)
UNIT = "score"
THRESHOLD = 7.0
VALUE_MIN = 0.0
VALUE_MAX = 10.0
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
BULK_MIN = 1
BULK_MAX = 100
CATEGORY_NAME_MIN = 2
CATEGORY_NAME_MAX = 40
CODE_MIN = 3
CODE_MAX = 40
TITLE_MIN = 3
TITLE_MAX = 120

# SQLite INTEGER: знакове 64-бітне ціле.
SQLITE_INT_MAX = 9223372036854775807
