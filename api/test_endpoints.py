import requests
import json
import uuid
import os
from datetime import datetime
import time

# API base URL
BASE_URL = "http://localhost:8000/api"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(message):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(50)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}\n")

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_fail(message):
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.ENDC}")

def test_create_resume():
    print_header("Testing Resume Creation")

    # Sample resume data
    resume_data = {
        "user_id": str(uuid.uuid4()),
        "title": "Software Engineer Resume",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "job_title": "Senior Software Engineer",
        "summary": "Experienced software engineer with 8+ years of experience in full-stack development.",
        "skills": ["Python", "Django", "JavaScript", "React", "Docker"],
        "phone": "123-456-7890",
        "city": "San Francisco",
        "country": "USA"
    }

    # Create resume
    try:
        response = requests.post(f"{BASE_URL}/resumes/", json=resume_data)
        response.raise_for_status()
        resume = response.json()
        print_success("Resume created successfully")
        print_info(f"Resume ID: {resume['id']}")
        return resume
    except Exception as e:
        print_fail(f"Failed to create resume: {str(e)}")
        return None

def test_get_resumes():
    print_header("Testing Get All Resumes")
    
    try:
        response = requests.get(f"{BASE_URL}/resumes/")
        response.raise_for_status()
        resumes = response.json()
        print_success(f"Retrieved {len(resumes)} resumes")
        return resumes
    except Exception as e:
        print_fail(f"Failed to get resumes: {str(e)}")
        return []

def test_get_resume_detail(resume_id):
    print_header(f"Testing Get Resume Detail")
    
    try:
        response = requests.get(f"{BASE_URL}/resumes/{resume_id}/?include=detail")
        response.raise_for_status()
        resume = response.json()
        print_success(f"Retrieved resume details for '{resume['title']}'")
        return resume
    except Exception as e:
        print_fail(f"Failed to get resume details: {str(e)}")
        return None

def test_update_resume(resume_id):
    print_header("Testing Resume Update")
    
    update_data = {
        "summary": "Updated summary with additional skills and expertise in cloud architecture.",
        "skills": ["Python", "Django", "JavaScript", "React", "Docker", "AWS", "Cloud Architecture"]
    }
    
    try:
        response = requests.patch(f"{BASE_URL}/resumes/{resume_id}/", json=update_data)
        response.raise_for_status()
        updated_resume = response.json()
        print_success("Resume updated successfully")
        
        # Verify changes
        if "Cloud Architecture" in updated_resume["skills"]:
            print_success("Skills updated successfully")
        else:
            print_fail("Skills not updated correctly")
            
        if update_data["summary"] == updated_resume["summary"]:
            print_success("Summary updated successfully")
        else:
            print_fail("Summary not updated correctly")
            
        return updated_resume
    except Exception as e:
        print_fail(f"Failed to update resume: {str(e)}")
        return None

def test_add_work_experience(resume_id):
    print_header("Testing Add Work Experience")
    
    work_exp_data = {
        "resume": resume_id,
        "position": "Senior Software Engineer",
        "company": "Tech Innovations Inc.",
        "start_date": "2018-01-01",
        "end_date": "2023-01-01",
        "description": "Led a team of 5 developers building scalable web applications. Improved system performance by 35% through code optimization."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/work-experiences/", json=work_exp_data)
        response.raise_for_status()
        work_exp = response.json()
        print_success("Work experience added successfully")
        print_info(f"Work Experience ID: {work_exp['id']}")
        return work_exp
    except Exception as e:
        print_fail(f"Failed to add work experience: {str(e)}")
        return None

def test_add_education(resume_id):
    print_header("Testing Add Education")
    
    education_data = {
        "resume": resume_id,
        "degree": "B.S. Computer Science",
        "school": "University of California",
        "start_date": "2010-09-01",
        "end_date": "2014-05-30"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/educations/", json=education_data)
        response.raise_for_status()
        education = response.json()
        print_success("Education added successfully")
        print_info(f"Education ID: {education['id']}")
        return education
    except Exception as e:
        print_fail(f"Failed to add education: {str(e)}")
        return None

def test_add_project(resume_id):
    print_header("Testing Add Project")
    
    project_data = {
        "resume": resume_id,
        "title": "E-commerce Platform",
        "description": "Developed a full-stack e-commerce platform using Django and React.",
        "start_date": "2020-03-01",
        "end_date": "2020-09-30"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/projects/", json=project_data)
        response.raise_for_status()
        project = response.json()
        print_success("Project added successfully")
        print_info(f"Project ID: {project['id']}")
        return project
    except Exception as e:
        print_fail(f"Failed to add project: {str(e)}")
        return None

def test_resume_parsing():
    print_header("Testing Resume Parsing")
    
    # Create a simple text file as a mock resume
    with open("mock_resume.txt", "w") as f:
        f.write("Jane Smith - Software Engineer\nExperienced in Python, Django, and React")
    
    try:
        files = {'resume': open('mock_resume.txt', 'rb')}
        response = requests.post(f"{BASE_URL}/parse-resume/", files=files)
        response.raise_for_status()
        parsed_data = response.json()
        print_success("Resume parsed successfully")
        print_info(f"Extracted name: {parsed_data['first_name']} {parsed_data['last_name']}")
        
        # Clean up
        os.remove("mock_resume.txt")
        return parsed_data
    except Exception as e:
        print_fail(f"Failed to parse resume: {str(e)}")
        # Clean up
        if os.path.exists("mock_resume.txt"):
            os.remove("mock_resume.txt")
        return None

def test_adapt_resume(resume_id):
    print_header("Testing Resume Adaptation")
    
    adaptation_data = {
        "resume_id": resume_id,
        "job_title": "Full Stack Developer",
        "company": "Innovative Solutions",
        "job_description": """
        We are looking for a Full Stack Developer to join our growing team. The ideal candidate 
        will have experience with Python, Django, and React. Responsibilities include developing 
        and maintaining web applications, collaborating with cross-functional teams, and ensuring 
        high-quality code through testing and code reviews.

        Requirements:
        - 3+ years of experience with Python
        - Experience with Django or similar web frameworks
        - Familiarity with React or other front-end frameworks
        - Understanding of RESTful APIs and web services
        - Experience with database design and SQL
        - Knowledge of containerization (Docker) and cloud services (preferably AWS)
        """
    }
    
    try:
        print_info("This may take a moment as it involves AI processing...")
        response = requests.post(f"{BASE_URL}/adapt-resume/", json=adaptation_data)
        response.raise_for_status()
        adapted_resume = response.json()
        print_success("Resume adapted successfully")
        print_info(f"Adapted Resume ID: {adapted_resume['id']}")
        print_info(f"Title: {adapted_resume['title']}")
        
        if 'additional_suggestions' in adapted_resume:
            print_info(f"Additional Suggestions: {adapted_resume['additional_suggestions']}")
            
        return adapted_resume
    except requests.exceptions.HTTPError as e:
        print_fail(f"Failed to adapt resume: {str(e)}")
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                print_info(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print_info(f"Error response text: {e.response.text}")
        return None
    except Exception as e:
        print_fail(f"Unexpected error: {str(e)}")
        return None

def test_delete_resume(resume_id):
    print_header("Testing Resume Deletion")
    
    try:
        response = requests.delete(f"{BASE_URL}/resumes/{resume_id}/")
        response.raise_for_status()
        print_success(f"Resume with ID {resume_id} deleted successfully")
        return True
    except Exception as e:
        print_fail(f"Failed to delete resume: {str(e)}")
        return False

def run_tests():
    print_header("RESUME MANAGEMENT API TEST SUITE")
    
    # Test creating a resume
    resume = test_create_resume()
    if not resume:
        print_fail("Aborting tests: Resume creation failed")
        return
    
    # Store the resume ID for subsequent tests
    resume_id = resume["id"]
    
    # Test getting all resumes
    test_get_resumes()
    
    # Test getting resume details
    test_get_resume_detail(resume_id)
    
    # Test updating a resume
    test_update_resume(resume_id)
    
    # Test adding components
    test_add_work_experience(resume_id)
    test_add_education(resume_id)
    test_add_project(resume_id)
    
    # Test resume parsing
    test_resume_parsing()
    
    # Test resume adaptation with AI
    adapted_resume = test_adapt_resume(resume_id)
    
    # Clean up: delete the resumes
    if resume:
        test_delete_resume(resume_id)
    
    if adapted_resume:
        test_delete_resume(adapted_resume['id'])
    
    print_header("TEST SUITE COMPLETED")

if __name__ == "__main__":
    run_tests() 