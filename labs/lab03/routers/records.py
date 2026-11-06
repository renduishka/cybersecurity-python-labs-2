"""HTTP-маршрути знахідок аудиту хмарної конфігурації."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, Response

from labs.lab03 import config, repository
from labs.lab03.schemas import RecordCreate, RecordRead, RecordReplace, Status

router = APIRouter(prefix="/records", tags=["Знахідки"])
NOT_FOUND = {404: {"description": "Запис або категорію не знайдено"}}
WRITE_ERRORS = {**NOT_FOUND, 409: {"description": "Унікальний code вже існує"}}
RecordId = Annotated[
    int,
    Path(gt=0, le=config.SQLITE_INT_MAX, description="Додатний id знахідки"),
]


@router.get(
    "", response_model=list[RecordRead], summary="Знайти знахідки з фільтрами"
)
def list_records(
    category_id: Annotated[
        int | None,
        Query(gt=0, le=config.SQLITE_INT_MAX, description="Напрям аудиту"),
    ] = None,
    status: Annotated[
        Status | None, Query(description="Стан опрацювання")
    ] = None,
    min_value: Annotated[
        float | None,
        Query(
            ge=config.VALUE_MIN,
            le=config.VALUE_MAX,
            allow_inf_nan=False,
            description="Мінімальна оцінка ризику (score)",
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=config.TITLE_MAX,
            description="Буквальний підрядок title з урахуванням регістру",
        ),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=config.MAX_LIMIT, description="Розмір сторінки")
    ] = config.DEFAULT_LIMIT,
    offset: Annotated[
        int,
        Query(
            ge=0,
            le=config.SQLITE_INT_MAX,
            description="Кількість пропущених записів",
        ),
    ] = 0,
) -> list[dict]:
    """Поєднати задані умови через AND, сортувати за id."""
    return repository.list_records(
        category_id, status, min_value, q, limit, offset
    )


@router.post(
    "/bulk",
    response_model=list[RecordRead],
    status_code=201,
    responses=WRITE_ERRORS,
    summary="Створити пакет атомарно",
)
def create_bulk(
    records: Annotated[
        list[RecordCreate],
        Body(min_length=config.BULK_MIN, max_length=config.BULK_MAX),
    ],
) -> list[dict]:
    """Валідувати весь масив; за будь-якої помилки скасувати весь пакет."""
    return repository.create_records(
        [record.model_dump() for record in records]
    )


@router.post(
    "",
    response_model=RecordRead,
    status_code=201,
    responses=WRITE_ERRORS,
    summary="Створити знахідку",
)
def create_record(record: RecordCreate) -> dict:
    """Додати знахідку для наявної категорії."""
    return repository.create_record(record.model_dump())


@router.get(
    "/{record_id}",
    response_model=RecordRead,
    responses=NOT_FOUND,
    summary="Отримати знахідку за id",
)
def get_record(record_id: RecordId) -> dict:
    """Повернути знахідку з назвою категорії."""
    return repository.get_record(record_id)


@router.put(
    "/{record_id}",
    response_model=RecordRead,
    responses=WRITE_ERRORS,
    summary="Повністю замінити поля знахідки",
)
def replace_record(record_id: RecordId, record: RecordReplace) -> dict:
    """Оновити п'ять полів; id залишається незмінним."""
    return repository.replace_record(record_id, record.model_dump())


@router.delete(
    "/{record_id}",
    status_code=204,
    responses=NOT_FOUND,
    summary="Видалити знахідку",
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис і повернути порожню відповідь."""
    repository.delete_record(record_id)
    return Response(status_code=204)
