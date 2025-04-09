import requests
import json
import os
from dotenv import load_dotenv
import sys

# --- Configuration ---
# Construct the path to the .env file inside the 'api' directory
workspace_root = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(workspace_root, 'api')
dotenv_path = os.path.join(api_dir, '.env')

# Load environment variables from api/.env
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print(f"Loaded environment variables from: {dotenv_path}")
else:
    print(f"Error: .env file not found at {dotenv_path}")
    sys.exit(1)

# Get JWT and Base URL from environment variables
SAMPLE_JWT = os.getenv('SAMPLE_JWT')
# Define a default base URL if not set in .env
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000').rstrip('/')

if not SAMPLE_JWT:
    print("Error: SAMPLE_JWT not found in .env file.")
    sys.exit(1)

print(f"Using API Base URL: {API_BASE_URL}")
print(f"Using JWT (first 10 chars): {SAMPLE_JWT[:10]}...")

# --- Data Definitions ---
sample_resume_data = {
    "title": "Live API Test Resume",
    "first_name": "Live",
    "last_name": "Tester",
    "email": "live_test@example.com",
    "phone": "987-654-3210",
    "summary": "Summary created via live API test script.",
    "skills": ["Requests", "JSON", "Python", "API Testing"],
    "work_experiences": [
        {
            "position": "API Caller",
            "company": "Script Inc.",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": None, # Test current job
            "description": "Making live API calls."
        }
    ],
    "educations": [
        {
            "degree": "Certificate of Testing",
            "school": "Online U",
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-12-31T00:00:00Z"
        }
    ]
}

sample_job_data = {
    "title": "Live Test Job",
    "raw_text": "Job description for the live API test. Requires Python and API testing skills.",
    "required_skills": ["Python", "API Testing"],
    "preferred_skills": ["JSON", "Requests"]
}

# --- API Call Logic ---
headers = {
    'Authorization': f'Bearer {SAMPLE_JWT}',
    'Content-Type': 'application/json'
}

created_resume_id = None

def run_api_flow():
    global created_resume_id

    # 1. Create Resume
    create_url = f"{API_BASE_URL}/api/resumes/"
    print(f"\n--- 1. Attempting to Create Resume ---")
    print(f"POST {create_url}")
    try:
        response_create = requests.post(
            create_url,
            headers=headers,
            json=sample_resume_data,
            timeout=30 # Add a timeout
        )
        response_create.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        print(f"Create Status Code: {response_create.status_code}")
        response_data = response_create.json()
        print(f"Create Response Body:\n{json.dumps(response_data, indent=2)}")

        if response_create.status_code == 201 and 'id' in response_data:
            created_resume_id = response_data['id']
            print(f"Successfully created resume with ID: {created_resume_id}")
        else:
            print("Error: Resume creation failed or ID missing in response.")
            return # Stop if creation failed

    except requests.exceptions.Timeout:
        print("Error: Request timed out.")
        return
    except requests.exceptions.RequestException as e:
        print(f"Error during resume creation request: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response Status Code: {e.response.status_code}")
             print(f"Response Body: {e.response.text}")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from create endpoint.")
        print(f"Raw response: {response_create.text}")
        return

    # 2. Score Resume
    if created_resume_id:
        score_url = f"{API_BASE_URL}/api/resumes/{created_resume_id}/score/"
        print(f"\n--- 2. Attempting to Score Resume (ID: {created_resume_id}) ---")
        print(f"POST {score_url}")
        try:
            response_score = requests.post(
                score_url,
                headers=headers,
                json=sample_job_data,
                 timeout=60 # Allow longer timeout for scoring
            )
            response_score.raise_for_status()

            print(f"Score Status Code: {response_score.status_code}")
            score_data = response_score.json()
            print(f"Score Response Body:\n{json.dumps(score_data, indent=2)}")

            if response_score.status_code == 200 and 'overall_score' in score_data:
                print("Successfully scored resume.")
            else:
                print("Error: Scoring failed or overall_score missing in response.")

        except requests.exceptions.Timeout:
            print("Error: Request timed out during scoring.")
        except requests.exceptions.RequestException as e:
            print(f"Error during scoring request: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                print(f"Response Body: {e.response.text}")
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from score endpoint.")
            print(f"Raw response: {response_score.text}")
    else:
        print("\nSkipping scoring because resume creation failed or ID was not obtained.")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting API Flow Checker Script...")
    run_api_flow()
    print("\nAPI Flow Checker Script Finished.") 