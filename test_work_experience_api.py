#!/usr/bin/env python3
"""
Test script for WorkExperience API endpoints.
Tests direct CRUD operations on /api/work-experiences/.
"""
import requests
import json
import uuid
from pprint import pprint
import os
from dotenv import load_dotenv
import time

# Load environment variables from .env file in the api/ directory
# Assuming script is run from the project root (mcg-django/)
dotenv_path = os.path.join(os.path.dirname(__file__), 'api', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Use the token stored in the environment variable
SUPABASE_TEST_TOKEN = os.getenv('SAMPLE_JWT')
if not SUPABASE_TEST_TOKEN:
    print("ERROR: SAMPLE_JWT environment variable not found.")
    print(f"Please ensure SAMPLE_JWT is set in your .env file (looked in: {dotenv_path})")
    exit(1)

# Base URL of the API
BASE_URL = "http://localhost:8000/api" # Make sure Django server is running

# Required headers for API requests
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
}

# --- Helper Functions ---

def create_test_resume():
    """Creates a temporary resume for testing work experience linkage."""
    print("\n--- Creating temporary resume ---")
    resume_payload = {
        "title": f"Temp Resume for WorkExp Test - {uuid.uuid4()}",
        # Add minimal required fields if any, otherwise rely on defaults/nulls
        "skills": ["temp skill"], # Example if skills are required by serializer now
        "section_order": ["experience"] # Example
    }
    try:
        response = requests.post(
            f"{BASE_URL}/resumes/",
            json=resume_payload,
            headers=headers,
            timeout=10 # Add timeout
        )
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        created_resume = response.json()
        resume_id = created_resume.get('id')
        if not resume_id:
            print("ERROR: Failed to get ID from created resume response.")
            pprint(created_resume)
            return None
        print(f"Temporary Resume created with ID: {resume_id}")
        return resume_id
    except requests.exceptions.RequestException as e:
        print(f"ERROR creating temporary resume: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print("Response content:")
                pprint(e.response.json())
            except json.JSONDecodeError:
                print("Response content: (Not JSON)")
                print(e.response.text)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during resume creation: {e}")
        return None


def delete_test_resume(resume_id):
    """Deletes the temporary resume."""
    if not resume_id:
        return False
    print(f"\n--- Deleting temporary resume {resume_id} ---")
    try:
        response = requests.delete(
            f"{BASE_URL}/resumes/{resume_id}/",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        print(f"Delete Status Code: {response.status_code}")
        return response.status_code == 204
    except requests.exceptions.RequestException as e:
        print(f"ERROR deleting temporary resume {resume_id}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during resume deletion: {e}")
        return False

# --- Test Function ---

def test_work_experience_crud():
    """Tests CRUD operations on the WorkExperience endpoint."""
    resume_id = None # Ensure resume_id is defined in the outer scope
    try:
        # 1. Create a parent Resume
        resume_id = create_test_resume()
        if not resume_id:
            print("Halting test: Could not create parent resume.")
            return

        work_exp_id = None # Define work_exp_id here

        # 2. Create WorkExperience (POST)
        print("\n=== Testing POST /api/work-experiences/ ===")
        work_exp_payload = {
            "position": "Test Position",
            "company": "Test Company Inc.",
            "start_date": "2022-01-01T00:00:00Z", # Use ISO format for DateTimeField
            "description": "Did test things.",
            "resume": resume_id # Link to the parent resume
        }
        try:
            response_post = requests.post(
                f"{BASE_URL}/work-experiences/",
                json=work_exp_payload,
                headers=headers,
                timeout=10
            )
            response_post.raise_for_status()
            created_work_exp = response_post.json()
            work_exp_id = created_work_exp.get('id')
            print(f"POST Status Code: {response_post.status_code}")
            print(f"Created WorkExperience ID: {work_exp_id}")
            pprint(created_work_exp)
            assert work_exp_id is not None
            assert created_work_exp.get('position') == "Test Position"
        except requests.exceptions.RequestException as e:
            print(f"ERROR during WorkExperience POST: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 try:
                    pprint(e.response.json())
                 except json.JSONDecodeError:
                    print(e.response.text)
            return # Stop test if creation fails
        except Exception as e:
            print(f"An unexpected error occurred during WorkExperience POST: {e}")
            return

        # Add a small delay before the next request
        time.sleep(1)

        # 3. Read WorkExperience (GET)
        print(f"\n=== Testing GET /api/work-experiences/{work_exp_id}/ ===")
        try:
            response_get = requests.get(
                f"{BASE_URL}/work-experiences/{work_exp_id}/",
                headers=headers,
                timeout=10
            )
            response_get.raise_for_status()
            retrieved_work_exp = response_get.json()
            print(f"GET Status Code: {response_get.status_code}")
            pprint(retrieved_work_exp)
            assert retrieved_work_exp.get('id') == work_exp_id
            assert retrieved_work_exp.get('company') == "Test Company Inc."
        except requests.exceptions.RequestException as e:
            print(f"ERROR during WorkExperience GET: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 try:
                    pprint(e.response.json())
                 except json.JSONDecodeError:
                    print(e.response.text)
        except Exception as e:
            print(f"An unexpected error occurred during WorkExperience GET: {e}")


        # Add a small delay
        time.sleep(1)

        # 4. Update WorkExperience (PATCH)
        print(f"\n=== Testing PATCH /api/work-experiences/{work_exp_id}/ ===")
        update_payload = {
            "position": "Updated Test Position",
            "description": "Updated description."
        }
        try:
            response_patch = requests.patch(
                f"{BASE_URL}/work-experiences/{work_exp_id}/",
                json=update_payload,
                headers=headers,
                timeout=10
            )
            response_patch.raise_for_status()
            updated_work_exp = response_patch.json()
            print(f"PATCH Status Code: {response_patch.status_code}")
            pprint(updated_work_exp)
            assert updated_work_exp.get('position') == "Updated Test Position"
            assert updated_work_exp.get('description') == "Updated description."
        except requests.exceptions.RequestException as e:
            print(f"ERROR during WorkExperience PATCH: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 try:
                    pprint(e.response.json())
                 except json.JSONDecodeError:
                    print(e.response.text)
        except Exception as e:
            print(f"An unexpected error occurred during WorkExperience PATCH: {e}")

        # Add a small delay
        time.sleep(1)

        # 5. Delete WorkExperience (DELETE)
        print(f"\n=== Testing DELETE /api/work-experiences/{work_exp_id}/ ===")
        try:
            response_delete = requests.delete(
                f"{BASE_URL}/work-experiences/{work_exp_id}/",
                headers=headers,
                timeout=10
            )
            response_delete.raise_for_status()
            print(f"DELETE Status Code: {response_delete.status_code}")
            assert response_delete.status_code == 204
        except requests.exceptions.RequestException as e:
            print(f"ERROR during WorkExperience DELETE: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 try:
                    pprint(e.response.json())
                 except json.JSONDecodeError:
                    print(e.response.text)
        except Exception as e:
            print(f"An unexpected error occurred during WorkExperience DELETE: {e}")


        # 6. Verify Deletion (GET again)
        print(f"\n=== Verifying DELETE /api/work-experiences/{work_exp_id}/ ===")
        try:
            response_get_after_delete = requests.get(
                f"{BASE_URL}/work-experiences/{work_exp_id}/",
                headers=headers,
                timeout=10
            )
            print(f"GET after DELETE Status Code: {response_get_after_delete.status_code}")
            assert response_get_after_delete.status_code == 404
        except requests.exceptions.RequestException as e:
             print(f"ERROR during WorkExperience GET after DELETE: {e}")
             # A 404 might raise an exception depending on raise_for_status usage upstream
             # So check the status code if the exception object has a response
             if hasattr(e, 'response') and e.response is not None:
                 print(f"Status code was: {e.response.status_code}")
                 assert e.response.status_code == 404
             else:
                 raise # Re-raise if it's not a response-related error
        except Exception as e:
            print(f"An unexpected error occurred during WorkExperience GET after DELETE: {e}")


    finally:
        # 7. Clean up the parent Resume
        if resume_id:
            if delete_test_resume(resume_id):
                print("Temporary resume cleaned up successfully.")
            else:
                print("ERROR: Failed to cleanup temporary resume.")

# --- Main Execution ---
if __name__ == "__main__":
    print("Testing WorkExperience API Endpoints")
    print("====================================")
    # Ensure server is running before starting
    try:
        requests.get(f"{BASE_URL}/resumes/", headers=headers, timeout=2) # Quick check
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to Django server at {BASE_URL}. Is it running?")
        exit(1)
    except Exception as e:
         print(f"Warning: Pre-check failed, but continuing test: {e}")

    test_work_experience_crud() 