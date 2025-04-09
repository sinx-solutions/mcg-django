#!/usr/bin/env python3
"""
Simple script to test only the Supabase authentication mechanism.
"""
import requests
import json

# Use the token we generated earlier
SUPABASE_TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiaWF0IjoxNzQ0MjAyOTU1LCJleHAiOjE3NDQyODkzNTUsInN1YiI6IjI1NTJjMjI5LTQ5ZjctNDlhYS1iMTlkLWQ5NjdiYzJiM2I3OCIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIn0sInVzZXJfbWV0YWRhdGEiOnsibmFtZSI6IlRlc3QgVXNlciJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCJ9.tb_FAtx5CtLZQAo1GW8eRQxPVcWEqkH-G2D5QWakNJU"

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_auth_with_token():
    """Test authentication with the Supabase token"""
    print("\n=== Testing Authentication with Supabase Token ===")
    
    # Headers with the token
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
    }
    
    # Make a simple GET request to the resumes endpoint
    print("Making GET request to /api/resumes/ with token...")
    response = requests.get(f"{BASE_URL}/resumes/", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Authentication successful!")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print("Authentication failed.")
        print(f"Response: {response.text}")
    
    # Print the raw request and response with headers for debugging
    print("\n=== Raw Request and Response ===")
    # Get information about the request
    print(f"Request URL: {response.request.url}")
    print(f"Request Method: {response.request.method}")
    print(f"Request Headers: {response.request.headers}")
    
    # Get information about the response
    print(f"Response Status: {response.status_code} {response.reason}")
    print(f"Response Headers: {response.headers}")
    print(f"Response Content: {response.text[:200]}...")  # First 200 chars
    
def test_auth_with_invalid_token():
    """Test authentication with an invalid token"""
    print("\n=== Testing Authentication with Invalid Token ===")
    
    # Headers with an invalid token
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer invalid_token_here"
    }
    
    # Make a simple GET request to the resumes endpoint
    print("Making GET request to /api/resumes/ with invalid token...")
    response = requests.get(f"{BASE_URL}/resumes/", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

def test_auth_without_token():
    """Test authentication without a token"""
    print("\n=== Testing Authentication without Token ===")
    
    # Headers without the token
    headers = {
        "Content-Type": "application/json"
    }
    
    # Make a simple GET request to the resumes endpoint
    print("Making GET request to /api/resumes/ without token...")
    response = requests.get(f"{BASE_URL}/resumes/", headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    print("Testing Supabase Authentication")
    print("==============================")
    
    # Test authentication with the token
    test_auth_with_token()
    
    # Test authentication with an invalid token
    test_auth_with_invalid_token()
    
    # Test authentication without a token
    test_auth_without_token() 