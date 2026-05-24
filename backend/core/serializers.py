"""Core serializers for authentication and user management."""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import Tenant

User = get_user_model()


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'tenant', 'tenant_name']
        read_only_fields = ['id']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, write_only=True)
    tenant_name = serializers.CharField(max_length=255)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    def create(self, validated_data):
        # Create tenant
        slug = validated_data['tenant_name'].lower().replace(' ', '-')[:100]
        # Handle duplicate slugs
        base_slug = slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        tenant = Tenant.objects.create(
            name=validated_data['tenant_name'],
            slug=slug,
        )

        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            tenant=tenant,
            role='admin',
        )
        return user
