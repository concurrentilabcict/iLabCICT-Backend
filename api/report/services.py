from django.db.models import Q
from api.report.models import Report
from api.repair_log.models import RepairLog
from groq import Groq
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
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
    
    @staticmethod
    def report_content_summarization(content):
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": f"summarize these repair logs into a clear report in a short but concise paragraph form:\n\n{content} || if there's no content return this exact message: no repair log content"
                }
            ]
        )

        return completion.choices[0].message.content
    
    @staticmethod
    def generate_report_content(self, request):

        repair_log_codes = request.data.get('repair_log_codes')

        repair_logs = ReportService.get_repair_logs_by_code(repair_log_codes)

        compiled = '\n'.join([
            f"Title: {log.title}\nNotes: {log.repair_notes}"
            for log in repair_logs
        ])

        summarized_report = ReportService.report_content_summarization(compiled)
        report = Report.objects.create(
            technician=None,
            title=request.data.get('title'),
            content=summarized_report,
            status='unread'
        )

        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        

