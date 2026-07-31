import random
from .products import PRODUCTS


def pick_random_product(exclude_names: set[str] | None = None) -> dict:
    """Выбирает случайный товар из встроенного прайса, по возможности не повторяя недавние."""
    exclude_names = exclude_names or set()
    pool = [p for p in PRODUCTS if p["name"] not in exclude_names] or PRODUCTS
    return random.choice(pool)
