from datetime import datetime
from datetime import timezone
from uuid import uuid4
from src.core.exceptions.exceptions import BadRequestError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.entities.balance import BalanceEntity
from src.enums.enums import OperationTypeEnum
from src.schemas.ledger import (
    LedgerListResponseSchema,
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
        uow: IUnitOfWork, balance_id: int
    ) -> LedgerListResponseSchema:
        operations = await uow.ledgers.find_all_by_balance_id(balance_id=balance_id)

        return LedgerListResponseSchema(
            items=[LedgerResponseSchema.model_validate(o) for o in operations]
        )

    @staticmethod
    async def update_ledger_by_id(
        uow: IUnitOfWork, ledger_id: int, ledger_data: LedgerUpdateSchema
    ) -> LedgerResponseSchema:
        updated_operation = await uow.ledgers.edit_one(
            id=ledger_id, data=ledger_data.model_dump(exclude_unset=True)
        )

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
