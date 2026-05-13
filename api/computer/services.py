from django.db.models import Q
from api.computer.models import Computer

class ComputerService:

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
    
    def get_all_active_no_peripherals():
        return Computer.objects.filter(
            Q(mouse_status=Computer.PeripheralStatus.NONE) &
            Q(keyboard_status=Computer.PeripheralStatus.NONE) &
            Q(monitor_status=Computer.PeripheralStatus.NONE) &
            Q(ups_status=Computer.PeripheralStatus.NONE)
        )
