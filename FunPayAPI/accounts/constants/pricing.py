from decimal import Decimal

MONEY_QUANTUM = Decimal("0.01")
MAX_PRICE_LENGTH = 20
MAX_IDENTIFIER_LENGTH = 20
PRICE_PATTERN = r"[0-9]+(?:[.,][0-9]{1,2})?"
SBP_PREFIXES = ("сбп", "sbp")
INVALID_PRICE = "Price must be a positive amount with at most two decimal places"
INVALID_IDENTIFIER = "Invalid lot or category identifier"
RUBLE_PRICE_REQUIRED = "SBP calculation requires a ruble-denominated lot"
SBP_METHOD_REQUIRED = "Exactly one ruble-denominated SBP method is required"
PRICE_FIELD_SELECTOR = 'input[name="price"]'
CATEGORY_FIELD_SELECTOR = 'input[name="node_id"]'
PRICE_UNIT_SELECTOR = ".form-control-feedback"
