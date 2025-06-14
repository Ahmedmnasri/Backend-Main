from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReportViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'', ReportViewSet)

urlpatterns = [
    # Router generated URLs
    path('', include(router.urls)),
] 