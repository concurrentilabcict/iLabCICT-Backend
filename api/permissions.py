from rest_framework.permissions import BasePermission
from api.user.models import User

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'
    
class IsOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.id == request.user.id
    
class IsTicketAccess(BasePermission):

    def has_permission(self, request, view):
        return request.user.role in User.UserRole.values

    def has_object_permission(self, request, view, obj):
        if request.user.role == "admin":
            return True

        if request.user.role == "technician":
            return obj.assigned_to_id == request.user.id

        if request.user.role == "faculty":
            return obj.reported_by_id == request.user.id

        return False
    
class IsTechnician(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'technician'
    
    def has_object_permission(self, request, view, obj):
        if obj.assigned_to_id is not None:
            return obj.assigned_to_id == request.user.id
    
class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'faculty'
    
    def has_object_permission(self, request, view, obj):
        if obj.reported_by_id is not None:
            return obj.reported_by_id == request.user.id