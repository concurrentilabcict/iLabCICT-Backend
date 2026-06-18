from rest_framework import serializers
from api.repair_log.models import RepairLog
from api.maintenance_history.models import MaintenanceHistory
from api.user.models import User
from api.repair_log.services import RepairLogService
class RepairLogSerializer(serializers.ModelSerializer):

    maintenance_type = serializers.ChoiceField(
        choices = MaintenanceHistory.MaintenanceTypes.choices,
        write_only = True)
    
    class Meta:
        model = RepairLog
        fields = '__all__'
        read_only_fields = ['repair_log_code','technician']

    def create(self, validated_data):
        #need to optimize further
        maintenance_type = validated_data.pop('maintenance_type')
        ticket = validated_data['ticket']

        if ticket.status == 'resolved':
            raise serializers.ValidationError({
                'message': f"Ticket has been completed already" 
            })
        elif ticket.status == 'open':
            raise serializers.ValidationError({
                'message': f"Ticket cannot be completed"
            })

        technician_id = ticket.assigned_to_id
        technician = User.objects.get(id=technician_id)
        validated_data['technician'] = technician
        repair_log = RepairLog.objects.create(**validated_data)
        
        RepairLogService.record_maintenance_history(repair_log.ticket, 
                                                    repair_log.repair_notes, 
                                                    maintenance_type, 
                                                    technician,
                                                    repair_log.ticket.computer)
        
        return repair_log
    

