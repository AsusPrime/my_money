import pytest

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import AlreadyExistsError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.balance_group import BalanceGroupCreateSchema
from src.schemas.balance_group import BalanceGroupUpdateSchema
from src.services.balance_group_service import BalanceGroupService
from tests.services.conftest import make_balance_group_row


class TestGetAllBalanceGroupsByAccountId:
    async def test_returns_groups_for_the_given_account(self, uow):
        uow.balance_groups.find_all.return_value = [
            make_balance_group_row(id=1, name="Savings", account_id=1),
            make_balance_group_row(id=2, name="Investments", account_id=1),
        ]

        result = await BalanceGroupService.get_all_balance_groups_by_account_id(
            uow=uow, account_id=1
        )

        assert [g.name for g in result.items] == ["Savings", "Investments"]
        uow.balance_groups.find_all.assert_awaited_once_with(account_id=1)

    async def test_returns_empty_list_when_no_groups(self, uow):
        uow.balance_groups.find_all.return_value = []

        result = await BalanceGroupService.get_all_balance_groups_by_account_id(
            uow=uow, account_id=1
        )

        assert result.items == []


class TestCreateBalanceGroup:
    async def test_creates_group(self, uow):
        uow.balance_groups.find_all.return_value = []
        uow.balance_groups.add_one.return_value = make_balance_group_row(
            id=1, name="Savings", account_id=1
        )

        result = await BalanceGroupService.create_balance_group(
            uow=uow, group_data=BalanceGroupCreateSchema(name="Savings", account_id=1)
        )

        assert result.name == "Savings"
        uow.balance_groups.add_one.assert_awaited_once_with(
            data={"name": "Savings", "account_id": 1}
        )

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.balance_groups.find_all.return_value = []
        uow.balance_groups.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await BalanceGroupService.create_balance_group(
                uow=uow, group_data=BalanceGroupCreateSchema(name="Savings", account_id=1)
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_BALANCE_GROUP

    async def test_raises_already_exists_when_name_taken_in_the_same_account(self, uow):
        uow.balance_groups.find_all.return_value = [
            make_balance_group_row(id=1, name="Savings", account_id=1),
        ]

        with pytest.raises(AlreadyExistsError) as exc_info:
            await BalanceGroupService.create_balance_group(
                uow=uow, group_data=BalanceGroupCreateSchema(name="savings", account_id=1)
            )

        assert exc_info.value.message == Messages.BALANCE_GROUP_ALREADY_EXISTS
        uow.balance_groups.add_one.assert_not_called()

    async def test_allows_the_same_name_in_a_different_account(self, uow):
        uow.balance_groups.find_all.return_value = []  # find_all is scoped to account_id
        uow.balance_groups.add_one.return_value = make_balance_group_row(
            id=2, name="Savings", account_id=2
        )

        result = await BalanceGroupService.create_balance_group(
            uow=uow, group_data=BalanceGroupCreateSchema(name="Savings", account_id=2)
        )

        assert result.name == "Savings"
        uow.balance_groups.find_all.assert_awaited_once_with(account_id=2)


class TestUpdateBalanceGroupById:
    async def test_updates_group(self, uow):
        uow.balance_groups.find_one_or_none.return_value = make_balance_group_row(
            id=1, name="Old name", account_id=1
        )
        uow.balance_groups.find_all.return_value = []
        uow.balance_groups.edit_one.return_value = make_balance_group_row(id=1, name="New name")

        result = await BalanceGroupService.update_balance_group_by_id(
            uow=uow, group_id=1, group_data=BalanceGroupUpdateSchema(name="New name")
        )

        assert result.name == "New name"

    async def test_raises_not_found_when_missing(self, uow):
        uow.balance_groups.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceGroupService.update_balance_group_by_id(
                uow=uow, group_id=999, group_data=BalanceGroupUpdateSchema(name="X")
            )

        assert exc_info.value.message == Messages.BALANCE_GROUP_NOT_FOUND
        uow.balance_groups.edit_one.assert_not_called()

    async def test_raises_already_exists_when_renaming_to_a_taken_name(self, uow):
        uow.balance_groups.find_one_or_none.return_value = make_balance_group_row(
            id=1, name="Savings", account_id=1
        )
        uow.balance_groups.find_all.return_value = [
            make_balance_group_row(id=1, name="Savings", account_id=1),
            make_balance_group_row(id=2, name="Investments", account_id=1),
        ]

        with pytest.raises(AlreadyExistsError) as exc_info:
            await BalanceGroupService.update_balance_group_by_id(
                uow=uow, group_id=1, group_data=BalanceGroupUpdateSchema(name="investments")
            )

        assert exc_info.value.message == Messages.BALANCE_GROUP_ALREADY_EXISTS
        uow.balance_groups.edit_one.assert_not_called()

    async def test_allows_renaming_to_the_same_name_it_already_has(self, uow):
        uow.balance_groups.find_one_or_none.return_value = make_balance_group_row(
            id=1, name="Savings", account_id=1
        )
        uow.balance_groups.find_all.return_value = [
            make_balance_group_row(id=1, name="Savings", account_id=1),
        ]
        uow.balance_groups.edit_one.return_value = make_balance_group_row(id=1, name="Savings")

        result = await BalanceGroupService.update_balance_group_by_id(
            uow=uow, group_id=1, group_data=BalanceGroupUpdateSchema(name="Savings")
        )

        assert result.name == "Savings"

    async def test_skips_the_uniqueness_check_when_name_is_not_being_changed(self, uow):
        uow.balance_groups.edit_one.return_value = make_balance_group_row(id=1, name="Savings")

        await BalanceGroupService.update_balance_group_by_id(
            uow=uow, group_id=1, group_data=BalanceGroupUpdateSchema()
        )

        uow.balance_groups.find_one_or_none.assert_not_called()
        uow.balance_groups.find_all.assert_not_called()


class TestDeleteBalanceGroupById:
    async def test_deletes_group(self, uow):
        uow.balance_groups.delete_one.return_value = make_balance_group_row(id=1)

        await BalanceGroupService.delete_balance_group_by_id(uow=uow, group_id=1)

        uow.balance_groups.delete_one.assert_awaited_once_with(_id=1)

    async def test_raises_not_found_when_missing(self, uow):
        uow.balance_groups.delete_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await BalanceGroupService.delete_balance_group_by_id(uow=uow, group_id=999)

        assert exc_info.value.message == Messages.BALANCE_GROUP_NOT_FOUND
