from django.db.models import Q
from api.computer.models import Computer
from rest_framework.exceptions import ValidationError
from api.audit_logs.services import AuditLogsService
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync 
 
class ComputerService:

    @staticmethod
    def get_computer_with_mainentance_history(include=None, computer_code=None):
        queryset = Computer.objects.select_related('room').filter(computer_code=computer_code)

        if "maintenance-history" in include.split(","):
            queryset = queryset.prefetch_related('maintenance_history', 
                                                 'maintenance_history__repair_log',
                                                 'maintenance_history__repair_log__ticket',
                                                 'maintenance_history__technician')

        return queryset

    #new method
    @staticmethod
    def get_all(filters):
        queryset = Computer.objects.select_related('room')

        ComputerService.validate_filters(filters)

        queryset = ComputerService.filter_per_computer_code(queryset, filters)
        queryset = ComputerService.filter_active(queryset, filters)
        queryset = ComputerService.filter_all_peripherals(queryset, filters)
        queryset = ComputerService.filter_peripheral_status(queryset, filters)

        include = filters.include or ""

        if "maintenance-history" in include.split(","):
            queryset = queryset.prefetch_related("maintenance_history")


        return queryset
    
    def filter_per_computer_code(queryset, filters):
        computer_code = filters.get('computer-code')
        if filters.get('computer-code') is not None:
            queryset = queryset.filter(computer_code=computer_code)

        return queryset
    
    @staticmethod
    def filter_active(queryset, filters):
        if filters.get('active') == 'true':
            queryset = queryset.filter(computer_status=Computer.ComputerStatus.ACTIVE)
        
        return queryset
    
    @staticmethod
    def filter_all_peripherals(queryset, filters):
        all_peripheral_status = filters.get('peripherals')
        
        if all_peripheral_status == 'none':
            queryset = queryset.filter(
                mouse_status=Computer.PeripheralStatus.NONE,
                keyboard_status=Computer.PeripheralStatus.NONE,
                monitor_status=Computer.PeripheralStatus.NONE,
                ups_status=Computer.PeripheralStatus.NONE
            )

        elif all_peripheral_status == 'all':
            queryset = queryset.filter(
                mouse_status=Computer.PeripheralStatus.ACTIVE,
                keyboard_status=Computer.PeripheralStatus.ACTIVE,
                monitor_status=Computer.PeripheralStatus.ACTIVE,
                ups_status=Computer.PeripheralStatus.ACTIVE
            )

        return queryset
    
    @staticmethod
    def filter_peripheral_status(queryset, filters):
        peripheral = filters.get('peripheral-type')
        status = filters.get('status')

        if peripheral and status:
            queryset = queryset.filter(
                **{f"{peripheral}_status": status}
            )

        return queryset


    @staticmethod
    def validate_filters(filters):
        allowed_peripheral_types=[
            'keyboard',
            'ups',
            'monitor',
            'mouse'
        ]

        allowed_statuses = Computer.ComputerStatus.values

        peripheral = filters.get('peripheral-type')
        status = filters.get('status')

        if peripheral and peripheral not in allowed_peripheral_types:
            raise ValidationError('Invalid peripheral type')
        
        if status and status not in allowed_statuses:
            raise ValidationError('Invalid peripheral status')


    @staticmethod
    def create_computers(serializer, request):
        computers = serializer.save()

        ComputerService.broadcast_computer_created(
            computers=computers,
            event_type='computer_created'
        )

        AuditLogsService.log(
            request=request,
            performed_by=request.user,
            action_title='Computers created',
            action_summary=f"{request.user.get_full_name()} created {len(computers)} computer(s).",
            metadata={
                "computer_ids": [computer.id for computer in computers],
                "quantity": len(computers),
            }
        )

        return computers

    @staticmethod
    def update_computer(serializer, request):
        from api.computer.serializers import ComputerDefaultSerializer
        computer = serializer.instance

        old_values = {}

        for field, new_value in serializer.validated_data.items():
            old_value = getattr(computer, field)

            if old_value != new_value:
                old_values[field] = old_value

        computer = serializer.save()

        changes = {}

        for field in old_values:
            changes[field] = {
                'old': old_values[field],
                'new': getattr(computer, field)
            }

        ComputerService.broadcast_computer_updated(
            computer=computer,
            event_type='computer_updated'
        )

        AuditLogsService.log(
            request=request,
            performed_by=request.user,
            action_title='Computer updated',
            action_summary=f"{request.user.get_full_name()} updated computer '{computer.computer_code}.'",
            metadata={
                'computer_id': computer.id,
                'changes': changes
            }
        )

        return computer

    @staticmethod
    def broadcast_computer_created(computers, event_type):
        from api.computer.serializers import ComputerDefaultSerializer

        channel_layer = get_channel_layer()

        room_id = computers[0].room_id

        serialized_computers = ComputerDefaultSerializer(
            computers,
            many=True
        ).data

        async_to_sync(channel_layer.group_send)(
            f'room_{room_id}',
            {
                'type': event_type,
                'computer': serialized_computers
            }
        )

    @staticmethod
    def broadcast_computer_updated(computer, event_type):
        from api.computer.serializers import ComputerDefaultSerializer
        channel_layer = get_channel_layer()

        room_id = computer.room_id

        serialized_computer = ComputerDefaultSerializer(computer).data

        async_to_sync(channel_layer.group_send)(
            f'room_{room_id}',
            {
                'type': event_type,
                'computer': serialized_computer
            }
        )

#---------------------------------------------old method-----------------------------------------------------------
    @staticmethod
    def get_all_active():
        return Computer.objects.filter(computer_status=Computer.ComputerStatus.ACTIVE)
    
    @staticmethod
    def get_all_with_active_peripherals():
        return Computer.objects.filter(
            computer_status=Computer.ComputerStatus.ACTIVE,
            mouse_status=Computer.PeripheralStatus.ACTIVE,
            monitor_status=Computer.PeripheralStatus.ACTIVE,
            keyboard_status=Computer.PeripheralStatus.ACTIVE,
            ups_status=Computer.PeripheralStatus.ACTIVE
            )
    
    @staticmethod
    def get_all_active_with_peripheral(filters):
        queryset = Computer.objects.filter(
            Q(computer_status=Computer.ComputerStatus.ACTIVE) &
            (
                ~Q(mouse_status=Computer.PeripheralStatus.NONE) &
                ~Q(keyboard_status=Computer.PeripheralStatus.NONE) &
                ~Q(monitor_status=Computer.PeripheralStatus.NONE) &
                ~Q(ups_status=Computer.PeripheralStatus.NONE)
            )
            )

        peripheral_type = filters.get("type")
        status = filters.get("status")

        if peripheral_type:
            queryset = queryset.filter(**{
                f"{peripheral_type}_status": f"{status}"
                })
        
        return queryset
    
    @staticmethod
    def get_all_active_no_peripherals():
        return Computer.objects.filter(
            Q(mouse_status=Computer.PeripheralStatus.NONE) &
            Q(keyboard_status=Computer.PeripheralStatus.NONE) &
            Q(monitor_status=Computer.PeripheralStatus.NONE) &
            Q(ups_status=Computer.PeripheralStatus.NONE)
        )   
    