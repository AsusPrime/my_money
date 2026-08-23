from enum import Enum


class CurrencyTypeEnum(str, Enum):
    FIAT = "fiat"
    BOND = "bond"
    STOCK = "stock"
    CRYPTO = "crypto"
    OTHER = "other"


class OperationTypeEnum(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    TRADE = "trade"
    FEE = "fee"


class RangeEnum(str, Enum):
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class AnalyticTypeEnum(str, Enum):
    BY_BALANCE = "by_balance"
    GENERAL = "general"


class AmountModeEnum(str, Enum):
    FIXED = "fixed"
    PERCENT_OF_BALANCE = "percent_of_balance"


class RecurrenceIntervalEnum(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
