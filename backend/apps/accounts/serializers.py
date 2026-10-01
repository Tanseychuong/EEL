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
        fields = ["id", "name", "email", "profile_picture", "is_premium_active", "role", "created_at"]
        read_only_fields = fields

    def get_is_premium_active(self, obj) -> bool:
        return obj.is_premium_active()

    def get_role(self, obj) -> str:
        if obj.is_superuser:
            return "admin"
        if obj.is_moderator():
            return "moderator"
        return "user"


class UserUpdateSerializer(serializers.ModelSerializer):
    """Write serializer for a user editing their own profile — deliberately
    excludes email, password, role/premium fields. Those go through their
    own dedicated flows (email is the login identity, password has its own
    change flow, role/premium are admin-only)."""

    class Meta:
        model = User
        fields = ["name", "profile_picture"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.")
        return value.strip()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["name", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
