# PRD: Supabase Authentication Integration for Django API

**Version:** 1.0
**Date:** 2023-04-04

## 1. Introduction & Goal

**Problem:** Our application currently consists of a Next.js frontend (`apps/mcg`) and a new Django backend (`apps/api`). The frontend handles user authentication (sign-up, login, session management) using Supabase Auth. The Django backend, which manages core application logic like resume building, currently lacks authentication and cannot securely identify which user is making API requests.

**Goal:** Integrate the existing Supabase authentication flow with the Django backend (`apps/api`) so that API endpoints are protected and can securely identify the authenticated user based on credentials issued by Supabase.

## 2. Proposed Solution Overview

We will leverage Supabase as the **single source of truth for user identity and authentication**.

1.  **Frontend Responsibility:** The Next.js frontend (`apps/mcg`) will continue to handle all user interactions for login, sign-up, password reset, etc., using Supabase. Upon successful authentication, the frontend receives a JSON Web Token (JWT) from Supabase.
2.  **Token Transmission:** The frontend will send this Supabase JWT with every API request it makes to the Django backend (`apps/api`) in the `Authorization: Bearer <token>` header.
3.  **Backend Responsibility (Django - `apps/api`):**
    - The Django backend will **verify** the incoming JWT using a shared secret key obtained from Supabase environment variables. It will **not** handle login/signup forms or password management itself.
    - A custom Django Authentication Backend will be implemented to decode the JWT and identify the Supabase user ID (`sub` claim).
    - Django REST Framework (DRF) views will use this verified user identity to authorize requests and filter data, ensuring users can only access their own resources (e.g., their own resumes).
4.  **Database Strategy (Option 2 - Shared Supabase Database):**
    - The Django application (`apps/api`) **connects directly to the same Supabase Postgres database** used by Supabase Auth.
    - Django manages the schema (via migrations) for its application-specific tables (e.g., `Resumes`, `WorkExperiences` defined in `api/models.py`) within this shared database, likely in the `public` schema.
    - A `user_id` (UUID) field in the Django models (like `Resume.user_id`) stores the corresponding Supabase User ID (from the JWT `sub` claim) to link Django data to the authenticated user.
    - **Important Security Note:** Since Django connects directly (likely as a privileged user bypassing Row Level Security), data access control for Django-managed tables relies **primarily on application-level permissions** implemented in Django REST Framework (e.g., ensuring users can only query/modify their own data).

## 3. Key Requirements

- All DRF API endpoints in `apps/api` (except potentially public ones, though none are defined yet) must require a valid Supabase JWT for access.
- The Django application must be able to securely extract the Supabase User ID (UUID) from the validated JWT.
- API views (e.g., `ResumeViewSet`) must filter data based on the extracted Supabase User ID, ensuring data ownership and privacy.
- The solution must use the `JWT_SECRET` provided via environment variables (`apps/api/.env`) for JWT validation.
- The implementation should follow DRF best practices for authentication and permissions.

## 4. Non-Goals

- Implementing login/signup/password reset UI or logic within Django. This remains the frontend's responsibility using Supabase.
- ~~Migrating existing Django data models _into_ the Supabase database instance (we are keeping databases separate).~~ (This is now the strategy)
- Replacing Supabase Auth entirely with Django's built-in authentication.
- Implementing RLS enforcement _directly_ within Django's ORM calls (relying on DRF permissions for now).
- Implementing complex role-based access control (RBAC) beyond basic ownership checks (this can be a future enhancement).

## 5. Current Setup Context

- **`apps/mcg` (Frontend):** Next.js 14+, React, TypeScript. Uses `@supabase/ssr` library for client-side and server-side Supabase interactions. Handles login/signup and obtains JWTs.
- **`apps/api` (Backend):** Django 5+, Django REST Framework. Contains models for resumes, work experiences, etc. (see `api/models.py`). **Connects to the shared Supabase Postgres database** for its data storage. Lacks specific authentication checks on its API endpoints (`api/views.py`, `api/urls.py`). Reads Supabase credentials (JWT secret, DB connection details) from `.env`.

## 6. Key Files for Understanding

To fully grasp the current setup and the integration task, review the following files:

**A. `apps/mcg` (Next.js Frontend & Supabase Client Logic):**

- **Goal:** Understand how Supabase authentication is currently handled on the frontend (login/signup UI, session management, token handling).
- `src/app/(auth)/login/page.tsx` & `src/app/(auth)/login/LoginForm.tsx`: Example login page structure (server component loading a client component form).
- `src/app/(auth)/login/actions.ts`: Example server action handling the call to Supabase's `signInWithPassword`. Similar patterns exist for signup.
- `src/utils/supabase/client.ts`: Utility for creating the Supabase client instance in browser components.
- `src/utils/supabase/server.ts`: Utility for creating the Supabase client instance in server components/actions.
- `src/utils/supabase/middleware.ts` & `src/middleware.ts`: How Supabase sessions are refreshed using middleware and SSR utilities.
- **Any component making API calls to `apps/api`:** Understand how `fetch` or other libraries are used. _These will need modification to add the `Authorization: Bearer <token>` header._ You'll need to figure out how to access the Supabase session/token within these components (likely via the Supabase client instance).

**B. `apps/api` (Django Backend & Authentication Integration):**

- **Goal:** Understand the Django project structure, existing models/views, and where/how the Supabase JWT authentication is being added.
- `backend/settings.py`: Crucial for understanding installed apps, middleware, database configuration (`DATABASES`), REST framework settings (`REST_FRAMEWORK`), and where the `JWT_SECRET` and `AUTHENTICATION_BACKENDS` are configured.
- `api/models.py`: Defines the data structures Django manages (Resumes, etc.) and the important `user_id` field that links to Supabase users.
- `api/urls.py` & `backend/urls.py`: How API routes are defined and structured.
- `api/views.py`: Contains the DRF ViewSets. Understand how `get_queryset` and `perform_create` work _before_ the changes, and how they need to be modified to use `request.user.supabase_id` for filtering/saving.
- `api/serializers.py`: How data is serialized/deserialized for the API.
- **`api/authentication.py` (New File):** The core implementation of the custom authentication backend (`SupabaseAuthenticationBackend`) that validates the JWT.
- **`api/permissions.py` (New File/Concept):** Implementation of the `IsOwner` permission class used to enforce data access rules at the DRF level.
- `.env`: Where the `JWT_SECRET` and database connection details are stored.
- `requirements.txt`: Lists Python dependencies, including `Django`, `djangorestframework`, and the newly added `PyJWT`.

By reviewing these files, you'll understand how the frontend gets the JWT, how the backend needs to verify it, and how to connect the verified user identity to the data within the Django application.

## 7. Development & Verification Steps

Follow these steps to implement and test the integration:

1.  **Setup:** Ensure you have both the `mcg` and `api` projects checked out and their respective dependencies installed (`npm install` or `yarn install` for `mcg`, `pip install -r requirements.txt` for `api`).
2.  **Run Backend (`api`):**
    - Navigate to the `apps/api` directory.
    - Activate the Python virtual environment (e.g., `source env/bin/activate`).
    - Start the Django development server:
      ```bash
      python manage.py runserver
      ```
    - Keep this terminal running. Monitor its logs for authentication messages (especially if DEBUG level logging is enabled in `settings.py`) and request errors.
3.  **Run Frontend (`mcg`):**
    - Navigate to the `apps/mcg` directory.
    - Start the Next.js development server (confirm the exact command in `package.json` if needed):
      ```bash
      npm run dev
      ```
      _(Note: If you use Yarn, the command might be `yarn dev`)_
    - Keep this terminal running.
4.  **Implement Backend Changes:** Implement the authentication backend (`api/authentication.py`), permissions (`api/permissions.py`), and update `settings.py` and `views.py` in the `api` project as described in the technical guide (`DJANGO_SUPABASE_AUTH_GUIDE.md`). Restart the Django server after making changes.
5.  **Implement Frontend Changes:** Modify the code in `mcg` where API calls are made to the Django backend (`/api/...`). Ensure these calls include the `Authorization: Bearer <supabase_jwt>` header. You will need to access the user's current Supabase session/token (using the Supabase client library) to get the JWT.
6.  **Iterative Testing & Debugging:**
    - **Use the Frontend:** Log in through the `mcg` application. Navigate to pages that trigger API calls to the Django backend.
    - **Check Browser DevTools:** Look at the Network tab to confirm the `Authorization` header is being sent correctly with requests to `/api/...`.
    - **Check Django Logs:** Monitor the `api` server's console for successful authentication messages or JWT validation errors from the `SupabaseAuthenticationBackend`. Check for permission errors from `IsOwner`.
    - **Use API Tools (Postman/Insomnia):** For more direct testing, manually get a valid JWT from the frontend's local storage/cookies after logging in. Use this token in Postman/Insomnia to send requests directly to `http://127.0.0.1:8000/api/...`:
      - Test without the token (expect 401/403).
      - Test with an invalid/expired token (expect 401/403).
      - Test with a valid token (expect 200 OK for reads, successful creates/updates).
      - Test accessing another user's data (expect 403/404).
    - **Add Logging:** Add `print()` statements or use Python's `logging` module liberally in the Django backend (authentication backend, views, permissions) to trace the execution flow and inspect variables (like the token, payload, user IDs) during testing.
    - **Iterate:** Based on errors or unexpected behavior, debug the relevant code in `mcg` or `api`, restart the necessary server, and re-test.
