from api.report.models import Report
from api.repair_log.models import RepairLog
import groq
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from django.db.models.functions import TruncDate
from django.db.models import Count
from api.report.serializers import ReportSerializer
from api.user.services import UserService
from api.common.utils.prompts import load_prompt
from api.notification.services import NotificationService
from rest_framework.exceptions import ValidationError
from api.common.utils.date_checker import is_invalid_date_format

class ReportService:
    
    @staticmethod
    def get_all(
        technician_id=None,
        date=None,
        status=None):

        ReportService.validate_filters(
            technician_id=technician_id,
            date=date,
            status=status
        )
        
        queryset = Report.objects.all()

        if technician_id is not None:
            queryset = queryset.filter(technician_id=technician_id)

        if date is not None:
            queryset = queryset.filter(created_at__date=date)
        
        if status is not None:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    @staticmethod
    def validate_filters(technician_id,date,status):
        allowed_report_statuses = Report.ReportStatus.values

        if status and status not in allowed_report_statuses:
            raise ValidationError({
                'message': f'Invalid report status'
            })
        
        if not isinstance(technician_id, int):
            raise ValidationError({
                'message': f'Invalid technician-id'
            })
        
        if is_invalid_date_format(date):
            raise ValidationError({
                'message': f'Date format must be in YYYY-MM-DD'
            })
    
    @staticmethod
    def generate_report_content(request):

        repair_logs = ReportService.get_repair_logs_by_week(request.data.get('start_time'), request.data.get('end_time'), request.data.get('assigned_id'))
        
        if not repair_logs.exists():
            return Response({'error': 'No repair logs found'}, status=status.HTTP_404_NOT_FOUND)
        
        repair_log_count = ReportService.count_repair_log_per_day(repair_logs)

        compiled_logs = '\n'.join([
            f"Title: {log.title}\nNotes: {log.repair_notes}"
            for log in repair_logs
        ])

        summarized_report = ReportService.report_content_summarization(compiled_logs)

        if summarized_report['status'] == 'unsuccessful':
            return Response({'error': summarized_report['value']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        assigned_id = request.data.get('assigned_id')
        technician_name = UserService.get_user_full_name(assigned_id)
        title = request.data.get('title')

        formatted_report = ReportService.format_report_response(repair_log_count, summarized_report['value'], technician_name)

        report = Report.objects.create(
            technician_id = assigned_id,
            title = title,
            content = formatted_report,
            status = 'unread'
        )

        NotificationService.create_new_report_notification(
            None,
            'New Report Created!',
            report.id
        )#should be admin but for now null

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
    

    def report_content_summarization(content: str):

        if not content or not content.strip():
            return {
                "value": "No content",
                "status": "unsuccessful"
            }
        
        groq_models = [
            "llama-3.3-70b-versatile",       
            "openai/gpt-oss-120b",           
            "qwen/qwen3-32b",                
            "meta-llama/llama-4-scout-17b-16e-instruct",  
            "llama-3.1-8b-instant",         
        ]

        summary_prompt = load_prompt('summary-report.md')

        client = groq.Groq(api_key=settings.GROQ_API_KEY)

        for model in groq_models:
            try:
                completion = client.chat.completions.create(
                model=model,
                messages=[
                        {
                            "role": "system",
                            "content": summary_prompt
                        },
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    temperature = 0.3,
                    max_completion_tokens=512 
                )

                return {
                    "value": completion.choices[0].message.content.strip(),
                    "status": "successful"
                    }
            
            except groq.RateLimitError:
                print(f"Rate Limit Exceeded on model: {model}")
                continue
            except groq.BadRequestError as e:
                return {
                "value": f"Bad Request: {str(e)}",
                "status": "unsuccessful"
                }

        return {
                "value": f"Summary generation failed: Models Exhausted",
                "status": "unsuccessful"
                }

       
        

        
    
    




        
        

