from django.db.models import Q
from api.computer.models import Computer
from rest_framework.exceptions import ValidationError

class ComputerService:

    #new method
    @staticmethod
    def get_all(filters):
        queryset = Computer.objects.all()

        ComputerService.validate_filters(filters)

        queryset = ComputerService.filter_active(queryset, filters)
        queryset = ComputerService.filter_all_peripherals(queryset, filters)
        queryset = ComputerService.filter_peripheral_status(queryset, filters)
        
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
    