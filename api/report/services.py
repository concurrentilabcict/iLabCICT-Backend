from django.db.models import Q
from api.report.models import Report
from api.repair_log.models import RepairLog
from groq import Groq
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from django.db.models.functions import TruncDate
from django.db.models import Count
from api.report.serializers import ReportSerializer
from api.user.services import UserService
class ReportService:
    
    @staticmethod
    def get_all_by_technician(technician_id=None):
        queryset = Report.objects.all()

        if technician_id:
            queryset = queryset.filter(technician=technician_id)

        return queryset
    
    @staticmethod
    def generate_report_content(request):
        #steps
        # 1 gather all the relative repair logs within the week
        # 2 summarize all repair log counts
        # 3 ai analysis 
        # if possible pwede siguro matrack kung saang repair log per room? 

        repair_logs = ReportService.get_repair_logs_by_week(request.data.get('start_time'), request.data.get('end_time'), request.data.get('assigned_id'))
        repair_log_count = ReportService.count_repair_log_per_day(repair_logs)

        compiled_logs = '\n'.join([
            f"Title: {log.title}\nNotes: {log.repair_notes}"
            for log in repair_logs
        ])

        summarized_report = ReportService.report_content_summarization(compiled_logs)

        assigned_id = request.data.get('assigned_id')
        technician_name = UserService.get_user_full_name(assigned_id)
        title = request.data.get('title')

        formatted_report = ReportService.format_report_response(repair_log_count, summarized_report, technician_name)

        report = Report.objects.create(
            technician_id = assigned_id,
            title = title,
            content = formatted_report,
            status = 'unread'
        )

        serializer = ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    #-----------------------------------------------NON-STATIC-METHODS-----------------------------------------

    def get_repair_logs_by_code(repair_log_codes: list):
        return RepairLog.objects.filter(repair_log_code__in=repair_log_codes)
    
    
    def get_repair_logs_by_week(start_week, end_week, id):
        start_date = parse_datetime(start_week)
        end_date = parse_datetime(end_week)
        return RepairLog.objects.filter(created_at__range=(start_date, end_date), technician_id=id)
    
    
    def count_repair_log_per_day(repair_logs):
        counted_logs = repair_logs.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        summary = {}

        for entry in counted_logs:
            date_str = entry['date'].strftime('%m-%d-%Y')
            summary[date_str] = entry['count']
        
        return summary

    
    def format_report_response(repair_logs_count, ai_summary, technician_name):
        formatted = {
            "technician_name": technician_name,
            "repair_log_summary": repair_logs_count,
            "ai_content_summary": ai_summary
        }
        return formatted    
    
    
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
    
    




        
        

