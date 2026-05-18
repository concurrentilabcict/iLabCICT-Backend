from django.db import models, transaction, IntegrityError
from django.conf import settings
from api.common.utils.entity_code import generate_entity_code

class Report(models.Model):

    class ReportStatus(models.TextChoices):
        READ = 'read', 'Read'
        UNREAD = 'unread', 'Unread'

    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    report_code = models.CharField(max_length=20, unique=True)

    title = models.CharField(max_length=100)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=ReportStatus)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.report_code:
            return super().save(*args, **kwargs)
        else:
            MAX_RETRIES = 5

            for _ in range(MAX_RETRIES):
                try:
                    with transaction.atomic():

                        self.report_code = generate_entity_code(
                            model=Report,
                            field_name="report_code",
                            prefix="RP",
                        )

                        return super().save(*args, **kwargs)
                except IntegrityError:
                    self.report_code = None

            raise IntegrityError("Failed to generate unique report code")