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
        queryset = Computer.objects.filter(computer_status=Computer.ComputerStatus.ACTIVE)

        peripheral_type = filters.get("type")

        if peripheral_type:
            queryset = queryset.filter(**{
                f"{peripheral_type}_status": f"{Computer.PeripheralStatus.ACTIVE}"
                })
        
        return queryset
