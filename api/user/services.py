from api.user.models import User

class UserService:

    @staticmethod
    def get_all_by_role(role=None):
        queryset = User.objects.all()

        if role:
            queryset = queryset.filter(role=role)

        return queryset