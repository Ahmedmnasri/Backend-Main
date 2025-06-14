"""
Management command to create a superuser for testing
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the superuser (default: admin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@maintenanceai.com',
            help='Email for the superuser (default: admin@maintenanceai.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Password for the superuser (default: admin123)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists!')
                )
                user = User.objects.get(username=username)
                # Update password
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated password for user "{username}"')
                )
            else:
                # Create new superuser
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser "{username}"')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Superuser Details:\n'
                    f'Username: {username}\n'
                    f'Email: {email}\n'
                    f'Password: {password}\n'
                    f'Admin URL: https://digital-mining-backend.fly.dev/admin/\n'
                )
            )

        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Unexpected error: {e}')
            )
