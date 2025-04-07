import requests
import json
import uuid
import os

# Create a new resume first
BASE_URL = "http://localhost:8000/api"

print("Creating a new resume...")
resume_data = {
    "user_id": str(uuid.uuid4()),
    "title": "Test Resume",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "skills": ["Python", "Django", "JavaScript"]
}

try:
    # Create the resume
    create_response = requests.post(f"{BASE_URL}/resumes/", json=resume_data)
    create_response.raise_for_status()
    resume = create_response.json()
    resume_id = resume["id"]
    print(f"Resume created successfully with ID: {resume_id}")
    
    # Add a work experience
    print("Adding work experience...")
    work_exp_data = {
        "resume": resume_id,
        "position": "Software Developer",
        "company": "Tech Company",
        "description": "Developed web applications."
    }
    
    work_exp_response = requests.post(f"{BASE_URL}/work-experiences/", json=work_exp_data)
    work_exp_response.raise_for_status()
    print("Work experience added successfully")
    
    # Now test the adapt endpoint
    print("\nTesting resume adaptation endpoint...")
    job_data = {
        "resume_id": resume_id,
        "job_title": "Full Stack Developer",
        "company": "Innovative Solutions",
        "job_description": """
        We are looking for a Full Stack Developer with Python and React experience.
        """
    }
    
    print(f"Sending request to {BASE_URL}/adapt-resume/...")
    print(f"Request data: {json.dumps(job_data, indent=2)}")
    
    adapt_response = requests.post(f"{BASE_URL}/adapt-resume/", json=job_data)
    print(f"Response status code: {adapt_response.status_code}")
    
    # Print response content
    try:
        resp_json = adapt_response.json()
        print(f"Response JSON: {json.dumps(resp_json, indent=2)}")
    except:
        print(f"Response text: {adapt_response.text}")
    
    # Clean up - delete the resume
    print("\nCleaning up - deleting the resume...")
    delete_response = requests.delete(f"{BASE_URL}/resumes/{resume_id}/")
    if delete_response.status_code == 204:
        print(f"Resume deleted successfully")
    else:
        print(f"Failed to delete resume: {delete_response.status_code}")
        
except Exception as e:
    print(f"Error: {str(e)}") 