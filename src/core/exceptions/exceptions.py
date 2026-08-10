class CustomBaseException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class NotFoundError(CustomBaseException):
    pass


class AlreadyExistsError(CustomBaseException):
    pass


class ConflictError(CustomBaseException):
    pass


class BadRequestError(CustomBaseException):
    pass


class AddRecordError(CustomBaseException):
    pass


class ConnectingDbError(CustomBaseException):
    pass
