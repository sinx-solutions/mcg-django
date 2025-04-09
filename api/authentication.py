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
# Set handler level to INFO for production, change to DEBUG if needed
handler.setLevel(logging.INFO)

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

    @property
    def is_anonymous(self):
        return False


class SupabaseAuthentication(BaseAuthentication):
    """
    Authentication backend for Supabase JWT tokens.
    Extracts the JWT from the Authorization header and validates it securely.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        logger.debug(f"Auth header present: {bool(auth_header)}")

        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("No Bearer token found or invalid header format")
            return None  # No credentials provided

        token = auth_header.replace('Bearer ', '', 1)
        logger.debug("Token extracted from header")

        # Check if the secret key is loaded
        jwt_secret = getattr(settings, 'SUPABASE_JWT_SECRET', None)
        if not jwt_secret:
            logger.error("SUPABASE_JWT_SECRET is not configured in settings.")
            # Raise AuthenticationFailed to signal a server config issue
            raise AuthenticationFailed("Server authentication configuration error.")

        try:
            logger.debug("Attempting secure JWT decoding...")
            decoded_token = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"], # Specify the expected algorithm
                # Explicitly specify the expected audience
                audience="authenticated",
                options={"verify_signature": True, "verify_exp": True} # Explicitly enable verification
            )
            logger.debug(f"Token decoded successfully. Payload keys: {decoded_token.keys()}")

            # Extract the user ID - in Supabase it's in the 'sub' claim
            user_id = decoded_token.get('sub')

            if not user_id:
                logger.warning("No user ID (sub) found in token claims.")
                raise AuthenticationFailed("Invalid token: Missing user identifier.")

            # Create a user object with the ID
            user = SupabaseUser(user_id)
            logger.info(f"Authentication successful for user ID: {user_id}")

            # Return (user, token) tuple as expected by DRF
            return (user, token)

        except jwt.ExpiredSignatureError:
            logger.warning("Token signature has expired.")
            raise AuthenticationFailed("Token has expired.")
        except jwt.InvalidSignatureError:
            logger.warning("Token signature verification failed.")
            raise AuthenticationFailed("Invalid token signature.")
        except jwt.InvalidAudienceError:
            logger.warning("Invalid token audience.")
            raise AuthenticationFailed("Invalid token audience.")
        except jwt.DecodeError as e:
            logger.warning(f"Token decode error: {str(e)}")
            raise AuthenticationFailed(f"Invalid token: {str(e)}")
        except jwt.PyJWTError as e:
            # Catch other JWT errors
            logger.error(f"Unhandled JWT error: {str(e)}")
            raise AuthenticationFailed(f"Token processing error: {str(e)}")
        except Exception as e:
            # Catch any other unexpected exceptions during authentication
            logger.error(f"Unexpected error in authentication: {str(e)}", exc_info=True)
            raise AuthenticationFailed("An unexpected error occurred during authentication.")

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the WWW-Authenticate
        header in a 401 Unauthorized response
        """
        return 'Bearer realm="api"' 