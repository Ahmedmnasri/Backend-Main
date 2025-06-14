from django.db import models


class Sector(models.Model):
    """
    Sector model to represent organizational units/divisions.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True, default="")
    code = models.CharField(max_length=20, blank=True, null=True, default="")
    location = models.CharField(max_length=255, blank=True, null=True, default="")
    
    # Manager/contact person for this sector
    manager_name = models.CharField(max_length=255, blank=True, null=True)
    manager_email = models.EmailField(blank=True, null=True)
    manager_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def user_count(self) -> int:
        """Return the count of users in this sector."""
        return self.users.all().count() if hasattr(self, 'users') else 0
    
    @property
    def technician_count(self) -> int:
        """Return the count of technicians in this sector."""
        return self.users.filter(role='Technician').count() if hasattr(self, 'users') else 0
    
    @property
    def supervisor_count(self) -> int:
        """Return the count of supervisors in this sector."""
        return self.users.filter(role='Supervisor').count() if hasattr(self, 'users') else 0
    
    class Meta:
        db_table = 'sectors'
        ordering = ['name']
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectors'