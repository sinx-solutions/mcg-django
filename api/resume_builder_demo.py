#!/usr/bin/env python
import requests
import json
import uuid
import os
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.text import Text
from rich.syntax import Syntax
from rich import box

# API base URL
BASE_URL = "http://localhost:8000/api"

# Initialize rich console for pretty output
console = Console()

# Resume creation flow stages
RESUME_STAGES = [
    "General info",
    "Personal info",
    "Work experience",
    "Education",
    "Skills",
    "Projects", 
    "Certifications",
    "Summary",
    "Custom sections"
]

def display_api_call(method, endpoint, data=None):
    """Display the API call being made"""
    # Create table for the API call
    api_table = Table(title=f"[bold blue]API Call: {method} {endpoint}", box=box.ROUNDED)
    api_table.add_column("Detail", style="cyan")
    api_table.add_column("Value", style="green")
    
    api_table.add_row("Method", method)
    api_table.add_row("Endpoint", endpoint)
    
    if data:
        # Truncate large data objects to avoid overwhelming the console
        if isinstance(data, dict) and len(str(data)) > 1000:
            # Create a simpler representation for large objects
            if 'description' in data and len(data['description']) > 100:
                data['description'] = data['description'][:100] + "..."
        
        formatted_data = json.dumps(data, indent=2)
        
        # Use Syntax highlighting for JSON
        json_syntax = Syntax(formatted_data, "json", theme="monokai", line_numbers=False)
        api_table.add_row("Request Data", "")
        console.print(api_table)
        console.print(Panel(json_syntax, title="Request Payload", border_style="blue"))
    else:
        console.print(api_table)

def display_api_response(response):
    """Display the API response"""
    try:
        # Try to parse as JSON for proper formatting
        response_data = response.json()
        # Truncate large response objects
        if isinstance(response_data, dict) and 'description' in response_data and isinstance(response_data['description'], str) and len(response_data['description']) > 100:
            response_data['description'] = response_data['description'][:100] + "..."
        
        if isinstance(response_data, list) and len(response_data) > 3:
            # Just show the first 3 items for lists
            truncated_data = response_data[:3]
            truncated_data.append({"note": f"... {len(response_data) - 3} more items (truncated)"})
            response_data = truncated_data
            
        formatted_data = json.dumps(response_data, indent=2)
        
        response_syntax = Syntax(formatted_data, "json", theme="monokai", line_numbers=False)
        
        # Create a response panel with status code
        color = "green" if response.status_code < 400 else "red"
        console.print(Panel(
            response_syntax,
            title=f"[bold {color}]Response (Status: {response.status_code})",
            border_style=color
        ))
    except ValueError:
        # Not JSON, just display as text
        console.print(Panel(
            response.text, 
            title=f"[bold {'green' if response.status_code < 400 else 'red'}]Response (Status: {response.status_code})",
            border_style="green" if response.status_code < 400 else "red"
        ))

def api_request(method, endpoint, data=None, display=True, files=None):
    """Make an API request and optionally display the details"""
    full_url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    
    if display:
        display_api_call(method, full_url, data)
    
    if method.lower() == 'get':
        response = requests.get(full_url)
    elif method.lower() == 'post':
        if files:
            response = requests.post(full_url, files=files)
        else:
            response = requests.post(full_url, json=data)
    elif method.lower() == 'put':
        response = requests.put(full_url, json=data)
    elif method.lower() == 'patch':
        response = requests.patch(full_url, json=data)
    elif method.lower() == 'delete':
        response = requests.delete(full_url)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    if display:
        display_api_response(response)
    
    return response

def create_resume_stage_by_stage():
    """
    Create a resume by going through each stage of the resume building process
    """
    console.rule("[bold blue]Resume Builder Demo - Creating a Resume Stage by Stage")
    
    # Start with creating an empty resume with just basic info
    user_id = str(uuid.uuid4())
    resume_data = {
        "user_id": user_id,
        "title": "Software Engineer Resume",
        "template": "classic"
    }
    
    # Stage 1: General Info
    console.print(f"\n[bold blue]Stage 1: Creating resume with General Info")
    
    # Make API call
    response = api_request('POST', '/resumes/', resume_data)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to create resume: {response.text}")
        return None
    
    resume = response.json()
    resume_id = resume["id"]
    
    console.print(Panel(f"[bold green]✓ Resume created successfully with ID: {resume_id}"))
    
    # Stage 2: Add Personal Info
    console.print(f"\n[bold blue]Stage 2: Adding Personal Info")
    
    personal_info = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com",
        "phone": "123-456-7890",
        "city": "San Francisco",
        "country": "USA",
        "job_title": "Senior Software Engineer"
    }
    
    # Display the personal info we're adding
    personal_info_table = Table(title="Personal Information", box=box.ROUNDED)
    personal_info_table.add_column("Field", style="cyan")
    personal_info_table.add_column("Value", style="green")
    
    for field, value in personal_info.items():
        personal_info_table.add_row(field, str(value))
    
    console.print(personal_info_table)
    
    # Make API call
    response = api_request('PATCH', f'/resumes/{resume_id}/', personal_info)
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to update personal info: {response.text}")
        return None
    
    console.print("[bold green]✓ Personal information added successfully")
    
    # Stage 3: Add Work Experience
    console.print(f"\n[bold blue]Stage 3: Adding Work Experience")
    
    work_experiences = [
        {
            "resume": resume_id,
            "position": "Senior Software Engineer",
            "company": "Tech Innovations Inc.",
            "start_date": "2020-01-01",
            "end_date": "2023-01-01",
            "description": "Led a team of 5 developers building scalable web applications using Python, Django, and React. Implemented CI/CD pipelines and containerized the application with Docker. Improved system performance by 35% through code optimization and query refinement."
        },
        {
            "resume": resume_id,
            "position": "Software Engineer",
            "company": "Digital Solutions",
            "start_date": "2017-03-01",
            "end_date": "2019-12-31",
            "description": "Developed RESTful APIs and microservices using Python and Flask. Implemented front-end components using React and Redux. Participated in Agile development processes and code reviews."
        }
    ]
    
    # Display the work experiences we're adding
    for i, exp in enumerate(work_experiences):
        console.print(Panel(
            f"[bold]Position:[/bold] {exp['position']}\n"
            f"[bold]Company:[/bold] {exp['company']}\n"
            f"[bold]Period:[/bold] {exp['start_date']} to {exp['end_date']}\n"
            f"[bold]Description:[/bold] {exp['description']}",
            title=f"Work Experience {i+1}",
            border_style="blue"
        ))
    
    for i, exp in enumerate(work_experiences):
        console.print(f"\n[bold cyan]Adding Work Experience {i+1}...[/bold cyan]")
        
        # Make API call
        response = api_request('POST', '/work-experiences/', exp)
        
        if response.status_code != 201:
            console.print(f"[bold red]Failed to add work experience: {response.text}")
            continue
        
        exp_id = response.json()["id"]
        console.print(f"[bold green]✓ Work experience added successfully (ID: {exp_id})")
    
    # Stage 4: Add Education
    console.print(f"\n[bold blue]Stage 4: Adding Education")
    
    educations = [
        {
            "resume": resume_id,
            "degree": "M.S. Computer Science",
            "school": "Stanford University",
            "start_date": "2015-09-01",
            "end_date": "2017-05-30"
        },
        {
            "resume": resume_id,
            "degree": "B.S. Computer Science",
            "school": "University of California, Berkeley",
            "start_date": "2011-09-01",
            "end_date": "2015-05-30"
        }
    ]
    
    # Display the educations we're adding
    for i, edu in enumerate(educations):
        console.print(Panel(
            f"[bold]Degree:[/bold] {edu['degree']}\n"
            f"[bold]School:[/bold] {edu['school']}\n"
            f"[bold]Period:[/bold] {edu['start_date']} to {edu['end_date']}",
            title=f"Education {i+1}",
            border_style="blue"
        ))
    
    for i, edu in enumerate(educations):
        console.print(f"\n[bold cyan]Adding Education {i+1}...[/bold cyan]")
        
        # Make API call
        response = api_request('POST', '/educations/', edu)
        
        if response.status_code != 201:
            console.print(f"[bold red]Failed to add education: {response.text}")
            continue
        
        edu_id = response.json()["id"]
        console.print(f"[bold green]✓ Education added successfully (ID: {edu_id})")
    
    # Stage 5: Add Skills
    console.print(f"\n[bold blue]Stage 5: Adding Skills")
    
    skills = ["Python", "Django", "React", "JavaScript", "Docker", "Kubernetes", "AWS", "PostgreSQL", "RESTful APIs", "CI/CD", "Agile Methodologies", "Team Leadership"]
    
    # Display the skills we're adding
    skills_table = Table(title="Skills", box=box.ROUNDED)
    skills_table.add_column("Skills", style="green")
    
    # Format skills in rows of 4
    for i in range(0, len(skills), 4):
        skills_row = skills[i:i+4]
        skills_table.add_row(", ".join(skills_row))
    
    console.print(skills_table)
    
    # Make API call
    response = api_request('PATCH', f'/resumes/{resume_id}/', {"skills": skills})
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to update skills: {response.text}")
    else:
        console.print("[bold green]✓ Skills added successfully")
    
    # Stage 6: Add Projects
    console.print(f"\n[bold blue]Stage 6: Adding Projects")
    
    projects = [
        {
            "resume": resume_id,
            "title": "E-commerce Platform",
            "description": "Built a scalable e-commerce platform using Django, React, and PostgreSQL. Implemented features like product search, shopping cart, payment processing, and order tracking. Deployed on AWS using Docker and Kubernetes.",
            "start_date": "2020-05-01",
            "end_date": "2020-12-31"
        },
        {
            "resume": resume_id,
            "title": "Data Analytics Dashboard",
            "description": "Developed a real-time analytics dashboard using Python, Django, React, and D3.js. Integrated with various data sources and APIs to visualize key business metrics. Implemented user authentication and role-based access control.",
            "start_date": "2019-02-01",
            "end_date": "2019-08-31"
        }
    ]
    
    # Display the projects we're adding
    for i, proj in enumerate(projects):
        console.print(Panel(
            f"[bold]Title:[/bold] {proj['title']}\n"
            f"[bold]Period:[/bold] {proj['start_date']} to {proj['end_date']}\n"
            f"[bold]Description:[/bold] {proj['description']}",
            title=f"Project {i+1}",
            border_style="blue"
        ))
    
    for i, proj in enumerate(projects):
        console.print(f"\n[bold cyan]Adding Project {i+1}...[/bold cyan]")
        
        # Make API call
        response = api_request('POST', '/projects/', proj)
        
        if response.status_code != 201:
            console.print(f"[bold red]Failed to add project: {response.text}")
            continue
        
        proj_id = response.json()["id"]
        console.print(f"[bold green]✓ Project added successfully (ID: {proj_id})")
    
    # Stage 7: Add Certifications
    console.print(f"\n[bold blue]Stage 7: Adding Certifications")
    
    certifications = [
        {
            "resume": resume_id,
            "name": "AWS Certified Solutions Architect",
            "issuer": "Amazon Web Services",
            "issue_date": "2022-06-01",
            "expiry_date": "2025-06-01"
        },
        {
            "resume": resume_id,
            "name": "Certified Kubernetes Administrator",
            "issuer": "Cloud Native Computing Foundation",
            "issue_date": "2021-03-15",
            "expiry_date": "2024-03-15"
        }
    ]
    
    # Display the certifications we're adding
    for i, cert in enumerate(certifications):
        console.print(Panel(
            f"[bold]Name:[/bold] {cert['name']}\n"
            f"[bold]Issuer:[/bold] {cert['issuer']}\n"
            f"[bold]Issued:[/bold] {cert['issue_date']}\n"
            f"[bold]Expires:[/bold] {cert['expiry_date']}",
            title=f"Certification {i+1}",
            border_style="blue"
        ))
    
    for i, cert in enumerate(certifications):
        console.print(f"\n[bold cyan]Adding Certification {i+1}...[/bold cyan]")
        
        # Make API call
        response = api_request('POST', '/certifications/', cert)
        
        if response.status_code != 201:
            console.print(f"[bold red]Failed to add certification: {response.text}")
            continue
        
        cert_id = response.json()["id"]
        console.print(f"[bold green]✓ Certification added successfully (ID: {cert_id})")
    
    # Stage 8: Add Summary
    console.print(f"\n[bold blue]Stage 8: Adding Summary")
    
    summary = (
        "Experienced Software Engineer with over 6 years of expertise in full-stack development, "
        "specializing in Python, Django, React, and cloud technologies. Proven track record of leading "
        "development teams, architecting scalable solutions, and improving system performance. "
        "Strong skills in RESTful APIs, containerization, and CI/CD pipelines. "
        "Passionate about clean code, performance optimization, and creating exceptional user experiences."
    )
    
    console.print(Panel(summary, title="Professional Summary", border_style="green"))
    
    # Make API call
    response = api_request('PATCH', f'/resumes/{resume_id}/', {"summary": summary})
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to update summary: {response.text}")
    else:
        console.print("[bold green]✓ Summary added successfully")
    
    # Stage 9: Add Custom Sections
    console.print(f"\n[bold blue]Stage 9: Adding Custom Sections")
    
    # Create a custom section for Publications
    custom_section = {
        "resume": resume_id,
        "title": "Publications"
    }
    
    console.print("\n[bold cyan]Creating Custom Section 'Publications'...[/bold cyan]")
    
    # Make API call
    response = api_request('POST', '/custom-sections/', custom_section)
    
    if response.status_code != 201:
        console.print(f"[bold red]Failed to create custom section: {response.text}")
        custom_section_id = None
    else:
        custom_section_id = response.json()["id"]
        console.print(f"[bold green]✓ Custom section created successfully (ID: {custom_section_id})")
    
    if custom_section_id:
        # Add items to the custom section
        publications = [
            {
                "custom_section": custom_section_id,
                "title": "Modern Approaches to Microservices Architecture",
                "description": "Published in Journal of Software Engineering, 2022. Discussed patterns and best practices for designing microservices architectures with Python and Go.",
                "start_date": "2022-03-01"
            },
            {
                "custom_section": custom_section_id,
                "title": "Optimizing React Applications for Performance",
                "description": "Published in Frontend Quarterly, 2021. Explored techniques for improving React application performance, including code splitting, memoization, and rendering optimization.",
                "start_date": "2021-06-01"
            }
        ]
        
        # Display the publications we're adding
        for i, pub in enumerate(publications):
            console.print(Panel(
                f"[bold]Title:[/bold] {pub['title']}\n"
                f"[bold]Date:[/bold] {pub['start_date']}\n"
                f"[bold]Description:[/bold] {pub['description']}",
                title=f"Publication {i+1}",
                border_style="blue"
            ))
        
        for i, pub in enumerate(publications):
            console.print(f"\n[bold cyan]Adding Publication {i+1}...[/bold cyan]")
            
            # Make API call
            response = api_request('POST', '/custom-section-items/', pub)
            
            if response.status_code != 201:
                console.print(f"[bold red]Failed to add publication: {response.text}")
                continue
            
            pub_id = response.json()["id"]
            console.print(f"[bold green]✓ Publication added successfully (ID: {pub_id})")
    
    # Get the final resume with all sections
    console.print(f"\n[bold blue]Retrieving Complete Resume")
    
    # Make API call
    response = api_request('GET', f'/resumes/{resume_id}/?include=detail')
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to retrieve complete resume: {response.text}")
        return None
    
    complete_resume = response.json()
    
    # Display summary of the complete resume
    console.print("\n[bold green]Resume Creation Complete!")
    
    resume_info_table = Table(title=f"Resume: {complete_resume['title']}", box=box.ROUNDED)
    resume_info_table.add_column("Section", style="cyan")
    resume_info_table.add_column("Content", style="green")
    
    personal_info = f"{complete_resume['first_name']} {complete_resume['last_name']}"
    if complete_resume.get('job_title'):
        personal_info += f", {complete_resume['job_title']}"
    if complete_resume.get('email'):
        personal_info += f" | {complete_resume['email']}"
    if complete_resume.get('phone'):
        personal_info += f" | {complete_resume['phone']}"
    if complete_resume.get('city') and complete_resume.get('country'):
        personal_info += f" | {complete_resume['city']}, {complete_resume['country']}"
    
    resume_info_table.add_row("Personal Info", personal_info)
    
    if complete_resume.get('summary'):
        summary_text = complete_resume['summary']
        if len(summary_text) > 100:
            summary_text = summary_text[:100] + "..."
        resume_info_table.add_row("Summary", summary_text)
    
    if complete_resume.get('skills'):
        resume_info_table.add_row("Skills", ", ".join(complete_resume['skills'][:5]) + "...")
    
    if complete_resume.get('work_experiences'):
        work_exp_text = f"{len(complete_resume['work_experiences'])} work experiences"
        resume_info_table.add_row("Work Experience", work_exp_text)
    
    if complete_resume.get('educations'):
        education_text = f"{len(complete_resume['educations'])} education entries"
        resume_info_table.add_row("Education", education_text)
    
    if complete_resume.get('projects'):
        projects_text = f"{len(complete_resume['projects'])} projects"
        resume_info_table.add_row("Projects", projects_text)
    
    if complete_resume.get('certifications'):
        cert_text = f"{len(complete_resume['certifications'])} certifications"
        resume_info_table.add_row("Certifications", cert_text)
    
    if complete_resume.get('custom_sections'):
        custom_text = f"{len(complete_resume['custom_sections'])} custom sections"
        resume_info_table.add_row("Custom Sections", custom_text)
    
    console.print(resume_info_table)
    
    return resume_id

def test_adapt_resume(resume_id):
    """
    Adapt a resume for a job using AI
    """
    console.rule("[bold blue]Resume Adaptation with AI")
    
    job_posting = {
        "title": "Senior Full Stack Developer",
        "company": "Tech Innovators",
        "description": """
        We are seeking a Senior Full Stack Developer with expertise in modern web technologies
        to join our product development team. The ideal candidate will have a strong background
        in building scalable web applications with Python (Django/Flask) and React.
        
        Key Responsibilities:
        - Design, develop, and maintain web applications using Python and React
        - Collaborate with cross-functional teams to define and implement new features
        - Optimize applications for maximum speed and scalability
        - Implement security and data protection
        - Write clean, maintainable code with appropriate tests
        
        Requirements:
        - 5+ years of experience in full-stack development
        - Strong expertise in Python and JavaScript/TypeScript
        - Experience with Django or Flask
        - Proficiency in React and modern frontend development
        - Knowledge of database design and SQL
        - Experience with Docker containerization
        - Familiarity with cloud services (AWS, Azure, GCP)
        - Excellent problem-solving and communication skills
        """
    }
    
    console.print(Panel(
        f"[bold]Title:[/bold] {job_posting['title']}\n"
        f"[bold]Company:[/bold] {job_posting['company']}\n\n"
        f"{job_posting['description']}",
        title="Job Posting",
        border_style="green",
        width=100
    ))
    
    adaptation_data = {
        "resume_id": resume_id,
        "job_title": job_posting["title"],
        "company": job_posting["company"],
        "job_description": job_posting["description"]
    }
    
    console.print("\n[bold blue]Adapting resume for the job posting using Claude AI...")
    console.print("\n[bold cyan]Making AI Adaptation API Call...[/bold cyan]")
    
    # Display and make the API call
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
        
        # Display the API call but don't show the response immediately (it will be large)
        display_api_call('POST', f"{BASE_URL}/adapt-resume/", adaptation_data)
        response = requests.post(f"{BASE_URL}/adapt-resume/", json=adaptation_data)
        progress.update(task, completed=True)
    
    # Display a summarized version of the response
    if response.status_code != 201:
        console.print(f"[bold red]Failed to adapt resume: {response.text}")
        return None
    
    try:
        adapted_resume = response.json()
        # Extract just the key points from the response
        console.print(Panel(
            f"[bold]Resume ID:[/bold] {adapted_resume['id']}\n"
            f"[bold]Title:[/bold] {adapted_resume['title']}\n"
            f"[bold]Message:[/bold] {adapted_resume['message']}",
            title="[bold green]Response (Status: 201)",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error parsing response: {str(e)}")
        return None
    
    console.print("[bold green]✓ Resume adapted successfully!")
    
    # Get the adapted resume details
    console.print("\n[bold cyan]Fetching Adapted Resume Details...[/bold cyan]")
    
    # Make API call
    response = api_request('GET', f'/resumes/{adapted_resume["id"]}/?include=detail')
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to retrieve adapted resume: {response.text}")
        return None
    
    adapted_resume_detail = response.json()
    
    # Display the adaptation results
    console.print("\n[bold blue]Resume Adaptation Results")
    
    # Show the tailored summary
    if adapted_resume_detail.get('summary'):
        console.print(Panel(
            adapted_resume_detail['summary'],
            title="Tailored Summary",
            border_style="green",
            width=100
        ))
    
    # Show prioritized skills
    if adapted_resume_detail.get('skills'):
        skills_table = Table(title="Prioritized Skills", box=box.ROUNDED)
        skills_table.add_column("Skills", style="green")
        
        # Format skills in rows of 4
        skills = adapted_resume_detail['skills']
        for i in range(0, len(skills), 4):
            skills_row = skills[i:i+4]
            skills_table.add_row(", ".join(skills_row))
        
        console.print(skills_table)
    
    # Show a sample of enhanced work experiences
    if adapted_resume_detail.get('work_experiences') and len(adapted_resume_detail['work_experiences']) > 0:
        console.print("\n[bold blue]Enhanced Work Experiences")
        for i, exp in enumerate(adapted_resume_detail['work_experiences'][:2]):  # Show first 2
            console.print(Panel(
                f"[bold]Position:[/bold] {exp['position']}\n"
                f"[bold]Company:[/bold] {exp['company']}\n"
                f"[bold]Period:[/bold] {exp['start_date']} to {exp['end_date']}\n"
                f"[bold]Description:[/bold] {exp['description']}",
                title=f"Enhanced Work Experience {i+1}",
                border_style="blue",
                width=100
            ))
    
    # Show additional suggestions
    if 'additional_suggestions' in adapted_resume:
        console.print(Panel(
            adapted_resume['additional_suggestions'],
            title="Additional Suggestions from AI",
            border_style="cyan",
            width=100
        ))
    
    return adapted_resume['id']

def main():
    console.print(Markdown("# Resume Builder API Demonstration"))
    console.print("\nThis demonstration will walk through the complete resume creation process, stage by stage:")
    
    # Print the stages
    for i, stage in enumerate(RESUME_STAGES, 1):
        console.print(f"  {i}. [bold cyan]{stage}[/bold cyan]")
    
    console.print("\nFollowed by AI-powered resume adaptation for a specific job posting.")
    console.print("[bold yellow]Note:[/bold yellow] Make sure the Django API server is running on localhost:8000")
    
    # Confirm if server is running
    console.print("\n[bold cyan]Checking API Server Connection...[/bold cyan]")
    try:
        response = api_request('GET', '/resumes/', display=False)
        if response.status_code >= 400:
            console.print("[bold red]Error: API server is not responding correctly. Please make sure it's running.")
            return
        console.print("[bold green]✓ API server is running and responding")
    except Exception:
        console.print("[bold red]Error: Could not connect to the API server. Please make sure it's running on localhost:8000")
        return
    
    console.print("\nPress Enter to begin the demonstration...", end="")
    input()
    
    # Create a resume stage by stage
    resume_id = create_resume_stage_by_stage()
    
    if resume_id:
        console.print("\nPress Enter to continue to resume adaptation with AI...", end="")
        input()
        
        # Adapt the resume for a job
        adapted_resume_id = test_adapt_resume(resume_id)
        
        # Clean up - delete the resumes
        console.print("\n[bold blue]Cleaning up...")
        
        if resume_id:
            console.print("\n[bold cyan]Deleting Original Resume...[/bold cyan]")
            response = api_request('DELETE', f'/resumes/{resume_id}/')
            if response.status_code == 204:
                console.print(f"[bold green]✓ Original resume deleted successfully")
            else:
                console.print(f"[bold red]Failed to delete original resume: {response.status_code}")
        
        if adapted_resume_id:
            console.print("\n[bold cyan]Deleting Adapted Resume...[/bold cyan]")
            response = api_request('DELETE', f'/resumes/{adapted_resume_id}/')
            if response.status_code == 204:
                console.print(f"[bold green]✓ Adapted resume deleted successfully")
            else:
                console.print(f"[bold red]Failed to delete adapted resume: {response.status_code}")
        
        console.print("[bold green]✓ Cleanup completed")
    
    console.print("\n[bold blue]Demonstration completed! Thank you for watching.")

if __name__ == "__main__":
    main() 