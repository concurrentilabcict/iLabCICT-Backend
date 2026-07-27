from datetime import datetime, timedelta
from django.utils import timezone
from api.task_scheduler.models import TaskScheduler
from api.report.services import ReportService
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone
class TaskSchedulerService:

    MANILA_TZ = ZoneInfo("Asia/Manila")

    @staticmethod
    def execute_task():
        now = timezone.now()

        schedules = TaskScheduler.objects.filter(
            enabled=True,
            next_execution__lte=now
        )

        for schedule in schedules:

            if schedule.type == "report":
                ReportService.generate()

            schedule.last_execution = now
            schedule.next_execution = TaskSchedulerService.calculate_next_exec(schedule=schedule)
        
            schedule.save(update_fields=[
                "last_execution",
                "next_execution"
                ])

            return "Report Created Successfully!"
        return "No Scheduled Task"
            

    @staticmethod
    def calculate_next_exec(schedule):
        now_utc = timezone.now()

        now = now_utc.astimezone(TaskSchedulerService.MANILA_TZ)

        execution_time = schedule.execution_time

        if schedule.frequency == TaskScheduler.FrequencyValues.DAILY:

            next_execution = now.replace(
                hour=execution_time.hour,
                minute=execution_time.minute,
                second=0,
                microsecond=0
            )

            if next_execution <= now:
                next_execution += timedelta(days=1)

        elif schedule.frequency == TaskScheduler.FrequencyValues.WEEKLY:

            days_until = (schedule.weekday - now.weekday()) % 7

            next_execution = (
                now + timedelta(days=days_until)
            ).replace(
                hour=execution_time.hour,
                minute=execution_time.minute,
                second=0,
                microsecond=0
            )

            if next_execution <= now:
                next_execution += timedelta(days=7)

        else:
            raise ValueError("Unsupported frequency")

        return next_execution.astimezone(dt_timezone.utc)

    @staticmethod
    def create_schedule(serializer):
        schedule = serializer.save()

        schedule.next_execution = (
            TaskSchedulerService.calculate_next_exec(schedule=schedule)
        )

        schedule.save(update_fields=["next_execution"])

        return schedule