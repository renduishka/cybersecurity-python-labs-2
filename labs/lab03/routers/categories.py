"""HTTP-маршрути категорій аудиту."""

from typing import Annotated

from fastapi import APIRouter, Path, Response

from labs.lab03 import config, repository
from labs.lab03.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["Категорії"])


@router.get(
    "", response_model=list[CategoryRead], summary="Список напрямів аудиту"
)
def list_categories() -> list[dict]:
    """Повернути категорії за зростанням id."""
    return repository.list_categories()


@router.post(
    "",
    response_model=CategoryRead,
    status_code=201,
    summary="Створити напрям аудиту",
    responses={409: {"description": "Назва вже існує"}},
)
def create_category(data: CategoryCreate) -> dict:
    """Створити категорію з унікальною назвою."""
    return repository.create_category(data.name)


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Видалити порожню категорію",
    responses={
        404: {"description": "Категорію не знайдено"},
        409: {"description": "Категорія містить записи"},
    },
)
def delete_category(
    category_id: Annotated[
        int,
        Path(
            gt=0, le=config.SQLITE_INT_MAX, description="Додатний id категорії"
        ),
    ],
) -> Response:
    """Не дозволяти видалення категорії, яка має записи."""
    repository.delete_category(category_id)
    return Response(status_code=204)
