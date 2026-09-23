"""GeoConnect rooms: serializers."""

from rest_framework import serializers

from accounts.serializers import PublicUserSerializer

from .models import Room, RoomMember


class RoomListSerializer(serializers.ModelSerializer):
    created_by = PublicUserSerializer(read_only=True)
    member_count = serializers.IntegerField(source="num_members", read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = (
            "id",
            "name",
            "description",
            "is_private",
            "created_by",
            "member_count",
            "my_role",
            "created_at",
            "updated_at",
        )

    def get_my_role(self, obj):
        request = self.context.get("request")
        if request and getattr(request, "user", None):
            membership = obj.memberships.filter(user=request.user).first()
            return membership.role if membership else None
        return None


class RoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("name", "description", "is_private")

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("A room name is required.")
        if len(value) > 120:
            raise serializers.ValidationError("Room name must be 120 characters or fewer.")
        return value


class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("name", "description", "is_private")
        extra_kwargs = {
            "name": {"required": False},
            "description": {"required": False},
            "is_private": {"required": False},
        }


class RoomMemberSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = RoomMember
        fields = ("user", "user_id", "role", "joined_at")


class RoomDetailSerializer(serializers.ModelSerializer):
    created_by = PublicUserSerializer(read_only=True)
    members = RoomMemberSerializer(source="memberships", many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = (
            "id",
            "name",
            "description",
            "is_private",
            "created_by",
            "members",
            "member_count",
            "created_at",
            "updated_at",
        )


class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()
    role = serializers.ChoiceField(
        choices=[RoomMember.Role.ADMIN, RoomMember.Role.MEMBER],
        default=RoomMember.Role.MEMBER,
    )


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=RoomMember.Role.choices)