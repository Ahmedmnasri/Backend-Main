from django.contrib import admin
from django.utils.html import format_html
from .models import (
    InspectionPDF,
    InspectionSystem,
    ChecklistTask,
    ChecklistAssignment,
    ChecklistExecution,
    TaskResult,
    TaskPhoto
)


@admin.register(InspectionPDF)
class InspectionPDFAdmin(admin.ModelAdmin):
    list_display = ('title', 'sector', 'uploaded_by', 'upload_date', 'processed', 'system_count')
    list_filter = ('processed', 'sector', 'upload_date')
    search_fields = ('title', 'description', 'uploaded_by__email')
    readonly_fields = ('upload_date', 'processed', 'processing_errors')
    fieldsets = (
        (None, {
            'fields': ('title', 'file_path', 'description', 'sector', 'uploaded_by')
        }),
        ('Processing', {
            'fields': ('processed', 'processing_errors', 'upload_date')
        }),
    )
    
    def system_count(self, obj):
        count = obj.inspection_systems.count()
        return count
    system_count.short_description = 'Systems'
    

class ChecklistTaskInline(admin.TabularInline):
    model = ChecklistTask
    extra = 1
    fields = ('number', 'description')


@admin.register(InspectionSystem)
class InspectionSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'pdf', 'task_count', 'created_at')
    list_filter = ('pdf__sector', 'created_at')
    search_fields = ('name', 'description', 'pdf__title')
    readonly_fields = ('created_at', 'task_count')
    inlines = [ChecklistTaskInline]
    
    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = 'Tasks'


@admin.register(ChecklistTask)
class ChecklistTaskAdmin(admin.ModelAdmin):
    list_display = ('number', 'description_truncated', 'system')
    list_filter = ('system__pdf__sector', 'system')
    search_fields = ('description', 'system__name')
    
    def description_truncated(self, obj):
        if len(obj.description) > 100:
            return f"{obj.description[:100]}..."
        return obj.description
    description_truncated.short_description = 'Description'


class TaskResultInline(admin.TabularInline):
    model = TaskResult
    extra = 0
    readonly_fields = ('task', 'status', 'notes', 'completed_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChecklistAssignment)
class ChecklistAssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'technician', 'sector', 'due_date', 'status', 'assigned_by')
    list_filter = ('status', 'sector', 'due_date')
    search_fields = ('title', 'description', 'technician__email', 'assigned_by__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'sector')
        }),
        ('Assignment', {
            'fields': ('technician', 'assigned_by', 'due_date', 'status', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ChecklistExecution)
class ChecklistExecutionAdmin(admin.ModelAdmin):
    list_display = ('assignment_title', 'status', 'progress', 'technician_name', 'started_at', 'completed_at')
    list_filter = ('status', 'assignment__sector', 'technician')
    search_fields = ('assignment__title', 'notes')
    readonly_fields = ('assignment', 'technician', 'started_at', 'completed_at', 'submitted_at', 'progress_percentage')
    inlines = [TaskResultInline]
    
    def assignment_title(self, obj):
        return obj.assignment.title
    assignment_title.short_description = 'Assignment'
    
    def technician_name(self, obj):
        return obj.technician.get_full_name()
    technician_name.short_description = 'Technician'
    
    def progress(self, obj):
        percentage = obj.progress_percentage
        color = 'green' if percentage == 100 else 'orange' if percentage > 50 else 'red'
        return format_html(
            '<div style="width:100px; background-color: #f1f1f1; border-radius: 4px;">'
            '<div style="width: {}%; background-color: {}; height: 10px; border-radius: 4px;">'
            '</div></div>&nbsp;{}%',
            percentage, color, percentage
        )
    progress.short_description = 'Progress'


class TaskPhotoInline(admin.TabularInline):
    model = TaskPhoto
    extra = 0
    readonly_fields = ('photo_preview', 'uploaded_at')
    fields = ('file_path', 'photo_preview', 'caption', 'uploaded_at')

    def photo_preview(self, obj):
        if obj.file_path:
            return format_html('<img src="{}" width="150" height="auto" />', obj.file_path)
        return "No Photo"
    photo_preview.short_description = 'Preview'


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ('task_info', 'status', 'execution_title', 'technician', 'photo_count', 'completed_at')
    list_filter = ('status', 'execution__assignment__sector', 'execution__technician')
    search_fields = ('task__description', 'notes', 'execution__assignment__title')
    readonly_fields = ('execution', 'task', 'completed_at', 'created_at', 'updated_at')
    inlines = [TaskPhotoInline]
    
    def task_info(self, obj):
        return f"{obj.task.number}. {obj.task.description[:50]}..."
    task_info.short_description = 'Task'
    
    def execution_title(self, obj):
        return obj.execution.assignment.title
    execution_title.short_description = 'Execution'
    
    def technician(self, obj):
        return obj.execution.technician.get_full_name()
    technician.short_description = 'Technician'
    
    def photo_count(self, obj):
        return obj.photos.count()
    photo_count.short_description = 'Photos'


@admin.register(TaskPhoto)
class TaskPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_result_info', 'caption', 'photo_preview', 'uploaded_at')
    list_filter = ('uploaded_at', 'task_result__execution__assignment__sector')
    search_fields = ('caption', 'task_result__task__description')
    readonly_fields = ('photo_preview', 'uploaded_at')

    def task_result_info(self, obj):
        task = obj.task_result.task
        return f"{task.number}. {task.description[:50]}..."
    task_result_info.short_description = 'Task'

    def photo_preview(self, obj):
        if obj.file_path:
            return format_html('<img src="{}" width="150" height="auto" />', obj.file_path)
        return "No Photo"
    photo_preview.short_description = 'Preview'