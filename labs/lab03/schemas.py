"""Моделі даних API та перевірки початкового набору."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from labs.lab03 import config

Status = Literal["new", "in_progress", "done"]


class StrictInput(BaseModel):
    """Вхідні дані без зайвих полів та крайових пробілів."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryCreate(StrictInput):
    """Назва напряму аудиту."""

    name: str = Field(
        min_length=config.CATEGORY_NAME_MIN,
        max_length=config.CATEGORY_NAME_MAX,
    )


class CategoryRead(CategoryCreate):
    """Категорія з ідентифікатором SQLite."""

    id: int = Field(gt=0, le=config.SQLITE_INT_MAX)


class RecordCreate(StrictInput):
    """Новий результат аудиту; id визначає база."""

    code: str = Field(
        min_length=config.CODE_MIN,
        max_length=config.CODE_MAX,
        examples=["V13-TEST"],
    )
    title: str = Field(
        min_length=config.TITLE_MIN, max_length=config.TITLE_MAX
    )
    category_id: int = Field(
        gt=0,
        le=config.SQLITE_INT_MAX,
        description="Ідентифікатор напряму аудиту",
    )
    value: float = Field(
        ge=config.VALUE_MIN,
        le=config.VALUE_MAX,
        allow_inf_nan=False,
        description="Навчальна оцінка ризику, score (0–10)",
    )
    status: Status


class RecordReplace(RecordCreate):
    """Повна заміна всіх п'яти змінюваних полів запису."""


class RecordRead(RecordCreate):
    """Результат JOIN із назвою категорії."""

    id: int = Field(gt=0, le=config.SQLITE_INT_MAX)
    category_name: str


class StudentRead(BaseModel):
    """Відомості про виконавця."""

    student_name: str
    group_name: str
    variant_number: int


class PingRead(BaseModel):
    """Ознака доступності API."""

    status: Literal["ok"]


class SeedData(StrictInput):
    """Три категорії та вісім навчальних знахідок."""

    categories: list[CategoryRead] = Field(min_length=3, max_length=3)
    records: list[RecordCreate] = Field(min_length=8, max_length=8)

    @model_validator(mode="after")
    def check_relations(self) -> "SeedData":
        """Відхилити дублікати та відсутні посилання до запису в БД."""
        ids = [category.id for category in self.categories]
        names = [category.name for category in self.categories]
        codes = [record.code for record in self.records]
        if len(set(ids)) != 3 or len(set(names)) != 3 or len(set(codes)) != 8:
            raise ValueError("Початковий набір містить дублікати")
        if any(record.category_id not in ids for record in self.records):
            raise ValueError("Категорію початкового запису не знайдено")
        return self
