from datetime import datetime, timedelta
from django.utils import timezone
from api.task_scheduler.models import TaskScheduler
from api.report.services import ReportService
class TaskSchedulerService:

    @staticmethod
    def execute_task():
        now = timezone.localtime()

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

    @staticmethod
    def calculate_next_exec(schedule):
        now = timezone.localtime()

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

            return next_execution

        elif schedule.frequency == TaskScheduler.FrequencyValues.WEEKLY:

            days_until = (schedule.weekday - now.weekday()) % 7

            next_execution = now + timedelta(days=days_until)

            next_execution = next_execution.replace(
                hour=execution_time.hour,
                minute=execution_time.minute,
                second=0,
                microsecond=0
            )

            if next_execution <= now:
                next_execution += timedelta(days=7)

            return next_execution

        raise ValueError("Unsupported frequency")

    @staticmethod
    def create_schedule(serializer):
        schedule = serializer.save()

        schedule.next_execution = (
            TaskSchedulerService.calculate_next_exec(schedule=schedule)
        )

        schedule.save(update_fields=["next_execution"])

        return schedule