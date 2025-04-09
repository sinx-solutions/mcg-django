# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.authentication.SupabaseAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Supabase settings (these would be configured properly in production)
SUPABASE_URL = 'https://your-supabase-project.supabase.co'
SUPABASE_JWT_SECRET = 'your-jwt-secret-would-be-here' 