from django.contrib import admin
from .models import Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    """Admin configuration for Sector model."""
    list_display = ('name', 'code', 'location', 'manager_name', 'is_active', 'user_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'location', 'manager_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        ('Location Details', {
            'fields': ('location',)
        }),
        ('Manager Information', {
            'fields': ('manager_name', 'manager_email', 'manager_phone')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_count(self, obj):
        """Display the number of users in this sector."""
        return obj.users.count()
    
    user_count.short_description = 'Users' 