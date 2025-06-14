from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from .models import (
    InspectionPDF, 
    InspectionSystem, 
    ChecklistTask, 
    ChecklistAssignment,
    ChecklistExecution,
    TaskResult,
    TaskPhoto
)


class InspectionPDFSerializer(serializers.ModelSerializer):
    """Serializer for InspectionPDF model with proper file upload handling."""

    class Meta:
        model = InspectionPDF
        fields = (
            'id', 'title', 'file', 'file_path', 'description', 'uploaded_by',
            'sector', 'upload_date', 'processed', 'processing_errors'
        )
        read_only_fields = ('id', 'upload_date', 'processed', 'processing_errors', 'uploaded_by')

    def create(self, validated_data):
        """Handle file upload and set uploaded_by from request user."""
        # Set uploaded_by from request context
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by'] = request.user

        return super().create(validated_data)
        

class ChecklistTaskSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistTask model."""
    
    class Meta:
        model = ChecklistTask
        fields = ('id', 'system', 'number', 'description')
        read_only_fields = ('id',)


class InspectionSystemSerializer(serializers.ModelSerializer):
    """Serializer for InspectionSystem model with nested tasks."""
    
    tasks = ChecklistTaskSerializer(many=True, read_only=True)
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionSystem
        fields = ('id', 'name', 'description', 'pdf', 'created_at', 'tasks', 'task_count')
        read_only_fields = ('id', 'created_at', 'task_count')
        
    def get_task_count(self, obj):
        return obj.task_count


class InspectionSystemListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing InspectionSystems."""
    
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionSystem
        fields = ('id', 'name', 'task_count')
        read_only_fields = ('id', 'task_count')
        
    def get_task_count(self, obj):
        return obj.task_count


class TaskPhotoSerializer(serializers.ModelSerializer):
    """Serializer for TaskPhoto model."""
    
    class Meta:
        model = TaskPhoto
        fields = ('id', 'task_result', 'photo', 'caption', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')


class TaskResultSerializer(serializers.ModelSerializer):
    """Serializer for TaskResult model with nested photos."""

    photos = TaskPhotoSerializer(many=True, read_only=True)
    task_description = serializers.CharField(source='task.description', read_only=True)
    task_number = serializers.IntegerField(source='task.number', read_only=True)
    task_system_id = serializers.IntegerField(source='task.system.id', read_only=True)
    task_system_name = serializers.CharField(source='task.system.name', read_only=True)

    class Meta:
        model = TaskResult
        fields = (
            'id', 'execution', 'task', 'task_description', 'task_number',
            'task_system_id', 'task_system_name',
            'status', 'notes', 'completed_at', 'created_at', 'updated_at', 'photos'
        )
        read_only_fields = ('id', 'completed_at', 'created_at', 'updated_at')
        

class ChecklistExecutionSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistExecution model with nested task results."""

    task_results = TaskResultSerializer(many=True, read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChecklistExecution
        fields = (
            'id', 'assignment', 'technician', 'status', 'started_at', 'completed_at',
            'notes', 'task_results', 'progress_percentage', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'progress_percentage', 'technician')

    def to_representation(self, instance):
        """Custom representation to avoid heavy task_results serialization during creation."""
        # Get the request from context
        request = self.context.get('request')

        # If this is a POST request (creation), don't include task_results to avoid performance issues
        if request and request.method == 'POST':
            # Create a copy of the serializer without task_results
            data = super().to_representation(instance)
            data.pop('task_results', None)  # Remove task_results from response
            data.pop('progress_percentage', None)  # Remove progress_percentage as well
            return data

        # For other requests (GET, PUT, etc.), include full data
        return super().to_representation(instance)

    
    def update(self, instance, validated_data):
        """Update the execution status and timestamps appropriately."""
        status = validated_data.get('status', instance.status)

        # Automatically set timestamps based on status changes
        if status == 'in_progress' and instance.status != 'in_progress':
            validated_data['started_at'] = timezone.now()
        elif status == 'completed' and instance.status != 'completed':
            validated_data['completed_at'] = timezone.now()

            # Also update the assignment status
            if instance.assignment.status != 'completed':
                instance.assignment.status = 'completed'
                instance.assignment.save()

        return super().update(instance, validated_data)


class ChecklistAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistAssignment model with nested execution."""
    
    execution = ChecklistExecutionSerializer(read_only=True)
    systems = InspectionSystemListSerializer(many=True, read_only=True)
    technician_name = serializers.CharField(source='technician.get_full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    sector_name = serializers.CharField(source='sector.name', read_only=True)
    
    class Meta:
        model = ChecklistAssignment
        fields = (
            'id', 'title', 'description', 'systems', 'technician', 'technician_name',
            'assigned_by', 'assigned_by_name', 'sector', 'sector_name',
            'due_date', 'status', 'notes', 'created_at', 'updated_at', 'execution'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'assigned_by', 'sector')
    
    @transaction.atomic
    def create(self, validated_data):
        """Create a ChecklistAssignment and initialize a ChecklistExecution."""
        systems = self.context['request'].data.get('systems', [])
        
        # Create the assignment
        assignment = super().create(validated_data)
        
        # Add the systems
        for system_id in systems:
            try:
                system = InspectionSystem.objects.get(pk=system_id)
                assignment.systems.add(system)
            except InspectionSystem.DoesNotExist:
                pass
        
        # Create the execution
        execution = ChecklistExecution.objects.create(
            assignment=assignment,
            technician=assignment.technician
        )
        
        # Create task results for all tasks in the assigned systems
        for system in assignment.systems.all():
            for task in system.tasks.all():
                TaskResult.objects.create(
                    execution=execution,
                    task=task
                )
        
        return assignment 