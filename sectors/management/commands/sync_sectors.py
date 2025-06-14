from django.core.management.base import BaseCommand
from sectors.supabase_sync import supabase_sync

class Command(BaseCommand):
    help = 'Sync sectors from Supabase to Django'

    def handle(self, *args, **options):
        self.stdout.write('Starting sector sync...')
        
        if supabase_sync.sync_sectors_to_django():
            self.stdout.write(self.style.SUCCESS('Successfully synced sectors from Supabase'))
        else:
            self.stdout.write(self.style.ERROR('Failed to sync sectors from Supabase'))
