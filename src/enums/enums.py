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


class LedgerReportGroupByEnum(str, Enum):
    CATEGORY = "category"
    COUNTERPARTY = "counterparty"
    OPERATION_TYPE = "operation_type"
    CURRENCY_TICKER = "currency_ticker"
    BALANCE = "balance"
    ACCOUNT = "account"
    # time buckets — values match Postgres date_trunc() units exactly
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class LedgerReportMetricEnum(str, Enum):
    SUM = "sum"
    COUNT = "count"
    NET_OF_FEES = "net_of_fees"


class AnalyticsWidgetMetricEnum(str, Enum):
    SUM = "sum"
    COUNT = "count"
    NET_OF_FEES = "net_of_fees"
    NET_WORTH = "net_worth"


class ChartTypeEnum(str, Enum):
    BAR = "bar"
    PIE = "pie"
    LINE = "line"
    CALENDAR = "calendar"


class DateRangePresetEnum(str, Enum):
    ALL = "all"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    THIS_YEAR = "this_year"
    CUSTOM = "custom"


class NetWorthBucketEnum(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
