from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Opportunity, OpportunityCategory, SavedOpportunity


class OpportunityCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OpportunityCategory
        fields = ["id", "slug", "name", "description"]


class OpportunitySerializer(serializers.ModelSerializer):
    """Read serializer — used for list/retrieve. Anything derived (is_saved,
    category/poster details) is computed here so the frontend doesn't need
    a second request per opportunity."""

    category = OpportunityCategorySerializer(read_only=True)
    posted_by = UserSerializer(read_only=True)
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            "id", "title", "organization", "description", "location",
            "opportunity_url", "application_deadline",
            "category", "posted_by", "source_type",
            "published_at", "is_saved",
        ]
        read_only_fields = fields

    def get_is_saved(self, obj) -> bool:
        user = self.context.get("request").user if self.context.get("request") else None
        if not user or not user.is_authenticated:
            return False
        return obj.saved_by.filter(user=user).exists()


class OpportunityCreateSerializer(serializers.ModelSerializer):
    """Write serializer for user submissions — deliberately excludes
    status/reviewed_by/published_at/etc; those are only ever set by
    services.approve_opportunity()/reject_opportunity(), never by the
    submitter directly."""

    class Meta:
        model = Opportunity
        fields = [
            "id", "title", "organization", "description", "location",
            "opportunity_url", "application_deadline", "category",
        ]
        read_only_fields = ["id"]


class OpportunityRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False)


class SavedOpportunitySerializer(serializers.ModelSerializer):
    opportunity = OpportunitySerializer(read_only=True)

    class Meta:
        model = SavedOpportunity
        fields = ["id", "opportunity", "saved_at"]
        read_only_fields = fields
