from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import os

def health_check(request):
    """
    Health check endpoint for deployment monitoring
    """
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check if we're in production
        is_production = not settings.DEBUG
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'environment': 'production' if is_production else 'development',
            'version': '1.0.0',
            'service': 'Digital Field Inspection Backend'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'service': 'Digital Field Inspection Backend'
        }, status=500)
