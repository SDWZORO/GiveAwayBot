"""
Pagination utility for participant lists.
"""

import math
from typing import List, Any


def paginate(items: List[Any], page: int, per_page: int = 10):
    """
    Returns (page_items, total_pages, current_page).
    """
    total = len(items)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total_pages, page
