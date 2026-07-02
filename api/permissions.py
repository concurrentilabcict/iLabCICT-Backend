from rest_framework.permissions import BasePermission
from api.user.models import User

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'admin'
    
class IsProfileOwner(BasePermission):

    def has_object_permission(self, request, view, obj):

        if obj.id is not None:
            return obj.id == request.user.id
        
class IsNotificationOwner(BasePermission):
    def has_object_permission(self, request, view, obj):

        if obj.receiver_id is not None:
            return obj.receiver_id == request.user.id
    

class IsStaff(BasePermission):

    def has_permission(self, request, view):
        return request.user.role in User.UserRole.values
    
class HasTicketPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user.role in User.UserRole.values

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.UserRole.ADMIN:
            return True
        
        if request.user.role == User.UserRole.TECHNICIAN and obj.assigned_to_id is not None:
            return obj.assigned_to_id == request.user.id

        if request.user.role == User.UserRole.FACULTY and obj.reported_by_id is not None:
            return obj.reported_by_id == request.user.id

        return False


class IsTechnicianAssignedTicket(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRole.TECHNICIAN
    
    def has_object_permission(self, request, view, obj):
        if obj.assigned_to_id is not None:
            return obj.assigned_to_id == request.user.id
    
class IsFacultyReportedTicket(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'faculty'
    
    def has_object_permission(self, request, view, obj):
        if obj.reported_by_id is not None:
            return obj.reported_by_id == request.user.id
        
class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRole.FACULTY
    
class IsTechnician(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == User.UserRole.TECHNICIAN