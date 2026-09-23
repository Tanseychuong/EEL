from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Opportunity, OpportunityCategory, SavedOpportunity
from .permissions import IsOwnerOrReadOnly, CanVerifyOpportunity
from .serializers import (
    OpportunitySerializer, OpportunityCreateSerializer, OpportunityRejectSerializer,
    OpportunityCategorySerializer, SavedOpportunitySerializer,
)
from .services import (
    submit_opportunity, approve_opportunity, reject_opportunity,
    list_visible_opportunities,
)


class OpportunityCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Public, read-only — categories are admin-managed via /admin/."""

    queryset = OpportunityCategory.objects.filter(is_active=True)
    serializer_class = OpportunityCategorySerializer
    permission_classes = [permissions.AllowAny]


class OpportunityViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return OpportunityCreateSerializer
        return OpportunitySerializer

    def get_queryset(self):
        user = self.request.user if self.request.user.is_authenticated else None

        if self.action in ("update", "partial_update", "destroy"):
            # Editing only ever allowed on your own still-pending submissions.
            return Opportunity.objects.filter(posted_by=user, status=Opportunity.Status.PENDING)

        if self.action == "retrieve":
            # Visible under the normal rule, OR it's your own submission
            # regardless of moderation status (so you can check on it).
            visible_ids = list_visible_opportunities(user).values("pk")
            qs = Opportunity.objects.filter(Q(pk__in=visible_ids) | Q(posted_by=user))
            return qs if user else Opportunity.objects.filter(pk__in=visible_ids)

        # list, and the default for any other action
        category_slug = self.request.query_params.get("category")
        return list_visible_opportunities(user, category_slug=category_slug)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        opportunity = submit_opportunity(self.request.user, serializer.validated_data)
        serializer.instance = opportunity

    # --- Moderation actions -------------------------------------------------

    @action(detail=False, methods=["get"], permission_classes=[CanVerifyOpportunity])
    def pending(self, request):
        """The moderation queue, API-side — the admin panel's bulk actions
        cover this too; this exists for a future custom moderator UI."""
        queryset = Opportunity.objects.filter(status=Opportunity.Status.PENDING).select_related("category", "posted_by")
        page = self.paginate_queryset(queryset)
        serializer = OpportunitySerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[CanVerifyOpportunity])
    def approve(self, request, pk=None):
        opportunity = Opportunity.objects.get(pk=pk)
        approve_opportunity(opportunity, request.user)
        return Response(OpportunitySerializer(opportunity, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], permission_classes=[CanVerifyOpportunity])
    def reject(self, request, pk=None):
        serializer = OpportunityRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opportunity = Opportunity.objects.get(pk=pk)
        reject_opportunity(opportunity, request.user, serializer.validated_data["reason"])
        return Response(OpportunitySerializer(opportunity, context=self.get_serializer_context()).data)

    # --- Save / unsave -------------------------------------------------------

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def save(self, request, pk=None):
        opportunity = Opportunity.objects.get(pk=pk)
        SavedOpportunity.objects.get_or_create(user=request.user, opportunity=opportunity)
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], permission_classes=[permissions.IsAuthenticated])
    def unsave(self, request, pk=None):
        SavedOpportunity.objects.filter(user=request.user, opportunity_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def saved(self, request):
        queryset = SavedOpportunity.objects.filter(user=request.user).select_related("opportunity", "opportunity__category")
        page = self.paginate_queryset(queryset)
        serializer = SavedOpportunitySerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)
