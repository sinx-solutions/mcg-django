import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
import logging
import sys

# Create a custom logger for more visibility during debugging
logger = logging.getLogger('supabase_auth')
logger.setLevel(logging.DEBUG)

# Create console handler
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

class SupabaseUser:
    """
    A minimal user class to mimic Django's User model with just the ID.
    This avoids needing to sync users between Supabase and Django.
    """
    def __init__(self, user_id):
        self.id = user_id
        self.is_authenticated = True
        print(f"DEBUG: Created SupabaseUser with ID: {user_id}")

    @property
    def is_anonymous(self):
        return False


class SupabaseAuthentication(BaseAuthentication):
    """
    Authentication backend for Supabase JWT tokens.
    Extracts the JWT from the Authorization header and validates it.
    """
    def authenticate(self, request):
        print(f"\n\n==== AUTHENTICATION ATTEMPT ====")
        print(f"Request path: {request.path}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Authentication attempt for {request.path}")
        
        # Get the token from the Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        print(f"Authorization header: {auth_header[:20]}...")
        logger.debug(f"Auth header present: {bool(auth_header)}")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            print("DEBUG: No Bearer token found in Authorization header")
            logger.warning("No Bearer token found")
            return None  # No credentials provided
            
        token = auth_header.replace('Bearer ', '', 1)
        print(f"DEBUG: Token extracted: {token[:20]}...")
        logger.debug("Token extracted from header")
        
        try:
            # For now, just decode the token without verification (for testing)
            # In production, you should verify this with the proper public key
            # jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"])
            
            print("DEBUG: Attempting to decode token...")
            # Simple decode without verification (for testing only!)
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            
            print(f"DEBUG: Token decoded successfully: {decoded_token}")
            logger.debug(f"Token decoded: {decoded_token}")
            
            # Extract the user ID - in Supabase it's in the 'sub' claim
            user_id = decoded_token.get('sub')
            print(f"DEBUG: User ID from token: {user_id}")
            
            if not user_id:
                print("DEBUG: No user ID found in token")
                logger.warning("No user ID (sub) found in token")
                return None
                
            # Create a user object with the ID
            user = SupabaseUser(user_id)
            print(f"DEBUG: Created user object with ID: {user.id}")
            logger.debug(f"Authentication successful for user ID: {user_id}")
            
            # Return (user, token) tuple as expected by DRF
            print("DEBUG: Returning authenticated user")
            return (user, token)
            
        except jwt.PyJWTError as e:
            # Log the error for debugging
            print(f"DEBUG: JWT Error: {str(e)}")
            print(f"DEBUG: Token that failed: {token[:30]}...")
            logger.error(f"JWT error: {str(e)}")
            return None
        except Exception as e:
            # Catch any other exceptions for debugging
            print(f"DEBUG: Unexpected error in authentication: {str(e)}")
            logger.error(f"Unexpected error: {str(e)}")
            return None
        
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the WWW-Authenticate
        header in a 401 Unauthorized response
        """
        return 'Bearer realm="api"' 