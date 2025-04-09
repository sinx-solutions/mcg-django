# test_all_components.py
#!/usr/bin/env python3
"""
Test script for CRUD operations on all main resume component API endpoints.
Verifies Education, Project, Certification, CustomSection, CustomSectionItem.
"""
import requests
import json
import uuid
from pprint import pprint
import os
from dotenv import load_dotenv
import time

# --- Setup ---
print("--- Test Setup ---")
dotenv_path = os.path.join(os.path.dirname(__file__), 'api', '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_TEST_TOKEN = os.getenv('SAMPLE_JWT')
if not SUPABASE_TEST_TOKEN:
    print("ERROR: SAMPLE_JWT environment variable not found.")
    exit(1)

BASE_URL = "http://localhost:8000/api"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
}
print(f"Using Base URL: {BASE_URL}")
print("Checking initial server connection...")
try:
    # Quick check to see if server is responsive
    response = requests.get(f"{BASE_URL}/resumes/", headers=headers, timeout=3)
    response.raise_for_status()
    print("Initial server connection successful.")
except requests.ConnectionError:
    print(f"ERROR: Cannot connect to Django server at {BASE_URL}. Is it running?")
    exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR: Initial connection check failed: {e}")
    if hasattr(e, 'response') and e.response is not None:
         try: pprint(e.response.json())
         except: print(e.response.text)
    exit(1)
except Exception as e:
    print(f"Warning: Pre-check failed, but continuing test: {e}")

# --- Helper Functions (Same as before) ---

def create_test_resume():
    """Creates a temporary resume."""
    print("\n--- Creating temporary resume ---")
    resume_payload = {
        "title": f"Temp Resume for Component Test - {uuid.uuid4()}",
        "skills": ["component test skill"],
        "section_order": ["experience", "education", "projects", "certifications", "customSections"]
    }
    try:
        response = requests.post(f"{BASE_URL}/resumes/", json=resume_payload, headers=headers, timeout=10)
        response.raise_for_status()
        created_resume = response.json()
        resume_id = created_resume.get('id')
        if not resume_id: raise ValueError("Failed to get ID from created resume response.")
        print(f"Temporary Resume created with ID: {resume_id}")
        return resume_id
    except requests.exceptions.RequestException as e:
        print(f"ERROR creating temporary resume: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during resume creation: {e}")
        return None

def delete_test_resume(resume_id):
    """Deletes the temporary resume."""
    if not resume_id: return False
    print(f"\n--- Deleting temporary resume {resume_id} ---")
    try:
        response = requests.delete(f"{BASE_URL}/resumes/{resume_id}/", headers=headers, timeout=10)
        response.raise_for_status()
        print(f"Resume Delete Status Code: {response.status_code}")
        return response.status_code == 204
    except requests.exceptions.RequestException as e:
        print(f"ERROR deleting temporary resume {resume_id}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during resume deletion: {e}")
        return False

# --- Generic CRUD Test Function ---

def test_component_crud(endpoint_path, component_name, create_payload, update_payload, parent_id_field, parent_id):
    """Performs generic CRUD test for a component."""
    component_id = None
    print(f"\n===== Testing {component_name} CRUD ({endpoint_path}) =====")

    # Add parent ID to payload
    create_payload[parent_id_field] = parent_id

    # 1. Create (POST)
    print(f"\n--- Testing POST {endpoint_path} ---")
    try:
        response_post = requests.post(f"{BASE_URL}{endpoint_path}", json=create_payload, headers=headers, timeout=10)
        response_post.raise_for_status()
        created_component = response_post.json()
        component_id = created_component.get('id')
        print(f"POST Status Code: {response_post.status_code}")
        print(f"Created {component_name} ID: {component_id}")
        pprint(created_component)
        assert component_id is not None
    except requests.exceptions.RequestException as e:
        print(f"ERROR during {component_name} POST: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
        raise # Re-raise exception to stop the test for this component
    except Exception as e:
        print(f"An unexpected error occurred during {component_name} POST: {e}")
        raise

    time.sleep(0.5) # Small delay

    # 2. Read (GET)
    print(f"\n--- Testing GET {endpoint_path}{component_id}/ ---")
    try:
        response_get = requests.get(f"{BASE_URL}{endpoint_path}{component_id}/", headers=headers, timeout=10)
        response_get.raise_for_status()
        print(f"GET Status Code: {response_get.status_code}")
        pprint(response_get.json())
        assert response_get.json().get('id') == component_id
    except requests.exceptions.RequestException as e:
        print(f"ERROR during {component_name} GET: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
    except Exception as e:
        print(f"An unexpected error occurred during {component_name} GET: {e}")

    time.sleep(0.5)

    # 3. Update (PATCH)
    print(f"\n--- Testing PATCH {endpoint_path}{component_id}/ ---")
    try:
        response_patch = requests.patch(f"{BASE_URL}{endpoint_path}{component_id}/", json=update_payload, headers=headers, timeout=10)
        response_patch.raise_for_status()
        print(f"PATCH Status Code: {response_patch.status_code}")
        pprint(response_patch.json())
        # Simple check: Assume first key in update_payload was updated
        first_update_key = list(update_payload.keys())[0]
        assert response_patch.json().get(first_update_key) == update_payload[first_update_key]
    except requests.exceptions.RequestException as e:
        print(f"ERROR during {component_name} PATCH: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
    except Exception as e:
        print(f"An unexpected error occurred during {component_name} PATCH: {e}")

    time.sleep(0.5)

    # 4. Delete (DELETE)
    print(f"\n--- Testing DELETE {endpoint_path}{component_id}/ ---")
    try:
        response_delete = requests.delete(f"{BASE_URL}{endpoint_path}{component_id}/", headers=headers, timeout=10)
        response_delete.raise_for_status()
        print(f"DELETE Status Code: {response_delete.status_code}")
        assert response_delete.status_code == 204
    except requests.exceptions.RequestException as e:
        print(f"ERROR during {component_name} DELETE: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
    except Exception as e:
        print(f"An unexpected error occurred during {component_name} DELETE: {e}")

    time.sleep(0.5)

    # 5. Verify Deletion (GET again)
    print(f"\n--- Verifying DELETE {endpoint_path}{component_id}/ ---")
    try:
        response_get_after = requests.get(f"{BASE_URL}{endpoint_path}{component_id}/", headers=headers, timeout=10)
        print(f"GET after DELETE Status Code: {response_get_after.status_code}")
        assert response_get_after.status_code == 404
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
             print(f"Status code was: {e.response.status_code}")
             assert e.response.status_code == 404 # Expected 404
        else:
             print(f"ERROR during {component_name} GET after DELETE (non-HTTP error): {e}")
    except Exception as e:
        print(f"An unexpected error occurred during {component_name} GET after DELETE: {e}")

    print(f"===== Finished {component_name} CRUD Test =====")
    return component_id # Return ID for potential nested tests

# --- Main Test Execution ---

def run_all_tests():
    resume_id = None
    try:
        # Create parent Resume
        resume_id = create_test_resume()
        if not resume_id:
            raise Exception("Failed to create prerequisite Resume.")

        # Test WorkExperience
        test_component_crud(
            endpoint_path="/work-experiences/",
            component_name="WorkExperience",
            create_payload={
                "position": "Test Position WE",
                "company": "Test Co WE",
                "start_date": "2021-05-01T00:00:00Z",
                "description": "WE Desc"
            },
            update_payload={"company": "Updated Test Co WE"},
            parent_id_field="resume",
            parent_id=resume_id
        )

        # Test Education
        test_component_crud(
            endpoint_path="/educations/",
            component_name="Education",
            create_payload={
                "degree": "Test Degree ED",
                "school": "Test School ED",
                "start_date": "2019-09-01T00:00:00Z",
                "end_date": "2021-06-01T00:00:00Z"
            },
            update_payload={"school": "Updated Test School ED"},
            parent_id_field="resume",
            parent_id=resume_id
        )

        # Test Project
        test_component_crud(
            endpoint_path="/projects/",
            component_name="Project",
            create_payload={
                "title": "Test Project PR",
                "description": "PR Desc",
                "start_date": "2023-01-10T00:00:00Z"
            },
            update_payload={"description": "Updated PR Desc"},
            parent_id_field="resume",
            parent_id=resume_id
        )

        # Test Certification
        test_component_crud(
            endpoint_path="/certifications/",
            component_name="Certification",
            create_payload={
                "name": "Test Cert CE",
                "issuer": "Test Issuer CE",
                "issue_date": "2023-03-15T00:00:00Z"
            },
            update_payload={"issuer": "Updated Test Issuer CE"},
            parent_id_field="resume",
            parent_id=resume_id
        )

        # --- Test CustomSection and CustomSectionItem (Corrected Order) ---
        print("\n===== Testing CustomSection & Item CRUD (Corrected Order) =====")
        custom_section_id = None
        custom_section_endpoint_path = "/custom-sections/"
        custom_section_name = "CustomSection"
        cs_create_payload = {"title": "Test Custom Section CS", "resume": resume_id}
        cs_update_payload = {"title": "Updated Custom Section CS"}

        # 1. Create CustomSection (Manual POST)
        print(f"\n--- Testing POST {custom_section_endpoint_path} ---")
        try:
            response_cs_post = requests.post(f"{BASE_URL}{custom_section_endpoint_path}", json=cs_create_payload, headers=headers, timeout=10)
            response_cs_post.raise_for_status()
            created_cs = response_cs_post.json()
            custom_section_id = created_cs.get('id')
            print(f"POST Status Code: {response_cs_post.status_code}")
            print(f"Created {custom_section_name} ID: {custom_section_id}")
            pprint(created_cs)
            assert custom_section_id is not None
        except requests.exceptions.RequestException as e:
            print(f"ERROR during {custom_section_name} POST: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try: pprint(e.response.json())
                except: print(e.response.text)
            # If CS creation fails, we can't test CSI
        except Exception as e:
            print(f"An unexpected error occurred during {custom_section_name} POST: {e}")
            # If CS creation fails, we can't test CSI

        # 2. Test CustomSectionItem CRUD (using the generic function)
        if custom_section_id:
            try:
                test_component_crud(
                    endpoint_path="/custom-section-items/",
                    component_name="CustomSectionItem",
                    create_payload={
                        "title": "Test Item CSI",
                        "description": "CSI Desc"
                    },
                    update_payload={"description": "Updated CSI Desc"},
                    parent_id_field="custom_section", # Note the different parent field name
                    parent_id=custom_section_id
                )
            except Exception as e:
                print(f"ERROR during CustomSectionItem CRUD test: {e}")
                # Continue to CS cleanup even if item test fails

            # 3. Update CustomSection (Manual PATCH)
            print(f"\n--- Testing PATCH {custom_section_endpoint_path}{custom_section_id}/ --- (Parent Section)")
            try:
                response_cs_patch = requests.patch(f"{BASE_URL}{custom_section_endpoint_path}{custom_section_id}/", json=cs_update_payload, headers=headers, timeout=10)
                response_cs_patch.raise_for_status()
                print(f"PATCH Status Code: {response_cs_patch.status_code}")
                pprint(response_cs_patch.json())
                assert response_cs_patch.json().get('title') == cs_update_payload['title']
            except requests.exceptions.RequestException as e:
                 print(f"ERROR during {custom_section_name} PATCH: {e}")
                 if hasattr(e, 'response') and e.response is not None:
                     try: pprint(e.response.json())
                     except: print(e.response.text)
            except Exception as e:
                print(f"An unexpected error occurred during {custom_section_name} PATCH: {e}")

            time.sleep(0.5)

            # 4. Delete CustomSection (Manual DELETE)
            print(f"\n--- Testing DELETE {custom_section_endpoint_path}{custom_section_id}/ --- (Parent Section)")
            try:
                response_cs_delete = requests.delete(f"{BASE_URL}{custom_section_endpoint_path}{custom_section_id}/", headers=headers, timeout=10)
                response_cs_delete.raise_for_status()
                print(f"DELETE Status Code: {response_cs_delete.status_code}")
                assert response_cs_delete.status_code == 204
            except requests.exceptions.RequestException as e:
                print(f"ERROR during {custom_section_name} DELETE: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try: pprint(e.response.json())
                    except: print(e.response.text)
            except Exception as e:
                print(f"An unexpected error occurred during {custom_section_name} DELETE: {e}")

            time.sleep(0.5)

            # 5. Verify Deletion CustomSection (Manual GET)
            print(f"\n--- Verifying DELETE {custom_section_endpoint_path}{custom_section_id}/ --- (Parent Section)")
            try:
                response_cs_get_after = requests.get(f"{BASE_URL}{custom_section_endpoint_path}{custom_section_id}/", headers=headers, timeout=10)
                print(f"GET after DELETE Status Code: {response_cs_get_after.status_code}")
                assert response_cs_get_after.status_code == 404
            except requests.exceptions.RequestException as e:
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Status code was: {e.response.status_code}")
                    assert e.response.status_code == 404 # Expected 404
                else:
                    print(f"ERROR during {custom_section_name} GET after DELETE (non-HTTP error): {e}")
            except Exception as e:
                print(f"An unexpected error occurred during {custom_section_name} GET after DELETE: {e}")

        else:
            print("Skipping CustomSectionItem test and CustomSection cleanup due to CustomSection creation failure.")
        print("===== Finished CustomSection & Item CRUD Test (Corrected Order) =====")


    except Exception as e:
        print(f"\n!!!!!! A CRITICAL ERROR OCCURRED DURING TESTING: {e} !!!!!!")
    finally:
        # Clean up the parent Resume
        if resume_id:
            if delete_test_resume(resume_id):
                print("\nTemporary resume cleaned up successfully.")
            else:
                print("\nERROR: Failed to cleanup temporary resume.")

if __name__ == "__main__":
    print("\nTesting ALL Resume Component API Endpoints")
    print("=========================================")
    run_all_tests()
    print("\n=========================================")
    print("All Component Tests Finished.") 