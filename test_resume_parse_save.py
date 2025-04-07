import requests
import json
import sys
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000/api"  # Adjust if your server runs on a different URL
USER_ID = "f47ac10b-58cc-4372-a567-0e02b2c3d479"  # Replace with actual user ID

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
        data = {"user_id": USER_ID}
        
        parse_response = requests.post(
            f"{BASE_URL}/parse-resume/",
            files=files,
            data=data
        )
    
    if parse_response.status_code != 200:
        print(f"Error parsing resume: {parse_response.status_code}")
        print(parse_response.text)
        return False
    
    parse_data = parse_response.json()
    
    # Print parsing results
    print("\nResume parsing successful!")
    print(f"First Name: {parse_data['validated_data']['personal_info'].get('first_name')}")
    print(f"Last Name: {parse_data['validated_data']['personal_info'].get('last_name')}")
    print(f"Email: {parse_data['validated_data']['personal_info'].get('email')}")
    
    # Step 2: Save the parsed resume
    save_response = requests.post(
        f"{BASE_URL}/save-parsed-resume/",
        json={
            "validated_data": parse_data["validated_data"],
            "user_id": USER_ID
        }
    )
    
    if save_response.status_code not in [200, 201]:
        print(f"Error saving resume: {save_response.status_code}")
        print(save_response.text)
        return False
    
    save_data = save_response.json()
    
    print("\nResume saved successfully!")
    print(f"Resume ID: {save_data['resume']['id']}")
    print(f"Resume Title: {save_data['resume']['title']}")
    
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