from api.user.models import User
from rest_framework.exceptions import ValidationError
from api.user.models import User
class UserService:

    @staticmethod
    def get_user_full_name(user_id):
        user = User.objects.filter(id=user_id).values('first_name','last_name').first()
        
        return f"{user['first_name']} {user['last_name']}"
    
    @staticmethod
    def get_all(is_active=None,
                role=None):
        
        UserService.validate_filter(is_active=is_active,
                                    role=role)
        
        queryset = User.objects.all()

        if is_active is not None:
        
            if is_active == 'true':
                is_active = True
            elif is_active == 'false':
                is_active = False

            queryset = queryset.filter(is_active=is_active)

        if role is not None:
            queryset = queryset.filter(role=role)

        return queryset
    
    @staticmethod
    def validate_filter(is_active,role):
        allowed_roles = User.UserRole.values

        if role and role not in allowed_roles:
            raise ValidationError({
                'message': f'Invalid user role'
            })
        
        if is_active not in ('true', 'false', None):
            raise ValidationError({
                'message': f'is-active must only be True or False'
            })
        

