"""
Management command to convert sectors from integer IDs to UUIDs.
This command will:
1. Clear all existing sectors and related data
2. Drop and recreate the sectors table with UUID primary key
3. Update foreign key references to use UUIDs
4. Handle all foreign key constraints properly
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.conf import settings
import uuid


class Command(BaseCommand):
    help = 'Convert sectors from integer IDs to UUIDs (destructive operation)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all existing sectors',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will DELETE ALL EXISTING SECTORS and related data.\n'
                    'Run with --confirm to proceed.'
                )
            )
            return

        self.stdout.write('🚨 Starting destructive sector UUID conversion...')
        
        try:
            with transaction.atomic():
                self._convert_sectors_to_uuid()
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully converted sectors to UUID!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during conversion: {e}')
            )
            raise

    def _convert_sectors_to_uuid(self):
        """Perform the actual conversion"""
        with connection.cursor() as cursor:
            
            # Step 1: Clear user sector assignments
            self.stdout.write('1. Clearing user sector assignments...')
            cursor.execute("UPDATE users SET sector_id = NULL WHERE sector_id IS NOT NULL")
            rows_updated = cursor.rowcount
            self.stdout.write(f'   ✅ Cleared {rows_updated} user sector assignments')
            
            # Step 2: Clear any other related data that might reference sectors
            self.stdout.write('2. Clearing related data...')
            
            # Check if inspection_pdfs table exists and clear sector references
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'inspection_pdfs'
                );
            """)
            if cursor.fetchone()[0]:
                cursor.execute("UPDATE inspection_pdfs SET sector_id = NULL WHERE sector_id IS NOT NULL")
                rows_updated = cursor.rowcount
                self.stdout.write(f'   ✅ Cleared {rows_updated} inspection PDF sector references')
            
            # Step 3: Drop foreign key constraints
            self.stdout.write('3. Dropping foreign key constraints...')
            
            # Drop constraint from users table
            cursor.execute("""
                ALTER TABLE users
                DROP CONSTRAINT IF EXISTS users_sector_id_fkey;
            """)
            
            # Drop constraint from inspection_pdfs if it exists
            cursor.execute("""
                ALTER TABLE inspection_pdfs 
                DROP CONSTRAINT IF EXISTS inspection_pdfs_sector_id_fkey;
            """)
            
            self.stdout.write('   ✅ Dropped foreign key constraints')
            
            # Step 4: Delete all sectors
            self.stdout.write('4. Deleting all existing sectors...')
            cursor.execute("DELETE FROM sectors")
            rows_deleted = cursor.rowcount
            self.stdout.write(f'   ✅ Deleted {rows_deleted} sectors')
            
            # Step 5: Drop and recreate sectors table with UUID primary key
            self.stdout.write('5. Recreating sectors table with UUID primary key...')
            
            cursor.execute("DROP TABLE IF EXISTS sectors CASCADE")
            
            cursor.execute("""
                CREATE TABLE sectors (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    code VARCHAR(20) DEFAULT '',
                    location VARCHAR(255) DEFAULT '',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            self.stdout.write('   ✅ Recreated sectors table with UUID primary key')
            
            # Step 6: Update users table to reference UUID
            self.stdout.write('6. Updating users table sector reference...')

            cursor.execute("""
                ALTER TABLE users
                ALTER COLUMN sector_id TYPE UUID USING NULL;
            """)

            cursor.execute("""
                ALTER TABLE users
                ADD CONSTRAINT users_sector_id_fkey
                FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE SET NULL;
            """)
            
            self.stdout.write('   ✅ Updated users table sector reference to UUID')
            
            # Step 7: Update inspection_pdfs table if it exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'inspection_pdfs'
                );
            """)
            if cursor.fetchone()[0]:
                self.stdout.write('7. Updating inspection_pdfs table sector reference...')
                
                cursor.execute("""
                    ALTER TABLE inspection_pdfs 
                    ALTER COLUMN sector_id TYPE UUID USING NULL;
                """)
                
                cursor.execute("""
                    ALTER TABLE inspection_pdfs 
                    ADD CONSTRAINT inspection_pdfs_sector_id_fkey 
                    FOREIGN KEY (sector_id) REFERENCES sectors(id) ON DELETE SET NULL;
                """)
                
                self.stdout.write('   ✅ Updated inspection_pdfs table sector reference to UUID')
            
            # Step 8: Update Django migrations table to mark UUID migration as applied
            self.stdout.write('8. Updating Django migrations...')
            
            # Mark the UUID migration as applied
            cursor.execute("""
                INSERT INTO django_migrations (app, name, applied) 
                VALUES ('sectors', '0003_convert_to_uuid_simple', NOW())
                ON CONFLICT (app, name) DO NOTHING;
            """)
            
            self.stdout.write('   ✅ Updated Django migrations table')
            
        self.stdout.write('\n🎉 Sector UUID conversion completed successfully!')
        self.stdout.write('You can now create new sectors with UUID primary keys.')
