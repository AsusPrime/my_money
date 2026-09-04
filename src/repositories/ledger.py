from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, select

from src.enums.enums import LedgerReportGroupByEnum, LedgerReportMetricEnum, OperationTypeEnum
from src.models import Account, Balance, Category, Ledger
from src.utils.repository.repository import SQLAlchemyRepository

_TIME_BUCKET_GROUP_BYS = {
    LedgerReportGroupByEnum.DAY,
    LedgerReportGroupByEnum.WEEK,
    LedgerReportGroupByEnum.MONTH,
    LedgerReportGroupByEnum.QUARTER,
    LedgerReportGroupByEnum.YEAR,
}


class LedgerRepository(SQLAlchemyRepository):

    model = Ledger

    async def get_amounts_by_balance_id(self, balance_id: int) -> dict[str, Decimal]:
        stmt = (
            select(self.model.currency_ticker, func.sum(self.model.amount))
            .group_by(self.model.currency_ticker)
            .where(self.model.balance_id == balance_id)
        )

        res = await self.session.execute(stmt)
        return dict(res.all())

    async def get_earliest_executed_at(
        self,
        *,
        account_id: int | None = None,
        balance_ids: list[int] | None = None,
    ) -> datetime | None:
        stmt = select(func.min(self.model.executed_at))
        needs_balance_join = not balance_ids
        if needs_balance_join:
            stmt = stmt.join(Balance, Balance.id == self.model.balance_id)

        filters = []
        if account_id is not None:
            filters.append(Balance.account_id == account_id)
        if balance_ids:
            filters.append(self.model.balance_id.in_(balance_ids))
        else:
            filters.append(Balance.is_archived.is_(False))
        if filters:
            stmt = stmt.where(*filters)

        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_rows_for_net_worth(
        self,
        *,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        account_id: int | None = None,
        balance_ids: list[int] | None = None,
    ) -> list[tuple[datetime, str, Decimal, Decimal | None, str]]:
        model = self.model
        stmt = (
            select(
                model.executed_at,
                model.currency_ticker,
                model.amount,
                model.base_currency_rate,
                Account.base_currency_ticker,
            )
            .join(Balance, Balance.id == model.balance_id)
            .join(Account, Account.id == Balance.account_id)
        )

        filters = []
        if date_start is not None:
            filters.append(model.executed_at >= date_start)
        if date_end is not None:
            filters.append(model.executed_at <= date_end)
        if account_id is not None:
            filters.append(Balance.account_id == account_id)
        if balance_ids:
            filters.append(model.balance_id.in_(balance_ids))
        else:
            filters.append(Balance.is_archived.is_(False))
        if filters:
            stmt = stmt.where(*filters)

        stmt = stmt.order_by(model.executed_at)

        res = await self.session.execute(stmt)
        return res.all()

    async def find_all_by_balance_id(self, balance_id: int, limit: int, offset: int = 0):
        stmt = (
            select(self.model)
            .where(self.model.balance_id == balance_id)
            .order_by(self.model.executed_at.desc(), self.model.id.desc())
            .limit(limit)
            .offset(offset)
        )

        res = await self.session.execute(stmt)
        return res.scalars().all()  # noqa

    async def aggregate(
        self,
        *,
        group_by: LedgerReportGroupByEnum,
        metric: LedgerReportMetricEnum,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        operation_types: list[OperationTypeEnum] | None = None,
        currency_ticker: str | None = None,
        category_ids: list[int] | None = None,
        balance_ids: list[int] | None = None,
        account_id: int | None = None,
    ) -> list[tuple]:
        model = self.model
        group_expr = self._group_expression(group_by)
        needs_balance_join = group_by in (
            LedgerReportGroupByEnum.BALANCE,
            LedgerReportGroupByEnum.ACCOUNT,
        ) or account_id is not None
        needs_account_join = group_by == LedgerReportGroupByEnum.ACCOUNT or account_id is not None
        needs_category_join = group_by == LedgerReportGroupByEnum.CATEGORY
        net_of_fees = metric == LedgerReportMetricEnum.NET_OF_FEES

        if metric == LedgerReportMetricEnum.COUNT:
            value_expr = func.count(model.id)
        elif net_of_fees:
            fee_subq = (
                select(
                    model.operation_id.label("operation_id"),
                    func.sum(model.amount).label("fee_sum"),
                )
                .where(model.operation_type == OperationTypeEnum.FEE)
                .group_by(model.operation_id)
                .subquery()
            )
            value_expr = func.sum(model.amount + func.coalesce(fee_subq.c.fee_sum, 0))
        else:
            value_expr = func.sum(model.amount)

        stmt = select(group_expr.label("group_key"), value_expr.label("value"))

        if needs_balance_join:
            stmt = stmt.join(Balance, Balance.id == model.balance_id)
        if needs_account_join:
            stmt = stmt.join(Account, Account.id == Balance.account_id)
        if needs_category_join:
            stmt = stmt.outerjoin(Category, Category.id == model.category_id)
        if net_of_fees:
            # fee legs are netted into whichever group their sibling (fee-bearing)
            # leg falls into, not reported as their own group
            stmt = stmt.outerjoin(fee_subq, fee_subq.c.operation_id == model.operation_id)
            stmt = stmt.where(model.operation_type != OperationTypeEnum.FEE)

        filters = []
        if date_start is not None:
            filters.append(model.executed_at >= date_start)
        if date_end is not None:
            filters.append(model.executed_at <= date_end)
        if operation_types:
            filters.append(model.operation_type.in_(operation_types))
        if currency_ticker is not None:
            filters.append(model.currency_ticker == currency_ticker)
        if category_ids:
            filters.append(model.category_id.in_(category_ids))
        if balance_ids:
            filters.append(model.balance_id.in_(balance_ids))
        if account_id is not None:
            filters.append(Account.id == account_id)

        if filters:
            stmt = stmt.where(*filters)

        stmt = stmt.group_by(group_expr).order_by(group_expr)

        res = await self.session.execute(stmt)
        return res.all()

    @staticmethod
    def _group_expression(group_by: LedgerReportGroupByEnum):
        model = Ledger
        if group_by == LedgerReportGroupByEnum.CATEGORY:
            return func.coalesce(Category.name, "Uncategorized")
        if group_by == LedgerReportGroupByEnum.COUNTERPARTY:
            return func.coalesce(model.counterparty, "Unknown")
        if group_by == LedgerReportGroupByEnum.OPERATION_TYPE:
            return model.operation_type
        if group_by == LedgerReportGroupByEnum.CURRENCY_TICKER:
            return model.currency_ticker
        if group_by == LedgerReportGroupByEnum.BALANCE:
            return Balance.name
        if group_by == LedgerReportGroupByEnum.ACCOUNT:
            return Account.name
        if group_by in _TIME_BUCKET_GROUP_BYS:
            return func.date_trunc(group_by.value, model.executed_at)
        raise ValueError(f"Unsupported group_by: {group_by}")
