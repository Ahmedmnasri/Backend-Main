from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'execution_title', 'report_type', 'generated_by', 'created_at')
    list_filter = ('report_type', 'created_at')
    search_fields = ('title', 'notes', 'generated_by__email')
    readonly_fields = ('created_at',)
    
    def execution_title(self, obj):
        return obj.execution.assignment.title
    execution_title.short_description = 'Execution' 