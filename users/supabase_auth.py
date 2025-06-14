"""
Supabase Authentication for Django REST Framework
"""
import os
import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import SupabaseUser


class SupabaseAuthentication(BaseAuthentication):
    """
    Custom authentication class for Supabase JWT tokens
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using Supabase JWT token
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        print(f"🔐 Supabase Auth: Received token: {token[:50]}...")

        try:
            # Decode the JWT token
            secret = os.getenv('SUPABASE_JWT_SECRET')
            if not secret:
                print("❌ Supabase JWT secret not found in environment")
                raise AuthenticationFailed('Supabase JWT secret not configured')

            print(f"🔑 Using JWT secret: {secret[:20]}...")
            # Decode with relaxed validation for time and audience issues
            payload = jwt.decode(
                token,
                secret,
                algorithms=['HS256'],
                options={
                    "verify_aud": False,  # Skip audience verification
                    "verify_iat": False,  # Skip issued-at time verification
                    "verify_exp": True,   # Still verify expiration
                }
            )
            print(f"✅ Token decoded successfully. Email: {payload.get('email')}")
            print(f"🔍 Token audience: {payload.get('aud')}")
            print(f"🔍 Token issuer: {payload.get('iss')}")
            print(f"🔍 Token role: {payload.get('role')}")

            # Get user email from token
            email = payload.get('email')
            if not email:
                raise AuthenticationFailed('Invalid token: no email found')

            # Get or create user
            try:
                user = SupabaseUser.objects.get(email=email)
                print(f"✅ Found existing user: {email}")
            except SupabaseUser.DoesNotExist:
                # Create user from token data
                print(f"🆕 Creating new user: {email}")
                user = SupabaseUser.objects.create(
                    email=email,
                    first_name=payload.get('user_metadata', {}).get('first_name', ''),
                    last_name=payload.get('user_metadata', {}).get('last_name', ''),
                    role=payload.get('user_metadata', {}).get('role', 'Technician')
                )

            return (user, token)

        except jwt.ExpiredSignatureError:
            print("❌ Token has expired")
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid token: {str(e)}")
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        return 'Bearer'
