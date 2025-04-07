#!/usr/bin/env python
"""
Test script to verify CRUD operations with Supabase PostgreSQL database.
This script tests creating, reading, updating, and deleting Resume records.
"""

import os
import sys
import django
import uuid
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Now import Django models
from api.models import Resume, WorkExperience, Education, Project

# Terminal colors for better readability
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    """Print a section title"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== {title} ==={Colors.ENDC}")

def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_error(message):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.ENDC}")

def print_info(message):
    """Print an info message"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.ENDC}")

def test_resume_crud():
    """Test CRUD operations on Resume model"""
    print_section("Testing CRUD Operations on Resume Model")
    
    # Generate a unique user ID for testing
    user_id = uuid.uuid4()
    
    try:
        # CREATE operation
        print_info("Creating a test resume...")
        resume = Resume.objects.create(
            user_id=user_id,
            title="Test Resume",
            template="modern",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            job_title="Software Engineer",
            skills=["Python", "Django", "PostgreSQL"]
        )
        resume_id = resume.id
        print_success(f"Resume created with ID: {resume_id}")
        
        # READ operation
        print_info("Reading the created resume...")
        retrieved_resume = Resume.objects.get(id=resume_id)
        print_success(f"Retrieved resume: {retrieved_resume.title} - {retrieved_resume.first_name} {retrieved_resume.last_name}")
        
        # UPDATE operation
        print_info("Updating the resume...")
        retrieved_resume.job_title = "Senior Software Engineer"
        retrieved_resume.skills = ["Python", "Django", "PostgreSQL", "React", "Docker"]
        retrieved_resume.save()
        print_success("Resume updated")
        
        # Verify UPDATE
        updated_resume = Resume.objects.get(id=resume_id)
        print_success(f"Updated job title: {updated_resume.job_title}")
        print_success(f"Updated skills: {', '.join(updated_resume.skills)}")
        
        # Test related models - WorkExperience
        print_info("Adding a work experience to the resume...")
        work_exp = WorkExperience.objects.create(
            resume=retrieved_resume,
            position="Software Engineer",
            company="Tech Company",
            start_date=datetime.strptime("2020-01-01", "%Y-%m-%d").date(),
            end_date=datetime.strptime("2023-01-01", "%Y-%m-%d").date(),
            description="Built amazing software"
        )
        print_success(f"Work experience created with ID: {work_exp.id}")
        
        # Test related models - Education
        print_info("Adding education to the resume...")
        education = Education.objects.create(
            resume=retrieved_resume,
            degree="Bachelor of Science in Computer Science",
            school="University of Technology",
            start_date=datetime.strptime("2016-09-01", "%Y-%m-%d").date(),
            end_date=datetime.strptime("2020-05-30", "%Y-%m-%d").date()
        )
        print_success(f"Education created with ID: {education.id}")
        
        # Test related models - Project
        print_info("Adding a project to the resume...")
        project = Project.objects.create(
            resume=retrieved_resume,
            title="Web Application",
            description="Built a web application using Django and React",
            start_date=datetime.strptime("2022-01-01", "%Y-%m-%d").date(),
            end_date=datetime.strptime("2022-06-30", "%Y-%m-%d").date()
        )
        print_success(f"Project created with ID: {project.id}")
        
        # Test relationships
        print_info("Testing relationships...")
        resume_with_related = Resume.objects.filter(id=resume_id).prefetch_related('work_experiences', 'educations', 'projects').first()
        print_success(f"Resume has {resume_with_related.work_experiences.count()} work experience(s)")
        print_success(f"Resume has {resume_with_related.educations.count()} education(s)")
        print_success(f"Resume has {resume_with_related.projects.count()} project(s)")
        
        # DELETE operation
        print_info("Deleting the resume and checking cascade deletion...")
        # Store IDs for verification
        work_exp_id = work_exp.id
        education_id = education.id
        project_id = project.id
        
        # Delete the resume
        retrieved_resume.delete()
        print_success("Resume deleted")
        
        # Verify DELETE and cascade
        if Resume.objects.filter(id=resume_id).exists():
            print_error("Resume was not deleted!")
        else:
            print_success("Resume deletion verified")
        
        # Check cascade deletion of related records
        if WorkExperience.objects.filter(id=work_exp_id).exists():
            print_error("Work experience was not cascade deleted!")
        else:
            print_success("Work experience cascade deletion verified")
        
        if Education.objects.filter(id=education_id).exists():
            print_error("Education was not cascade deleted!")
        else:
            print_success("Education cascade deletion verified")
        
        if Project.objects.filter(id=project_id).exists():
            print_error("Project was not cascade deleted!")
        else:
            print_success("Project cascade deletion verified")
        
        print_section("All CRUD Tests Completed Successfully")
        return True
    
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print_section("Supabase PostgreSQL Integration Test")
    print_info("Testing connection to Supabase PostgreSQL database...")
    
    try:
        # Get total count of resumes as a simple DB connectivity test
        count = Resume.objects.count()
        print_success(f"Successfully connected to database. Current resume count: {count}")
        
        # Run CRUD tests
        test_resume_crud()
        
    except Exception as e:
        print_error(f"Database connection failed: {str(e)}")
        sys.exit(1) 