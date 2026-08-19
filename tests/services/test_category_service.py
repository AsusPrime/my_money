import pytest

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import ConflictError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.category import CategoryCreateSchema
from src.schemas.category import CategoryUpdateSchema
from src.services.category_service import CategoryService
from tests.services.conftest import make_category_row


class TestGetAllCategories:
    async def test_returns_all_categories(self, uow):
        uow.categories.find_all.return_value = [
            make_category_row(id=1, name="Salary"),
            make_category_row(id=2, name="Food"),
        ]

        result = await CategoryService.get_all_categories(uow=uow)

        assert [c.name for c in result.items] == ["Salary", "Food"]

    async def test_returns_empty_list_when_no_categories(self, uow):
        uow.categories.find_all.return_value = []

        result = await CategoryService.get_all_categories(uow=uow)

        assert result.items == []


class TestGetCategoryById:
    async def test_returns_category_when_found(self, uow):
        uow.categories.find_one_or_none.return_value = make_category_row(id=1, name="Salary")

        result = await CategoryService.get_category_by_id(uow=uow, category_id=1)

        assert result.id == 1
        assert result.name == "Salary"
        uow.categories.find_one_or_none.assert_awaited_once_with(id=1)

    async def test_raises_not_found_when_missing(self, uow):
        uow.categories.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await CategoryService.get_category_by_id(uow=uow, category_id=999)

        assert exc_info.value.message == Messages.CATEGORY_NOT_FOUND


class TestCreateCategory:
    async def test_creates_category(self, uow):
        uow.categories.add_one.return_value = make_category_row(id=1, name="Savings")

        result = await CategoryService.create_category(
            uow=uow, category_data=CategoryCreateSchema(name="Savings")
        )

        assert result.name == "Savings"
        uow.categories.add_one.assert_awaited_once_with(data={"name": "Savings"})

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.categories.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await CategoryService.create_category(
                uow=uow, category_data=CategoryCreateSchema(name="Savings")
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_CATEGORY


class TestUpdateCategoryById:
    async def test_updates_category(self, uow):
        uow.categories.edit_one.return_value = make_category_row(id=1, name="New name")

        result = await CategoryService.update_category_by_id(
            uow=uow, category_id=1, category_data=CategoryUpdateSchema(name="New name")
        )

        assert result.name == "New name"

    async def test_raises_not_found_when_missing(self, uow):
        uow.categories.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await CategoryService.update_category_by_id(
                uow=uow, category_id=999, category_data=CategoryUpdateSchema(name="X")
            )

        assert exc_info.value.message == Messages.CATEGORY_NOT_FOUND


class TestDeleteCategoryById:
    async def test_deletes_category_when_not_in_use(self, uow):
        uow.categories.find_one_or_none.return_value = make_category_row(id=1)
        uow.ledgers.count_all.return_value = 0

        await CategoryService.delete_category_by_id(uow=uow, category_id=1)

        uow.categories.delete_one.assert_awaited_once_with(_id=1)

    async def test_raises_not_found_when_missing(self, uow):
        uow.categories.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await CategoryService.delete_category_by_id(uow=uow, category_id=999)

        assert exc_info.value.message == Messages.CATEGORY_NOT_FOUND
        uow.categories.delete_one.assert_not_called()

    async def test_raises_conflict_when_category_still_in_use(self, uow):
        uow.categories.find_one_or_none.return_value = make_category_row(id=1)
        uow.ledgers.count_all.return_value = 3

        with pytest.raises(ConflictError) as exc_info:
            await CategoryService.delete_category_by_id(uow=uow, category_id=1)

        assert exc_info.value.message == Messages.CATEGORY_IN_USE
        uow.categories.delete_one.assert_not_called()
