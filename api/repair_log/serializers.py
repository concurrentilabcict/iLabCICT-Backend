from rest_framework import serializers
from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory
from api.user.models import User
from api.repair_log.services import RepairLogService
from api.ticket.serializers import MinimalTicketSerializer
from api.ticket.models import Ticket

class RepairLogWriteSerializer(serializers.ModelSerializer):

    maintenance_type = serializers.ChoiceField(
        choices = MaintenanceHistory.MaintenanceTypes.choices,
        write_only = True)
    
    class Meta:
        model = RepairLog
        fields = '__all__'
        read_only_fields = ['repair_log_code','technician']

    def validate(self, attrs):

        view = self.context.get("view")

        if view and view.kwargs.get("pk"):
            raise serializers.ValidationError('Repair logs cannot be created through this endpoint')
        
        ticket = attrs.get('ticket')
        technician = attrs.get('technician_id')

        if ticket.type == Ticket.TicketType.REQUEST:
            raise serializers.ValidationError('Request Tickets are not eligible for repair logging')
        
        if ticket.status == Ticket.TicketStatus.RESOLVED:
            raise serializers.ValidationError('Ticket has been completed already')
        
        if ticket.status == Ticket.TicketStatus.OPEN:
            raise serializers.ValidationError('Ticket cannot be completed')
        
        if RepairLog.objects.filter(ticket=ticket).exists():
            raise serializers.ValidationError('Ticket already has a repair log')

        return attrs
    
    
    def create(self, validated_data):
        #need to optimize further
        maintenance_type = validated_data.pop('maintenance_type')
        ticket = validated_data['ticket']

        technician = ticket.assigned_to
        validated_data['technician'] = technician
        repair_log = RepairLog.objects.create(**validated_data)
        
        RepairLogService.record_maintenance_history(repair_log.ticket, 
                                                    repair_log.repair_notes, 
                                                    maintenance_type, 
                                                    technician,
                                                    repair_log.ticket.computer)
        
        return repair_log
    

class RepairLogReadSerializer(serializers.ModelSerializer):
    ticket = MinimalTicketSerializer(read_only=True)

    class Meta:
        model = RepairLog
        fields = '__all__'
    

