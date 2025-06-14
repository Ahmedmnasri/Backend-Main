from django.contrib import admin
from django import forms
from django.db import transaction
from .models import SupabaseUser
import os
import logging

logger = logging.getLogger(__name__)


class UserAdminForm(forms.ModelForm):
    """Custom form for User admin with password field."""
    password = forms.CharField(
        widget=forms.PasswordInput(),
        help_text="Password for Supabase authentication",
        required=True
    )

    class Meta:
        model = SupabaseUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make auth_user_id not required in form (it will be set automatically)
        if 'auth_user_id' in self.fields:
            self.fields['auth_user_id'].required = False


@admin.register(SupabaseUser)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for SupabaseUser model with complete Supabase integration."""
    form = UserAdminForm
    list_display = ('email', 'first_name', 'last_name', 'role', 'sector', 'is_active', 'created_at')
    list_filter = ('role', 'sector', 'is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('id', 'auth_user_id', 'created_at', 'updated_at')

    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'auth_user_id', 'email', 'first_name', 'last_name', 'password')
        }),
        ('Role and Sector', {
            'fields': ('role', 'sector')
        }),
        ('Contact Info', {
            'fields': ('phone', 'profile_picture_url', 'profile_picture_storage_type')
        }),
        ('Status', {
            'fields': ('is_active', 'last_login_ip')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Complete user creation with Supabase Auth and database sync."""
        password = form.cleaned_data.get('password')
        
        if not change:  # New user creation
            print(f"🔑 Admin: Creating new user {obj.email}")
            
            with transaction.atomic():
                # Save Django user first
                super().save_model(request, obj, form, change)
                print(f"💾 Saved Django user: {obj.id}")
                
                # Create Supabase Auth user and sync
                if password:
                    success = self._create_complete_supabase_user(obj, password)
                    if success:
                        print(f"✅ Complete Supabase setup successful for {obj.email}")
                    else:
                        print(f"❌ Supabase setup failed for {obj.email}")
        else:
            # Update existing user
            super().save_model(request, obj, form, change)
            if password:
                self._update_supabase_password(obj, password)

    def _create_complete_supabase_user(self, user, password):
        """Create user in Supabase Auth and sync to database table."""
        try:
            # Initialize Supabase client
            from supabase import create_client, Client

            supabase_url = os.getenv("SUPABASE_URL", "https://yoolzpzbumgqqyyyzjpn.supabase.co")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

            if not supabase_key:
                print("❌ Supabase service key not configured")
                print("⚠️ Please set SUPABASE_SERVICE_ROLE_KEY environment variable")
                return False

            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Step 1: Create user in Supabase Auth
            print(f"🚀 Creating Supabase Auth user for {user.email}")
            auth_response = supabase.auth.admin.create_user({
                "email": user.email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "full_name": user.get_full_name()
                }
            })
            
            if not auth_response.user:
                print(f"❌ Failed to create Supabase Auth user")
                return False
                
            # Step 2: Update Django user with auth_user_id
            user.auth_user_id = auth_response.user.id
            user.save(update_fields=['auth_user_id'])
            print(f"✅ Auth user created with ID: {auth_response.user.id}")
            
            # Step 3: Verify password works
            try:
                test_response = supabase.auth.sign_in_with_password({
                    "email": user.email,
                    "password": password
                })
                if test_response.user:
                    print(f"✅ Password verification successful")
                    supabase.auth.sign_out()
                else:
                    print(f"⚠️ Password verification failed")
            except Exception as e:
                print(f"⚠️ Password verification error: {e}")
            
            # Step 4: Sync to Supabase users table
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'phone': user.phone or '',
                'profile_picture_url': user.profile_picture_url or '',
                'sector_id': str(user.sector.id) if user.sector else None,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                'date_joined': user.date_joined.isoformat() if user.date_joined else user.created_at.isoformat(),
                'auth_user_id': str(user.auth_user_id)
            }
            
            result = supabase.table('users').insert(user_data).execute()
            if result.data:
                print(f"✅ User synced to Supabase users table")
                return True
            else:
                print(f"❌ Failed to sync to users table")
                return False
                
        except Exception as e:
            print(f"❌ Error in Supabase user creation: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _update_supabase_password(self, user, password):
        """Update password in Supabase Auth."""
        try:
            from supabase import create_client, Client
            
            supabase_url = os.getenv("SUPABASE_URL", "https://yoolzpzbumgqqyyyzjpn.supabase.co")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            
            if not supabase_key or not user.auth_user_id:
                return False
                
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Update password in Supabase Auth
            update_response = supabase.auth.admin.update_user_by_id(
                str(user.auth_user_id),
                {"password": password}
            )
            
            if update_response.user:
                print(f"✅ Password updated for {user.email}")
                return True
            else:
                print(f"❌ Failed to update password for {user.email}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating password: {e}")
            return False
