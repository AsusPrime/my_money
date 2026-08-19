from src.entities.category import CategoryEntity
from tests.entities.conftest import make_category_row


class TestIsInUse:
    async def test_true_when_ledgers_reference_category(self, uow):
        uow.ledgers.count_all.return_value = 3
        entity = CategoryEntity(category=make_category_row(id=1), uow=uow)

        result = await entity.is_in_use()

        assert result is True
        uow.ledgers.count_all.assert_awaited_once_with(category_id=1)

    async def test_false_when_no_ledgers_reference_category(self, uow):
        uow.ledgers.count_all.return_value = 0
        entity = CategoryEntity(category=make_category_row(id=1), uow=uow)

        result = await entity.is_in_use()

        assert result is False
