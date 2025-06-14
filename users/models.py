from django.db import models
import uuid


class SupabaseUser(models.Model):
    """User profile model that references Supabase auth users."""

    ROLE_CHOICES = [
        ('Admin', 'Admin'),
        ('Supervisor', 'Supervisor'),
        ('Technician', 'Technician'),
    ]

    # Primary key as UUID to match Supabase
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Reference to Supabase auth user
    auth_user_id = models.UUIDField(unique=True, help_text="Supabase auth.users.id")

    # User information
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, default='')
    last_name = models.CharField(max_length=150, default='')

    # Role field to identify user type
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Technician')

    # Additional fields
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture_url = models.TextField(blank=True, null=True, help_text="URL to profile picture in Supabase Storage")
    profile_picture_storage_type = models.CharField(max_length=50, default='supabase')

    # Track when user last logged in
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    # Sector relationship (many users can belong to one sector)
    sector = models.ForeignKey(
        'sectors.Sector',
        on_delete=models.SET_NULL,
        related_name='users',
        blank=True,
        null=True
    )

    # Django compatibility fields (not used with Supabase auth)
    username = models.CharField(max_length=150, blank=True, null=True)  # Not used with Supabase
    password = models.CharField(max_length=128, blank=True, null=True)  # Not used with Supabase
    last_login = models.DateTimeField(blank=True, null=True)

    # Timestamps
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now_add=True)  # Required for Django compatibility

    class Meta:
        db_table = 'users'  # Keep original table name

    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    @property
    def is_admin(self):
        return self.role == 'Admin'

    @property
    def is_supervisor(self):
        return self.role == 'Supervisor'

    @property
    def is_technician(self):
        return self.role == 'Technician'

    # Override AbstractUser properties for role-based permissions
    @property
    def is_staff(self):
        """Return True if user is Admin or Supervisor."""
        return self.role in ['Admin', 'Supervisor']

    @property
    def is_superuser(self):
        """Return True if user is Admin."""
        return self.role == 'Admin'

    @property
    def is_authenticated(self):
        """Always return True for authenticated users."""
        return True

    @property
    def is_anonymous(self):
        """Always return False for authenticated users."""
        return False

    # Required for Django admin compatibility
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']