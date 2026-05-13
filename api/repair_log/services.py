from api.repair_log.models import RepairLog

class RepairLogService:

    @staticmethod
    def get_all_by_technician(technician_id=None):
        queryset = RepairLog.objects.all()

        if technician_id:
            queryset = queryset.filter(technician=technician_id)

        return queryset
