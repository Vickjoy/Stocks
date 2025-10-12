from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Only allow admin users"""
    message = 'You do not have permission to perform this action. Admin access required.'
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin full access, others read-only"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff


class IsStaffOrAdmin(permissions.BasePermission):
    """Only staff or admin users"""
    message = 'You do not have permission to perform this action. Staff access required.'
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)