#!/usr/bin/env python3
"""
Test script for resume API endpoints.
Tests both create (POST) and update (PATCH) operations with the full resume structure.
"""
import requests
import json
import uuid
from pprint import pprint
import os  # Import os
from dotenv import load_dotenv  # Import load_dotenv

# Load environment variables from .env file in the api/ directory
dotenv_path = os.path.join(os.path.dirname(__file__), 'api', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Use the token stored in the environment variable
SUPABASE_TEST_TOKEN = os.getenv('SAMPLE_JWT')

if not SUPABASE_TEST_TOKEN:
    print("ERROR: SAMPLE_JWT environment variable not found.")
    print(f"Please ensure SAMPLE_JWT is set in your .env file (looked in: {dotenv_path})")
    exit(1)

# Set the Supabase user ID to match the one in the token
# This should match the 'sub' claim in your token
# Extract user ID from token instead of hardcoding (optional but good practice)
SUPABASE_USER_ID_FROM_TOKEN = None
try:
    import jwt
    # Decode without verification just to get the sub claim for the test data
    decoded = jwt.decode(SUPABASE_TEST_TOKEN, options={"verify_signature": False})
    SUPABASE_USER_ID_FROM_TOKEN = decoded.get('sub')
except Exception as e:
    print(f"Warning: Could not decode SAMPLE_JWT to extract user ID: {e}")

# If decoding failed or no sub, fallback or raise error if needed
SUPABASE_USER_ID = SUPABASE_USER_ID_FROM_TOKEN or "fallback_user_id_if_needed"
if not SUPABASE_USER_ID_FROM_TOKEN:
     print(f"Warning: Using fallback user ID: {SUPABASE_USER_ID}")

# Base URL of the API
BASE_URL = "http://localhost:8000/api"

# Test data for creating a new resume
test_resume_data = {
    # Main resume data
    "user_id": SUPABASE_USER_ID,  # Should match the Supabase user ID in the token
    "title": "Sanchay Thalnerkar ULTRA FINAL TESTING FOR JWT DAMMIT",
    "description": "Created for testing API",
    "first_name": "SANCHAY",
    "last_name": "SANCHAY",
    "job_title": "PROOMPT Engineer",
    "city": "Mumbai",
    "country": "USA",
    "phone": "555-123-4567",
    "email": "test@example.com",
    "summary": "Experienced software engineer with skills in Python and Django",
    "skills": ["Python", "Django", "REST API", "Testing"],
    "photo_url": None,
    "color_hex": "#3b82f6",
    "border_style": "rounded",
    "font_family": "Inter",
    "template": "modern",
    "font_size": 10,
    "section_spacing": 24,
    "line_height": 1.4,
    "content_margin": 32,
    "section_order": ["summary", "skills", "work_experiences", "projects", "educations", "certifications"],
    "extra_sections": [],
    
    # Nested resume components
    "work_experiences": [
        {
            "position": "Senior Software Engineer",
            "company": "Tech Corp",
            "start_date": "2020-01-15",
            "end_date": None,
            "description": "• Led development of microservices using Django.\n• Mentored junior engineers."
        },
        {
            "position": "Software Engineer",
            "company": "Startup Inc",
            "start_date": "2016-06-01",
            "end_date": "2019-12-31",
            "description": "• Developed full-stack features with Python and React."
        }
    ],
    "educations": [
        {
            "degree": "M.S. Computer Science",
            "school": "State University",
            "start_date": "2014-09-01",
            "end_date": "2016-05-15"
        }
    ],
    "projects": [
        {
            "title": "Personal Portfolio Website",
            "description": "• Built with Next.js and deployed on Vercel."
        }
    ],
    "certifications": [
        {
            "name": "AWS Certified Developer - Associate",
            "issuer": "Amazon Web Services",
            "issue_date": "2021-07-01"
        }
    ],
    "custom_sections": [
        {
            "title": "Volunteering",
            "items": [
                {
                    "title": "Code Mentor",
                    "description": "Mentored students learning Python.",
                    "start_date": "2022-01-01",
                    "end_date": None
                }
            ]
        }
    ]
}

# Required headers for API requests
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SUPABASE_TEST_TOKEN}"
}

def test_create_resume():
    """Test creating a new resume with the complete structure"""
    print("\n=== Testing POST to /api/resumes/ (Create) ===")
    
    # Make the POST request to create a new resume
    response = requests.post(
        f"{BASE_URL}/resumes/", 
        json=test_resume_data,
        headers=headers
    )
    
    # Print response status and basic info
    print(f"Status Code: {response.status_code}")
    
    if response.status_code not in (200, 201):
        print("Error Response:")
        pprint(response.json())
        return None
    
    # Success - print the created resume ID and basic info
    created_resume = response.json()
    print(f"Created Resume ID: {created_resume.get('id')}")
    print(f"Title: {created_resume.get('title')}")
    print(f"Number of work experiences: {len(created_resume.get('work_experiences', []))}")
    print(f"Number of educations: {len(created_resume.get('educations', []))}")
    print(f"Number of projects: {len(created_resume.get('projects', []))}")
    print(f"Number of custom sections: {len(created_resume.get('custom_sections', []))}")
    
    # Return the created resume data for further testing
    return created_resume

def test_update_resume(resume_id):
    """Test updating an existing resume with modified data"""
    print(f"\n=== Testing PATCH to /api/resumes/{resume_id}/ (Update) ===")
    
    # Create a modified version of the test data
    modified_data = test_resume_data.copy()
    
    # Modify some fields
    modified_data["title"] = "Updated Test Resume"
    modified_data["job_title"] = "Senior Software Engineer"
    modified_data["skills"] = ["Python", "Django", "REST API", "Testing", "AWS", "Docker"]
    
    # Modify a work experience
    if modified_data["work_experiences"]:
        modified_data["work_experiences"][0]["description"] = "• Led development of microservices using Django.\n• Mentored junior engineers.\n• Improved API performance by 30%."
    
    # Add a new education entry
    modified_data["educations"].append({
        "degree": "B.S. Computer Science",
        "school": "Tech Institute",
        "start_date": "2010-09-01",
        "end_date": "2014-05-15"
    })
    
    # Make the PATCH request to update the resume
    response = requests.patch(
        f"{BASE_URL}/resumes/{resume_id}/", 
        json=modified_data,
        headers=headers
    )
    
    # Print response status and basic info
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print("Error Response:")
        pprint(response.json())
        return None
    
    # Success - print the updated resume info
    updated_resume = response.json()
    print(f"Updated Resume ID: {updated_resume.get('id')}")
    print(f"Updated Title: {updated_resume.get('title')}")
    print(f"Updated Job Title: {updated_resume.get('job_title')}")
    print(f"Updated Skills Count: {len(updated_resume.get('skills', []))}")
    print(f"Updated Number of work experiences: {len(updated_resume.get('work_experiences', []))}")
    print(f"Updated Number of educations: {len(updated_resume.get('educations', []))}")
    
    # Return the updated resume data
    return updated_resume

def cleanup(resume_id):
    """Delete the test resume"""
    print(f"\n=== Cleanup: DELETE /api/resumes/{resume_id}/ ===")
    
    response = requests.delete(
        f"{BASE_URL}/resumes/{resume_id}/",
        headers=headers
    )
    
    print(f"Delete Status Code: {response.status_code}")
    return response.status_code == 204  # Success is 204 No Content

def main():
    """Run the test sequence"""
    print("Testing Resume API Endpoints")
    print("===========================")
    
    # Test creating a resume
    created_resume = test_create_resume()
    if not created_resume:
        print("Failed to create resume. Stopping tests.")
        return
    
    resume_id = created_resume.get('id')
    
    # Test updating the resume
    updated_resume = test_update_resume(resume_id)
    if not updated_resume:
        print("Failed to update resume.")

    # Cleanup - delete the test resume (Commented out for manual inspection)
    # if resume_id:
    #     if cleanup(resume_id):
    #         print("Test resume deleted successfully.")
    #     else:
    #         print("Failed to delete test resume.")

if __name__ == "__main__":
    main()
