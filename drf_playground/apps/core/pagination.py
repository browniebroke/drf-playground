from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Project default: ``?page=2&page_size=50``, capped at 100 items per page."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
