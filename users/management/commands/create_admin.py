from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create admin superuser for production'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Check if admin already exists
        if User.objects.filter(username='admin').exists():
            self.stdout.write(
                self.style.WARNING('Admin user already exists!')
            )
            admin = User.objects.get(username='admin')
            self.stdout.write(f'Username: {admin.username}')
            self.stdout.write(f'Email: {admin.email}')
            self.stdout.write(f'Is superuser: {admin.is_superuser}')
            return

        # Create admin user
        try:
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@digitalmining.com',
                password='admin123',
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            
            self.stdout.write(
                self.style.SUCCESS('Successfully created admin user!')
            )
            self.stdout.write(f'Username: {admin.username}')
            self.stdout.write(f'Email: {admin.email}')
            self.stdout.write(f'Password: admin123')
            self.stdout.write(f'Role: {admin.role}')
            self.stdout.write(f'Is superuser: {admin.is_superuser}')
            self.stdout.write(f'Is staff: {admin.is_staff}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {e}')
            )
