from django.urls import path
from api.ticket.consumers import TicketConsumer
from api.notification.consumers import NotifcationConsumer
from api.room.consumers import RoomConsumer, RoomIDAllComputersConsumer
from api.report.consumers import ReportConsumer
from api.repair_log.consumers import RepairLogConsumer
from api.audit_logs.consumers import AuditLogsConsumer
websocket_urlpatterns = [
    path('ws/tickets/', TicketConsumer.as_asgi()),
    path('ws/notifications/user/', NotifcationConsumer.as_asgi()),
    path('ws/rooms/', RoomConsumer.as_asgi()),
    path('ws/rooms/<int:room_id>/computers/', RoomIDAllComputersConsumer.as_asgi()),
    path('ws/reports/', ReportConsumer.as_asgi()),
    path('ws/repair-logs/', RepairLogConsumer.as_asgi()),
    path('ws/audit-logs/', AuditLogsConsumer.as_asgi())
]
