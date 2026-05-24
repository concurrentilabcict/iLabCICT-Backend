from api.user.models import User

class UserService:

    @staticmethod
    def get_all_by_role(role=None):
        queryset = User.objects.all()

        if role:
            queryset = queryset.filter(role=role)

        return queryset
    
    @staticmethod
    def get_user_full_name(user_id):
        user = User.objects.filter(id=user_id).values('first_name','last_name').first()
        
        return f"{user['first_name']} {user['last_name']}"