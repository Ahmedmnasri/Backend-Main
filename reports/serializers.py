from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model."""

    execution_title = serializers.CharField(source='execution.assignment.title', read_only=True)
    technician_name = serializers.CharField(source='execution.assignment.technician.get_full_name', read_only=True)
    technician_id = serializers.IntegerField(source='execution.assignment.technician.id', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    sector_name = serializers.CharField(source='execution.assignment.sector.name', read_only=True)
    sector_id = serializers.IntegerField(source='execution.assignment.sector.id', read_only=True)
    file_url = serializers.SerializerMethodField()

    # Add nested execution data for frontend filtering
    execution_data = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'title', 'execution', 'execution_title', 'execution_data',
            'technician_name', 'technician_id', 'generated_by', 'generated_by_name',
            'sector_name', 'sector_id', 'report_type', 'file_path', 'file_url',
            'notes', 'created_at'
        )
        read_only_fields = ('id', 'generated_by', 'created_at', 'file_url', 'execution_data')

    def get_file_url(self, obj):
        """Get the URL for the report file."""
        if obj.file_path:
            import os
            from django.conf import settings

            # Convert absolute path to relative path from MEDIA_ROOT
            try:
                relative_path = os.path.relpath(obj.file_path, settings.MEDIA_ROOT)
                file_url = f'/media/{relative_path.replace(os.sep, "/")}'

                request = self.context.get('request')
                if request is not None:
                    return request.build_absolute_uri(file_url)
                return file_url
            except Exception as e:
                print(f"Error generating file URL for report {obj.id}: {e}")
                return None
        return None

    def get_execution_data(self, obj):
        """Get nested execution data for frontend filtering."""
        try:
            return {
                'id': obj.execution.id,
                'status': obj.execution.status,
                'assignment': {
                    'id': obj.execution.assignment.id,
                    'title': obj.execution.assignment.title,
                    'technician': {
                        'id': obj.execution.assignment.technician.id,
                        'email': obj.execution.assignment.technician.email,
                        'first_name': obj.execution.assignment.technician.first_name,
                        'last_name': obj.execution.assignment.technician.last_name,
                    },
                    'sector': {
                        'id': obj.execution.assignment.sector.id if obj.execution.assignment.sector else None,
                        'name': obj.execution.assignment.sector.name if obj.execution.assignment.sector else None,
                    } if obj.execution.assignment.sector else None
                }
            }
        except Exception as e:
            print(f"Error serializing execution data for report {obj.id}: {e}")
            return None