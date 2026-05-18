from django.db.models import Q
from api.report.models import Report
from api.repair_log.models import RepairLog
class ReportService:
    
    @staticmethod
    def get_all_by_technician(technician_id=None):
        queryset = Report.objects.all()

        if technician_id:
            queryset = queryset.filter(technician=technician_id)

        return queryset
    
    @staticmethod
    def get_repair_logs_by_code(repair_log_codes: list):
        return RepairLog.objects.filter(repair_log_code__in=repair_log_codes)
        

