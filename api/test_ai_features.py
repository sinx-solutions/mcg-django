#!/usr/bin/env python
"""
Test script for AI enhancement features in the resume builder
This script tests the AI enhancement endpoints for work experience, projects, certifications, summary generation, and skill suggestions
"""

import requests
import json
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

# API base URL
BASE_URL = "http://localhost:8000/api"

# Initialize rich console for pretty output
console = Console()

def print_response(response, title):
    """Print the API response in a nice format"""
    try:
        data = response.json()
        console.print(Panel(
            json.dumps(data, indent=2),
            title=f"[bold green]{title} (Status: {response.status_code})",
            border_style="green" if response.status_code < 400 else "red"
        ))
    except ValueError:
        console.print(Panel(
            response.text,
            title=f"[bold {'green' if response.status_code < 400 else 'red'}]{title} (Status: {response.status_code})",
            border_style="green" if response.status_code < 400 else "red"
        ))

def print_before_after(before, after, title):
    """Print a before/after comparison"""
    console.rule(f"[bold cyan]{title}")
    console.print("[bold yellow]Before:[/bold yellow]")
    console.print(Panel(before, padding=(1, 2)))
    console.print("[bold green]After (AI Enhanced):[/bold green]")
    console.print(Panel(after, padding=(1, 2)))
    console.print()

def create_test_resume():
    """Create a test resume for AI enhancement testing"""
    console.rule("[bold blue]Creating Test Resume")
    
    # Generate a unique user ID for testing
    user_id = str(uuid.uuid4())
    
    # Basic resume data
    resume_data = {
        "user_id": user_id,
        "title": "Software Developer Resume",
        "template": "professional",
        "first_name": "Alex",
        "last_name": "Johnson",
        "email": "alex.johnson@example.com",
        "phone": "555-123-4567",
        "job_title": "Software Developer",
        "city": "San Francisco",
        "country": "USA",
        "skills": ["JavaScript", "React", "Node.js", "HTML", "CSS"]
    }
    
    console.print("[bold cyan]Creating resume...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/resumes/", json=resume_data)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to create resume: {response.text}[/bold red]")
        return None
    
    resume_id = response.json()["id"]
    console.print(f"[bold green]Resume created with ID: {resume_id}[/bold green]")
    
    # Add work experience
    work_exp_data = {
        "resume": resume_id,
        "position": "Junior Developer",
        "company": "Tech Startup Inc.",
        "start_date": "2020-01-01",
        "end_date": "2022-06-30",
        "description": "Worked on front-end development using React. Fixed bugs in the UI. Participated in code reviews. Helped with testing."
    }
    
    console.print("[bold cyan]Adding work experience...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/work-experiences/", json=work_exp_data)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to add work experience: {response.text}[/bold red]")
    else:
        work_exp_id = response.json()["id"]
        console.print(f"[bold green]Work experience added with ID: {work_exp_id}[/bold green]")
    
    # Add project
    project_data = {
        "resume": resume_id,
        "title": "E-commerce Website",
        "start_date": "2021-03-01",
        "end_date": "2021-08-30",
        "description": "Built an online store using React and Node.js. Implemented shopping cart and payment features."
    }
    
    console.print("[bold cyan]Adding project...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/projects/", json=project_data)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to add project: {response.text}[/bold red]")
    else:
        project_id = response.json()["id"]
        console.print(f"[bold green]Project added with ID: {project_id}[/bold green]")
    
    # Add certification
    certification_data = {
        "resume": resume_id,
        "name": "React Developer Certification",
        "issuer": "Frontend Masters",
        "issue_date": "2022-01-15"
    }
    
    console.print("[bold cyan]Adding certification...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/certifications/", json=certification_data)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to add certification: {response.text}[/bold red]")
    else:
        cert_id = response.json()["id"]
        console.print(f"[bold green]Certification added with ID: {cert_id}[/bold green]")
    
    # Add education
    education_data = {
        "resume": resume_id,
        "degree": "Bachelor of Science in Computer Science",
        "school": "University of Technology",
        "start_date": "2016-09-01",
        "end_date": "2020-05-30"
    }
    
    console.print("[bold cyan]Adding education...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/educations/", json=education_data)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to add education: {response.text}[/bold red]")
    else:
        edu_id = response.json()["id"]
        console.print(f"[bold green]Education added with ID: {edu_id}[/bold green]")
    
    # Get the complete resume
    response = requests.get(f"{BASE_URL}/resumes/{resume_id}/?include=detail")
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to retrieve resume: {response.text}[/bold red]")
        return None
    
    console.print(f"[bold green]Test resume created and populated successfully[/bold green]")
    return response.json()

def test_work_experience_enhancement(resume_data):
    """Test the work experience enhancement feature"""
    console.rule("[bold blue]Testing Work Experience Enhancement")
    
    # Find a work experience from the resume
    if not resume_data.get("work_experiences"):
        console.print("[bold red]No work experiences found in the resume[/bold red]")
        return
    
    work_exp = resume_data["work_experiences"][0]
    work_exp_id = work_exp["id"]
    original_description = work_exp["description"]
    
    console.print("[bold cyan]Enhancing work experience description...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/work-experiences/{work_exp_id}/enhance/")
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to enhance work experience: {response.text}[/bold red]")
        return
    
    enhanced_description = response.json()["enhanced_description"]
    
    # Display the before and after
    print_before_after(original_description, enhanced_description, "Work Experience Description Enhancement")
    
    # Update the work experience with the enhanced description
    console.print("[bold cyan]Updating work experience with enhanced description...[/bold cyan]")
    response = requests.patch(f"{BASE_URL}/work-experiences/{work_exp_id}/", json={
        "description": enhanced_description
    })
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to update work experience: {response.text}[/bold red]")
    else:
        console.print("[bold green]Work experience updated successfully[/bold green]")

def test_project_enhancement(resume_data):
    """Test the project enhancement feature"""
    console.rule("[bold blue]Testing Project Enhancement")
    
    # Find a project from the resume
    if not resume_data.get("projects"):
        console.print("[bold red]No projects found in the resume[/bold red]")
        return
    
    project = resume_data["projects"][0]
    project_id = project["id"]
    original_description = project["description"]
    
    console.print("[bold cyan]Enhancing project description...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/projects/{project_id}/enhance/")
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to enhance project: {response.text}[/bold red]")
        return
    
    enhanced_description = response.json()["enhanced_description"]
    
    # Display the before and after
    print_before_after(original_description, enhanced_description, "Project Description Enhancement")
    
    # Update the project with the enhanced description
    console.print("[bold cyan]Updating project with enhanced description...[/bold cyan]")
    response = requests.patch(f"{BASE_URL}/projects/{project_id}/", json={
        "description": enhanced_description
    })
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to update project: {response.text}[/bold red]")
    else:
        console.print("[bold green]Project updated successfully[/bold green]")

def test_certification_enhancement(resume_data):
    """Test the certification enhancement feature"""
    console.rule("[bold blue]Testing Certification Enhancement")
    
    # Find a certification from the resume
    if not resume_data.get("certifications"):
        console.print("[bold red]No certifications found in the resume[/bold red]")
        return
    
    certification = resume_data["certifications"][0]
    cert_id = certification["id"]
    original_description = certification.get("description", "No description provided")
    
    console.print("[bold cyan]Enhancing certification description...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/certifications/{cert_id}/enhance/")
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to enhance certification: {response.text}[/bold red]")
        return
    
    enhanced_description = response.json()["enhanced_description"]
    
    # Display the before and after
    print_before_after(original_description, enhanced_description, "Certification Description Enhancement")
    
    # Update the certification with the enhanced description
    console.print("[bold cyan]Updating certification with enhanced description...[/bold cyan]")
    response = requests.patch(f"{BASE_URL}/certifications/{cert_id}/", json={
        "description": enhanced_description
    })
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to update certification: {response.text}[/bold red]")
    else:
        console.print("[bold green]Certification updated successfully[/bold green]")

def test_summary_generation(resume_data):
    """Test the professional summary generation feature"""
    console.rule("[bold blue]Testing Professional Summary Generation")
    
    resume_id = resume_data["id"]
    original_summary = resume_data.get("summary", "No summary provided")
    
    console.print("[bold cyan]Generating professional summary...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/resumes/{resume_id}/generate_summary/")
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to generate summary: {response.text}[/bold red]")
        return
    
    generated_summary = response.json()["summary"]
    
    # Display the before and after
    print_before_after(original_summary, generated_summary, "Professional Summary Generation")

def test_skills_suggestions(resume_data):
    """Test the skills suggestion feature"""
    console.rule("[bold blue]Testing Skills Suggestion")
    
    resume_id = resume_data["id"]
    existing_skills = resume_data.get("skills", [])
    
    console.print("[bold cyan]Getting skill suggestions...[/bold cyan]")
    response = requests.post(f"{BASE_URL}/resumes/{resume_id}/suggest_skills/")
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to get skill suggestions: {response.text}[/bold red]")
        return
    
    suggested_skills = response.json()["suggested_skills"]
    
    # Display the existing and suggested skills
    console.rule(f"[bold cyan]Skills Comparison")
    console.print("[bold yellow]Existing Skills:[/bold yellow]")
    
    if existing_skills:
        for skill in existing_skills:
            console.print(f"- {skill}")
    else:
        console.print("No existing skills")
    
    console.print("\n[bold green]Suggested Skills:[/bold green]")
    
    if suggested_skills:
        for skill in suggested_skills:
            console.print(f"- {skill}")
    else:
        console.print("No suggested skills")
    
    console.print()

def cleanup(resume_id):
    """Clean up test data"""
    console.rule("[bold blue]Cleaning Up Test Data")
    
    if not resume_id:
        console.print("[bold yellow]No resume ID provided for cleanup[/bold yellow]")
        return
    
    console.print(f"[bold cyan]Deleting resume with ID: {resume_id}...[/bold cyan]")
    response = requests.delete(f"{BASE_URL}/resumes/{resume_id}/")
    
    if response.status_code == 204:
        console.print("[bold green]Resume deleted successfully[/bold green]")
    else:
        console.print(f"[bold red]Failed to delete resume: {response.status_code}[/bold red]")

def main():
    console.print("[bold]Resume Builder AI Enhancement Feature Test[/bold]")
    console.print("This script tests the AI enhancement features for the resume builder.\n")
    
    # Verify server is running
    try:
        response = requests.get(f"{BASE_URL}/resumes/")
        if response.status_code >= 400:
            console.print("[bold red]API server is not responding. Make sure it's running on localhost:8000.[/bold red]")
            return
        console.print("[bold green]Server connection successful[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to connect to server: {str(e)}[/bold red]")
        return
    
    # Ask for user confirmation
    console.print("\n[bold yellow]This script will create test data and test AI enhancement features.[/bold yellow]")
    console.print("[bold yellow]It may take several minutes to run all tests as AI processing takes time.[/bold yellow]")
    console.print("Press Enter to continue or Ctrl+C to exit...", end="")
    input()
    
    # Create test resume
    resume_data = create_test_resume()
    
    if not resume_data:
        console.print("[bold red]Failed to create test resume. Exiting.[/bold red]")
        return
    
    resume_id = resume_data["id"]
    
    try:
        # Test AI enhancement features
        test_work_experience_enhancement(resume_data)
        test_project_enhancement(resume_data)
        test_certification_enhancement(resume_data)
        test_summary_generation(resume_data)
        test_skills_suggestions(resume_data)
        
        # Clean up test data
        console.print("\nPress Enter to clean up test data or Ctrl+C to keep it...", end="")
        input()
        cleanup(resume_id)
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Test interrupted. Cleaning up...[/bold yellow]")
        cleanup(resume_id)
    except Exception as e:
        console.print(f"\n[bold red]An error occurred: {str(e)}[/bold red]")
        console.print("[bold yellow]Cleaning up test data...[/bold yellow]")
        cleanup(resume_id)
    
    console.print("\n[bold green]Testing completed![/bold green]")

if __name__ == "__main__":
    main() 