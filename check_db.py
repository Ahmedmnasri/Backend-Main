import os
import sys
import django
from dotenv import load_dotenv

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'field_inspection.settings')
django.setup()

# Try to connect to the database
from django.db import connections
from django.db.utils import OperationalError

try:
    conn = connections['default']
    conn.cursor()
    print("Database connection successful!")
except OperationalError:
    print("Database connection failed!")
    import traceback
    traceback.print_exc()
