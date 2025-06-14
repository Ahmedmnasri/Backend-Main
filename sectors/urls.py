from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SectorViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'', SectorViewSet)

urlpatterns = [
    # Router generated URLs
    path('', include(router.urls)),
] 