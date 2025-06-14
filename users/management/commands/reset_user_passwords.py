"""
Management command to reset user passwords in Supabase Auth
"""
from django.core.management.base import BaseCommand
from users.models import SupabaseUser as User
from users.supabase_sync import SupabaseUserSync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reset user passwords in Supabase Auth system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Reset password for specific user by email',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='TempPassword123!',
            help='New password to set (default: TempPassword123!)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset passwords for all users',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔑 Starting password reset for Supabase Auth users...'))
        
        # Initialize sync service
        sync_service = SupabaseUserSync()
        if not sync_service.supabase:
            self.stdout.write(self.style.ERROR('❌ Failed to initialize Supabase client'))
            return

        # Get users to reset
        if options['email']:
            # Reset specific user
            try:
                user = User.objects.get(email=options['email'])
                users_to_reset = [user]
                self.stdout.write(f"📧 Resetting password for user: {user.email}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ User with email {options["email"]} not found'))
                return
        elif options['all']:
            # Reset all users with auth_user_id
            users_to_reset = User.objects.filter(auth_user_id__isnull=False)
            self.stdout.write("🔄 Resetting passwords for all users with Supabase Auth")
        else:
            self.stdout.write(self.style.ERROR('❌ Please specify --email or --all'))
            return

        total_users = len(users_to_reset)
        self.stdout.write(f"📊 Found {total_users} users to reset")

        if total_users == 0:
            self.stdout.write(self.style.SUCCESS('✅ No users need password reset'))
            return

        # Reset passwords
        success_count = 0
        error_count = 0
        new_password = options['password']

        for i, user in enumerate(users_to_reset, 1):
            self.stdout.write(f"\n🔄 [{i}/{total_users}] Processing: {user.email}")
            
            if not user.auth_user_id:
                self.stdout.write(f"⏭️  User {user.email} has no auth_user_id, skipping")
                continue
            
            try:
                # Update password in Supabase Auth
                auth_response = sync_service.supabase.auth.admin.update_user_by_id(
                    str(user.auth_user_id),
                    {
                        "password": new_password
                    }
                )
                
                if auth_response.user:
                    self.stdout.write(self.style.SUCCESS(f"✅ Successfully reset password for {user.email}"))
                    self.stdout.write(f"   Auth ID: {user.auth_user_id}")
                    self.stdout.write(f"   New Password: {new_password}")
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Failed to reset password for {user.email}"))
                    error_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error resetting password for {user.email}: {str(e)}"))
                error_count += 1

        # Summary
        self.stdout.write(f"\n📊 Password Reset Summary:")
        self.stdout.write(f"   ✅ Successful: {success_count}")
        self.stdout.write(f"   ❌ Failed: {error_count}")
        self.stdout.write(f"   📊 Total processed: {success_count + error_count}")

        if success_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully reset passwords for {success_count} users!'))
            self.stdout.write(f'🔑 New password for all users: {new_password}')
            self.stdout.write(f'💡 Users can now log in with their email and this password')
        
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'\n⚠️  {error_count} users failed password reset. Check logs for details.'))
