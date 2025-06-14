from django.core.management.base import BaseCommand
from users.models import SupabaseUser as User
from users.supabase_sync import SupabaseUserSync


class Command(BaseCommand):
    help = 'Fix user password in Supabase Auth'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email')
        parser.add_argument('password', type=str, help='New password')

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        
        self.stdout.write(f'=== FIXING PASSWORD FOR {email} ===')
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'✅ Found Django user: {user.email}')
            self.stdout.write(f'🔑 Auth User ID: {user.auth_user_id}')
            
            sync_service = SupabaseUserSync()
            if sync_service.supabase and user.auth_user_id:
                self.stdout.write('🔄 Updating password in Supabase Auth...')
                
                # Update password in Supabase Auth
                auth_response = sync_service.supabase.auth.admin.update_user_by_id(
                    user.auth_user_id,
                    {'password': password}
                )
                
                if auth_response.user:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Password updated successfully for {email}')
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'💡 You can now login with: {email} / {password}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('❌ Failed to update password in Supabase Auth')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Supabase not available or user has no auth_user_id')
                )
                
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User {email} not found in Django database')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error: {str(e)}')
            )
