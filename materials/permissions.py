from rest_framework import permissions
from django.contrib.auth.models import Group

class IsModerator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="moderators").exists()

class IsOwnerOrModerator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.groups.filter(name='moderators').exists():
            # Модераторы могут читать и обновлять, но не удалять
            return view.action in ['retrieve', 'update', 'partial_update']
        return obj.owner == request.user

class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsCourseOwnerOrModerator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.groups.filter(name='moderators').exists():
            return view.action in ['retrieve', 'update', 'partial_update']
        return obj.owner == request.user

class IsLessonOwnerOrModerator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.groups.filter(name='moderators').exists():
            return view.action in ['retrieve', 'update', 'partial_update']
        return obj.owner == request.user