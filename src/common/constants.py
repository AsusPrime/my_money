from src.enums.enums import OperationTypeEnum

DEFAULT_API_LIMIT = 250  # TODO: make limit smarter and start to use it

RATE_CLIENT_HTTP_TIMEOUT_SECONDS = 10.0

RECURRING_OPERATION_SUPPORTED_TYPES = {
    OperationTypeEnum.INCOME,
    OperationTypeEnum.EXPENSE,
    OperationTypeEnum.FEE,
}

RECURRING_OPERATION_POLL_INTERVAL_MINUTES = 5

MAX_DAYS_IN_MONTH = {
    1: 31,
    2: 29,
    3: 31,
    4: 30,
    5: 31,
    6: 30,
    7: 31,
    8: 31,
    9: 30,
    10: 31,
    11: 30,
    12: 31,
}

MONTH_END_OFFSET_TRIGGER_LOOKAHEAD_MONTHS = 96
