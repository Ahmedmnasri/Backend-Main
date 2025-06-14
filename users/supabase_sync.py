"""
Supabase User Synchronization Service

This module handles synchronization between Django users and Supabase Auth users.
"""

import os
import logging
from typing import Optional, Dict, Any
from supabase import create_client, Client
from django.conf import settings

logger = logging.getLogger(__name__)


class SupabaseUserSync:
    """Service for synchronizing Django users with Supabase Auth."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Supabase client."""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not supabase_url or not supabase_service_key:
                logger.error("❌ Missing Supabase credentials in environment variables")
                return
            
            self.supabase = create_client(supabase_url, supabase_service_key)
            logger.info("✅ Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            self.supabase = None
    
    def create_auth_user(self, user, password: str = None) -> bool:
        """
        Create a user in Supabase Auth.
        
        Args:
            user: Django user instance
            password: Password for the auth user
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase:
            logger.error("❌ Supabase client not initialized")
            return False
        
        try:
            # Use provided password or generate a default one
            auth_password = password or 'TempPassword123!'
            
            logger.info(f"🔄 Creating Supabase Auth user for: {user.email}")
            
            # Create user in Supabase Auth
            auth_response = self.supabase.auth.admin.create_user({
                'email': user.email,
                'password': auth_password,
                'email_confirm': True,  # Auto-confirm email
                'user_metadata': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'sector': str(user.sector.id) if user.sector else None,
                    'created_from_django': True
                }
            })
            
            if auth_response.user:
                # Update Django user with auth_user_id
                user.auth_user_id = auth_response.user.id
                user.save(update_fields=['auth_user_id'])
                
                logger.info(f"✅ Successfully created Supabase Auth user for {user.email}")
                logger.info(f"   Auth User ID: {auth_response.user.id}")
                return True
            else:
                logger.error(f"❌ Failed to create Supabase Auth user for {user.email}: No user returned")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creating Supabase Auth user for {user.email}: {e}")
            return False
    
    def update_auth_user(self, user, **kwargs) -> bool:
        """
        Update a user in Supabase Auth.
        
        Args:
            user: Django user instance
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase or not user.auth_user_id:
            logger.error(f"❌ Cannot update auth user for {user.email}: Missing Supabase client or auth_user_id")
            return False
        
        try:
            logger.info(f"🔄 Updating Supabase Auth user for: {user.email}")
            
            # Prepare update data
            update_data = {}
            
            # Handle password update
            if 'password' in kwargs:
                update_data['password'] = kwargs['password']
            
            # Handle metadata update
            if any(field in kwargs for field in ['first_name', 'last_name', 'role', 'sector']):
                update_data['user_metadata'] = {
                    'first_name': kwargs.get('first_name', user.first_name),
                    'last_name': kwargs.get('last_name', user.last_name),
                    'role': kwargs.get('role', user.role),
                    'sector': str(kwargs.get('sector', user.sector).id) if kwargs.get('sector', user.sector) else None,
                }
            
            if update_data:
                auth_response = self.supabase.auth.admin.update_user_by_id(
                    str(user.auth_user_id),
                    update_data
                )
                
                if auth_response.user:
                    logger.info(f"✅ Successfully updated Supabase Auth user for {user.email}")
                    return True
                else:
                    logger.error(f"❌ Failed to update Supabase Auth user for {user.email}: No user returned")
                    return False
            else:
                logger.info(f"ℹ️ No updates needed for Supabase Auth user {user.email}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error updating Supabase Auth user for {user.email}: {e}")
            return False
    
    def delete_auth_user(self, auth_user_id: str) -> bool:
        """
        Delete a user from Supabase Auth.
        
        Args:
            auth_user_id: Supabase Auth user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase:
            logger.error("❌ Supabase client not initialized")
            return False
        
        try:
            logger.info(f"🔄 Deleting Supabase Auth user: {auth_user_id}")
            
            self.supabase.auth.admin.delete_user(str(auth_user_id))
            logger.info(f"✅ Successfully deleted Supabase Auth user: {auth_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting Supabase Auth user {auth_user_id}: {e}")
            return False
    
    def get_auth_user(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user from Supabase Auth.
        
        Args:
            auth_user_id: Supabase Auth user ID
            
        Returns:
            Dict containing user data or None if not found
        """
        if not self.supabase:
            logger.error("❌ Supabase client not initialized")
            return None
        
        try:
            auth_response = self.supabase.auth.admin.get_user_by_id(str(auth_user_id))
            
            if auth_response.user:
                return {
                    'id': auth_response.user.id,
                    'email': auth_response.user.email,
                    'created_at': auth_response.user.created_at,
                    'user_metadata': auth_response.user.user_metadata,
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting Supabase Auth user {auth_user_id}: {e}")
            return None
    
    def list_auth_users(self) -> list:
        """
        List all users from Supabase Auth.
        
        Returns:
            List of auth users
        """
        if not self.supabase:
            logger.error("❌ Supabase client not initialized")
            return []
        
        try:
            auth_response = self.supabase.auth.admin.list_users()
            
            if hasattr(auth_response, 'users') and auth_response.users:
                return auth_response.users
            else:
                return []
                
        except Exception as e:
            logger.error(f"❌ Error listing Supabase Auth users: {e}")
            return []


# Global instance for easy access
supabase_user_sync = SupabaseUserSync()
