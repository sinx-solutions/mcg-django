#!/usr/bin/env python
"""
Resume Builder Flow Demo

This script demonstrates the full resume creation flow, showing each step of the UI workflow
with the corresponding API endpoints, request data, and responses.
"""

import requests
import json
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
import time

# API base URL
BASE_URL = "http://localhost:8000/api"

# Initialize rich console for pretty output
console = Console()

def display_api_call(method, endpoint, data=None, headers=None):
    """Display the API call being made"""
    # Create table for the API call
    api_table = Table(title=f"[bold blue]API Call: {method} {endpoint}", box=box.ROUNDED)
    api_table.add_column("Detail", style="cyan")
    api_table.add_column("Value", style="green")
    
    api_table.add_row("Method", method)
    api_table.add_row("Endpoint", endpoint)
    
    if headers:
        headers_str = json.dumps(headers, indent=2)
        api_table.add_row("Headers", headers_str)
    
    if data:
        # Format data nicely
        formatted_data = json.dumps(data, indent=2)
        
        # Use Syntax highlighting for JSON
        json_syntax = Syntax(formatted_data, "json", theme="monokai", line_numbers=False)
        api_table.add_row("Request Data", "")
        console.print(api_table)
        console.print(Panel(json_syntax, title="Request Payload", border_style="blue"))
    else:
        console.print(api_table)

def display_api_response(response, title=None):
    """Display the API response"""
    if not title:
        title = "Response"
        
    try:
        # Try to parse as JSON for proper formatting
        response_data = response.json()
        formatted_data = json.dumps(response_data, indent=2)
        
        response_syntax = Syntax(formatted_data, "json", theme="monokai", line_numbers=False)
        
        # Create a response panel with status code
        color = "green" if response.status_code < 400 else "red"
        console.print(Panel(
            response_syntax,
            title=f"[bold {color}]{title} (Status: {response.status_code})",
            border_style=color
        ))
        return response_data
    except ValueError:
        # Not JSON, just display as text
        console.print(Panel(
            response.text, 
            title=f"[bold {'green' if response.status_code < 400 else 'red'}]{title} (Status: {response.status_code})",
            border_style="green" if response.status_code < 400 else "red"
        ))
        return response.text

def api_request(method, endpoint, data=None, headers=None, display=True):
    """Make an API request and display details"""
    full_url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    
    if display:
        display_api_call(method, full_url, data, headers)
    
    if method.lower() == 'get':
        response = requests.get(full_url, headers=headers)
    elif method.lower() == 'post':
        response = requests.post(full_url, json=data, headers=headers)
    elif method.lower() == 'put':
        response = requests.put(full_url, json=data, headers=headers)
    elif method.lower() == 'patch':
        response = requests.patch(full_url, json=data, headers=headers)
    elif method.lower() == 'delete':
        response = requests.delete(full_url, headers=headers)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    if display:
        return display_api_response(response)
    return response.json() if response.status_code < 400 else None

def display_tab_header(tab_number, title, description=None):
    """Display a section header for a UI tab"""
    console.rule(f"[bold magenta]TAB {tab_number}: {title}")
    
    if description:
        console.print(Panel(description, border_style="blue"))

def display_before_after(before, after, title):
    """
    Display before/after comparison with emphasis
    """
    before_panel = Panel(
        before, 
        title="[bold yellow]BEFORE (Original Input)",
        border_style="yellow",
        width=80,
        padding=1
    )
    
    after_panel = Panel(
        after, 
        title="[bold green]AFTER (AI-Enhanced)",
        border_style="green",
        width=80,
        padding=1
    )
    
    console.print(f"\n[bold cyan]◆ {title} AI Enhancement ◆[/bold cyan]")
    console.print(before_panel)
    console.print("\n[bold]↓ AI Enhancement Applied ↓[/bold]\n")
    console.print(after_panel)

def display_form(title, fields):
    """Display a form-like representation"""
    form_table = Table(title=f"[bold cyan]{title} Form", box=box.ROUNDED)
    form_table.add_column("Field", style="yellow")
    form_table.add_column("Value", style="green")
    
    for field, value in fields.items():
        # Format field name to look like a form label
        field_name = field.replace('_', ' ').title()
        
        # Format value appropriately
        if isinstance(value, list):
            formatted_value = ", ".join(value)
        elif isinstance(value, (dict, list)):
            formatted_value = json.dumps(value, indent=2)
        else:
            formatted_value = str(value)
        
        form_table.add_row(field_name, formatted_value)
    
    console.print(form_table)
    console.print("\n[bold]User clicks 'Next' button to proceed[/bold]")

def resume_builder_flow():
    """
    Demonstrate the complete resume builder flow, following the UI tabs
    """
    # Check server connection
    try:
        response = requests.get(f"{BASE_URL}/resumes/")
        if response.status_code >= 400:
            console.print("[bold red]API server is not responding. Make sure it's running on localhost:8000[/bold red]")
            return
    except Exception as e:
        console.print(f"[bold red]Failed to connect to server: {str(e)}[/bold red]")
        return
    
    console.print("[bold green]✓ Server connection successful[/bold green]")
    
    # Generate a unique user ID for this demo
    user_id = str(uuid.uuid4())
    
    # ================================================================
    # Tab 1: General Information
    # ================================================================
    display_tab_header(
        1,
        "General Information", 
        "First, the user fills out the basic resume information form.\nThis creates a new resume with a title and description."
    )
    
    general_info = {
        "user_id": user_id,
        "title": "Software Engineer Resume",
        "description": "Resume for applying to software engineering positions at tech companies",
        "template": "professional",
    }
    
    # Display the form as the user would see it
    display_form("General Information", general_info)
    
    console.print("\n[bold]System creates a new resume with the general information...[/bold]")
    resume_data = api_request('POST', '/resumes/', general_info)
    
    if not resume_data:
        console.print("[bold red]Failed to create resume. Exiting.[/bold red]")
        return
    
    resume_id = resume_data["id"]
    console.print(f"[bold green]✓ Resume created with ID: {resume_id}[/bold green]")
    
    # ================================================================
    # Tab 2: Personal Information
    # ================================================================
    display_tab_header(
        2,
        "Personal Information", 
        "Next, the user enters their personal details like name, contact information, etc."
    )
    
    personal_info = {
        "first_name": "Taylor",
        "last_name": "Smith",
        "job_title": "Senior Software Engineer",
        "email": "taylor.smith@example.com",
        "phone": "555-987-6543",
        "city": "Austin",
        "country": "USA",
        "photo_url": "https://example.com/profile-photo.jpg"  # Mock photo URL
    }
    
    # Display the form as the user would see it
    display_form("Personal Information", personal_info)
    
    console.print("\n[bold]System updates the resume with personal information...[/bold]")
    updated_resume = api_request('PATCH', f'/resumes/{resume_id}/', personal_info)
    
    if not updated_resume:
        console.print("[bold red]Failed to update personal information. Continuing anyway.[/bold red]")
    else:
        console.print("[bold green]✓ Personal information updated successfully[/bold green]")
    
    # ================================================================
    # Tab 3: Work Experience
    # ================================================================
    display_tab_header(
        3,
        "Work Experience", 
        "The user adds their work experience entries. Multiple entries can be added.\nEach entry can be enhanced with AI."
    )
    
    # First work experience
    work_exp1 = {
        "resume": resume_id,
        "position": "Senior Software Engineer",
        "company": "Tech Innovations Inc.",
        "start_date": "2020-01-01",
        "end_date": "2023-04-01",
        "description": "Led a team of 5 developers building web applications using React and Node.js. Implemented CI/CD pipelines using GitHub Actions."
    }
    
    # Display the form as the user would see it
    display_form("Work Experience Entry #1", {k: v for k, v in work_exp1.items() if k != 'resume'})
    
    console.print("\n[bold]Adding work experience entry...[/bold]")
    work_exp1_data = api_request('POST', '/work-experiences/', work_exp1)
    
    if work_exp1_data:
        work_exp1_id = work_exp1_data["id"]
        console.print(f"[bold green]✓ Work experience added with ID: {work_exp1_id}[/bold green]")
        
        # Demonstrate AI enhancement for work experience
        console.print("\n[bold yellow]User clicks the 'Enhance with AI' button for this work experience[/bold yellow]")
        
        # Show "Loading" indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
            enhance_response = api_request('POST', f'/work-experiences/{work_exp1_id}/enhance/', display=False)
            progress.update(task, completed=True)
        
        if enhance_response and "enhanced_description" in enhance_response:
            enhanced_description = enhance_response["enhanced_description"]
            
            # Show before/after with emphasis
            display_before_after(
                work_exp1["description"], 
                enhanced_description,
                "Work Experience Description"
            )
            
            # Update with enhanced description
            console.print("\n[bold yellow]User clicks 'Use Enhanced Description' button[/bold yellow]")
            api_request('PATCH', f'/work-experiences/{work_exp1_id}/', {
                "description": enhanced_description
            })
            
            console.print("[bold green]✓ Work experience updated with enhanced description[/bold green]")
    
    # Second work experience
    work_exp2 = {
        "resume": resume_id,
        "position": "Software Engineer",
        "company": "Digital Solutions LLC",
        "start_date": "2017-06-01",
        "end_date": "2019-12-31",
        "description": "Developed and maintained web applications using JavaScript, React, and Express. Collaborated with design team to implement UI/UX improvements."
    }
    
    console.print("\n[bold yellow]User clicks 'Add Another Experience' button[/bold yellow]")
    
    # Display the form as the user would see it
    display_form("Work Experience Entry #2", {k: v for k, v in work_exp2.items() if k != 'resume'})
    
    console.print("\n[bold]Adding second work experience entry...[/bold]")
    work_exp2_data = api_request('POST', '/work-experiences/', work_exp2)
    
    if work_exp2_data:
        work_exp2_id = work_exp2_data["id"]
        console.print(f"[bold green]✓ Second work experience added with ID: {work_exp2_id}[/bold green]")
    
    # ================================================================
    # Tab 4: Education
    # ================================================================
    display_tab_header(
        4,
        "Education", 
        "The user adds their educational background. Multiple entries can be added."
    )
    
    # First education entry
    education1 = {
        "resume": resume_id,
        "degree": "Master of Science in Computer Science",
        "school": "Stanford University",
        "start_date": "2015-09-01",
        "end_date": "2017-05-31"
    }
    
    # Display the form as the user would see it
    display_form("Education Entry #1", {k: v for k, v in education1.items() if k != 'resume'})
    
    console.print("\n[bold]Adding education entry...[/bold]")
    education1_data = api_request('POST', '/educations/', education1)
    
    if education1_data:
        education1_id = education1_data["id"]
        console.print(f"[bold green]✓ Education added with ID: {education1_id}[/bold green]")
    
    # Second education entry
    education2 = {
        "resume": resume_id,
        "degree": "Bachelor of Science in Computer Engineering",
        "school": "University of Texas at Austin",
        "start_date": "2011-09-01",
        "end_date": "2015-05-31"
    }
    
    console.print("\n[bold yellow]User clicks 'Add Another Education' button[/bold yellow]")
    
    # Display the form as the user would see it
    display_form("Education Entry #2", {k: v for k, v in education2.items() if k != 'resume'})
    
    console.print("\n[bold]Adding second education entry...[/bold]")
    education2_data = api_request('POST', '/educations/', education2)
    
    if education2_data:
        education2_id = education2_data["id"]
        console.print(f"[bold green]✓ Second education added with ID: {education2_id}[/bold green]")
    
    # ================================================================
    # Tab 5: Skills
    # ================================================================
    display_tab_header(
        5,
        "Skills", 
        "The user adds their skills and can get AI-suggested skills based on their profile."
    )
    
    # Initial skills
    initial_skills = ["JavaScript", "React", "Node.js", "TypeScript", "HTML/CSS"]
    
    # Display the form as the user would see it
    display_form("Skills", {"skills": initial_skills})
    
    console.print("\n[bold]Adding initial skills...[/bold]")
    skills_update = api_request('PATCH', f'/resumes/{resume_id}/', {
        "skills": initial_skills
    })
    
    if skills_update:
        console.print("[bold green]✓ Initial skills added successfully[/bold green]")
    
    # Get AI suggested skills
    console.print("\n[bold yellow]User clicks 'Suggest More Skills' button[/bold yellow]")
    
    # Show "Loading" indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
        suggested_skills_data = api_request('POST', f'/resumes/{resume_id}/suggest_skills/', display=False)
        progress.update(task, completed=True)
    
    if suggested_skills_data and "suggested_skills" in suggested_skills_data:
        suggested_skills = suggested_skills_data["suggested_skills"]
        
        # Display AI suggestion panel
        console.print(Panel(
            "\n".join([f"• {skill}" for skill in suggested_skills]),
            title="[bold green]AI-Suggested Skills Based on Your Profile",
            border_style="green",
            padding=1
        ))
        
        # User selects skills to add
        selected_skills = initial_skills + suggested_skills[:3]  # Adding first 3 suggested skills
        
        console.print("\n[bold yellow]User selects additional skills from suggestions[/bold yellow]")
        
        # Show before/after with emphasis
        display_before_after(
            ", ".join(initial_skills), 
            ", ".join(selected_skills),
            "Skills List"
        )
        
        console.print("\n[bold]Updating skills with selected suggestions...[/bold]")
        updated_skills = api_request('PATCH', f'/resumes/{resume_id}/', {
            "skills": selected_skills
        })
        
        if updated_skills:
            console.print("[bold green]✓ Skills updated with selections from suggestions[/bold green]")
    
    # ================================================================
    # Tab 6: Projects
    # ================================================================
    display_tab_header(
        6,
        "Projects", 
        "The user adds their projects. Multiple entries can be added.\nEach entry can be enhanced with AI."
    )
    
    # First project
    project1 = {
        "resume": resume_id,
        "title": "E-commerce Platform",
        "start_date": "2022-01-01",
        "end_date": "2022-06-30",
        "description": "Built an online store using React, Node.js, and MongoDB. Implemented features like product search, shopping cart, and payment processing."
    }
    
    # Display the form as the user would see it
    display_form("Project Entry #1", {k: v for k, v in project1.items() if k != 'resume'})
    
    console.print("\n[bold]Adding project entry...[/bold]")
    project1_data = api_request('POST', '/projects/', project1)
    
    if project1_data:
        project1_id = project1_data["id"]
        console.print(f"[bold green]✓ Project added with ID: {project1_id}[/bold green]")
        
        # Demonstrate AI enhancement for project description
        console.print("\n[bold yellow]User clicks the 'Enhance with AI' button for this project[/bold yellow]")
        
        # Show "Loading" indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
            enhance_response = api_request('POST', f'/projects/{project1_id}/enhance/', display=False)
            progress.update(task, completed=True)
        
        if enhance_response and "enhanced_description" in enhance_response:
            enhanced_description = enhance_response["enhanced_description"]
            
            # Show before/after with emphasis
            display_before_after(
                project1["description"], 
                enhanced_description,
                "Project Description"
            )
            
            # Update with enhanced description
            console.print("\n[bold yellow]User clicks 'Use Enhanced Description' button[/bold yellow]")
            api_request('PATCH', f'/projects/{project1_id}/', {
                "description": enhanced_description
            })
            
            console.print("[bold green]✓ Project updated with enhanced description[/bold green]")
    
    # Second project
    project2 = {
        "resume": resume_id,
        "title": "Task Management App",
        "start_date": "2021-05-01",
        "end_date": "2021-11-30",
        "description": "Developed a task management web application with React and Firebase. Implemented user authentication, real-time updates, and task categorization."
    }
    
    console.print("\n[bold yellow]User clicks 'Add Another Project' button[/bold yellow]")
    
    # Display the form as the user would see it
    display_form("Project Entry #2", {k: v for k, v in project2.items() if k != 'resume'})
    
    console.print("\n[bold]Adding second project entry...[/bold]")
    project2_data = api_request('POST', '/projects/', project2)
    
    if project2_data:
        project2_id = project2_data["id"]
        console.print(f"[bold green]✓ Second project added with ID: {project2_id}[/bold green]")
    
    # ================================================================
    # Tab 7: Certifications
    # ================================================================
    display_tab_header(
        7,
        "Certifications", 
        "The user adds their certifications. Multiple entries can be added.\nEach entry can have an AI-generated description."
    )
    
    # First certification
    certification1 = {
        "resume": resume_id,
        "name": "AWS Certified Solutions Architect",
        "issuer": "Amazon Web Services",
        "issue_date": "2022-03-15",
        "expiry_date": "2025-03-15",
        "description": ""  # Empty initially
    }
    
    # Display the form as the user would see it
    display_form("Certification Entry #1", {k: v for k, v in certification1.items() if k != 'resume'})
    
    console.print("\n[bold]Adding certification entry...[/bold]")
    certification1_data = api_request('POST', '/certifications/', certification1)
    
    if certification1_data:
        certification1_id = certification1_data["id"]
        console.print(f"[bold green]✓ Certification added with ID: {certification1_id}[/bold green]")
        
        # Demonstrate AI enhancement for certification description
        console.print("\n[bold yellow]User clicks the 'Generate Description with AI' button[/bold yellow]")
        
        # Show "Loading" indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
            enhance_response = api_request('POST', f'/certifications/{certification1_id}/enhance/', display=False)
            progress.update(task, completed=True)
        
        if enhance_response and "enhanced_description" in enhance_response:
            enhanced_description = enhance_response["enhanced_description"]
            
            # Show before/after with emphasis
            display_before_after(
                "No description provided", 
                enhanced_description,
                "Certification Description"
            )
            
            # Update with enhanced description
            console.print("\n[bold yellow]User clicks 'Use Generated Description' button[/bold yellow]")
            api_request('PATCH', f'/certifications/{certification1_id}/', {
                "description": enhanced_description
            })
            
            console.print("[bold green]✓ Certification updated with AI-generated description[/bold green]")
    
    # ================================================================
    # Tab 8: Professional Summary
    # ================================================================
    display_tab_header(
        8,
        "Professional Summary", 
        "The user can write a summary or have one generated by AI based on their profile data."
    )
    
    # First, check the current summary (should be empty or null)
    console.print("[bold]Checking current summary status...[/bold]")
    current_resume = api_request('GET', f'/resumes/{resume_id}/')
    current_summary = current_resume.get("summary", None)
    
    if current_summary is None or current_summary == "":
        summary_status = "No summary exists yet"
    else:
        summary_status = current_summary
    
    display_form("Professional Summary", {"summary": summary_status})
    
    # Generate summary with AI
    console.print("\n[bold yellow]User clicks the 'Generate with AI' button[/bold yellow]")
    
    # Show "Loading" indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
        summary_response = api_request('POST', f'/resumes/{resume_id}/generate_summary/', display=False)
        progress.update(task, completed=True)
    
    if summary_response and "summary" in summary_response:
        generated_summary = summary_response["summary"]
        
        # Show before/after with emphasis
        display_before_after(
            summary_status, 
            generated_summary,
            "Professional Summary"
        )
        
        console.print("\n[bold yellow]User clicks 'Use Generated Summary' button[/bold yellow]")
        console.print("[bold green]✓ Summary has been automatically saved to the resume[/bold green]")
    else:
        console.print("[bold red]Failed to generate summary[/bold red]")
    
    # ================================================================
    # Tab 9: Custom Sections
    # ================================================================
    display_tab_header(
        9,
        "Custom Sections", 
        "The user can add custom sections to highlight additional achievements.\nEach section can have multiple items, and item descriptions can be enhanced with AI."
    )
    
    # Create a custom section for "Publications"
    custom_section = {
        "resume": resume_id,
        "title": "Publications"
    }
    
    # Display the form as the user would see it
    display_form("Custom Section", {"title": custom_section["title"]})
    
    console.print("\n[bold]Creating custom section...[/bold]")
    custom_section_data = api_request('POST', '/custom-sections/', custom_section)
    
    if custom_section_data:
        custom_section_id = custom_section_data["id"]
        console.print(f"[bold green]✓ Custom section created with ID: {custom_section_id}[/bold green]")
        
        # Add items to the custom section
        publication1 = {
            "custom_section": custom_section_id,
            "title": "Modern Web Development Techniques",
            "start_date": "2022-05-01",
            "description": "An article about modern web development techniques and best practices."
        }
        
        console.print("\n[bold yellow]User clicks 'Add Item' button[/bold yellow]")
        
        # Display the form as the user would see it
        display_form("Publication Item #1", {k: v for k, v in publication1.items() if k != 'custom_section'})
        
        console.print("\n[bold]Adding publication item...[/bold]")
        item1_data = api_request('POST', '/custom-section-items/', publication1)
        
        if item1_data:
            item1_id = item1_data["id"]
            console.print(f"[bold green]✓ Custom section item added with ID: {item1_id}[/bold green]")
            
            # Demonstrate AI enhancement for custom section item
            console.print("\n[bold yellow]User clicks the 'Enhance with AI' button for this publication[/bold yellow]")
            
            # Show "Loading" indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Processing with Claude AI...", total=None)
                enhance_response = api_request('POST', f'/custom-section-items/{item1_id}/enhance/', display=False)
                progress.update(task, completed=True)
            
            if enhance_response and "enhanced_description" in enhance_response:
                enhanced_description = enhance_response["enhanced_description"]
                
                # Show before/after with emphasis
                display_before_after(
                    publication1["description"], 
                    enhanced_description,
                    "Publication Description"
                )
                
                # Update with enhanced description
                console.print("\n[bold yellow]User clicks 'Use Enhanced Description' button[/bold yellow]")
                api_request('PATCH', f'/custom-section-items/{item1_id}/', {
                    "description": enhanced_description
                })
                
                console.print("[bold green]✓ Publication updated with enhanced description[/bold green]")
        
        # Add second publication
        publication2 = {
            "custom_section": custom_section_id,
            "title": "Performance Optimization in React Applications",
            "start_date": "2021-11-15",
            "description": "A technical paper on optimizing performance in React applications."
        }
        
        console.print("\n[bold yellow]User clicks 'Add Another Item' button[/bold yellow]")
        
        # Display the form as the user would see it
        display_form("Publication Item #2", {k: v for k, v in publication2.items() if k != 'custom_section'})
        
        console.print("\n[bold]Adding second publication item...[/bold]")
        item2_data = api_request('POST', '/custom-section-items/', publication2)
        
        if item2_data:
            item2_id = item2_data["id"]
            console.print(f"[bold green]✓ Second publication item added with ID: {item2_id}[/bold green]")
    
    # ================================================================
    # Resume Complete View
    # ================================================================
    console.rule("[bold green]RESUME COMPLETION")
    
    console.print("\n[bold]User completes all tabs and views the final resume[/bold]")
    console.print("\n[bold]Fetching the complete resume with all sections...[/bold]")
    complete_resume = api_request('GET', f'/resumes/{resume_id}/?include=detail')
    
    if complete_resume:
        # Display a summary of what was created
        resume_table = Table(title="Complete Resume Content", box=box.ROUNDED)
        resume_table.add_column("Section", style="cyan")
        resume_table.add_column("Content", style="green")
        
        # Basic Info
        resume_table.add_row(
            "Basic Info", 
            f"{complete_resume.get('first_name', '')} {complete_resume.get('last_name', '')} - {complete_resume.get('job_title', '')}"
        )
        
        # Summary
        if complete_resume.get('summary'):
            summary_preview = complete_resume['summary'][:100] + "..." if len(complete_resume['summary']) > 100 else complete_resume['summary']
            resume_table.add_row("Summary", summary_preview)
        
        # Skills
        if complete_resume.get('skills'):
            resume_table.add_row("Skills", ", ".join(complete_resume['skills'][:8]) + ("..." if len(complete_resume['skills']) > 8 else ""))
        
        # Work Experience
        if complete_resume.get('work_experiences'):
            work_exp_text = f"{len(complete_resume['work_experiences'])} entries"
            resume_table.add_row("Work Experience", work_exp_text)
        
        # Education
        if complete_resume.get('educations'):
            education_text = f"{len(complete_resume['educations'])} entries"
            resume_table.add_row("Education", education_text)
        
        # Projects
        if complete_resume.get('projects'):
            projects_text = f"{len(complete_resume['projects'])} entries"
            resume_table.add_row("Projects", projects_text)
        
        # Certifications
        if complete_resume.get('certifications'):
            cert_text = f"{len(complete_resume['certifications'])} entries"
            resume_table.add_row("Certifications", cert_text)
        
        # Custom Sections
        if complete_resume.get('custom_sections'):
            for section in complete_resume['custom_sections']:
                items_count = len(section.get('items', [])) if 'items' in section else 0
                custom_section_text = f"{items_count} items"
                resume_table.add_row(f"Custom: {section['title']}", custom_section_text)
        
        console.print(resume_table)
    
    # Final message
    console.print(f"\n[bold green]✓ Resume creation flow completed![/bold green]")
    console.print(f"[bold cyan]Resume ID: {resume_id}[/bold cyan]")
    console.print("[yellow]Note: The resume data has NOT been deleted and can be accessed at any time.[/yellow]")
    console.print("[yellow]To view the complete resume, visit: " + f"{BASE_URL}/resumes/{resume_id}/?include=detail[/yellow]")

if __name__ == "__main__":
    console.print(Panel.fit(
        Markdown("# Resume Builder Flow Demonstration"),
        title="Resume Builder API Demo",
        border_style="green"
    ))
    
    console.print("""
This script demonstrates the complete resume builder flow, showing each step as it would appear
in the UI interface, along with the corresponding API calls, request data, and responses.

Each tab in the UI is represented as a separate step in this flow:
1. General Information - Create the resume with title and description
2. Personal Information - Add personal details like name, contact info
3. Work Experience - Add professional experience with AI enhancement
4. Education - Add educational background
5. Skills - Add skills and get AI suggestions
6. Projects - Add projects with AI-enhanced descriptions
7. Certifications - Add certifications with AI-generated descriptions
8. Professional Summary - Generate a compelling summary with AI
9. Custom Sections - Add custom sections like publications
    """)
    
    console.print("[yellow]Make sure the Django API server is running on localhost:8000[/yellow]")
    console.print("Press Enter to start the demonstration...", end="")
    input()
    
    resume_builder_flow() 