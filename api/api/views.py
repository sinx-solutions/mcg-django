from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, action , parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .schemas import ParsedResumeSchema
from django.http import Http404
import os
import json
import re
import anthropic
from dotenv import load_dotenv
import uuid
import io
import PyPDF2
import docx
import google.generativeai as genai
import requests # Added for OpenRouter
from pydantic import ValidationError # Keep for potential validation if needed, though OpenRouter handles it
from datetime import datetime

from .models import (
    Resume,
    WorkExperience,
    Education,
    Project,
    Certification,
    CustomSection,
    CustomSectionItem
)
from .serializers import (
    ResumeSerializer,
    ResumeDetailSerializer,
    ResumeCompleteSerializer,
    WorkExperienceSerializer,
    EducationSerializer,
    ProjectSerializer,
    CertificationSerializer,
    CustomSectionSerializer,
    CustomSectionItemSerializer
)

# Date parsing helper function
def parse_date_string(date_str):
    """
    Parse various date formats and return YYYY-MM-DD format if possible,
    otherwise return None.
    """
    if not date_str or not isinstance(date_str, str):
        return None
        
    if date_str.lower() == 'present' or date_str.lower() == 'current':
        return None
    
    # Handle common date formats
    formats_to_try = [
        '%Y-%m-%d',       # 2020-01-30
        '%B %Y',          # January 2020
        '%b %Y',          # Jan 2020
        '%m/%d/%Y',       # 01/30/2020
        '%m/%Y',          # 01/2020
        '%m-%Y',          # 01-2020
        '%Y'              # 2020
    ]
    
    # Try standard formats first
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Try to extract year with regex if standard formats fail
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if year_match:
        year = year_match.group(0)
        return f"{year}-01-01"  # Default to January 1st of the matched year
    
    # If all parsing attempts fail
    print(f"Could not parse date: {date_str}")
    return None

# Load environment variables
load_dotenv()

# Initialize Claude API client
def get_claude_client():
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise Exception("Claude API key not found in environment variables")
    return anthropic.Anthropic(api_key=api_key)

# Resume ViewSet with support for different serialization depths
class ResumeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing resumes
    """
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        # Use different serializers based on the action
        if self.action == 'retrieve' or self.action == 'create' or self.action == 'update':
            # Get the include parameter from query params
            include = self.request.query_params.get('include', 'basic')
            
            if include == 'all' or include == 'complete':
                return ResumeCompleteSerializer
            elif include == 'detail':
                return ResumeDetailSerializer
        
        return ResumeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        # Here we would usually set the user_id based on the authenticated user
        # For now, we're just using the provided user_id
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def generate_summary(self, request, pk=None):
        """
        Generate a professional summary using Claude AI based on resume information
        """
        try:
            resume = self.get_object()
            
            # Get detailed data for the resume
            serializer = ResumeDetailSerializer(resume)
            resume_data = serializer.data
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Generate a professional summary for a resume based on the person's 
            experience, education, and skills. The summary should be concise (3-5 sentences), highlight key strengths,
            and be written in first person.

            Resume Information:
            -------------------
            Name: {resume.first_name} {resume.last_name}
            Job Title: {resume.job_title or "Not specified"}
            Skills: {", ".join(resume.skills) if resume.skills else "Not specified"}
            
            Work Experience:
            """
            
            # Add work experience details
            work_experiences = resume.work_experiences.all()
            if work_experiences:
                for i, exp in enumerate(work_experiences):
                    prompt += f"""
                    {i+1}. {exp.position or "Role"} at {exp.company or "Company"}
                    Duration: {exp.start_date or "Start date"} to {exp.end_date or "Present"}
                    Description: {exp.description or "Not provided"}
                    """
            else:
                prompt += "\nNo work experience provided.\n"
            
            # Add education details
            educations = resume.educations.all()
            prompt += "\nEducation:\n"
            if educations:
                for i, edu in enumerate(educations):
                    prompt += f"""
                    {i+1}. {edu.degree or "Degree"} from {edu.school or "School"}
                    Duration: {edu.start_date or "Start date"} to {edu.end_date or "End date"}
                    """
            else:
                prompt += "No education details provided.\n"
            
            # Add projects details if available
            projects = resume.projects.all()
            if projects:
                prompt += "\nProjects:\n"
                for i, proj in enumerate(projects):
                    prompt += f"""
                    {i+1}. {proj.title or "Project"}
                    Description: {proj.description or "Not provided"}
                    """
            
            prompt += """
            Generate a professional summary that is:
            1. Written in first person
            2. 3-5 sentences long
            3. Highlights key skills and experiences
            4. Is tailored to their career level and industry
            5. Uses confident and professional language
            
            Don't use phrases like "I have X years of experience" unless you know the exact number from the work history.
            Return only the summary text with no additional explanation or markdown.
            """
            
            # Call Claude API
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract summary from response
            summary = message.content[0].text.strip()
            
            # Update the resume with the generated summary
            resume.summary = summary
            resume.save()
            
            return Response({
                "summary": summary
            }, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response(
                {'error': 'Resume not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def suggest_skills(self, request, pk=None):
        """
        Suggest relevant skills based on resume information
        """
        try:
            resume = self.get_object()
            
            # Gather context from resume for skill suggestions
            context = {
                "job_title": resume.job_title or "",
                "existing_skills": resume.skills or [],
                "work_experience": [],
                "education": []
            }
            
            # Add work experience context
            for exp in resume.work_experiences.all():
                context["work_experience"].append({
                    "position": exp.position or "",
                    "company": exp.company or "",
                    "description": exp.description or ""
                })
            
            # Add education context
            for edu in resume.educations.all():
                context["education"].append({
                    "degree": edu.degree or "",
                    "school": edu.school or ""
                })
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Based on the resume information provided, suggest relevant skills that the person should add to their resume.
            Consider the person's job title, existing skills, work experience, and education.
            
            Resume Information:
            -------------------
            Job Title: {context["job_title"]}
            Existing Skills: {", ".join(context["existing_skills"]) if context["existing_skills"] else "None provided"}
            
            Work Experience:
            """
            
            if context["work_experience"]:
                for i, exp in enumerate(context["work_experience"]):
                    prompt += f"""
                    {i+1}. {exp["position"]} at {exp["company"]}
                    Description: {exp["description"]}
                    """
            else:
                prompt += "\nNo work experience provided.\n"
            
            prompt += "\nEducation:\n"
            if context["education"]:
                for i, edu in enumerate(context["education"]):
                    prompt += f"{i+1}. {edu['degree']} from {edu['school']}\n"
            else:
                prompt += "No education details provided.\n"
            
            prompt += """
            Based on this information, suggest 15-20 relevant skills that would strengthen this resume.
            Include both technical and soft skills appropriate for their role and industry.
            Don't suggest skills they already have listed.
            
            Return your response as a JSON array of strings, with each skill as a separate string item. For example:
            ["Skill 1", "Skill 2", "Skill 3"]
            
            Return only the JSON array with no additional text or explanation.
            """
            
            # Call Claude API
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract skills from response
            response_text = message.content[0].text.strip()
            
            # Extract JSON using regex pattern in case Claude wraps it in markdown
            json_pattern = re.compile(r'```(?:json)?\s*(.*?)```', re.DOTALL)
            json_match = json_pattern.search(response_text)
            
            if json_match:
                # Use the extracted JSON string
                json_str = json_match.group(1).strip()
                suggested_skills = json.loads(json_str)
            else:
                # Try parsing the whole response directly
                try:
                    suggested_skills = json.loads(response_text)
                except json.JSONDecodeError:
                    return Response(
                        {'error': 'Failed to parse AI response', 'raw_response': response_text[:1000]},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            return Response({
                "suggested_skills": suggested_skills
            }, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist:
            return Response(
                {'error': 'Resume not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ViewSets for Resume components
class WorkExperienceViewSet(viewsets.ModelViewSet):
    queryset = WorkExperience.objects.all()
    serializer_class = WorkExperienceSerializer
    
    @action(detail=True, methods=['post'])
    def enhance(self, request, pk=None):
        """
        Enhance work experience description using Claude AI
        """
        try:
            work_exp = self.get_object()
            
            # Get context information from the work experience
            position = work_exp.position or "Not specified"
            company = work_exp.company or "Not specified"
            current_description = work_exp.description or ""
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Enhance the following work experience description for a resume.
            Make it more impactful, achievement-oriented, and use strong action verbs.
            Focus on quantifiable achievements and skills demonstrated.
            
            Position: {position}
            Company: {company}
            Current Description: {current_description}
            
            Provide an enhanced description that:
            1. Starts with strong action verbs
            2. Includes specific accomplishments with metrics when possible
            3. Demonstrates skills and impact
            4. Is concise yet comprehensive
            5. Is relevant to the position
            
            Return only the enhanced description with no additional explanation or markdown.
            """
            
            # Call Claude API
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract enhanced description
            enhanced_description = message.content[0].text.strip()
            
            return Response({
                "enhanced_description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except WorkExperience.DoesNotExist:
            return Response(
                {'error': 'Work experience not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EducationViewSet(viewsets.ModelViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    
    @action(detail=True, methods=['post'])
    def enhance(self, request, pk=None):
        """
        Enhance project description using Claude AI
        """
        try:
            project = self.get_object()
            
            # Get context information from the project
            title = project.title or "Not specified"
            current_description = project.description or ""
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Enhance the following project description for a resume.
            Make it more impactful, achievement-oriented, and focus on skills demonstrated.
            
            Project Title: {title}
            Current Description: {current_description}
            
            Provide an enhanced description that:
            1. Clearly explains the project purpose
            2. Highlights the technologies or methodologies used
            3. Emphasizes your specific contributions
            4. Mentions any challenges overcome
            5. Notes the impact or outcomes of the project
            
            Return only the enhanced description with no additional explanation or markdown.
            """
            
            # Call Claude API
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract enhanced description
            enhanced_description = message.content[0].text.strip()
            
            return Response({
                "enhanced_description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CertificationViewSet(viewsets.ModelViewSet):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer
    
    @action(detail=True, methods=['post'])
    def enhance(self, request, pk=None):
        """
        Enhance certification description using Claude AI
        """
        try:
            certification = self.get_object()
            
            # Get context information from the certification
            name = certification.name or "Not specified"
            issuer = certification.issuer or "Not specified"
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Create an impactful description for the following certification to be included in a resume.
            
            Certification Name: {name}
            Issuing Organization: {issuer}
            
            Provide a description that:
            1. Explains what the certification demonstrates (skills, knowledge)
            2. Mentions its relevance to the person's career path
            3. Notes any particularly challenging aspects of earning it
            4. Is concise (2-3 sentences)
            
            Return only the description with no additional explanation or markdown.
            """
            
            # Call Claude API
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=256,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract enhanced description
            enhanced_description = message.content[0].text.strip()
            
            return Response({
                "enhanced_description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except Certification.DoesNotExist:
            return Response(
                {'error': 'Certification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomSectionViewSet(viewsets.ModelViewSet):
    queryset = CustomSection.objects.all()
    serializer_class = CustomSectionSerializer

class CustomSectionItemViewSet(viewsets.ModelViewSet):
    queryset = CustomSectionItem.objects.all()
    serializer_class = CustomSectionItemSerializer
    
    @action(detail=True, methods=['post'])
    def enhance(self, request, pk=None):
        """
        Enhance custom section item description using Claude AI
        """
        try:
            item = self.get_object()
            custom_section = item.custom_section
            
            # Get context information
            section_title = custom_section.title
            item_title = item.title or "Not specified"
            current_description = item.description or ""
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Enhance the following description for a custom section item in a resume.
            
            Section Title: {section_title}
            Item Title: {item_title}
            Current Description: {current_description}
            
            Provide an enhanced description that:
            1. Is specific and detailed
            2. Focuses on achievements and skills demonstrated
            3. Uses professional language
            4. Is relevant to the section and item title
            
            Return only the enhanced description with no additional explanation or markdown.
            """
            
            # Call Claude API
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=512,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract enhanced description
            enhanced_description = message.content[0].text.strip()
            
            return Response({
                "enhanced_description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except CustomSectionItem.DoesNotExist:
            return Response(
                {'error': 'Custom section item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Resume Parser API View using OpenRouter
@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def parse_resume(request):
    """
    Parse a resume file (PDF/Word) and extract structured data using OpenRouter.
    """
    print("Received request for /api/parse-resume/ (Using OpenRouter)")

    # 1. Get file and validate user_id from the request
    resume_files = request.FILES.get('resume')
    user_id = request.data.get('user_id')

    print(f"Received File: {resume_files.name if resume_files else 'None'}")
    print(f'Received user_id : {user_id}')

    # 2. Validate input
    if not resume_files:
        return Response(
            {'error': "No resume files were uploaded"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not user_id:
        return Response(
            {'error': "No user id provided in the request"}, status=status.HTTP_400_BAD_REQUEST
        )
    
    # 3. Validate user_id UUID format
    try:
        user_id_uuid = uuid.UUID(user_id)
        print(f"Validated user_id as UUID: {user_id_uuid}")
    except ValueError:
        return Response(
            {"error": "Invalid user_id format. Please provide a valid UUID format."}, status=status.HTTP_400_BAD_REQUEST
        )

    # 4. Validate file type
    file_name = resume_files.name.lower()
    if not (file_name.endswith('.pdf') or file_name.endswith('.docx')):
        return Response(
            {"error": f"Unsupported file format: {file_name}. Please upload a PDF or DOCX file."}, status=status.HTTP_400_BAD_REQUEST
        )

    # 5. Extract text from file
    raw_text = ""
    try:
        print(f"Attempting to extract text from: {resume_files.name}")
        file_stream = io.BytesIO(resume_files.read())
        
        if file_name.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file_stream)
            if not reader.pages:
                print("Warning: PDF reader found 0 pages.")
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        raw_text += page_text + "\n"
                except Exception as page_err:
                    print(f"Warning: Could not extract text from PDF page {i+1}: {page_err}")
        elif file_name.endswith('.docx'):
            document = docx.Document(file_stream)
            for para in document.paragraphs:
                raw_text += para.text + "\n"

        print(f"Successfully extracted text. Length is {len(raw_text)}")
        if raw_text:
            print(f"Preview of extracted text: {raw_text[:200]}...")
        else:
            print("Warning: Extracted text is empty.")

        if not raw_text.strip():
            print("Error: Failed to extract meaningful content from the file.")
            return Response(
                {"error": "Failed to extract text content from the provided file. It might be empty or corrupted."},
                status=status.HTTP_400_BAD_REQUEST
            )

    except PyPDF2.errors.PdfReadError as pdf_err:
        print(f"Error reading PDF file: {pdf_err}")
        return Response(
            {"error": f"Could not read the PDF file. It might be corrupted or password-protected. Error: {pdf_err}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        print(f"Error during text extraction: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return Response(
            {"error": f"Could not extract text from the provided file. Error: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 6. Process raw text with OpenRouter
    try:
        print("Attempting to parse resume content with OpenRouter")
        
        # Get API key from environment variable
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            print("Error: OpenRouter API key not found in environment variables")
            return Response(
                {"error": "OpenRouter API key not configured. Please check server configuration."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Fix the JSON schema based on the error message
        resume_json_schema = {
            "type": "object",
            "properties": {
                "first_name": {
                    "type": "string",
                    "description": "First name of the person"
                },
                "last_name": {
                    "type": "string",
                    "description": "Last name of the person"
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the person"
                },
                "phone": {
                    "type": "string", 
                    "description": "Phone number of the person"
                },
                "location": {
                    "type": "string",
                    "description": "City and/or country location"
                },
                "summary": {
                    "type": "string",
                    "description": "Professional summary or objective statement"
                },
                "skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of skills mentioned in the resume"
                },
                "work_experiences": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "position": {"type": "string"},
                            "company": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["position", "company", "start_date", "end_date", "description"],
                        "additionalProperties": False
                    },
                    "description": "List of work experiences, including position, company, dates, and description"
                },
                "educations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "degree": {"type": "string"},
                            "school": {"type": "string"},
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"}
                        },
                        "required": ["degree", "school", "start_date", "end_date"],
                        "additionalProperties": False
                    },
                    "description": "List of educational backgrounds, including degree, school, and dates"
                },
                "projects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["title", "description"],
                        "additionalProperties": False
                    },
                    "description": "List of projects mentioned in the resume, including title and description"
                },
                "certifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "issuer": {"type": "string"},
                            "issue_date": {"type": "string"}
                        },
                        "required": ["name", "issuer", "issue_date"],
                        "additionalProperties": False
                    },
                    "description": "List of certifications, including name, issuer, and issue date"
                }
            },
            "required": ["first_name", "last_name", "email", "phone", "location", "summary", "skills", "work_experiences", "educations", "projects", "certifications"],
            "additionalProperties": False
        }
        
        # Print the schema for debugging
        print("JSON Schema being sent to OpenRouter:")
        print(json.dumps(resume_json_schema, indent=2))

        # Prepare the prompt for OpenRouter
        prompt = f"""
        Extract structured resume data from the following text. Focus on identifying:
        - Personal information (name, email, phone, location)
        - Professional summary
        - Skills (as a list)
        - Work experience with position, company, dates, and descriptions
        - Education with degree, school, and dates
        - Projects with title and description
        - Certifications with name, issuer, and date

        Resume text:
        {raw_text}

        Provide the extracted information in structured JSON format according to the provided schema.
        If certain information is missing, leave those fields as null or empty arrays as appropriate.
        """

        # Call OpenRouter API
        print("Sending request to OpenRouter...")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o",
                "messages": [
                    {"role": "user", "content": prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "parsed_resume",
                        "strict": True,
                        "schema": resume_json_schema,
                    },
                },
            },
        )

        # Print full response for debugging
        print(f"Response status code: {response.status_code}")
        print(f"Full response: {response.text}")
        
        # Check the response status
        if response.status_code != 200:
            print(f"OpenRouter API error: {response.status_code}")
            print(f"Response content: {response.text}")
            return Response(
                {"error": f"Error from OpenRouter API: {response.text}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Parse the response data
        data = response.json()
        
        # Debug the response structure
        print(f"OpenRouter response keys: {data.keys()}")
        
        # Check if we have the expected structure
        if 'choices' not in data:
            print("Error: 'choices' not found in OpenRouter response")
            return Response(
                {"error": "Unexpected response format from OpenRouter", "response": data},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Get the string content from OpenRouter response
        parsed_resume_json_str = data["choices"][0]["message"]["content"]
        print(f"OpenRouter successfully returned parsed resume data:")
        print(parsed_resume_json_str)
        
        try:
            # Parse the JSON string into a Python dictionary
            parsed_resume_json = json.loads(parsed_resume_json_str)
            
            # Validate and clean data with particular attention to dates
            validated_data = {
                "personal_info": {
                    "first_name": parsed_resume_json.get('first_name'),
                    "last_name": parsed_resume_json.get('last_name'),
                    "email": parsed_resume_json.get('email'),
                    "phone": parsed_resume_json.get('phone'),
                    "location": parsed_resume_json.get('location')
                },
                "summary": parsed_resume_json.get('summary'),
                "skills": parsed_resume_json.get('skills', []),
                "work_experiences": [],
                "educations": [],
                "projects": [],
                "certifications": []
            }
            
            # Process work experiences with date parsing
            for exp in parsed_resume_json.get('work_experiences', []):
                cleaned_exp = {
                    "position": exp.get('position'),
                    "company": exp.get('company'),
                    "description": exp.get('description'),
                    "start_date_raw": exp.get('start_date'),
                    "end_date_raw": exp.get('end_date'),
                    "start_date": parse_date_string(exp.get('start_date')),
                    "end_date": parse_date_string(exp.get('end_date'))
                }
                validated_data["work_experiences"].append(cleaned_exp)
            
            # Process education with date parsing
            for edu in parsed_resume_json.get('educations', []):
                cleaned_edu = {
                    "degree": edu.get('degree'),
                    "school": edu.get('school'),
                    "start_date_raw": edu.get('start_date'),
                    "end_date_raw": edu.get('end_date'),
                    "start_date": parse_date_string(edu.get('start_date')),
                    "end_date": parse_date_string(edu.get('end_date'))
                }
                validated_data["educations"].append(cleaned_edu)
            
            # Process projects with date parsing
            for proj in parsed_resume_json.get('projects', []):
                cleaned_proj = {
                    "title": proj.get('title'),
                    "description": proj.get('description')
                    # Note: Projects have start_date and end_date in model but not in parsed data
                }
                validated_data["projects"].append(cleaned_proj)
            
            # Process certifications with date parsing
            for cert in parsed_resume_json.get('certifications', []):
                cleaned_cert = {
                    "name": cert.get('name'),
                    "issuer": cert.get('issuer'),
                    "issue_date_raw": cert.get('issue_date'),
                    "issue_date": parse_date_string(cert.get('issue_date'))
                }
                validated_data["certifications"].append(cleaned_cert)
            
            # Return both the raw parsed data and the validated/cleaned data
            return Response({
                "message": "Resume parsed successfully",
                "raw_data": parsed_resume_json,
                "validated_data": validated_data,
                "ready_for_db": True
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return Response(
                {"error": f"Error decoding JSON: {e}", "raw_content": parsed_resume_json_str},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Unexpected error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    except requests.RequestException as req_err:
        print(f"Error making request to OpenRouter: {req_err}")
        return Response(
            {"error": f"Failed to communicate with OpenRouter: {req_err}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        print(f"Unexpected error during resume parsing: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Unexpected error during resume parsing: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Resume Adaptation API View with Claude AI integration
@api_view(['POST'])
def adapt_resume(request):
    """
    Adapt a resume for a specific job using Claude AI
    """
    # Validate required fields
    required_fields = ['resume_id', 'job_title', 'job_description']
    for field in required_fields:
        if field not in request.data:
            return Response(
                {'error': f'Missing required field: {field}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    resume_id = request.data['resume_id']
    job_title = request.data['job_title']
    company = request.data.get('company', '')
    job_description = request.data['job_description']
    
    try:
        # Get the original resume with all related data
        resume = Resume.objects.get(id=resume_id)
        
        # Get detailed data for the resume
        serializer = ResumeDetailSerializer(resume)
        resume_data = serializer.data
        
        # Initialize Claude API client
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            return Response(
                {'error': 'AI service configuration error: API key not found'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        client = anthropic.Anthropic(api_key=api_key)
        
        # Helper function to convert to JSON-serializable data
        def serialize_uuid(obj):
            if isinstance(obj, uuid.UUID):
                return str(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Prepare the prompt for Claude
        prompt = f"""
        You are an AI career assistant that helps tailor resumes for specific job postings.
        I'll provide you with a resume and a job posting. Please analyze the resume against the job requirements and:

        1. Create an improved summary section that highlights relevant experience
        2. Prioritize and reorder skills based on job relevance
        3. Enhance work experience descriptions to emphasize relevant achievements
        4. Suggest any additional sections or information that should be added
        
        Resume:
        {json.dumps(resume_data, indent=2, default=serialize_uuid)}
        
        Job Posting:
        Title: {job_title}
        Company: {company}
        Description: {job_description}
        
        Please format your response as a valid JSON object with the following structure:
        {{
          "tailored_summary": "...",
          "prioritized_skills": ["skill1", "skill2", ...],
          "enhanced_work_experiences": [{{position, company, start_date, end_date, enhanced_description}}, ...],
          "additional_suggestions": "..."
        }}
        
        Return only the JSON object without any markdown formatting or other text.
        """
        
        print(f"Prompt length: {len(prompt)} characters")
        print(f"Calling Claude API with prompt...")
        
        # Call Claude API
        try:
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            print(f"Claude API response received.")
            
            # Extract JSON from response
            raw_text = message.content[0].text
            
            # Extract JSON using regex pattern in case Claude wraps it in markdown
            json_pattern = re.compile(r'```(?:json)?\s*(.*?)```', re.DOTALL)
            json_match = json_pattern.search(raw_text)
            
            if json_match:
                # Use the extracted JSON string
                json_str = json_match.group(1).strip()
                claude_response = json.loads(json_str)
                print(f"JSON extracted from code block")
            else:
                # Try parsing the whole response directly
                try:
                    claude_response = json.loads(raw_text)
                    print(f"JSON parsed directly from response")
                except json.JSONDecodeError:
                    print(f"Failed to parse JSON. Raw response: {raw_text[:500]}...")
                    return Response(
                        {'error': 'Failed to parse AI response', 'raw_response': raw_text[:1000]},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            print(f"Claude response parsed successfully")
            
        except anthropic.APIError as api_err:
            print(f"Claude API error: {str(api_err)}")
            return Response(
                {'error': f'AI service error: {str(api_err)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as api_ex:
            print(f"Unexpected error in Claude API call: {str(api_ex)}")
            return Response(
                {'error': f'Unexpected error in AI service: {str(api_ex)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create a new resume based on the tailored data
        new_resume_data = {
            'user_id': str(resume.user_id),  # Convert UUID to string
            'title': f"{resume.title or 'Resume'} for {company} {job_title}",
            'first_name': resume.first_name,
            'last_name': resume.last_name,
            'email': resume.email,
            'phone': resume.phone,
            'city': resume.city,
            'country': resume.country,
            'job_title': resume.job_title,
            'summary': claude_response.get('tailored_summary', resume.summary),
            'skills': claude_response.get('prioritized_skills', resume.skills),
            'template': resume.template,
            'color_hex': resume.color_hex,
            'border_style': resume.border_style,
            'font_family': resume.font_family,
            'section_order': resume.section_order,
            'extra_sections': resume.extra_sections,
            'font_size': resume.font_size,
            'section_spacing': resume.section_spacing,
            'line_height': resume.line_height,
            'content_margin': resume.content_margin,
        }
        
        # Create the new resume
        new_resume = Resume.objects.create(**new_resume_data)
        
        # Add work experiences with enhanced descriptions
        enhanced_work_exps = claude_response.get('enhanced_work_experiences', [])
        
        if enhanced_work_exps:
            for exp_data in enhanced_work_exps:
                WorkExperience.objects.create(
                    resume=new_resume,
                    position=exp_data.get('position', ''),
                    company=exp_data.get('company', ''),
                    start_date=exp_data.get('start_date'),
                    end_date=exp_data.get('end_date'),
                    description=exp_data.get('enhanced_description', '')
                )
        else:
            # If no enhanced work experiences, copy the original ones
            for work_exp in resume.work_experiences.all():
                WorkExperience.objects.create(
                    resume=new_resume,
                    position=work_exp.position,
                    company=work_exp.company,
                    start_date=work_exp.start_date,
                    end_date=work_exp.end_date,
                    description=work_exp.description
                )
        
        # Copy education records
        for education in resume.educations.all():
            Education.objects.create(
                resume=new_resume,
                degree=education.degree,
                school=education.school,
                start_date=education.start_date,
                end_date=education.end_date
            )
        
        # Copy projects
        for project in resume.projects.all():
            Project.objects.create(
                resume=new_resume,
                title=project.title,
                description=project.description,
                start_date=project.start_date,
                end_date=project.end_date
            )
        
        # Copy certifications
        for cert in resume.certifications.all():
            Certification.objects.create(
                resume=new_resume,
                name=cert.name,
                issuer=cert.issuer,
                issue_date=cert.issue_date,
                expiry_date=cert.expiry_date
            )
        
        # Copy custom sections
        for section in resume.custom_sections.all():
            new_section = CustomSection.objects.create(
                resume=new_resume,
                title=section.title
            )
            
            # Copy custom section items
            for item in section.items.all():
                CustomSectionItem.objects.create(
                    custom_section=new_section,
                    title=item.title,
                    description=item.description,
                    start_date=item.start_date,
                    end_date=item.end_date
                )
        
        return Response({
            'id': str(new_resume.id),  # Convert UUID to string
            'title': new_resume.title,
            'message': 'Resume adapted successfully',
            'additional_suggestions': claude_response.get('additional_suggestions', '')
        }, status=status.HTTP_201_CREATED)
        
    except Resume.DoesNotExist:
        return Response(
            {'error': 'Resume not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except anthropic.APIError as e:
        print(f"Claude API error: {str(e)}")
        return Response(
            {'error': f'AI service error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return Response(
            {'error': f'Error parsing AI response: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Unexpected error: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Add this function after your parse_resume function

@api_view(['POST'])
def save_parsed_resume(request):
    """
    Save a parsed resume from the validated data to the database
    """
    try:
        # Get validated data from request
        validated_data = request.data.get('validated_data')
        if not validated_data:
            return Response(
                {"error": "No validated resume data provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get user ID
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {"error": "No user ID provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate user_id as UUID
        try:
            user_id_uuid = uuid.UUID(user_id)
        except ValueError:
            return Response(
                {"error": "Invalid user_id format. Please provide a valid UUID format."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Extract personal info
        personal_info = validated_data.get('personal_info', {})
        
        # Create a new Resume instance
        new_resume = Resume(
            user_id=user_id_uuid,
            title=f"Resume - {personal_info.get('first_name', '')} {personal_info.get('last_name', '')}",
            first_name=personal_info.get('first_name'),
            last_name=personal_info.get('last_name'),
            email=personal_info.get('email'),
            phone=personal_info.get('phone'),
            # Split location into city and country if needed
            city=personal_info.get('location', '').split(',')[0].strip() if personal_info.get('location') else None,
            country=personal_info.get('location', '').split(',')[-1].strip() if personal_info.get('location') and ',' in personal_info.get('location', '') else None,
            summary=validated_data.get('summary'),
            skills=validated_data.get('skills', [])
        )
        new_resume.save()
        
        # Add work experiences
        work_experiences = validated_data.get('work_experiences', [])
        for work_exp in work_experiences:
            WorkExperience.objects.create(
                resume=new_resume,
                position=work_exp.get('position'),
                company=work_exp.get('company'),
                start_date=work_exp.get('start_date'),  # Already parsed to YYYY-MM-DD or None
                end_date=work_exp.get('end_date'),      # Already parsed to YYYY-MM-DD or None
                description=work_exp.get('description')
            )
        
        # Add education
        educations = validated_data.get('educations', [])
        for edu in educations:
            Education.objects.create(
                resume=new_resume,
                degree=edu.get('degree'),
                school=edu.get('school'),
                start_date=edu.get('start_date'),  # Already parsed to YYYY-MM-DD or None
                end_date=edu.get('end_date')       # Already parsed to YYYY-MM-DD or None
            )
        
        # Add projects
        projects = validated_data.get('projects', [])
        for proj in projects:
            Project.objects.create(
                resume=new_resume,
                title=proj.get('title'),
                description=proj.get('description')
                # Note: Projects have start_date and end_date fields in the model 
                # but they're not in our parsed data
            )
        
        # Add certifications
        certifications = validated_data.get('certifications', [])
        for cert in certifications:
            Certification.objects.create(
                resume=new_resume,
                name=cert.get('name'),
                issuer=cert.get('issuer'),
                issue_date=cert.get('issue_date')  # Already parsed to YYYY-MM-DD or None
            )
        
        # Return the created resume with detailed info
        serializer = ResumeDetailSerializer(new_resume)
        
        return Response({
            "message": "Resume saved successfully",
            "resume": serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error saving resume: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
