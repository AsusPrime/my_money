from src.enums.enums import OperationTypeEnum

DEFAULT_API_LIMIT = 250  # TODO: make limit smarter and start to use it

RATE_CLIENT_HTTP_TIMEOUT_SECONDS = 10.0

RECURRING_OPERATION_SUPPORTED_TYPES = {
    OperationTypeEnum.INCOME,
    OperationTypeEnum.EXPENSE,
    OperationTypeEnum.FEE,
}

RECURRING_OPERATION_POLL_INTERVAL_MINUTES = 5
