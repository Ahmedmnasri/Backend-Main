from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permission to only allow admin users access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'Admin'


class IsSupervisor(permissions.BasePermission):
    """
    Permission to only allow supervisor users access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'Supervisor'


class IsTechnician(permissions.BasePermission):
    """
    Permission to only allow technician users access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'Technician'


class IsAdminOrSupervisor(permissions.BasePermission):
    """
    Permission to allow either admin or supervisor users access.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['Admin', 'Supervisor']


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can do anything
        if request.user.role == 'Admin':
            return True
            
        # Owner can edit their own object
        return obj.user == request.user


class IsSupervisorInSameSector(permissions.BasePermission):
    """
    Object-level permission for supervisors to manage objects within their sector.
    """
    def has_object_permission(self, request, view, obj):
        # Only allow if user is supervisor and obj is in their sector
        if hasattr(obj, 'sector') and request.user.role == 'Supervisor':
            return obj.sector == request.user.sector
            
        # For user objects specifically
        if hasattr(obj, 'role') and request.user.role == 'Supervisor':
            return obj.sector == request.user.sector
            
        return False 