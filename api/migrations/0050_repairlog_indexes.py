# Generated for repair-log list speedup (no serializer change)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0049_alter_computer_computer_status_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='repairlog',
            index=models.Index(fields=['-created_at', '-id'], name='api_repairlo_created_2b0f9c_idx'),
        ),
        migrations.AddIndex(
            model_name='repairlog',
            index=models.Index(fields=['technician', '-created_at'], name='api_repairlo_technici_c8f1c8_idx'),
        ),
        migrations.AddIndex(
            model_name='repairlog',
            index=models.Index(fields=['ticket', '-created_at'], name='api_repairlo_ticket__9e5a4c_idx'),
        ),
    ]
