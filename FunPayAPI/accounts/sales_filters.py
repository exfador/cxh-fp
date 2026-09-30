from FunPayAPI.security.constants import SALES_PAGE_TITLES


def is_sales_heading(header) -> bool:
    if header is None:
        return False
    title = header.get_text(" ", strip=True).casefold()
    return any(
        title == allowed or title.startswith(f"{allowed} ")
        for allowed in SALES_PAGE_TITLES
    )
