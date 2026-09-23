"""GeoConnect accounts: serializers (register / login / profile / users)."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Profile

User = get_user_model()


def user_location_dict(user):
    """Last known location for a user, if shared. Used by profile/me responses."""
    location = getattr(user, "user_location", None)
    if location is None:
        return {}
    return {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "accuracy": location.accuracy,
        "updated_at": location.updated_at.isoformat(),
    }


class ProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True)
    location = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            "user_id",
            "username",
            "email",
            "avatar",
            "status",
            "is_sharing_location",
            "last_seen",
            "location",
        )

    def get_location(self, obj):
        if not obj.is_sharing_location:
            return {}
        try:
            from locations.models import UserLocation

            location = UserLocation.objects.filter(user=obj.user).first()
        except Exception:
            return {}
        if location is None:
            return {}
        return user_location_dict(obj.user)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "That username is already taken."})
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "That email is already registered."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"].strip(),
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError({"detail": "Invalid username or password."})
        if not user.is_active:
            raise serializers.ValidationError({"detail": "This account is disabled."})
        attrs["user"] = user
        return attrs


class UpdateProfileSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Profile.Status.choices, required=False)
    is_sharing_location = serializers.BooleanField(required=False)

    class Meta:
        model = Profile
        fields = ("avatar", "status", "is_sharing_location")

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance


class PublicUserSerializer(serializers.ModelSerializer):
    """Minimal info about a user, safe to expose to other members."""

    user_id = serializers.IntegerField(source="id", read_only=True)
    status = serializers.CharField(source="profile.status", read_only=True)
    is_sharing_location = serializers.BooleanField(
        source="profile.is_sharing_location", read_only=True
    )
    last_seen = serializers.DateTimeField(source="profile.last_seen", read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("user_id", "username", "avatar", "status", "is_sharing_location", "last_seen")

    def get_avatar(self, obj):
        avatar = getattr(obj.profile, "avatar", None)
        if not avatar:
            return None
        try:
            return avatar.url
        except Exception:
            return None