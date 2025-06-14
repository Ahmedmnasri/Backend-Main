from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserViewSet,
    CustomTokenObtainPairView,
    ChangePasswordView,
    CurrentUserView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    simple_login
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'', UserViewSet)

urlpatterns = [
    # JWT authentication endpoints
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Password change endpoint
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # Current user endpoint
    path('me/', CurrentUserView.as_view(), name='current_user'),

    # Password reset endpoints
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Django authentication endpoint
    path('simple-login/', simple_login, name='simple_login'),

    # Router generated URLs
    path('', include(router.urls)),
]