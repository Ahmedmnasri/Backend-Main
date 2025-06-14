from rest_framework import serializers
from .models import Sector


class SectorSerializer(serializers.ModelSerializer):
    """Serializer for the Sector model."""
    
    # These field names match the serialized output but can get values from renamed annotations
    user_count = serializers.SerializerMethodField()
    technician_count = serializers.SerializerMethodField()
    supervisor_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sector
        fields = ('id', 'name', 'description', 'code', 'location', 
                  'manager_name', 'manager_email', 'manager_phone', 
                  'is_active', 'created_at', 'updated_at',
                  'user_count', 'technician_count', 'supervisor_count')
        read_only_fields = ('id', 'created_at', 'updated_at')
        
    def get_user_count(self, obj):
        """Get user count from annotation if available, otherwise use the model property"""
        if hasattr(obj, 'users_count'):
            return obj.users_count
        return obj.user_count
    
    def get_technician_count(self, obj):
        """Get technician count from annotation if available, otherwise use the model property"""
        if hasattr(obj, 'techs_count'):
            return obj.techs_count
        return obj.technician_count
    
    def get_supervisor_count(self, obj):
        """Get supervisor count from annotation if available, otherwise use the model property"""
        if hasattr(obj, 'supers_count'):
            return obj.supers_count
        return obj.supervisor_count


class SectorListSerializer(serializers.ModelSerializer):
    """Serializer for listing Sectors with all display fields."""

    # Use SerializerMethodField for flexibility with annotation source
    user_count = serializers.SerializerMethodField()
    technician_count = serializers.SerializerMethodField()
    supervisor_count = serializers.SerializerMethodField()

    class Meta:
        model = Sector
        fields = ('id', 'name', 'description', 'code', 'location', 'is_active',
                  'user_count', 'technician_count', 'supervisor_count')
        read_only_fields = ('id',)
        
    def get_user_count(self, obj):
        """Get user count from annotation if available, otherwise use the model property"""
        if hasattr(obj, 'users_count'):
            return obj.users_count
        return obj.user_count

    def get_technician_count(self, obj):
        """Get technician count from annotation if available, otherwise use the model property"""
        if hasattr(obj, 'techs_count'):
            return obj.techs_count
        return obj.technician_count

    def get_supervisor_count(self, obj):
        """Get supervisor count from annotation if available, otherwise use the model property"""
        if hasattr(obj, 'supers_count'):
            return obj.supers_count
        return obj.supervisor_count