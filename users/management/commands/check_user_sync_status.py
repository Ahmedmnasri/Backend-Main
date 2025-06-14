"""
Management command to check user synchronization status between Django and Supabase Auth
"""
from django.core.management.base import BaseCommand
from users.models import SupabaseUser as User
from users.supabase_sync import SupabaseUserSync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check synchronization status between Django users and Supabase Auth'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information for each user',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Checking user synchronization status...'))
        
        # Initialize sync service
        sync_service = SupabaseUserSync()
        if not sync_service.supabase:
            self.stdout.write(self.style.ERROR('❌ Failed to initialize Supabase client'))
            return

        # Get all users
        all_users = User.objects.all()
        total_users = all_users.count()
        
        # Categorize users
        users_with_auth = all_users.filter(auth_user_id__isnull=False)
        users_without_auth = all_users.filter(auth_user_id__isnull=True)
        
        synced_count = users_with_auth.count()
        unsynced_count = users_without_auth.count()

        # Display summary
        self.stdout.write(f"\n📊 User Synchronization Status Summary:")
        self.stdout.write(f"   👥 Total Django users: {total_users}")
        self.stdout.write(f"   ✅ Users with Supabase Auth ID: {synced_count}")
        self.stdout.write(f"   ❌ Users without Supabase Auth ID: {unsynced_count}")
        
        if total_users > 0:
            sync_percentage = (synced_count / total_users) * 100
            self.stdout.write(f"   📈 Sync percentage: {sync_percentage:.1f}%")

        # Show users without auth_user_id
        if unsynced_count > 0:
            self.stdout.write(f"\n❌ Users missing Supabase Auth ID:")
            for user in users_without_auth:
                self.stdout.write(f"   • {user.email} ({user.role}) - Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}")

        # Show detailed information if requested
        if options['detailed'] and synced_count > 0:
            self.stdout.write(f"\n✅ Users with Supabase Auth ID:")
            for user in users_with_auth:
                self.stdout.write(f"   • {user.email} ({user.role})")
                self.stdout.write(f"     Auth ID: {user.auth_user_id}")
                self.stdout.write(f"     Created: {user.created_at.strftime('%Y-%m-%d %H:%M')}")

        # Check Supabase Auth users
        self.stdout.write(f"\n🔍 Checking Supabase Auth users...")
        try:
            # Get auth users from Supabase
            auth_response = sync_service.supabase.auth.admin.list_users()
            
            if hasattr(auth_response, 'users') and auth_response.users:
                auth_users_count = len(auth_response.users)
                self.stdout.write(f"   🔐 Total Supabase Auth users: {auth_users_count}")
                
                # Check for orphaned auth users (exist in Auth but not in Django)
                auth_emails = {user.email for user in auth_response.users if user.email}
                django_emails = set(all_users.values_list('email', flat=True))
                
                orphaned_auth = auth_emails - django_emails
                missing_auth = django_emails - auth_emails
                
                if orphaned_auth:
                    self.stdout.write(f"   ⚠️  Auth users without Django records: {len(orphaned_auth)}")
                    for email in orphaned_auth:
                        self.stdout.write(f"      • {email}")
                
                if missing_auth:
                    self.stdout.write(f"   ⚠️  Django users without Auth records: {len(missing_auth)}")
                    for email in missing_auth:
                        self.stdout.write(f"      • {email}")
                
                if not orphaned_auth and not missing_auth:
                    self.stdout.write(f"   ✅ All users are properly synchronized!")
                    
            else:
                self.stdout.write(f"   ❌ No auth users found or error accessing Supabase Auth")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error checking Supabase Auth: {str(e)}"))

        # Recommendations
        self.stdout.write(f"\n💡 Recommendations:")
        if unsynced_count > 0:
            self.stdout.write(f"   • Run 'python manage.py sync_users_to_auth --all' to sync missing users")
        if unsynced_count == 0 and synced_count > 0:
            self.stdout.write(f"   • All users are synchronized! ✅")
        if total_users == 0:
            self.stdout.write(f"   • No users found. Create some users first.")

        self.stdout.write(f"\n🏁 Check complete!")
