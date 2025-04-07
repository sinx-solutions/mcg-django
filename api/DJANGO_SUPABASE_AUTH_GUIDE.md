# Technical Guide: Implementing Supabase JWT Authentication in Django (`apps/api`)

**Objective:** Configure the Django REST Framework (DRF) application in `apps/api` to authenticate API requests using JWTs issued by Supabase.

**Chosen Strategy:** Option 2 - Shared Supabase Database. Django verifies Supabase JWTs and connects to the main Supabase Postgres instance for its data, managing its own tables within that database. Data access control relies primarily on DRF permissions.

## 1. Prerequisites

- **`.env` File:** Ensure the `.env` file in the `apps/api` root directory contains the correct Supabase credentials:
  - `JWT_SECRET`: **Critical** for verifying JWT signatures. Found in Supabase Project Settings -> API -> JWT Settings.
  - **Database Connection Details:**
    - `DB_NAME`: Your Supabase database name (usually `postgres`).
    - `DB_USER`: The Postgres user Django will connect as (e.g., `postgres` or a dedicated role).
    - `DB_PASSWORD`: The password for the `DB_USER`.
    - `DB_HOST`: The host address for your Supabase database (e.g., `aws-0-your-region.pooler.supabase.com`). Find this in Project Settings -> Database -> Connection info.
    - `DB_PORT`: The port for your Supabase database (usually `5432` for direct connection or `6543` if using Supavisor pooling). Find this in Project Settings -> Database -> Connection info.
  - `SUPABASE_URL` (Optional but good practice): Base URL for your Supabase project.
  - `ANON_PUBLIC`, `SERVICE_ROLE` (Not directly used here but may be relevant elsewhere).
- **Python Environment:** Your Django development environment (`apps/api/env`) should be active.
- **Database Configuration:** Verify that `apps/api/backend/settings.py` has the `DATABASES['default']` setting configured to use `django.db.backends.postgresql` and correctly reads the `DB_*` environment variables from `.env`.

## 2. Install Dependencies

We need `PyJWT` to decode and verify tokens and `cryptography` which is often a dependency for JWT algorithms.

```bash
# Ensure your virtual environment (e.g., ./env/bin/activate) is active
pip install PyJWT cryptography requests
```

- **Action:** Add `PyJWT`, `cryptography`, and `requests` (if not already present) with their versions to the `apps/api/requirements.txt` file.

## 3. Shared Database Implications (Important!)

Since Django is using the same Postgres database instance as Supabase, be aware of the following:

- **Migrations:**
  - Use Django's migration system (`python manage.py makemigrations api`, `python manage.py migrate`) to create and update the tables defined in `apps/api/api/models.py` (e.g., `resumes`, `work_experiences`).
  - **Do NOT** use the Supabase dashboard GUI or direct SQL commands to modify the schema of tables managed by Django migrations. This _will_ cause conflicts.
  - Ensure your Django models use explicit `Meta.db_table = "your_table_name"` to avoid potential naming collisions, especially within the `public` schema.
- **Row Level Security (RLS):**
  - Supabase relies heavily on RLS policies (e.g., `auth.uid() = user_id`) for fine-grained data access control, especially for tables managed directly through Supabase APIs or libraries.
  - Django's ORM **does not** automatically interact with or enforce these database-level RLS policies.
  - **Recommended Approach (Permissions Bypass):** Configure the `DB_USER` in `settings.py` to connect as a Postgres role that **bypasses RLS** (like the default `postgres` user, or a custom role granted `BYPASSRLS`).
  - **Security Implication:** With this approach, data security for tables managed by Django (like `resumes`) **depends entirely on the application-level permissions enforced within your Django REST Framework code** (e.g., the `IsOwner` permission checking `object.user_id == request.user.supabase_id`). A bug or omission in your DRF permissions could potentially expose data that would otherwise be protected by RLS if accessed via Supabase directly.
  - **Advanced Approach (RLS Passthrough):** Making Django respect RLS requires complex custom middleware or connection handling to set session variables like `request.jwt.claims.sub` for each request. This is not covered here and adds significant complexity.

## 4. Create Custom Authentication Backend

This class will handle the logic of extracting the token, verifying it using the `JWT_SECRET`, and associating it with a Django user representation.

- **Action:** Create a new file: `apps/api/api/authentication.py`
- **Action:** Add the following code:

```python
# apps/api/api/authentication.py
import jwt
import uuid
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User # Using Django's default User for simplicity
from django.core.exceptions import ValidationError
import logging # Optional: for better logging

logger = logging.getLogger(__name__)

class SupabaseAuthenticationBackend(BaseBackend):
    """
    Custom Django authentication backend to validate Supabase JWTs.
    """
    def authenticate(self, request, token=None):
        """
        Authenticates a request by validating a Supabase JWT.

        Args:
            request: The HttpRequest object.
            token (str, optional): The JWT token. If None, attempts to extract
                                     from the 'Authorization: Bearer <token>' header.

        Returns:
            A Django User object if authentication is successful, None otherwise.
        """
        if token is None:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.debug("No Bearer token found in Authorization header.")
                return None # No token provided or incorrect format
            token = auth_header.split(' ')[1]

        if not settings.JWT_SECRET:
             logger.error("CRITICAL: JWT_SECRET not configured in Django settings. Cannot verify Supabase token.")
             return None # Cannot verify without secret

        try:
            # Decode the token using the secret from Django settings
            # We expect the HS256 algorithm as standard for Supabase secrets.
            # Supabase typically uses 'authenticated' as the audience ('aud') for logged-in users.
            # Set verify_aud=False if you haven't explicitly added your Django API
            # as an audience in Supabase token settings, otherwise it might fail.
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=["HS256"],
                audience='authenticated', # Default Supabase audience for users
                options={"verify_aud": False} # Adjust if necessary based on Supabase config
            )

            # --- User Mapping ---
            # Extract the Supabase user ID (subject claim)
            user_id_str = payload.get('sub')
            if not user_id_str:
                 raise jwt.InvalidTokenError("JWT payload missing 'sub' (subject) claim.")

            try:
                # Convert Supabase user ID string to UUID
                supabase_user_id = uuid.UUID(user_id_str)
            except ValueError:
                raise jwt.InvalidTokenError(f"Invalid UUID format in 'sub' claim: {user_id_str}")

            # Get or create a minimal Django User associated with the Supabase ID.
            # We use the Supabase UUID as the username for uniqueness in Django's User model.
            # This avoids needing a separate 'Profile' model just for the Supabase ID initially.
            user, created = User.objects.get_or_create(
                username=str(supabase_user_id), # Store Supabase UUID as Django username
                defaults={
                    'email': payload.get('email', ''),
                    'is_active': True,
                    # Set unusable password as Supabase handles actual auth
                    'password': User.objects.make_random_password()
                 }
            )

            if created:
                logger.info(f"Created new Django user for Supabase ID: {supabase_user_id}")
            # Optionally update email if it changed in Supabase since last login
            elif payload.get('email') and user.email != payload.get('email'):
               user.email = payload.get('email')
               user.save(update_fields=['email'])

            # --- IMPORTANT: Attach Supabase ID to the User object ---
            # This makes the original Supabase UUID easily accessible in views/permissions
            # without needing to parse the username string again.
            user.supabase_id = supabase_user_id

            logger.debug(f"Successfully authenticated Supabase user: {supabase_user_id}")
            return user # Authentication successful

        except jwt.ExpiredSignatureError:
            logger.warning("Authentication failed: Supabase token has expired.")
            return None # Token is valid but expired
        except jwt.InvalidTokenError as e:
            logger.warning(f"Authentication failed: Invalid Supabase token: {e}")
            return None # Token is invalid (bad signature, missing claims, etc.)
        except Exception as e:
             # Catch unexpected errors during validation
             logger.error(f"An unexpected error occurred during JWT authentication: {e}", exc_info=True)
             return None

        return None # Default fail case


    def get_user(self, user_id):
         """
         Required by Django's auth system. Given a Django User PK (user_id),
         it should return the User object.
         """
         try:
             user = User.objects.get(pk=user_id)
             # Try to fetch supabase_id if possible (might not be set if user never logged in via JWT)
             try:
                user.supabase_id = uuid.UUID(user.username)
             except ValueError:
                user.supabase_id = None # Username isn't a valid UUID
             return user
         except User.DoesNotExist:
             return None

```

- **Explanation:**
  - It inherits from `BaseBackend`.
  - The `authenticate` method checks the `Authorization` header, decodes the JWT using the `JWT_SECRET` from `settings.py`, and validates standard claims like expiry and audience.
  - It extracts the Supabase user ID from the `sub` claim.
  - It uses `User.objects.get_or_create` to find or create a corresponding _Django_ `User` record, using the Supabase UUID as the Django `username` to ensure uniqueness. This keeps the Django user representation simple.
  - **Crucially**, it attaches the actual `uuid.UUID` object from Supabase to the Django `user` object as `user.supabase_id` for easy use in views.
  - It handles common JWT errors (`ExpiredSignatureError`, `InvalidTokenError`).
  - The `get_user` method is required by Django but is less critical for pure token-based auth.

## 5. Update Django Settings

Configure Django and DRF to use the new authentication backend.

- **Action:** Edit `apps/api/backend/settings.py`

```python
# apps/api/backend/settings.py

# ... near the top ...
import os # Make sure os is imported
import logging.config # Add for logging config (optional but good)

# ... existing settings ...

# --- Authentication Backends ---
# Replace or augment the default Django ModelBackend
AUTHENTICATION_BACKENDS = [
    'api.authentication.SupabaseAuthenticationBackend', # Our custom backend
    # Keep ModelBackend if you still need Django admin login via username/password
    # 'django.contrib.auth.backends.ModelBackend',
]

# --- REST Framework Settings ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Tells DRF to look for tokens and use AUTHENTICATION_BACKENDS
        'rest_framework.authentication.TokenAuthentication',
        # Add SessionAuthentication if you kept ModelBackend for the admin panel
        # 'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # Default to requiring authentication for all API endpoints
        'rest_framework.permissions.IsAuthenticated',
    ]
}

# --- JWT Secret ---
# Ensure the JWT_SECRET is loaded correctly from .env
JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    # In production, you might want to raise an ImproperlyConfigured error
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("WARNING: SUPABASE JWT_SECRET environment variable is not set!")
    print("JWT Authentication will NOT work.")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")


# --- Logging Configuration (Optional but Recommended) ---
# Add basic logging to see auth backend messages
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO', # Set to DEBUG for more verbose output during development
    },
    'loggers': {
        'api.authentication': { # Target our specific backend logger
            'handlers': ['console'],
            'level': 'DEBUG', # Show DEBUG messages from the auth backend
            'propagate': False,
        },
         'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}


# ... rest of settings.py ...
```

- **Explanation:**
  - `AUTHENTICATION_BACKENDS`: Tells Django to use our `SupabaseAuthenticationBackend`.
  - `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`: Configures DRF to use `TokenAuthentication`. When DRF tries to authenticate a request (`request.user`), `TokenAuthentication` will iterate through the `AUTHENTICATION_BACKENDS` and call their `authenticate` methods.
  - `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']`: Sets `IsAuthenticated` as the default, meaning users must provide a valid token to access endpoints unless explicitly allowed otherwise.
  - `JWT_SECRET` Loading: Added an explicit check and warning if the secret is missing.
  - Logging: Basic logging setup to help debug authentication issues.

## 6. Update Views and Permissions

Modify your DRF ViewSets (`api/views.py`) to use the authenticated user's Supabase ID for data filtering and ownership.

- **Action:** Create a new file for custom permissions: `apps/api/api/permissions.py` (optional but good practice)
- **Action:** Add the following code:

```python
# apps/api/api/permissions.py
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)

class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to view/edit it.
    Assumes:
        - The request user has been authenticated by SupabaseAuthenticationBackend.
        - The user object has a `supabase_id` attribute (UUID).
        - The data model instance (`obj`) has a `user_id` field (UUID)
          that should match the `request.user.supabase_id`.
    """
    message = "You do not have permission to access or modify this resource."

    def has_object_permission(self, request, view, obj):
        # Check if the user object from the authenticator has the supabase_id
        user_supabase_id = getattr(request.user, 'supabase_id', None)
        if not user_supabase_id:
            logger.warning(f"Permission check failed: Authenticated user (Django ID: {request.user.pk}) missing 'supabase_id' attribute.")
            return False

        # Check if the object instance has a 'user_id' field
        object_user_id = getattr(obj, 'user_id', None)
        if not object_user_id:
             # Log an error because the model is missing the expected field for ownership check
             logger.error(f"Permission check failed: Object {type(obj).__name__} (ID: {obj.pk}) is missing the 'user_id' field needed for ownership check.")
             return False # Or maybe True/False depending on desired default behaviour

        # Compare the user's Supabase ID with the object's user_id
        is_owner = (user_supabase_id == object_user_id)
        if not is_owner:
             logger.debug(f"Permission denied: User {user_supabase_id} is not owner of object {type(obj).__name__} (ID: {obj.pk}, Owner: {object_user_id}).")

        return is_owner
```

- **Action:** Edit `apps/api/api/views.py`

```python
# apps/api/api/views.py
from rest_framework import viewsets, permissions, serializers # Make sure serializers is imported if raising ValidationErrors
from .models import Resume # Import other models as needed
from .serializers import ResumeSerializer # Import other serializers
from .permissions import IsOwner # Import the custom permission
from rest_framework.decorators import action # If using custom actions
from rest_framework.response import Response # If using custom actions
import logging # Optional: for logging

logger = logging.getLogger(__name__)

# --- Apply Permissions to ViewSets ---

class ResumeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows resumes to be viewed or edited.
    Requires authentication and ownership.
    """
    serializer_class = ResumeSerializer
    # Apply IsAuthenticated (from DRF defaults) AND our custom IsOwner permission
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        """
        This view should return a list of all the resumes
        for the currently authenticated Supabase user.
        """
        user = self.request.user
        user_supabase_id = getattr(user, 'supabase_id', None)

        if not user_supabase_id:
             # This should technically not be reached if IsAuthenticated works correctly,
             # but it's a safe fallback.
             logger.warning(f"ResumeViewSet: Could not find supabase_id for authenticated user (Django ID: {user.pk}). Returning empty queryset.")
             return Resume.objects.none()

        # Filter resumes based on the user_id field matching the user's Supabase ID
        logger.debug(f"ResumeViewSet: Fetching resumes for Supabase user ID: {user_supabase_id}")
        return Resume.objects.filter(user_id=user_supabase_id)

    def perform_create(self, serializer):
        """
        Associate the new resume with the currently authenticated Supabase user.
        """
        user = self.request.user
        user_supabase_id = getattr(user, 'supabase_id', None)

        if not user_supabase_id:
             # Raise a validation error if we can't associate the resume with a user
             logger.error(f"ResumeViewSet: Cannot create resume. No supabase_id found for authenticated user (Django ID: {user.pk}).")
             raise serializers.ValidationError("Could not identify the user to associate the resume with. Authentication may have failed.")

        # Save the instance, automatically setting the user_id field
        # to the authenticated user's Supabase ID.
        logger.info(f"ResumeViewSet: Creating resume for Supabase user ID: {user_supabase_id}")
        serializer.save(user_id=user_supabase_id)

# --- Apply similarly to other ViewSets (WorkExperience, Education, etc.) ---
# Make sure their models also have a 'user_id' field if they are directly owned,
# or rely on the permission check cascading from the parent Resume if accessed via nested routes.
# If accessed directly (e.g., /api/work-experiences/<id>), they need their own ownership check.

# Example for a related model (adjust model name and serializer)
# class WorkExperienceViewSet(viewsets.ModelViewSet):
#     serializer_class = WorkExperienceSerializer
#     permission_classes = [permissions.IsAuthenticated, IsOwner] # Reuse IsOwner if WorkExperience has user_id
#
#     def get_queryset(self):
#         user = self.request.user
#         user_supabase_id = getattr(user, 'supabase_id', None)
#         if not user_supabase_id:
#             return WorkExperience.objects.none()
#         # If WorkExperience has a direct user_id:
#         # return WorkExperience.objects.filter(user_id=user_supabase_id)
#         # If ownership is determined via the Resume:
#         return WorkExperience.objects.filter(resume__user_id=user_supabase_id)
#
#     def perform_create(self, serializer):
#         # You might need to get the resume_id from the request data
#         # and ensure the user owns that resume before saving the work experience.
#         user_supabase_id = getattr(self.request.user, 'supabase_id', None)
#         resume_id = serializer.validated_data.get('resume').id # Assuming resume is passed/validated
#         if not user_supabase_id:
#              raise serializers.ValidationError("Authentication required.")
#         try:
#             # Check user owns the target resume
#             resume = Resume.objects.get(pk=resume_id, user_id=user_supabase_id)
#             serializer.save(resume=resume) # Pass the validated resume instance
#         except Resume.DoesNotExist:
#             raise serializers.ValidationError("You do not have permission to add work experience to this resume.")


# --- Update Function-Based Views (if any) ---
# If you have plain function-based views using @api_view,
# ensure they also check request.user and request.user.supabase_id.

# Example (adapt imports and logic):
# from rest_framework.decorators import api_view, permission_classes
#
# @api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated]) # Basic auth check
# def parse_resume(request):
#     user_supabase_id = getattr(request.user, 'supabase_id', None)
#     if not user_supabase_id:
#         return Response({"error": "Authentication failed."}, status=401)
#
#     # Proceed with parsing logic, potentially associating results with user_supabase_id
#     # ... your parsing logic ...
#     logger.info(f"parse_resume called by Supabase user: {user_supabase_id}")
#     return Response({"message": "Parsed successfully (logic TBC)"})


```

- **Explanation:**
  - `IsOwner` Permission: Checks if `request.user.supabase_id` matches the `user_id` field on the model instance being accessed. This ensures users can only modify/view their own data.
  - `permission_classes`: Added `IsOwner` to the ViewSets alongside the default `IsAuthenticated`.
  - `get_queryset`: Filters the list of objects to only include those where `object.user_id == request.user.supabase_id`.
  - `perform_create`: Automatically sets the `user_id` field of the newly created object to `request.user.supabase_id` when saving.
  - Related Models: Added comments on how to handle permissions and creation for related models like `WorkExperience` (checking ownership of the parent `Resume`).
  - Function Views: Added comments on how to adapt function-based views.

## 7. Database Considerations (Recap)

- We are using **Option 2 (Shared Supabase Database)**.
- Django (`apps/api`) connects directly to the Supabase Postgres instance using connection details from `.env`.
- Django uses its migration system to manage its application tables (e.g., `resumes`, `work_experiences`) within that shared database.
- Data security for Django-managed tables relies **primarily on DRF permissions (`IsOwner`)**, as Django likely connects as a user bypassing RLS.
- The `user_id` field in Django models (e.g., `Resume.user_id`) links records to the Supabase user UUID obtained from the validated JWT.

## 8. Testing and Verification

1.  **Run Django Server:** `python manage.py runserver`
2.  **Use Frontend or API Client (e.g., Postman, Insomnia):**
    - **Without Token:** Make a request to a protected endpoint (e.g., `GET /api/resumes/`). You should receive a `401 Unauthorized` or `403 Forbidden` error.
    - **With Invalid/Expired Token:** Send a request with a bad token in the `Authorization: Bearer <bad_token>` header. You should receive a `401/403` error. Check the Django console logs for "Invalid Supabase token" or "ExpiredSignatureError" messages (if logging level is DEBUG).
    - **With Valid Token:**
      - Log in via the `apps/mcg` frontend to get a valid Supabase JWT.
      - Copy this token.
      - Make a `GET /api/resumes/` request with the valid `Authorization: Bearer <valid_token>` header. You should receive a `200 OK` with a list of resumes belonging _only_ to that user (likely an empty list initially).
      - Try `POST /api/resumes/` with valid data and the token. It should create a resume linked to the correct `user_id`. Check the response and the database.
      - Try accessing a resume belonging to _another_ user (if you can create one) using the first user's token. You should receive a `403 Forbidden` or `404 Not Found` due to the `IsOwner` permission.

## 9. Key Concepts Recap

- **JWT (JSON Web Token):** A standard for securely transmitting information between parties as a JSON object. Supabase issues these upon login.
- **Stateless Authentication:** The Django backend doesn't store session state for users. It relies solely on the validity of the token sent with each request.
- **Django Authentication Backend:** A pluggable system in Django for verifying credentials. We created a custom one for Supabase JWTs.
- **DRF `TokenAuthentication`:** A DRF class that triggers the configured `AUTHENTICATION_BACKENDS`.
- **DRF Permissions:** Classes (`IsAuthenticated`, `IsOwner`) that run after authentication to authorize the specific request.
- **`request.user`:** After successful authentication by our backend, DRF populates `request.user` with the Django `User` object returned by the `authenticate` method. We added the `supabase_id` attribute to this object for convenience.

Good luck! Let me know if any steps are unclear.
