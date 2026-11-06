"""FastAPI-застосунок для лабораторної роботи 3, варіант 13."""

import logging
import math
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from labs.lab03 import config, database, repository
from labs.lab03.routers import categories, records
from labs.lab03.schemas import PingRead, StudentRead
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці один раз під час запуску."""
    database.initialize_database()
    yield


app = FastAPI(
    title=config.VARIANT_TITLE,
    description=(
        f"{config.DOMAIN_DESCRIPTION} Одиниця: {config.UNIT}. "
        f"Поріг: {config.THRESHOLD}; вибірка: /records?min_value=7."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(repository.NotFoundError)
def not_found(
    request: Request, error: repository.NotFoundError
) -> JSONResponse:
    """Перетворити відсутність ресурсу на HTTP 404."""
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(sqlite3.IntegrityError)
def integrity_error(
    request: Request, error: sqlite3.IntegrityError
) -> JSONResponse:
    """Повернути конфлікт без розкриття SQL і структури файлів."""
    logger.warning("Порушення цілісності SQLite: %s", error)
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Конфлікт даних: дублікат або категорія містить записи"
        },
    )


@app.exception_handler(sqlite3.Error)
def database_error(request: Request, error: sqlite3.Error) -> JSONResponse:
    """Зберегти технічні подробиці лише в журналі сервера."""
    logger.error(
        "Помилка SQLite", exc_info=(type(error), error, error.__traceback__)
    )
    return JSONResponse(
        status_code=500, content={"detail": "Помилка роботи з базою даних"}
    )


def _json_safe(value: Any) -> Any:
    """Зробити повідомлення валідації серіалізовним навіть для NaN/inf."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Exception):
        return str(value)
    return value


@app.exception_handler(RequestValidationError)
def validation_error(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Відхилити некоректні дані з JSON-відповіддю 422."""
    return JSONResponse(
        status_code=422, content={"detail": _json_safe(error.errors())}
    )


@app.get(
    "/ping",
    response_model=PingRead,
    tags=["Службові"],
    summary="Перевірити доступність",
)
def ping() -> dict[str, str]:
    """Повернути ознаку доступності API."""
    return {"status": "ok"}


@app.get(
    "/student",
    response_model=StudentRead,
    tags=["Службові"],
    summary="Дані студента",
)
def student() -> dict[str, Any]:
    """Прочитати дані виконавця зі спільного пакета."""
    return {
        "student_name": STUDENT_NAME,
        "group_name": GROUP_NAME,
        "variant_number": VARIANT_NUMBER,
    }
