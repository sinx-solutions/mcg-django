# test_cover_letter.py
#!/usr/bin/env python3
"""
Test script for the generate-cover-letter API endpoint.
Uses an existing resume ID and job details provided as arguments.
"""
import requests
import json
import sys
import os
import uuid
from pprint import pprint
from dotenv import load_dotenv

# --- Setup ---
print("--- Cover Letter Generation Test Setup ---")
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

# --- Comprehensive Resume Payload ---
# Use details that should appear in the cover letter
full_resume_payload = {
    "title": f"Test Resume for Cover Letter Gen - {uuid.uuid4()}",
    "first_name": "Sanchay_Test",
    "last_name": "Thalnerkar_Test",
    "email": "sanchay.test.cl@example.com",
    "phone": "+91 9988776655",
    "city": "TestCity",
    "country": "TestCountry",
    "summary": "Highly motivated test engineer with experience in API testing and automation, seeking new challenges.",
    "skills": ["API Testing", "Python", "Requests", "Pytest", "Problem Solving"],
    "section_order": ["summary", "skills", "work_experiences", "educations"],
    "extra_sections": [],
    "work_experiences": [
        {
            "position": "Senior QA Engineer",
            "company": "TestCorp",
            "start_date": "2022-01-15T00:00:00Z",
            "description": "Led testing efforts for major API releases, developed automated test suites using Python."
        },
        {
            "position": "QA Analyst",
            "company": "BugFinders Inc.",
            "start_date": "2020-06-01T00:00:00Z",
            "end_date": "2021-12-31T00:00:00Z",
            "description": "Performed manual and automated testing for web applications."
        }
    ],
    "educations": [
        {
            "degree": "B.Sc. Computer Science",
            "school": "University of Testing",
            "start_date": "2016-09-01T00:00:00Z",
            "end_date": "2020-05-15T00:00:00Z"
        }
    ],
    "projects": [],
    "certifications": [],
    "custom_sections": []
}

# --- Helper Functions ---

def create_full_test_resume():
    """Creates a new, fully populated resume for testing."""
    print("\n--- Creating Test Resume ---")
    try:
        response = requests.post(
            f"{BASE_URL}/resumes/",
            json=full_resume_payload,
            headers=headers_json,
            timeout=15
        )
        response.raise_for_status()
        created_resume = response.json()
        resume_id = created_resume.get('id')
        if not resume_id: raise ValueError("Failed to get ID from created resume.")
        print(f"Test Resume created successfully with ID: {resume_id}")
        return resume_id
    except requests.exceptions.RequestException as e:
        print(f"ERROR creating test resume: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try: pprint(e.response.json())
            except: print(e.response.text)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during test resume creation: {e}")
        return None

def delete_test_resume(resume_id):
    """Deletes the test resume."""
    if not resume_id: return False
    print(f"\n--- Deleting Test Resume {resume_id} ---")
    try:
        response = requests.delete(f"{BASE_URL}/resumes/{resume_id}/", headers=headers_json, timeout=10)
        response.raise_for_status()
        print(f"Test Resume Delete Status Code: {response.status_code}")
        return response.status_code == 204
    except requests.exceptions.RequestException as e:
        print(f"ERROR deleting test resume {resume_id}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during test resume deletion: {e}")
        return False

# --- Test Function ---

def generate_test_cover_letter(resume_id, job_title, company_name, job_description):
    """Calls the generate-cover-letter endpoint."""

    print("\n--- Calling /api/generate-cover-letter/ ---")
    print(f"Using Resume ID: {resume_id}")
    print(f"Job Title: {job_title}")
    print(f"Company Name: {company_name}")
    # print(f"Job Description: {job_description[:100]}...") # Print snippet

    payload = {
        "resume_id": resume_id,
        "job_title": job_title,
        "company_name": company_name,
        "job_description": job_description
    }

    try:
        print("Sending request...")
        response = requests.post(
            f"{BASE_URL}/generate-cover-letter/",
            json=payload,
            headers=headers_json,
            timeout=120 # Allow ample time for AI generation
        )
        print(f"Response Status Code: {response.status_code}")

        # Try to print JSON response, fallback to text
        try:
            response_data = response.json()
            print("\nResponse Content (JSON):")
            pprint(response_data)
            # Basic success check
            if response.status_code == 200 and response_data.get("cover_letter_text"):
                 print("\nSUCCESS: Cover letter generated and received successfully.")
                 print(f"Saved Cover Letter ID: {response_data.get('saved_cover_letter_id')}")
                 return True
            else:
                 print("\nFAILURE: Request completed but response indicates an error or missing data.")
                 return False
        except json.JSONDecodeError:
            print("\nResponse Content (Non-JSON):")
            print(response.text)
            print("\nFAILURE: Received non-JSON response.")
            return False

    except requests.exceptions.Timeout:
        print("ERROR: Request timed out.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("\nUsage: python test_cover_letter.py \"<job_title>\" \"<company_name>\" \"<job_description>\"")
        print("\nExample:")
        print("python test_cover_letter.py \"Software Engineer\" \"Tech Corp\" \"Looking for a Python expert...\"")
        print("\nNOTE: Creates a new test resume first. Use quotes around arguments with spaces.")
        sys.exit(1)

    # Get arguments for job details
    job_title_arg = sys.argv[1]
    company_name_arg = sys.argv[2]
    job_description_arg = sys.argv[3]

    print("\n--- Starting Cover Letter Generation Test (with fresh resume) ---")
    
    test_resume_id = None
    final_success = False
    try:
        # 1. Create a full resume for the test
        test_resume_id = create_full_test_resume()
        if not test_resume_id:
            raise Exception("Failed to create test resume.")

        # 2. Generate cover letter using the new resume ID
        final_success = generate_test_cover_letter(
            resume_id=test_resume_id,
            job_title=job_title_arg,
            company_name=company_name_arg,
            job_description=job_description_arg
        )

    except Exception as e:
        print(f"\n!!! Test Script Error: {e} !!!")
        final_success = False
    finally:
        # 3. Clean up the created resume
        if test_resume_id:
            delete_test_resume(test_resume_id)
        else:
            print("\nSkipping cleanup as test resume was not created.")

    print("\n--- Test Finished ---")
    if final_success:
        print("Result: SUCCESS")
    else:
        print("Result: FAILED")
        # Exit with error code if failed
        if not final_success: sys.exit(1) 