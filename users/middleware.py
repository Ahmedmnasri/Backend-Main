"""
Supabase Authentication Middleware for Django
"""
import os
import jwt
from django.contrib.auth.models import AnonymousUser
from .models import SupabaseUser


class SupabaseAuthMiddleware:
    """
    Middleware to handle Supabase authentication
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        self.process_request(request)
        
        response = self.get_response(request)
        return response

    def process_request(self, request):
        """
        Process the request to authenticate user via Supabase token
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Decode the JWT token
                secret = os.getenv('SUPABASE_JWT_SECRET')
                if secret:
                    payload = jwt.decode(token, secret, algorithms=['HS256'])
                    
                    # Get user email from token
                    email = payload.get('email')
                    if email:
                        try:
                            user = SupabaseUser.objects.get(email=email)
                            request.user = user
                            return
                        except SupabaseUser.DoesNotExist:
                            # Create user from token data
                            user_metadata = payload.get('user_metadata', {})
                            user = SupabaseUser.objects.create(
                                email=email,
                                first_name=user_metadata.get('first_name', ''),
                                last_name=user_metadata.get('last_name', ''),
                                role=user_metadata.get('role', 'Technician')
                            )
                            request.user = user
                            return
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
                pass
        
        # If no valid token, set anonymous user
        if not hasattr(request, 'user') or request.user is None:
            request.user = AnonymousUser()
