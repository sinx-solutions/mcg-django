#!/usr/bin/env python3
"""
Script to generate a mock Supabase JWT token for testing.
This creates a token with the same structure as Supabase but is NOT properly signed.
It's only for testing the flow, not for security.
"""
import jwt
import uuid
import time
import json
from datetime import datetime, timedelta

# Generate a random user ID
user_id = str(uuid.uuid4())

# Create the payload structure similar to Supabase tokens
payload = {
    # Standard JWT claims
    "aud": "authenticated",
    "iat": int(time.time()),
    "exp": int((datetime.now() + timedelta(hours=24)).timestamp()),
    
    # Supabase specific claims
    "sub": user_id,  # This is what we use as the user ID
    "email": "test@example.com",
    "app_metadata": {
        "provider": "email"
    },
    "user_metadata": {
        "name": "Test User"
    },
    "role": "authenticated"
}

# Generate a mock secret (in production this would be from Supabase)
mock_secret = "mock_secret_key_for_testing_only"

# Create the token (not securely signed, just for testing)
token = jwt.encode(payload, mock_secret, algorithm="HS256")

print("\n=== Mock Supabase Token for Testing ===")
print(f"User ID: {user_id}")
print(f"\nAuthorization Header:")
print(f"Authorization: Bearer {token}")
print("\nDecoded Token Payload:")
print(json.dumps(payload, indent=2))
print("\n=== Copy the Authorization header for testing ===\n") 