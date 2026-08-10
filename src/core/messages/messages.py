from enum import Enum


class Messages(str, Enum):
    ERROR_CONNECTING_DATABASE = "Error connecting to the database"

    ACCOUNT_NOT_FOUND = "Account not found"
    ACCOUNT_ALREADY_EXISTS = "Account already exists"
    ERROR_FILLED_TO_ADD_NEW_ACCOUNT = "Error filled to add new account"

    def __str__(self):
        return self.value
