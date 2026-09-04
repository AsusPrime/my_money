from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.enums.enums import CurrencyTypeEnum
from src.enums.enums import LedgerReportGroupByEnum
from src.enums.enums import LedgerReportMetricEnum
from src.enums.enums import OperationTypeEnum
from src.repositories.account import AccountRepository
from src.repositories.balance import BalanceRepository
from src.repositories.category import CategoryRepository
from src.repositories.currency import CurrencyRepository
from src.repositories.ledger import LedgerRepository

pytestmark = pytest.mark.integration


async def _make_account(session, base_currency_ticker: str = "USD") -> int:
    await CurrencyRepository(session).add_one(
        data={
            "ticker": base_currency_ticker,
            "currency_type": CurrencyTypeEnum.FIAT,
            "decimal_places": 2,
        }
    )
    account = await AccountRepository(session).add_one(
        data={"name": "Main", "base_currency_ticker": base_currency_ticker}
    )
    return account["id"]


async def _make_balance(
    session, account_id: int, name: str = "Cash", is_archived: bool = False
) -> int:
    balance = await BalanceRepository(session).add_one(
        data={"name": name, "account_id": account_id, "is_archived": is_archived}
    )
    return balance["id"]


async def _make_category(session, name: str = "Salary") -> int:
    category = await CategoryRepository(session).add_one(data={"name": name})
    return category["id"]


class TestGetAmountsByBalanceId:
    async def test_groups_and_sums_by_currency(self, session):
        account_id = await _make_account(session)
        await CurrencyRepository(session).add_one(
            data={"ticker": "EUR", "currency_type": CurrencyTypeEnum.FIAT, "decimal_places": 2}
        )
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-30"), "operation_type": OperationTypeEnum.EXPENSE,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "EUR",
                "amount": Decimal("15"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        result = await ledger_repo.get_amounts_by_balance_id(balance_id=balance_id)

        assert result == {"USD": Decimal("70"), "EUR": Decimal("15")}

    async def test_returns_empty_dict_when_no_ledger_rows(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id, name="Empty")
        await session.commit()

        result = await LedgerRepository(session).get_amounts_by_balance_id(balance_id=balance_id)

        assert result == {}

    async def test_only_sums_rows_for_the_given_balance(self, session):
        account_id = await _make_account(session)
        balance_a = await _make_balance(session, account_id, name="A")
        balance_b = await _make_balance(session, account_id, name="B")
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_a, "currency_ticker": "USD",
                "amount": Decimal("50"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_b, "currency_ticker": "USD",
                "amount": Decimal("999"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        result = await ledger_repo.get_amounts_by_balance_id(balance_id=balance_a)

        assert result == {"USD": Decimal("50")}


class TestAggregate:
    async def test_groups_by_category_and_sums(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        salary_id = await _make_category(session, name="Salary")
        food_id = await _make_category(session, name="Food")
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("1000"), "operation_type": OperationTypeEnum.INCOME,
                "category_id": salary_id,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-30"), "operation_type": OperationTypeEnum.EXPENSE,
                "category_id": food_id,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-20"), "operation_type": OperationTypeEnum.EXPENSE,
                "category_id": None,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.CATEGORY, metric=LedgerReportMetricEnum.SUM
        )

        assert dict(result) == {
            "Salary": Decimal("1000"),
            "Food": Decimal("-30"),
            "Uncategorized": Decimal("-20"),
        }

    async def test_groups_by_counterparty_defaults_to_unknown(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
                "counterparty": None,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.COUNTERPARTY, metric=LedgerReportMetricEnum.SUM
        )

        assert dict(result) == {"Unknown": Decimal("100")}

    async def test_groups_by_month_time_bucket(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("50"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2026, 1, 28, tzinfo=timezone.utc),
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("10"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2026, 2, 1, tzinfo=timezone.utc),
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.MONTH, metric=LedgerReportMetricEnum.SUM
        )

        buckets = {key.date(): value for key, value in result}
        assert buckets == {
            datetime(2026, 1, 1).date(): Decimal("150"),
            datetime(2026, 2, 1).date(): Decimal("10"),
        }

    async def test_groups_by_balance_with_count_metric(self, session):
        account_id = await _make_account(session)
        balance_a = await _make_balance(session, account_id, name="A")
        balance_b = await _make_balance(session, account_id, name="B")
        ledger_repo = LedgerRepository(session)

        for _ in range(2):
            await ledger_repo.add_one(
                data={
                    "operation_id": uuid4(), "balance_id": balance_a, "currency_ticker": "USD",
                    "amount": Decimal("10"), "operation_type": OperationTypeEnum.INCOME,
                }
            )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_b, "currency_ticker": "USD",
                "amount": Decimal("10"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.BALANCE, metric=LedgerReportMetricEnum.COUNT
        )

        assert dict(result) == {"A": 2, "B": 1}

    async def test_groups_by_account_and_filters_by_account_id(self, session):
        account_a = await _make_account(session, base_currency_ticker="USD")
        account_b = await _make_account(session, base_currency_ticker="EUR")
        balance_a = await _make_balance(session, account_a, name="A")
        balance_b = await _make_balance(session, account_b, name="B")
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_a, "currency_ticker": "USD",
                "amount": Decimal("10"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_b, "currency_ticker": "USD",
                "amount": Decimal("999"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.ACCOUNT,
            metric=LedgerReportMetricEnum.SUM,
            account_id=account_a,
        )

        assert dict(result) == {"Main": Decimal("10")}

    async def test_net_of_fees_subtracts_the_sibling_fee_leg(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        food_id = await _make_category(session, name="Food")
        ledger_repo = LedgerRepository(session)
        operation_id = uuid4()

        await ledger_repo.add_one(
            data={
                "operation_id": operation_id, "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-100"), "operation_type": OperationTypeEnum.EXPENSE,
                "category_id": food_id,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": operation_id, "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-5"), "operation_type": OperationTypeEnum.FEE,
                "category_id": None,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.CATEGORY, metric=LedgerReportMetricEnum.NET_OF_FEES
        )

        # the fee leg is netted into Food's group, not reported as its own
        # "Uncategorized" group
        assert dict(result) == {"Food": Decimal("-105")}

    async def test_filters_by_date_range(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("999"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.CURRENCY_TICKER,
            metric=LedgerReportMetricEnum.SUM,
            date_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            date_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )

        assert dict(result) == {"USD": Decimal("100")}

    async def test_filters_by_operation_type(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-40"), "operation_type": OperationTypeEnum.EXPENSE,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.OPERATION_TYPE,
            metric=LedgerReportMetricEnum.SUM,
            operation_types=[OperationTypeEnum.EXPENSE],
        )

        assert dict(result) == {"expense": Decimal("-40")}

    async def test_filters_by_multiple_operation_types(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-40"), "operation_type": OperationTypeEnum.EXPENSE,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-5"), "operation_type": OperationTypeEnum.FEE,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.OPERATION_TYPE,
            metric=LedgerReportMetricEnum.SUM,
            operation_types=[OperationTypeEnum.INCOME, OperationTypeEnum.EXPENSE],
        )

        assert dict(result) == {"income": Decimal("100"), "expense": Decimal("-40")}

    async def test_filters_by_multiple_category_ids(self, session):
        account_id = await _make_account(session)
        balance_id = await _make_balance(session, account_id)
        salary_id = await _make_category(session, name="Salary")
        gift_id = await _make_category(session, name="Gifts")
        food_id = await _make_category(session, name="Food")
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("1000"), "operation_type": OperationTypeEnum.INCOME,
                "category_id": salary_id,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("50"), "operation_type": OperationTypeEnum.INCOME,
                "category_id": gift_id,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": balance_id, "currency_ticker": "USD",
                "amount": Decimal("-30"), "operation_type": OperationTypeEnum.EXPENSE,
                "category_id": food_id,
            }
        )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.CATEGORY,
            metric=LedgerReportMetricEnum.SUM,
            category_ids=[salary_id, gift_id],
        )

        assert dict(result) == {"Salary": Decimal("1000"), "Gifts": Decimal("50")}

    async def test_filters_by_multiple_balance_ids(self, session):
        account_id = await _make_account(session)
        balance_a = await _make_balance(session, account_id, name="A")
        balance_b = await _make_balance(session, account_id, name="B")
        balance_c = await _make_balance(session, account_id, name="C")
        ledger_repo = LedgerRepository(session)

        for balance, amount in [(balance_a, "10"), (balance_b, "20"), (balance_c, "30")]:
            await ledger_repo.add_one(
                data={
                    "operation_id": uuid4(), "balance_id": balance, "currency_ticker": "USD",
                    "amount": Decimal(amount), "operation_type": OperationTypeEnum.INCOME,
                }
            )
        await session.commit()

        result = await ledger_repo.aggregate(
            group_by=LedgerReportGroupByEnum.BALANCE,
            metric=LedgerReportMetricEnum.SUM,
            balance_ids=[balance_a, balance_c],
        )

        assert dict(result) == {"A": Decimal("10"), "C": Decimal("30")}


class TestGetRowsForNetWorth:
    async def test_excludes_archived_balances_by_default(self, session):
        account_id = await _make_account(session, base_currency_ticker="UAH")
        active_balance = await _make_balance(session, account_id, name="Active")
        archived_balance = await _make_balance(
            session, account_id, name="Dead wallet", is_archived=True
        )
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": active_balance, "currency_ticker": "UAH",
                "amount": Decimal("100"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": archived_balance, "currency_ticker": "UAH",
                "amount": Decimal("999"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        rows = await ledger_repo.get_rows_for_net_worth()

        assert [row.amount for row in rows] == [Decimal("100")]

    async def test_filters_by_multiple_balance_ids(self, session):
        account_id = await _make_account(session, base_currency_ticker="UAH")
        balance_a = await _make_balance(session, account_id, name="A")
        balance_b = await _make_balance(session, account_id, name="B")
        balance_c = await _make_balance(session, account_id, name="C")
        ledger_repo = LedgerRepository(session)

        for balance, amount in [(balance_a, "10"), (balance_b, "20"), (balance_c, "30")]:
            await ledger_repo.add_one(
                data={
                    "operation_id": uuid4(), "balance_id": balance, "currency_ticker": "UAH",
                    "amount": Decimal(amount), "operation_type": OperationTypeEnum.INCOME,
                }
            )
        await session.commit()

        rows = await ledger_repo.get_rows_for_net_worth(balance_ids=[balance_a, balance_c])

        assert sorted(row.amount for row in rows) == [Decimal("10"), Decimal("30")]

    async def test_includes_an_archived_balance_when_explicitly_filtered_to_it(self, session):
        account_id = await _make_account(session, base_currency_ticker="UAH")
        archived_balance = await _make_balance(
            session, account_id, name="Dead wallet", is_archived=True
        )
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": archived_balance, "currency_ticker": "UAH",
                "amount": Decimal("999"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        rows = await ledger_repo.get_rows_for_net_worth(balance_ids=[archived_balance])

        assert [row.amount for row in rows] == [Decimal("999")]

    async def test_excludes_archived_balances_when_scoped_by_account_id(self, session):
        account_id = await _make_account(session, base_currency_ticker="UAH")
        active_balance = await _make_balance(session, account_id, name="Active")
        archived_balance = await _make_balance(
            session, account_id, name="Dead wallet", is_archived=True
        )
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": active_balance, "currency_ticker": "UAH",
                "amount": Decimal("50"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": archived_balance, "currency_ticker": "UAH",
                "amount": Decimal("500"), "operation_type": OperationTypeEnum.INCOME,
            }
        )
        await session.commit()

        rows = await ledger_repo.get_rows_for_net_worth(account_id=account_id)

        assert [row.amount for row in rows] == [Decimal("50")]


class TestGetEarliestExecutedAt:
    async def test_ignores_activity_in_archived_balances_by_default(self, session):
        account_id = await _make_account(session)
        active_balance = await _make_balance(session, account_id, name="Active")
        archived_balance = await _make_balance(
            session, account_id, name="Dead wallet", is_archived=True
        )
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": archived_balance, "currency_ticker": "USD",
                "amount": Decimal("1"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            }
        )
        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": active_balance, "currency_ticker": "USD",
                "amount": Decimal("1"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            }
        )
        await session.commit()

        result = await ledger_repo.get_earliest_executed_at()

        assert result == datetime(2026, 1, 1, tzinfo=timezone.utc)

    async def test_returns_none_when_only_archived_balances_have_activity(self, session):
        account_id = await _make_account(session)
        archived_balance = await _make_balance(
            session, account_id, name="Dead wallet", is_archived=True
        )
        ledger_repo = LedgerRepository(session)

        await ledger_repo.add_one(
            data={
                "operation_id": uuid4(), "balance_id": archived_balance, "currency_ticker": "USD",
                "amount": Decimal("1"), "operation_type": OperationTypeEnum.INCOME,
                "executed_at": datetime(2020, 1, 1, tzinfo=timezone.utc),
            }
        )
        await session.commit()

        result = await ledger_repo.get_earliest_executed_at()

        assert result is None
