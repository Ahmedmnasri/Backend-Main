"""
Management command to sync Django users to Supabase Auth
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import SupabaseUser as User
from users.supabase_sync import SupabaseUserSync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Django users to Supabase Auth system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Sync specific user by email',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all users without auth_user_id',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if user already has auth_user_id',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='TempPassword123!',
            help='Default password for new auth users',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting user synchronization to Supabase Auth...'))
        
        # Initialize sync service
        sync_service = SupabaseUserSync()
        if not sync_service.supabase:
            self.stdout.write(self.style.ERROR('❌ Failed to initialize Supabase client'))
            return

        # Get users to sync
        if options['email']:
            # Sync specific user
            try:
                user = User.objects.get(email=options['email'])
                users_to_sync = [user]
                self.stdout.write(f"📧 Syncing user: {user.email}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ User with email {options["email"]} not found'))
                return
        elif options['all']:
            # Sync all users
            if options['force']:
                users_to_sync = User.objects.all()
                self.stdout.write("🔄 Syncing ALL users (force mode)")
            else:
                users_to_sync = User.objects.filter(auth_user_id__isnull=True)
                self.stdout.write("🔄 Syncing users without auth_user_id")
        else:
            # Default: sync users without auth_user_id
            users_to_sync = User.objects.filter(auth_user_id__isnull=True)
            self.stdout.write("🔄 Syncing users without auth_user_id (default)")

        # Handle both QuerySet and list
        try:
            # Try QuerySet count() first
            total_users = users_to_sync.count()
        except (TypeError, AttributeError):
            # Fall back to len() for lists
            total_users = len(users_to_sync)

        self.stdout.write(f"📊 Found {total_users} users to sync")

        if total_users == 0:
            self.stdout.write(self.style.SUCCESS('✅ No users need syncing'))
            return

        # Sync users
        success_count = 0
        error_count = 0

        for i, user in enumerate(users_to_sync, 1):
            self.stdout.write(f"\n🔄 [{i}/{total_users}] Processing: {user.email}")
            
            try:
                with transaction.atomic():
                    # Check if user already has auth_user_id and not forcing
                    if user.auth_user_id and not options['force']:
                        self.stdout.write(f"⏭️  User {user.email} already has auth_user_id: {user.auth_user_id}")
                        continue

                    # Create auth user
                    success = sync_service.create_auth_user(user, password=options['password'])
                    
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"✅ Successfully synced {user.email}"))
                        self.stdout.write(f"   Auth ID: {user.auth_user_id}")
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Failed to sync {user.email}"))
                        error_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error syncing {user.email}: {str(e)}"))
                error_count += 1

        # Summary
        self.stdout.write(f"\n📊 Synchronization Summary:")
        self.stdout.write(f"   ✅ Successful: {success_count}")
        self.stdout.write(f"   ❌ Failed: {error_count}")
        self.stdout.write(f"   📊 Total processed: {success_count + error_count}")

        if success_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully synced {success_count} users to Supabase Auth!'))
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'\n⚠️  {error_count} users failed to sync. Check logs for details.'))
