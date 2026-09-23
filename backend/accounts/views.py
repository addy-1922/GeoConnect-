"""GeoConnect accounts: authentication views (register / login / logout / me)."""

from django.contrib.auth import get_user_model, login as django_login, logout as django_logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import services
from .serializers import (
    LoginSerializer,
    ProfileSerializer,
    PublicUserSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
)

User = get_user_model()


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_view(request):
    """Return the CSRF token and force-set the csrftoken cookie.

    The React SPA calls this before performing any state-changing request.
    """
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        user = services.register_user(
            username=serializer.validated_data["username"],
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
    except Exception as exc:
        return Response({"detail": f"Could not create account: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

    django_login(request, user)
    services.mark_seen(user)
    return Response(
        {
            "user": ProfileSerializer(user.profile).data,
            "csrfToken": get_token(request),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    django_login(request, user)
    services.mark_seen(user)
    return Response(
        {
            "user": ProfileSerializer(user.profile).data,
            "csrfToken": get_token(request),
        }
    )


@api_view(["POST"])
def logout_view(request):
    django_logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET", "PATCH"])
def me_view(request):
    user = request.user
    services.mark_seen(user)
    if request.method == "GET":
        return Response(ProfileSerializer(user.profile).data)

    serializer = UpdateProfileSerializer(user.profile, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(ProfileSerializer(user.profile).data)


@api_view(["GET"])
def user_list_view(request):
    """Search users by username/email (used to find people for a room)."""
    query = (request.query_params.get("search") or "").strip()
    qs = User.objects.select_related("profile").all().order_by("username")
    if query:
        qs = qs.filter(username__icontains=query)
    qs = qs[:20]
    return Response(PublicUserSerializer(qs, many=True).data)