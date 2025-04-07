#!/usr/bin/env python
"""
Test script to verify API endpoints are working with Supabase PostgreSQL database.
"""

import requests
import json
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

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

def test_resume_api():
    """Test Resume API endpoints"""
    console.rule("[bold blue]Testing Resume API Endpoints")
    
    # Generate a unique user ID for testing
    user_id = str(uuid.uuid4())
    
    # Test POST /resumes/ endpoint (Create)
    console.print("\n[bold cyan]1. Creating a new resume...[/bold cyan]")
    resume_data = {
        "user_id": user_id,
        "title": "API Test Resume",
        "template": "professional",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "job_title": "Full Stack Developer",
        "skills": ["JavaScript", "TypeScript", "React", "Node.js"]
    }
    
    response = requests.post(f"{BASE_URL}/resumes/", json=resume_data)
    print_response(response, "Create Resume Response")
    
    if response.status_code != 201:
        console.print("[bold red]Failed to create resume. Stopping tests.[/bold red]")
        return
    
    # Get the resume ID from the response
    resume_id = response.json()["id"]
    console.print(f"[bold green]Resume created with ID: {resume_id}[/bold green]")
    
    # Test GET /resumes/{id}/ endpoint (Read)
    console.print("\n[bold cyan]2. Retrieving the created resume...[/bold cyan]")
    response = requests.get(f"{BASE_URL}/resumes/{resume_id}/")
    print_response(response, "Get Resume Response")
    
    # Test PATCH /resumes/{id}/ endpoint (Update)
    console.print("\n[bold cyan]3. Updating the resume...[/bold cyan]")
    update_data = {
        "job_title": "Senior Full Stack Developer",
        "skills": ["JavaScript", "TypeScript", "React", "Node.js", "GraphQL", "AWS"]
    }
    
    response = requests.patch(f"{BASE_URL}/resumes/{resume_id}/", json=update_data)
    print_response(response, "Update Resume Response")
    
    # Test adding a work experience
    console.print("\n[bold cyan]4. Adding work experience...[/bold cyan]")
    work_exp_data = {
        "resume": resume_id,
        "position": "Full Stack Developer",
        "company": "Tech Solutions Inc.",
        "start_date": "2020-03-01",
        "end_date": "2023-04-30",
        "description": "Developed and maintained web applications using React and Node.js."
    }
    
    response = requests.post(f"{BASE_URL}/work-experiences/", json=work_exp_data)
    print_response(response, "Create Work Experience Response")
    
    if response.status_code == 201:
        work_exp_id = response.json()["id"]
        console.print(f"[bold green]Work experience created with ID: {work_exp_id}[/bold green]")
    
    # Test GET /resumes/{id}/?include=detail endpoint (Read with relations)
    console.print("\n[bold cyan]5. Retrieving resume with related data...[/bold cyan]")
    response = requests.get(f"{BASE_URL}/resumes/{resume_id}/?include=detail")
    print_response(response, "Get Resume with Related Data Response")
    
    # Test DELETE /resumes/{id}/ endpoint (Delete)
    console.print("\n[bold cyan]6. Deleting the resume...[/bold cyan]")
    response = requests.delete(f"{BASE_URL}/resumes/{resume_id}/")
    
    if response.status_code == 204:
        console.print("[bold green]Resume deleted successfully (Status: 204)[/bold green]")
    else:
        print_response(response, "Delete Resume Response")
    
    # Verify resume is deleted
    console.print("\n[bold cyan]7. Verifying resume deletion...[/bold cyan]")
    response = requests.get(f"{BASE_URL}/resumes/{resume_id}/")
    
    if response.status_code == 404:
        console.print("[bold green]Resume deletion verified (Status: 404)[/bold green]")
    else:
        print_response(response, "Verification Response")

if __name__ == "__main__":
    console.print("[bold]API Endpoint Testing with Supabase PostgreSQL[/bold]")
    console.print("This script tests the API endpoints to verify they're working with the new database.\n")
    
    # Test Resume API endpoints
    test_resume_api()
    
    console.print("\n[bold green]Testing completed![/bold green]") 