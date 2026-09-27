from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Default pagination for list endpoints.

    Page-based, with a client-adjustable page size capped at 100. Viewsets whose
    ``list`` output is a computed statement or a bounded hierarchy opt out by
    setting ``pagination_class = None`` (ledger, reports, accounts).
    """

    page_size_query_param = "page_size"
    max_page_size = 100