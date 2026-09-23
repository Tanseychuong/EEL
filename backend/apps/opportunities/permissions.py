from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Anyone can read (subject to the visibility filter applied in the
    view's queryset); only the original poster can edit/delete — and only
    while it's still PENDING, enforced in the view/service, not here."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.posted_by_id == request.user.id


class CanVerifyOpportunity(permissions.BasePermission):
    """Gate on the can_verify_opportunity permission — true for superusers
    automatically, and for anyone in the Moderators group (or otherwise
    granted the permission directly)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_perm("opportunities.can_verify_opportunity")
        )
