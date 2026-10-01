from rest_framework import generics, permissions
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response

from .models import User
from .serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """GET /api/auth/me — the logged-in user's own profile.
    PATCH /api/auth/me — update name and/or profile_picture (multipart for
    the picture; JSON works fine for name-only updates)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def update(self, request, *args, **kwargs):
        # Always partial — a profile edit updates whichever fields were
        # sent, never requires every field present (no PUT semantics here).
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Respond with the full read shape (UserSerializer), not the
        # narrower write serializer, so the frontend can just drop the
        # response straight into its user state.
        return Response(UserSerializer(instance, context=self.get_serializer_context()).data)
