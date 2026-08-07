from datetime import datetime, timedelta
from django.utils import timezone
from api.task_scheduler.models import TaskScheduler
from api.report.services import ReportService
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone
from api.audit_logs.services import AuditLogsService
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
    def create_schedule(serializer, request):
        schedule = serializer.save()

        schedule.next_execution = (
            TaskSchedulerService.calculate_next_exec(schedule=schedule)
        )

        schedule.save(update_fields=["next_execution"])

        AuditLogsService.log(
            request=request,
            performed_by=request.user,
            action_title='New task schedule created',
            action_summary=f'{request.user.get_full_name()} created a task scheduler.',
            metadata={
                'task_scheduler_id': schedule.id,
                'schedule': schedule.schedule,
                'next_execution': schedule.next_execution,
            }
        )

        return schedule

    @staticmethod
    def update_schedule(serializer, request):
        schedule = serializer.instance

        old_schedule = schedule.schedule
        old_next_execution = schedule.next_execution
        old_enabled = schedule.enabled

        schedule = serializer.save()

        updated_fields = serializer.validated_data.keys()

        if any(field in updated_fields for field in (
            "execution_time",
            "weekday",
            "frequency",
            "enabled",
        )):
            schedule.next_execution = (
                TaskSchedulerService.calculate_next_exec(schedule)
            )
            schedule.save(update_fields=["next_execution"])

        if updated_fields:
            AuditLogsService.log(
                request=request,
                performed_by=request.user,
                action_title="Task scheduler updated",
                action_summary=(
                    f"{request.user.get_full_name()} updated a task scheduler."
                ),
                metadata={
                    "task_scheduler_id": schedule.id,
                    "updated_fields": list(updated_fields),
                    "old_schedule": old_schedule,
                    "new_schedule": schedule.schedule,
                    "old_enabled": old_enabled,
                    "new_enabled": schedule.enabled,
                    "old_next_execution": old_next_execution,
                    "new_next_execution": schedule.next_execution,
                },
            )

        return schedule