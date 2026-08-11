from rest_framework.pagination import PageNumberPagination

class AuditLogPagination(PageNumberPagination):
    page_size = 50

class RequestHistoryPagination(PageNumberPagination):
    page_size = 20

class MaintenanceHistoryPagination(PageNumberPagination):
    page_size = 20