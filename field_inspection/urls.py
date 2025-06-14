"""
URL configuration for field_inspection project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from .health import health_check
from rest_framework.documentation import include_docs_urls
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

def root_view(request):
    """Root API endpoint"""
    return JsonResponse({
        'message': 'Maintenance AI - Digital Field Inspection Backend',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health/',
            'authentication': '/api/token/',
            'documentation': '/docs/',
            'admin': '/admin/',
        }
    })

urlpatterns = [
    path('', root_view, name='root'),
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health_check'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/', include('users.urls')),
    path('api/sectors/', include('sectors.urls')),
    path('api/checklists/', include('checklists.urls')),
    path('api/reports/', include('reports.urls')),
    path('docs/', include_docs_urls(title='Field Inspection API')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)