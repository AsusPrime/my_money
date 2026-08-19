import pytest
from pydantic import ValidationError

from src.schemas.category import CategoryCreateSchema
from src.schemas.category import CategoryResponseSchema
from src.schemas.category import CategoryUpdateSchema


class TestCategoryCreateSchema:
    def test_accepts_a_name(self):
        payload = CategoryCreateSchema(name="Salary")

        assert payload.name == "Salary"

    def test_requires_name(self):
        with pytest.raises(ValidationError):
            CategoryCreateSchema()


class TestCategoryUpdateSchema:
    def test_all_fields_optional(self):
        payload = CategoryUpdateSchema()

        assert payload.name is None

    def test_accepts_partial_update(self):
        payload = CategoryUpdateSchema(name="Groceries")

        assert payload.name == "Groceries"


class TestCategoryResponseSchema:
    def test_reads_from_attributes(self):
        from types import SimpleNamespace

        row = SimpleNamespace(id=1, name="Salary")

        result = CategoryResponseSchema.model_validate(row)

        assert result.id == 1
        assert result.name == "Salary"
