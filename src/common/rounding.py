from decimal import ROUND_HALF_UP
from decimal import Decimal


def round_to_currency_precision(amount: Decimal, decimal_places: int) -> Decimal:
    quantum = Decimal(1).scaleb(-decimal_places)
    return amount.quantize(quantum, rounding=ROUND_HALF_UP)
