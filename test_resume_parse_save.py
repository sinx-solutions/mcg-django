import requests
import json
import sys
import os
from dotenv import load_dotenv

# Configuration
BASE_URL = "http://127.0.0.1:8000/api"  # Adjust if your server runs on a different URL
# USER_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479" # No longer needed from script

# Load .env file from api/ directory
dotenv_path = os.path.join(os.path.dirname(__file__), 'api', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Get JWT from environment
SUPABASE_TEST_TOKEN = os.getenv('SAMPLE_JWT')
if not SUPABASE_TEST_TOKEN:
    print(f"ERROR: SAMPLE_JWT not found in {dotenv_path}")
    sys.exit(1)

# Prepare headers
headers = {
    "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
    # Content-Type for multipart/form-data is set automatically by requests
}

headers_json = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
}

def parse_and_save_resume(resume_file_path):
    """Parse a resume file and save the parsed data to the database"""
    
    # Check if file exists
    if not os.path.exists(resume_file_path):
        print(f"Error: File {resume_file_path} does not exist")
        return False
    
    print(f"Step 1: Parsing resume file: {resume_file_path}")
    
    # Step 1: Parse the resume file
    with open(resume_file_path, "rb") as file:
        files = {"resume": file}
        # data = {"user_id": USER_ID} # user_id no longer sent in body
        
        parse_response = requests.post(
            f"{BASE_URL}/parse-resume/",
            files=files,
            # data=data,
            headers=headers # Pass headers with JWT
        )
    
    if parse_response.status_code != 200:
        print(f"Error parsing resume: {parse_response.status_code}")
        try:
            print(parse_response.json()) # Try to print JSON error
        except json.JSONDecodeError:
            print(parse_response.text) # Print text if not JSON
        return False
    
    parse_data = parse_response.json()
    
    # Print parsing results
    print("\nResume parsing successful!")
    validated_data = parse_data.get("validated_data")
    if not validated_data:
        print("ERROR: 'validated_data' not found in parse response.")
        pprint(parse_data)
        return False

    personal_info = validated_data.get('personal_info', {})
    print(f"First Name: {personal_info.get('first_name')}")
    print(f"Last Name: {personal_info.get('last_name')}")
    print(f"Email: {personal_info.get('email')}")
    
    # Step 2: Save the parsed resume
    print("\nStep 2: Saving parsed resume to database...")
    save_payload = {
        "validated_data": validated_data
        # "user_id": USER_ID # user_id is determined by JWT, not sent in body
    }
    save_response = requests.post(
        f"{BASE_URL}/save-parsed-resume/",
        json=save_payload,
        headers=headers_json # Pass headers with JWT and Content-Type JSON
    )
    
    if save_response.status_code not in [200, 201]:
        print(f"Error saving resume: {save_response.status_code}")
        try:
            print(save_response.json()) # Try to print JSON error
        except json.JSONDecodeError:
            print(save_response.text) # Print text if not JSON
        return False
    
    save_data = save_response.json()
    
    print("\nResume saved successfully!")
    resume_details = save_data.get('resume')
    if not resume_details:
        print("ERROR: 'resume' details not found in save response.")
        pprint(save_data)
        return False

    print(f"Resume ID: {resume_details.get('id')}")
    print(f"Resume Title: {resume_details.get('title')}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_resume_parse_save.py <resume_file_path>")
        sys.exit(1)
        
    resume_file_path = sys.argv[1]
    success = parse_and_save_resume(resume_file_path)
    
    if success:
        print("\nComplete resume parsing and saving process was successful!")
    else:
        print("\nProcess failed. Please check the error messages above.") 