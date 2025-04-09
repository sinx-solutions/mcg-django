# test_saved_cover_letter_crud.py
#!/usr/bin/env python3
"""
Test script for SavedCoverLetter API CRUD endpoints (/api/saved-cover-letters/).
"""
import requests
import json
import sys
import os
import uuid
from pprint import pprint
from dotenv import load_dotenv
import time

# --- Setup ---
print("--- SavedCoverLetter CRUD Test Setup ---")
dotenv_path = os.path.join(os.path.dirname(__file__), 'api', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Get JWT from environment
SUPABASE_TEST_TOKEN = os.getenv('SAMPLE_JWT')
if not SUPABASE_TEST_TOKEN:
    print(f"ERROR: SAMPLE_JWT not found in {dotenv_path}")
    sys.exit(1)

# Base URL of the API
BASE_URL = "http://127.0.0.1:8000/api" # Adjust if needed

# Prepare headers
headers_json = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
}

# --- Helper: Generate a Cover Letter to get an ID ---

def generate_letter_for_test(resume_id):
    """Calls generate-cover-letter to get a saved letter ID."""
    print("\n--- Generating a cover letter for testing CRUD ---")
    payload = {
        "resume_id": resume_id,
        "job_title": f"CRUD Test Job {uuid.uuid4()}",
        "company_name": "CRUD Test Company",
        "job_description": "Testing CRUD operations for saved cover letters."
    }
    try:
        response = requests.post(
            f"{BASE_URL}/generate-cover-letter/",
            json=payload,
            headers=headers_json,
            timeout=120
        )
        response.raise_for_status()
        response_data = response.json()
        saved_id = response_data.get("saved_cover_letter_id")
        if not saved_id:
            raise ValueError("Failed to get saved_cover_letter_id from generation response.")
        print(f"Successfully generated and saved cover letter: {saved_id}")
        return saved_id
    except Exception as e:
        print(f"ERROR generating cover letter for test: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
        return None

# --- Helper: Create a temporary resume ---
# (Slightly simplified version)
def create_test_resume():
    print("\n--- Creating temporary resume ---")
    resume_payload = {"title": f"Temp Resume for CL CRUD - {uuid.uuid4()}", "skills": [], "section_order": []}
    try:
        response = requests.post(f"{BASE_URL}/resumes/", json=resume_payload, headers=headers_json, timeout=10)
        response.raise_for_status()
        return response.json().get('id')
    except Exception as e:
        print(f"ERROR creating temporary resume: {e}")
        return None

# --- Helper: Delete temporary resume ---
def delete_test_resume(resume_id):
    if not resume_id: return
    print(f"\n--- Deleting temporary resume {resume_id} ---")
    try:
        requests.delete(f"{BASE_URL}/resumes/{resume_id}/", headers=headers_json, timeout=10).raise_for_status()
        print("Temporary resume deleted.")
    except Exception as e:
        print(f"ERROR deleting temporary resume {resume_id}: {e}")

# --- Test Function ---

def test_saved_cover_letter_crud(resume_id_for_gen):
    """Tests CRUD operations on the SavedCoverLetter endpoint."""
    saved_letter_id = None
    endpoint_path = "/saved-cover-letters/"

    try:
        # 1. Generate/Create a letter to work with
        saved_letter_id = generate_letter_for_test(resume_id_for_gen)
        if not saved_letter_id:
            raise Exception("Prerequisite failed: Could not generate initial cover letter.")

        time.sleep(1)

        # 2. Read (GET)
        print(f"\n--- Testing GET {endpoint_path}{saved_letter_id}/ ---")
        response_get = requests.get(f"{BASE_URL}{endpoint_path}{saved_letter_id}/", headers=headers_json, timeout=10)
        response_get.raise_for_status()
        retrieved_data = response_get.json()
        print(f"GET Status Code: {response_get.status_code}")
        pprint(retrieved_data)
        assert retrieved_data.get('id') == saved_letter_id
        assert "Testing CRUD operations" in retrieved_data.get('cover_letter', '')

        time.sleep(1)

        # 3. Update (PATCH)
        print(f"\n--- Testing PATCH {endpoint_path}{saved_letter_id}/ ---")
        update_payload = {
            "job_title": "Updated CRUD Job Title",
            "cover_letter": "This cover letter text has been updated via PATCH."
        }
        try:
            response_patch = requests.patch(f"{BASE_URL}{endpoint_path}{saved_letter_id}/", json=update_payload, headers=headers_json, timeout=10)
            print(f"PATCH Raw Status Code: {response_patch.status_code}")
            response_patch.raise_for_status()
            updated_data = response_patch.json()
            print(f"PATCH Status Code (after raise): {response_patch.status_code}")
            pprint(updated_data)
            assert updated_data.get('job_title') == "Updated CRUD Job Title"
            assert "updated via PATCH" in updated_data.get('cover_letter', '')
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP ERROR during PATCH: {http_err}")
            print("Response Body:")
            try: pprint(http_err.response.json())
            except: print(http_err.response.text)
            raise
        except Exception as patch_err:
            print(f"UNEXPECTED ERROR during PATCH: {patch_err}")
            raise

        time.sleep(1)

        # 4. Delete (DELETE)
        print(f"\n--- Testing DELETE {endpoint_path}{saved_letter_id}/ ---")
        response_delete = requests.delete(f"{BASE_URL}{endpoint_path}{saved_letter_id}/", headers=headers_json, timeout=10)
        response_delete.raise_for_status()
        print(f"DELETE Status Code: {response_delete.status_code}")
        assert response_delete.status_code == 204

        time.sleep(1)

        # 5. Verify Deletion (GET again)
        print(f"\n--- Verifying DELETE {endpoint_path}{saved_letter_id}/ ---")
        response_get_after = requests.get(f"{BASE_URL}{endpoint_path}{saved_letter_id}/", headers=headers_json, timeout=10)
        print(f"GET after DELETE Status Code: {response_get_after.status_code}")
        assert response_get_after.status_code == 404

        return True # Indicate overall success

    except Exception as e:
        print(f"\n!!!!!! ERROR during SavedCoverLetter CRUD test: {e} !!!!!!")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
        # No need to delete the cover letter if test failed, it might not exist
        return False


# --- Main Execution ---
if __name__ == "__main__":
    print("\n--- Starting SavedCoverLetter CRUD Test ---")
    # Create a temporary resume to generate the initial letter against
    temp_resume_id = create_test_resume()
    final_success = False

    if temp_resume_id:
        try:
            # Run the CRUD test using the temp resume ID
            final_success = test_saved_cover_letter_crud(temp_resume_id)
        finally:
            # Always try to clean up the temp resume
            delete_test_resume(temp_resume_id)
    else:
        print("Could not create temporary resume, aborting test.")

    print("\n--- Test Finished ---")
    if final_success:
        print("Result: SUCCESS")
    else:
        print("Result: FAILED")
        sys.exit(1) 