from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'
    
    
class IsOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.id == request.user.id
    
class IsTechnician(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'technician'
    
    def has_object_permission(self, request, view, obj):
        return obj.id == request.user.id
    
class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'faculty'
    
    def has_object_permission(self, request, view, obj):
        return obj.id == request.user.id