from enum import Enum


class Messages(str, Enum):
    ERROR_CONNECTING_DATABASE = "Error connecting to the database"

    ACCOUNT_NOT_FOUND = "Account not found"
    ACCOUNT_ALREADY_EXISTS = "Account already exists"
    ERROR_FILLED_TO_ADD_NEW_ACCOUNT = "Error filled to add new account"
    ACCOUNT_HAS_ACTIVE_BALANCES = (
        "Account still has non-archived balances — archive them before archiving the account"
    )
    CURRENCY_NOT_FOUND = "Currency not found"
    CURRENCY_ALREADY_EXISTS = "Currency already exists"
    CURRENCY_IN_USE = "Currency is still in use and cannot be deleted"
    ERROR_FILLED_TO_ADD_NEW_CURRENCY = "Error filled to add new currency"
    BALANCE_NOT_FOUND = "Balance not found"
    ERROR_FILLED_TO_ADD_NEW_BALANCE = "Error filled to add new balance"
    BALANCE_IS_ARCHIVED = "Balance is archived and cannot be used for new operations"
    BALANCE_INSUFFICIENT_FUNDS = "Balance does not have enough funds in this currency for this operation"
    OPERATION_TYPE_NOT_FOUND = "Operation type not found"

    def __str__(self):
        return self.value
