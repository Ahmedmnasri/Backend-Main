from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper
from supabase import create_client, Client

class SupabaseDatabaseWrapper(PostgresDatabaseWrapper):
    def get_new_connection(self, conn_params):
        # First try direct connection
        try:
            return super().get_new_connection(conn_params)
        except Exception as e:
            # If direct connection fails, try using Supabase client
            supabase: Client = create_client(
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            )
            return supabase.postgrest
