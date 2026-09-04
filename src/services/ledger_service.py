from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from uuid import uuid4
from dateutil.relativedelta import relativedelta
from src.common.constants import DEFAULT_API_LIMIT
from src.common.rounding import round_to_currency_precision
from src.core.exceptions.exceptions import BadRequestError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.entities.balance import BalanceEntity
from src.enums.enums import (
    CurrencyTypeEnum,
    LedgerReportGroupByEnum,
    LedgerReportMetricEnum,
    NetWorthBucketEnum,
    OperationTypeEnum,
)
from src.schemas.ledger import (
    LedgerListResponseSchema,
    LedgerPageResponseSchema,
    LedgerReportItemSchema,
    LedgerReportResponseSchema,
    LedgerResponseSchema,
    LedgerUpdateSchema,
    RecordSingleLegOperationPayload,
    RecordTradePayload,
    RecordTransferPayload,
)
from src.services.account_service import AccountService
from src.services.balance_service import BalanceService
from src.services.currency_service import CurrencyService
from src.services.exchange_rate_service import ExchangeRateService
from src.utils.uow.unitofwork import IUnitOfWork


class LedgerService:

    @staticmethod
    async def record_operation(
        uow: IUnitOfWork, payload: RecordSingleLegOperationPayload | RecordTransferPayload | RecordTradePayload
    ) -> LedgerResponseSchema | LedgerListResponseSchema:
        if payload.operation_type in (
            OperationTypeEnum.INCOME,
            OperationTypeEnum.EXPENSE,
            OperationTypeEnum.FEE
        ):
            return await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=payload
            )
        elif payload.operation_type == OperationTypeEnum.TRANSFER:
            return await LedgerService._transfer(
                uow=uow,
                payload=payload
            )
        elif payload.operation_type == OperationTypeEnum.TRADE:
            return await LedgerService._trade(
                uow=uow,
                payload=payload
            )

        raise NotFoundError(Messages.OPERATION_TYPE_NOT_FOUND)

    @staticmethod
    async def _record_single_leg_operation(
        uow: IUnitOfWork,
        payload: RecordSingleLegOperationPayload,
        balance_service: BalanceService = BalanceService(),
        currency_service: CurrencyService = CurrencyService(),
        account_service: AccountService = AccountService(),
        exchange_rate_service: ExchangeRateService = ExchangeRateService(),
        resolve_base_currency_rate: bool = True,
    ) -> LedgerResponseSchema:
        # check if currency exist
        # if not, it will raise an error
        currency = await currency_service.get_currency_by_ticker(uow=uow, ticker=payload.currency_ticker)
        # check if balance exist and is not archived
        # if not, it will raise an error
        balance = await balance_service.get_active_balance_by_id(uow=uow, balance_id=payload.balance_id)

        if payload.operation_type in (OperationTypeEnum.EXPENSE, OperationTypeEnum.FEE):
            payload.amount = -abs(payload.amount)
        elif payload.operation_type == OperationTypeEnum.INCOME:
            payload.amount = abs(payload.amount)

        # check if balance has enough funds in this currency for the operation
        # if not, it will raise an error
        balance_entity = BalanceEntity(balance=balance, uow=uow)
        await balance_entity.ensure_sufficient_funds(
            currency_ticker=payload.currency_ticker, amount=payload.amount
        )

        # executed_at defaults to now when the caller doesn't specify one
        if payload.executed_at is None:
            payload.executed_at = datetime.now(timezone.utc)

        # a standalone single-leg op has no paired leg to derive a rate from, so
        # auto-fetch it — unless the caller already gave one, or the currency
        # already matches the account's base currency (no conversion needed).
        # transfer/trade legs pass resolve_base_currency_rate=False and skip this
        # entirely, since their cost basis is already derivable from the paired
        # leg amounts.
        if resolve_base_currency_rate and payload.base_currency_rate is None:
            account = await account_service.get_account_by_id(
                uow=uow, account_id=balance.account_id
            )
            if payload.currency_ticker != account.base_currency_ticker:
                payload.base_currency_rate = await exchange_rate_service.get_historical_rate(
                    currency_ticker=payload.currency_ticker,
                    base_currency_ticker=account.base_currency_ticker,
                    currency_type=currency.currency_type,
                    rate_at=payload.executed_at,
                )

        new_operation = await uow.ledgers.add_one(data=payload.model_dump())
        return LedgerResponseSchema.model_validate(new_operation)

    @staticmethod
    async def _transfer(
        uow: IUnitOfWork,
        payload: RecordTransferPayload,
        balance_service: BalanceService = BalanceService(),
        currency_service: CurrencyService = CurrencyService(),
    ) -> LedgerListResponseSchema:
        response = LedgerListResponseSchema(items=[])
        operation_id = uuid4()
        # resolved once so every leg of this transfer shares the exact same
        # timestamp, instead of each leg independently defaulting to its own now()
        executed_at = payload.executed_at or datetime.now(timezone.utc)

        received_currency_ticker = payload.received_currency_ticker or payload.currency_ticker
        if payload.received_amount is not None:
            received_amount = payload.received_amount
        elif received_currency_ticker == payload.currency_ticker:
            received_amount = payload.amount
        else:
            raise BadRequestError(Messages.TRANSFER_RECEIVED_AMOUNT_REQUIRED)

        # creating the outflow leg — money leaving from_balance_id
        to_balance_name = await uow.balances.get_name_by_id(id=payload.to_balance_id)
        from_ledger = await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=payload.operation_type,
                balance_id=payload.from_balance_id,
                amount=-abs(payload.amount),
                currency_ticker=payload.currency_ticker,
                counterparty=to_balance_name,
                operation_id=operation_id,
                executed_at=executed_at,
                base_currency_rate=payload.base_currency_rate,
            ),
            balance_service=balance_service,
            currency_service=currency_service,
            resolve_base_currency_rate=False,
        )
        response.items.append(from_ledger)
        # creating the inflow leg — money arriving at to_balance_id
        from_balance_name = await uow.balances.get_name_by_id(id=payload.from_balance_id)
        to_ledger = await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=payload.operation_type,
                balance_id=payload.to_balance_id,
                amount=abs(received_amount),
                currency_ticker=received_currency_ticker,
                counterparty=from_balance_name,
                operation_id=operation_id,
                executed_at=executed_at,
                base_currency_rate=payload.base_currency_rate,
            ),
            balance_service=balance_service,
            currency_service=currency_service,
            resolve_base_currency_rate=False,
        )
        response.items.append(to_ledger)

        if payload.fee_currency_ticker:
            # creating fee transaction
            fee_ledger = await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.FEE,
                    balance_id=payload.from_balance_id,
                    amount=-abs(payload.fee_amount),
                    currency_ticker=payload.fee_currency_ticker,
                    operation_id=operation_id,
                    executed_at=executed_at,
                    base_currency_rate=payload.base_currency_rate,
                ),
                balance_service=balance_service,
                currency_service=currency_service,
                resolve_base_currency_rate=False,
            )
            response.items.append(fee_ledger)

        return response

    @staticmethod
    async def get_operations_by_balance_id(
        uow: IUnitOfWork, balance_id: int, limit: int = DEFAULT_API_LIMIT, offset: int = 0
    ) -> LedgerPageResponseSchema:
        operations = await uow.ledgers.find_all_by_balance_id(
            balance_id=balance_id, limit=limit + 1, offset=offset
        )
        has_more = len(operations) > limit

        return LedgerPageResponseSchema(
            items=[LedgerResponseSchema.model_validate(o) for o in operations[:limit]],
            has_more=has_more,
        )

    @staticmethod
    async def get_operation_group_by_ledger_id(
        uow: IUnitOfWork, ledger_id: int
    ) -> LedgerListResponseSchema:
        entry = await uow.ledgers.find_one_or_none(id=ledger_id)

        if entry is None:
            raise NotFoundError(Messages.LEDGER_ENTRY_NOT_FOUND)

        legs = (
            [entry]
            if entry.operation_id is None
            else await uow.ledgers.find_all(operation_id=entry.operation_id)
        )

        return LedgerListResponseSchema(
            items=[LedgerResponseSchema.model_validate(leg) for leg in legs]
        )

    @staticmethod
    async def update_ledger_by_id(
        uow: IUnitOfWork, ledger_id: int, ledger_data: LedgerUpdateSchema
    ) -> LedgerResponseSchema:
        data = ledger_data.model_dump(exclude_unset=True)
        if not data:
            raise BadRequestError(Messages.LEDGER_UPDATE_NO_FIELDS)

        updated_operation = await uow.ledgers.edit_one(id=ledger_id, data=data)

        if updated_operation is None:
            raise NotFoundError(Messages.LEDGER_ENTRY_NOT_FOUND)

        return LedgerResponseSchema.model_validate(updated_operation)

    @staticmethod
    async def delete_operation_by_id(uow: IUnitOfWork, ledger_id: int) -> None:
        entry = await uow.ledgers.find_one_or_none(id=ledger_id)

        if entry is None:
            raise NotFoundError(Messages.LEDGER_ENTRY_NOT_FOUND)

        if entry.operation_id is None:
            await uow.ledgers.delete_one(_id=entry.id)
            return

        # transfer/trade leg — delete every row sharing the operation_id together,
        # or the sibling leg(s) are left orphaned (money "arrives from nowhere" /
        # "leaves to nowhere")
        legs = await uow.ledgers.find_all(operation_id=entry.operation_id)
        for leg in legs:
            await uow.ledgers.delete_one(_id=leg.id)

    @staticmethod
    async def replace_operation(
        uow: IUnitOfWork,
        ledger_id: int,
        payload: RecordSingleLegOperationPayload | RecordTransferPayload | RecordTradePayload,
    ) -> LedgerResponseSchema | LedgerListResponseSchema:
        await LedgerService.delete_operation_by_id(uow=uow, ledger_id=ledger_id)
        return await LedgerService.record_operation(uow=uow, payload=payload)

    @staticmethod
    async def _trade(
        uow: IUnitOfWork,
        payload: RecordTradePayload,
        balance_service: BalanceService = BalanceService(),
        currency_service: CurrencyService = CurrencyService(),
    ) -> LedgerListResponseSchema:
        response = LedgerListResponseSchema(items=[])
        operation_id = uuid4()
        # resolved once so every leg of this trade shares the exact same
        # timestamp, instead of each leg independently defaulting to its own now()
        executed_at = payload.executed_at or datetime.now(timezone.utc)
        balance_name = await uow.balances.get_name_by_id(id=payload.balance_id)
        # creating the spend leg
        spend_ledger = await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=payload.operation_type,
                balance_id=payload.balance_id,
                amount=-abs(payload.spend_amount),
                currency_ticker=payload.spend_currency_ticker,
                counterparty=balance_name,
                operation_id=operation_id,
                executed_at=executed_at,
                base_currency_rate=payload.base_currency_rate,
            ),
            balance_service=balance_service,
            currency_service=currency_service,
            resolve_base_currency_rate=False,
        )
        response.items.append(spend_ledger)
        # creating the receive leg
        receive_ledger = await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=payload.operation_type,
                balance_id=payload.balance_id,
                amount=abs(payload.receive_amount),
                currency_ticker=payload.receive_currency_ticker,
                counterparty=balance_name,
                operation_id=operation_id,
                executed_at=executed_at,
                base_currency_rate=payload.base_currency_rate,
            ),
            balance_service=balance_service,
            currency_service=currency_service,
            resolve_base_currency_rate=False,
        )
        response.items.append(receive_ledger)

        if payload.fee_currency_ticker:
            # creating fee transaction
            fee_ledger = await LedgerService._record_single_leg_operation(
                uow=uow,
                payload=RecordSingleLegOperationPayload(
                    operation_type=OperationTypeEnum.FEE,
                    balance_id=payload.balance_id,
                    amount=-abs(payload.fee_amount),
                    currency_ticker=payload.fee_currency_ticker,
                    operation_id=operation_id,
                    executed_at=executed_at,
                    base_currency_rate=payload.base_currency_rate,
                ),
                balance_service=balance_service,
                currency_service=currency_service,
                resolve_base_currency_rate=False,
            )
            response.items.append(fee_ledger)

        return response

    @staticmethod
    async def get_report(
        uow: IUnitOfWork,
        group_by: LedgerReportGroupByEnum,
        metric: LedgerReportMetricEnum,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        operation_types: list[OperationTypeEnum] | None = None,
        currency_ticker: str | None = None,
        category_ids: list[int] | None = None,
        balance_ids: list[int] | None = None,
        account_id: int | None = None,
    ) -> LedgerReportResponseSchema:
        rows = await uow.ledgers.aggregate(
            group_by=group_by,
            metric=metric,
            date_start=date_start,
            date_end=date_end,
            operation_types=operation_types,
            currency_ticker=currency_ticker,
            category_ids=category_ids,
            balance_ids=balance_ids,
            account_id=account_id,
        )

        return LedgerReportResponseSchema(
            items=[
                LedgerReportItemSchema(
                    group=LedgerService._format_report_group(group_key),
                    value=Decimal(value) if value is not None else Decimal("0"),
                )
                for group_key, value in rows
            ]
        )

    @staticmethod
    def _format_report_group(group_key) -> str | None:
        if group_key is None:
            return None
        if isinstance(group_key, datetime):
            return group_key.date().isoformat()
        if hasattr(group_key, "value"):  # enum member, e.g. OperationTypeEnum
            return group_key.value
        return str(group_key)

    @staticmethod
    async def get_net_worth(
        uow: IUnitOfWork,
        currency_ticker: str,
        group_by: NetWorthBucketEnum,
        date_start: datetime | None = None,
        date_end: datetime | None = None,
        account_id: int | None = None,
        balance_ids: list[int] | None = None,
        currency_service: CurrencyService = CurrencyService(),
        exchange_rate_service: ExchangeRateService = ExchangeRateService(),
    ) -> LedgerReportResponseSchema:
        if date_end is None:
            date_end = datetime.now(timezone.utc)
        if date_start is None:
            earliest = await uow.ledgers.get_earliest_executed_at(
                account_id=account_id, balance_ids=balance_ids
            )
            if earliest is None:
                return LedgerReportResponseSchema(items=[])
            date_start = earliest

        rows = await uow.ledgers.get_rows_for_net_worth(
            date_start=date_start,
            date_end=date_end,
            account_id=account_id,
            balance_ids=balance_ids,
        )

        target_currency = await currency_service.get_currency_by_ticker(
            uow=uow, ticker=currency_ticker
        )
        currency_types: dict[str, CurrencyTypeEnum] = {}
        deltas_by_bucket: dict[date, Decimal] = {}

        for executed_at, leg_currency, amount, base_currency_rate, account_base_currency in rows:
            bucket = LedgerService._bucket_start(executed_at.date(), group_by.value)
            amount = Decimal(amount)

            if leg_currency == currency_ticker:
                contribution = amount
            elif base_currency_rate is not None and account_base_currency == currency_ticker:
                contribution = amount * Decimal(base_currency_rate)
            else:
                if leg_currency not in currency_types:
                    currency_obj = await currency_service.get_currency_by_ticker(
                        uow=uow, ticker=leg_currency
                    )
                    currency_types[leg_currency] = currency_obj.currency_type
                rate = await exchange_rate_service.get_current_rate(
                    currency_ticker=leg_currency,
                    base_currency_ticker=currency_ticker,
                    currency_type=currency_types[leg_currency],
                )
                contribution = amount * rate

            deltas_by_bucket[bucket] = deltas_by_bucket.get(bucket, Decimal("0")) + contribution

        buckets = LedgerService._generate_buckets(
            group_by.value, date_start.date(), date_end.date()
        )

        running_total = Decimal("0")
        items: list[LedgerReportItemSchema] = []
        for bucket in buckets:
            running_total += deltas_by_bucket.get(bucket, Decimal("0"))
            items.append(
                LedgerReportItemSchema(
                    group=bucket.isoformat(),
                    value=round_to_currency_precision(
                        running_total, target_currency.decimal_places
                    ),
                )
            )

        return LedgerReportResponseSchema(items=items)

    @staticmethod
    def _bucket_start(day: date, unit: str) -> date:
        if unit == "day":
            return day
        if unit == "week":
            return day - relativedelta(days=day.weekday())
        if unit == "month":
            return day.replace(day=1)
        if unit == "quarter":
            quarter_start_month = ((day.month - 1) // 3) * 3 + 1
            return day.replace(month=quarter_start_month, day=1)
        if unit == "year":
            return day.replace(month=1, day=1)
        raise ValueError(f"Unsupported bucket unit: {unit}")

    @staticmethod
    def _bucket_step(unit: str) -> relativedelta:
        return {
            "day": relativedelta(days=1),
            "week": relativedelta(weeks=1),
            "month": relativedelta(months=1),
            "quarter": relativedelta(months=3),
            "year": relativedelta(years=1),
        }[unit]

    @staticmethod
    def _generate_buckets(unit: str, start: date, end: date) -> list[date]:
        step = LedgerService._bucket_step(unit)
        current = LedgerService._bucket_start(start, unit)
        end_bucket = LedgerService._bucket_start(end, unit)
        buckets = []
        while current <= end_bucket:
            buckets.append(current)
            current = current + step
        return buckets
