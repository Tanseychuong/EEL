from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation used by /me and anywhere else a user's
    public info is embedded (e.g. Opportunity.posted_by)."""

    is_premium_active = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "is_premium_active", "role", "created_at"]
        read_only_fields = fields

    def get_is_premium_active(self, obj) -> bool:
        return obj.is_premium_active()

    def get_role(self, obj) -> str:
        if obj.is_superuser:
            return "admin"
        if obj.is_moderator():
            return "moderator"
        return "user"


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["name", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
