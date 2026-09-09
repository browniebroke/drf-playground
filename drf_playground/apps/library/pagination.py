from rest_framework.pagination import CursorPagination


class LoanCursorPagination(CursorPagination):
    """Cursor pagination: opaque ``?cursor=`` tokens, stable under inserts, no total ``count``.

    Requires a consistent ordering; when ``OrderingFilter`` is present on the view, its ordering is used.
    """

    page_size = 10
    ordering = "-loaned_at"
