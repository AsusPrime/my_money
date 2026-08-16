from uuid import uuid4
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import OperationTypeEnum
from src.schemas.ledger import (
    LedgerListResponseSchema,
    LedgerResponseSchema,
    RecordSingleLegOperationPayload,
    RecordTradePayload,
    RecordTransferPayload,
)
from src.services.balance_service import BalanceService
from src.services.currency_service import CurrencyService
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
    ) -> LedgerResponseSchema:
        # check if currency exist
        # if not, it will raise an error
        await currency_service.get_currency_by_ticker(uow=uow, ticker=payload.currency_ticker)
        # check if balance exist and is not archived
        # if not, it will raise an error
        await balance_service.get_active_balance_by_id(uow=uow, balance_id=payload.balance_id)

        if payload.operation_type in (OperationTypeEnum.EXPENSE, OperationTypeEnum.FEE):
            payload.amount = -abs(payload.amount)
        elif payload.operation_type == OperationTypeEnum.INCOME:
            payload.amount = abs(payload.amount)

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
            ),
            balance_service=balance_service,
            currency_service=currency_service
        )
        response.items.append(from_ledger)
        # creating the inflow leg — money arriving at to_balance_id
        from_balance_name = await uow.balances.get_name_by_id(id=payload.from_balance_id)
        to_ledger = await LedgerService._record_single_leg_operation(
            uow=uow,
            payload=RecordSingleLegOperationPayload(
                operation_type=payload.operation_type,
                balance_id=payload.to_balance_id,
                amount=abs(payload.received_amount),
                currency_ticker=payload.currency_ticker,
                counterparty=from_balance_name,
                operation_id=operation_id,
            ),
            balance_service=balance_service,
            currency_service=currency_service
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
                ),
                balance_service=balance_service,
                currency_service=currency_service
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
    async def _trade(
        uow: IUnitOfWork,
        payload: RecordTradePayload,
        balance_service: BalanceService = BalanceService(),
        currency_service: CurrencyService = CurrencyService(),
    ) -> LedgerListResponseSchema:
        response = LedgerListResponseSchema(items=[])
        operation_id = uuid4()
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
            ),
            balance_service=balance_service,
            currency_service=currency_service
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
            ),
            balance_service=balance_service,
            currency_service=currency_service
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
                ),
                balance_service=balance_service,
                currency_service=currency_service
            )
            response.items.append(fee_ledger)

        return response
