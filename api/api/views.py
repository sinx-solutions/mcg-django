from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied # Import PermissionDenied
from .schemas import ParsedResumeSchema
from django.http import Http404, HttpResponseBadRequest, JsonResponse
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
from datetime import datetime, date
import logging # Import logging
import sys
import asyncio # Ensure asyncio is imported
from django.views.decorators.csrf import csrf_exempt # Import csrf_exempt
from rest_framework.authentication import BaseAuthentication
# Import the correct authentication class
from authentication import SupabaseAuthentication
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiRequest, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
# Import the new serializer
from .serializers import JobSearchQuerySerializer, GenerateCoverLetterInputSerializer, GeneratedCoverLetterSerializer, SavedCoverLetterSerializer, ResumeDetailSerializer, JobDescriptionInputSerializer
from django.utils.decorators import method_decorator # Import for decorating class methods/class
from api.scoring.ats_scorer import ATSScorer # Ensure Scorer is imported

# Configure logging for views
logger = logging.getLogger('resume_api')
logger.setLevel(logging.DEBUG)

# Add console handler if not already added
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

from .models import Profile # Explicitly import Profile first
from .models import (
    Resume,
    WorkExperience,
    Education,
    Project,
    Certification,
    CustomSection,
    CustomSectionItem,
    # Profile, # Already imported above
    SavedCoverLetter
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
    API endpoint for managing resumes.
    Handles create, retrieve, update, partial update, list, and destroy.
    Updates (PUT/PATCH) use a delete-and-recreate strategy for nested sections.
    Requires authentication.
    """
    serializer_class = ResumeSerializer # Default serializer for list/retrieve (basic)
    # Use the imported SupabaseAuthentication class
    authentication_classes = [SupabaseAuthentication]
    permission_classes = [IsAuthenticated] # Require authentication
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [filters.OrderingFilter] # Optional: Add ordering if needed
    ordering_fields = ['updated_at', 'created_at', 'title'] # Optional: Fields to order by
    ordering = ['-updated_at'] # Default ordering

    def get_queryset(self):
        """Ensure users only see their own resumes."""
        print("\n==== ResumeViewSet.get_queryset() ====")
        
        # Debug auth information directly
        print("AUTHENTICATION DEBUG:")
        print(f"Request headers: {self.request.headers.items()}")
        auth_header = self.request.META.get('HTTP_AUTHORIZATION', 'None')
        print(f"Authorization header: {auth_header}")
        
        # Try to get token directly for testing
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '', 1)
            print(f"Token found: {token[:20]}...")
            
            try:
                import jwt
                # Simple decode without verification (for testing only)
                decoded = jwt.decode(token, options={"verify_signature": False})
                print(f"Decoded token: {decoded}")
                user_id = decoded.get('sub')
                print(f"User ID from token: {user_id}")
                
                # Return resumes for this user ID as a test
                print(f"Filtering resumes by user_id from token: {user_id}")
                return Resume.objects.filter(user_id=user_id)
            except Exception as e:
                print(f"Error decoding token: {str(e)}")
        
        user = self.request.user
        print(f"DEBUG: User: {user}, Is authenticated: {getattr(user, 'is_authenticated', False)}")
        logger.debug(f"get_queryset called with user: {user}")
        
        if user and user.is_authenticated:
            # With Supabase auth, user.id contains the Supabase user ID
            print(f"DEBUG: Filtering resumes by user_id: {user.id}")
            logger.debug(f"Filtering resumes for user_id: {user.id}")
            return Resume.objects.filter(user_id=user.id)
        
        print("DEBUG: User not authenticated, returning empty queryset")
        logger.warning("User not authenticated in get_queryset")
        return Resume.objects.none()  # Return empty queryset if not authenticated

    def get_serializer_class(self):
        """
        Use ResumeCompleteSerializer for create/update actions,
        ResumeDetailSerializer for retrieve (single instance),
        and default ResumeSerializer for list.
        """
        print(f"\n==== ResumeViewSet.get_serializer_class() ====")
        print(f"DEBUG: Action: {self.action}")
        logger.debug(f"get_serializer_class called for action: {self.action}")
        
        if self.action in ['create', 'update', 'partial_update']:
            print("DEBUG: Using ResumeCompleteSerializer for write operation")
            return ResumeCompleteSerializer
        elif self.action == 'retrieve':
            # Allow detail via query param for flexibility, default to detail
            include = self.request.query_params.get('include', 'detail')
            print(f"DEBUG: Using retrieve with include={include}")
            
            if include == 'complete' or include == 'detail':
                print("DEBUG: Using ResumeDetailSerializer for detail view")
                return ResumeDetailSerializer # Use Detail for retrieve
            # Fallback to basic serializer if include is not detail/complete
            print("DEBUG: Using basic ResumeSerializer")
            return ResumeSerializer
            
        # Use the default ResumeSerializer for list action
        print("DEBUG: Using default ResumeSerializer (likely for list action)")
        return super().get_serializer_class()

    def perform_create(self, serializer):
        """Associate the resume with the logged-in user."""
        print("\n==== ResumeViewSet.perform_create() ====")
        user = self.request.user
        print(f"DEBUG: User: {user}, Is authenticated: {getattr(user, 'is_authenticated', False)}")
        logger.debug(f"perform_create called with user: {user}")

        if not user.is_authenticated:
            print("DEBUG: User not authenticated, raising PermissionDenied") # Keep this specific debug print for now
            logger.warning("Unauthenticated user attempted to create resume")
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Authentication required to create a resume.")

        # The user_id from the validated data is not needed and could potentially allow
        # a user to create a resume for someone else if validation was misconfigured.
        # Always rely on the authenticated user from the token.
        # user_id_in_data = serializer.validated_data.get('user_id')
        # print(f"DEBUG: user_id in data: {user_id_in_data}")
        # print(f"DEBUG: authenticated user.id: {user.id}")
        # if user_id_in_data and str(user_id_in_data) != str(user.id):
        #     print("DEBUG: user_id mismatch, raising PermissionDenied")
        #     logger.warning(f"User ID mismatch: {user_id_in_data} vs {user.id}")
        #     from rest_framework.exceptions import PermissionDenied
        #     raise PermissionDenied("Cannot create resume for another user.")

        # Save with the authenticated user's ID
        print(f"DEBUG: Saving resume with user_id: {user.id}") # Keep this specific debug print for now
        logger.info(f"Creating resume for user_id: {user.id}")
        serializer.save(user_id=user.id)

    def create(self, request, *args, **kwargs):
        """Handle POST request. Use ResumeDetailSerializer for the response."""
        print("\n==== ResumeViewSet.create() ====")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request data: {request.data}")
        logger.debug(f"create called with data: {request.data}")
        
        # Just temporarily verify we can see the auth header in the request
        auth_header = request.META.get('HTTP_AUTHORIZATION', 'Not provided')
        print(f"DEBUG: Auth header in create: {auth_header[:20]}...")
        
        serializer = self.get_serializer(data=request.data)
        valid = serializer.is_valid()
        print(f"DEBUG: Serializer valid: {valid}")
        
        if not valid:
            print(f"DEBUG: Serializer errors: {serializer.errors}")
            logger.error(f"Validation errors: {serializer.errors}")
            serializer.is_valid(raise_exception=True)
        
        # perform_create will save the instance and set the user_id
        self.perform_create(serializer)
        print("DEBUG: Resume created successfully")
        
        # Serialize the saved instance using the Detail serializer for the response
        response_serializer = ResumeDetailSerializer(serializer.instance, context=self.get_serializer_context())
        headers = self.get_success_headers(response_serializer.data)
        print(f"DEBUG: Returning response with status 201")
        logger.info(f"Resume created with ID: {serializer.instance.id}")
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """
        Handle PUT/PATCH requests. Use ResumeDetailSerializer for the response.
        Ensures user can only update their own resume.
        """
        print("\n==== ResumeViewSet.update() ====")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request data keys: {request.data.keys() if hasattr(request.data, 'keys') else 'No keys available'}")
        logger.debug(f"update called for pk: {kwargs.get('pk')}")
        
        partial = kwargs.pop('partial', False)
        print(f"DEBUG: Partial update: {partial}")
        
        try:
            instance = self.get_object() # get_object already filters by user via get_queryset
            print(f"DEBUG: Got instance with ID: {instance.id}")
            logger.debug(f"Found resume: {instance.id}")
        except Exception as e:
            print(f"DEBUG: Error getting object: {str(e)}")
            logger.error(f"Error retrieving resume: {str(e)}")
            raise

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            valid = serializer.is_valid()
            print(f"DEBUG: Serializer valid: {valid}")
            
            if not valid:
                print(f"DEBUG: Serializer errors: {serializer.errors}")
                logger.error(f"Validation errors: {serializer.errors}")
                
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            print("DEBUG: Resume updated successfully")
            logger.info(f"Resume updated: {instance.id}")

            if getattr(instance, '_prefetched_objects_cache', None):
                # If 'prefetch_related' has been applied to a queryset, we need to
                # forcibly invalidate the prefetch cache on the instance.
                instance._prefetched_objects_cache = {}

            # Serialize the updated instance using the Detail serializer for the response
            response_serializer = ResumeDetailSerializer(serializer.instance, context=self.get_serializer_context())
            print(f"DEBUG: Returning response with status 200")
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"DEBUG: Error updating resume: {str(e)}")
            logger.error(f"Error updating resume: {str(e)}")
            raise

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'resume_data': {
                        'type': 'object',
                        'description': 'Complete resume data for non-authenticated users'
                    }
                }
            }
        },
        responses={
            200: OpenApiResponse(
                description="Summary generated successfully.", 
                response={'type': 'object', 'properties': {'summary': {'type': 'string'}}}
            ),
            404: OpenApiResponse(description="Resume not found or access denied."),
            500: OpenApiResponse(description="Server error during generation.")
        },
        summary="Generate a professional summary using AI",
        description="Generates a professional summary from resume data. Can be used with either a resume ID (for authenticated users) or complete resume data in the request (for non-authenticated users)."
    )
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def generate_summary(self, request, pk=None):
        """
        Generate a professional summary using Claude AI based on resume information.
        Can be used with either:
        1. A resume ID (authenticated users with saved resumes)
        2. Complete resume data in the request body (non-authenticated users)
        """
        try:
            # Check if resume data is provided in the request
            if request.data and 'resume_data' in request.data:
                # For unauthenticated users sending resume data from local state
                resume_data = request.data['resume_data']
                # No need to save the resume or the generated summary for unauthenticated users
                save_to_db = False
            else:
                # For authenticated users using existing resume by ID
                try:
                    resume = self.get_object()  # Ensures user owns the resume if authenticated
                    # Get detailed data for the resume
                    serializer = ResumeDetailSerializer(resume)
                    resume_data = serializer.data
                    save_to_db = True
                except (PermissionDenied, Resume.DoesNotExist):
                    # If user is not authenticated or doesn't own the resume and didn't provide resume_data
                    return Response(
                        {'error': 'You must either provide resume data or be authenticated and own this resume'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            first_name = resume_data.get('first_name', '')
            last_name = resume_data.get('last_name', '')
            job_title = resume_data.get('job_title', 'Not specified')
            skills = resume_data.get('skills', [])
            
            prompt = f"""
            You are an AI career assistant. Generate a professional summary for a resume based on the person's 
            experience, education, and skills. The summary should be concise (3-5 sentences), highlight key strengths,
            and be written in first person.

            Resume Information:
            -------------------
            Name: {first_name} {last_name}
            Job Title: {job_title}
            Skills: {", ".join(skills) if skills else "Not specified"}
            
            Work Experience:
            """
            
            # Add work experience details
            work_experiences = resume_data.get('work_experiences', [])
            if work_experiences:
                for i, exp in enumerate(work_experiences):
                    prompt += f"""
                    {i+1}. {exp.get('position', 'Role')} at {exp.get('company', 'Company')}
                    Duration: {exp.get('start_date', 'Start date')} to {exp.get('end_date', 'Present')}
                    Description: {exp.get('description', 'Not provided')}
                    """
            else:
                prompt += "\nNo work experience provided.\n"
            
            # Add education details
            educations = resume_data.get('educations', [])
            prompt += "\nEducation:\n"
            if educations:
                for i, edu in enumerate(educations):
                    prompt += f"""
                    {i+1}. {edu.get('degree', 'Degree')} from {edu.get('school', 'School')}
                    Duration: {edu.get('start_date', 'Start date')} to {edu.get('end_date', 'End date')}
                    """
            else:
                prompt += "No education details provided.\n"
            
            # Add projects details if available
            projects = resume_data.get('projects', [])
            if projects:
                prompt += "\nProjects:\n"
                for i, proj in enumerate(projects):
                    prompt += f"""
                    {i+1}. {proj.get('title', 'Project')}
                    Description: {proj.get('description', 'Not provided')}
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
            
            # Update the resume with the generated summary if authenticated user
            if save_to_db:
                resume.summary = summary
                resume.save()
            
            return Response({
                "summary": summary
            }, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist: # Should be handled by get_object permissions
            return Response(
                {'error': 'Resume not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Log the error
            print(f"Error generating summary: {e}")
            return Response(
                {'error': 'Failed to generate summary'}, # Generic error for client
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def suggest_skills(self, request, pk=None):
        """
        Suggest relevant skills based on resume information
        Requires authentication and ownership.
        """
        try:
            resume = self.get_object() # Ensures user owns the resume
            
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
                    # Log the error
                    print(f"Error parsing suggested skills AI response: {response_text[:1000]}")
                    return Response(
                        {'error': 'Failed to parse AI response'}, # Generic error for client
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            return Response({
                "suggested_skills": suggested_skills
            }, status=status.HTTP_200_OK)
            
        except Resume.DoesNotExist: # Should be handled by get_object permissions
            return Response(
                {'error': 'Resume not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Log the error
            print(f"Error suggesting skills: {e}")
            return Response(
                {'error': 'Failed to suggest skills'}, # Generic error for client
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ViewSets for Resume components
class WorkExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkExperienceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Ensure users only see work experiences linked to their resumes."""
        user = self.request.user
        if user.is_authenticated:
            # Filter based on the resume__user_id relationship
            return WorkExperience.objects.filter(resume__user_id=user.id)
        return WorkExperience.objects.none()

    def perform_create(self, serializer):
        """Ensure the work experience is linked to a resume owned by the user."""
        resume_id = self.request.data.get('resume')
        try:
            # Validate that the resume exists and belongs to the user
            resume = Resume.objects.get(id=resume_id, user_id=self.request.user.id)
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add work experience to this resume.")
        except ValueError: # Handle invalid UUID format for resume_id
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Invalid resume ID format.")

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'position': {
                        'type': 'string',
                        'description': 'Job position/title'
                    },
                    'company': {
                        'type': 'string',
                        'description': 'Company name'
                    },
                    'startDate': {
                        'type': 'string',
                        'format': 'date',
                        'description': 'Start date of the position'
                    },
                    'endDate': {
                        'type': 'string',
                        'format': 'date',
                        'description': 'End date of the position'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Current work experience description to enhance'
                    }
                },
                'required': ['description']
            }
        },
        responses={
            200: OpenApiResponse(
                description="Enhanced description generated.", 
                response={'type': 'object', 'properties': {'enhanced_description': {'type': 'string'}}}
            ),
            400: OpenApiResponse(description="Invalid input data."),
            500: OpenApiResponse(description="Server error during enhancement.")
        },
        summary="Enhance work experience description using AI",
        description="Takes work experience details and uses AI to generate an improved description. Can be used by either authenticated or non-authenticated users."
    )
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def enhance(self, request, pk=None):
        """
        Enhance work experience description using Claude AI.
        No authentication required. Can accept either:
        1. A work experience ID (for authenticated users with saved work experiences)
        2. Complete work experience data in the request body (for all users)
        """
        try:
            # Check if work experience data is provided in the request
            if request.data and 'description' in request.data:
                # For users sending work experience data directly
                position = request.data.get('position', "Not specified")
                company = request.data.get('company', "Not specified")
                start_date = request.data.get('startDate', "Not specified")
                end_date = request.data.get('endDate', "Not specified")
                current_description = request.data.get('description', "")
            else:
                # For users with a saved work experience
                try:
                    work_exp = self.get_object()
                    position = work_exp.position or "Not specified"
                    company = work_exp.company or "Not specified"
                    start_date = work_exp.start_date or "Not specified"
                    end_date = work_exp.end_date or "Not specified"
                    current_description = work_exp.description or ""
                except (PermissionDenied, WorkExperience.DoesNotExist):
                    return Response(
                        {'error': 'You must either provide work experience details or have access to the specified work experience'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Enhance the following work experience description for a resume.
            Make it more impactful, achievement-oriented, and use strong action verbs.
            Focus on quantifiable achievements and skills demonstrated.
            
            Position: {position}
            Company: {company}
            Duration: {start_date} to {end_date}
            Current Description: {current_description}
            
            Provide an enhanced description that:
            1. Starts with strong action verbs
            2. Includes specific accomplishments with metrics when possible
            3. Demonstrates skills and impact
            4. Is concise yet comprehensive
            5. Is relevant to the position
            
            Return the response as a JSON object with a 'description' field containing bullet points with line breaks.

            Example format:
            {{
              "description": "• Led development of a full-stack web application using React and Node.js, resulting in 40% faster load times\\\\n• Managed a team of 5 developers, implementing agile methodologies that improved sprint velocity by 25%\\\\n• Architected and deployed microservices infrastructure reducing system downtime by 60%"
            }}

            Guidelines:
            - Start each bullet point with •
            - Use \\\\n for new lines
            - Focus on achievements and impact
            - Use strong action verbs
            - Include metrics and numbers
            - Highlight leadership and collaboration
            - Keep it to 3-5 bullet points
            - Only return the JSON response, no other text
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
            response_text = message.content[0].text.strip()
            
            # Parse the JSON response
            try:
                # Try to parse the JSON response from Claude
                import json
                response_json = json.loads(response_text)
                
                # Get the description value from the response
                enhanced_description = response_json.get("description", "")
                
                # Return only the description value, not nested in another JSON object
                return Response({
                    "description": enhanced_description
                }, status=status.HTTP_200_OK)
                
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract using regex
                import re
                match = re.search(r'"description":\s*"([^"]*)"', response_text)
                if match:
                    enhanced_description = match.group(1)
                    return Response({
                        "description": enhanced_description
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "error": "Failed to parse AI response",
                        "raw_response": response_text
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            # Log the error
            print(f"Error enhancing work experience: {e}")
            return Response(
                {'error': 'Failed to enhance work experience'}, # Generic error for client
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Education.objects.filter(resume__user_id=user.id)
        return Education.objects.none()

    def perform_create(self, serializer):
        resume_id = self.request.data.get('resume')
        try:
            resume = Resume.objects.get(id=resume_id, user_id=self.request.user.id)
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add education to this resume.")
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Invalid resume ID format.")

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Project.objects.filter(resume__user_id=user.id)
        return Project.objects.none()

    def perform_create(self, serializer):
        resume_id = self.request.data.get('resume')
        try:
            resume = Resume.objects.get(id=resume_id, user_id=self.request.user.id)
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add project to this resume.")
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Invalid resume ID format.")

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': 'Project title'
                    },
                    'shortDescription': {
                        'type': 'string',
                        'description': 'Brief description of the project'
                    },
                    'startDate': {
                        'type': 'string',
                        'format': 'date',
                        'description': 'Start date of the project'
                    },
                    'endDate': {
                        'type': 'string',
                        'format': 'date',
                        'description': 'End date of the project'
                    },
                    'description': {
                        'type': 'string',
                        'description': 'Current project description to enhance'
                    }
                },
                'required': ['description']
            }
        },
        responses={
            200: OpenApiResponse(
                description="Enhanced description generated.", 
                response={'type': 'object', 'properties': {'description': {'type': 'string'}}}
            ),
            400: OpenApiResponse(description="Invalid input data."),
            500: OpenApiResponse(description="Server error during enhancement.")
        },
        summary="Enhance project description using AI",
        description="Takes project details and uses AI to generate an improved description. Can be used by either authenticated or non-authenticated users."
    )
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def enhance(self, request, pk=None):
        """
        Enhance project description using Claude AI.
        No authentication required. Can accept either:
        1. A project ID (for authenticated users with saved projects)
        2. Complete project data in the request body (for all users)
        """
        try:
            # Check if project data is provided in the request
            if request.data and 'description' in request.data:
                # For users sending project data directly
                title = request.data.get('title', "Not specified")
                short_description = request.data.get('shortDescription', "")
                start_date = request.data.get('startDate', "Not specified")
                end_date = request.data.get('endDate', "Not specified")
                current_description = request.data.get('description', "")
            else:
                # For users with a saved project
                try:
                    project = self.get_object()
                    title = project.title or "Not specified"
                    # The Project model likely doesn't have a short_description field
                    short_description = ""
                    start_date = project.start_date or "Not specified"
                    end_date = project.end_date or "Not specified"
                    current_description = project.description or ""
                except (PermissionDenied, Project.DoesNotExist):
                    return Response(
                        {'error': 'You must either provide project details or have access to the specified project'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            client = get_claude_client()
            
            # Prepare prompt for Claude
            prompt = f"""
            You are an AI career assistant. Enhance the following project description for a resume.
            Make it more impactful, achievement-oriented, and focus on skills demonstrated.
            
            Project Title: {title}
            Short Description: {short_description}
            Duration: {start_date} to {end_date}
            Current Description: {current_description}
            
            Provide an enhanced description that:
            1. Clearly explains the project purpose
            2. Highlights the technologies or methodologies used
            3. Emphasizes your specific contributions
            4. Mentions any challenges overcome
            5. Notes the impact or outcomes of the project
            
            Return the response as a JSON object with a 'description' field containing bullet points with line breaks.

            Example format:
            {{
              "description": "• Developed a responsive web application with React and Node.js that streamlined data processing by 40%\\\\n• Implemented RESTful API endpoints that improved system reliability and reduced client-side errors by 35%\\\\n• Engineered a user authentication system with JWT, enhancing security and user experience"
            }}

            Guidelines:
            - Start each bullet point with •
            - Use \\\\n for new lines
            - Focus on achievements and impact
            - Use strong action verbs
            - Include metrics and numbers when possible
            - Highlight technical skills and problem-solving
            - Keep it to 3-5 bullet points
            - Only return the JSON response, no other text
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
            response_text = message.content[0].text.strip()
            
            # Parse the JSON response
            try:
                # Try to parse the JSON response from Claude
                import json
                response_json = json.loads(response_text)
                
                # Get the description value from the response
                enhanced_description = response_json.get("description", "")
                
                # Return only the description value, not nested in another JSON object
                return Response({
                    "description": enhanced_description
                }, status=status.HTTP_200_OK)
                
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract using regex
                import re
                match = re.search(r'"description":\s*"([^"]*)"', response_text)
                if match:
                    enhanced_description = match.group(1)
                    return Response({
                        "description": enhanced_description
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        "error": "Failed to parse AI response",
                        "raw_response": response_text
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            # Log the error
            print(f"Error enhancing project: {e}")
            return Response(
                {'error': 'Failed to enhance project'}, # Generic error for client
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CertificationViewSet(viewsets.ModelViewSet):
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Certification.objects.filter(resume__user_id=user.id)
        return Certification.objects.none()

    def perform_create(self, serializer):
        resume_id = self.request.data.get('resume')
        try:
            resume = Resume.objects.get(id=resume_id, user_id=self.request.user.id)
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add certification to this resume.")
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Invalid resume ID format.")

    @action(detail=True, methods=['post'])
    def enhance(self, request, pk=None):
        """ Enhance certification description using Claude AI. Requires auth and ownership. """
        try:
            certification = self.get_object()
            # ... (Enhance logic - potentially less common for certs, maybe enhance name/issuer?) ...
            # Example: Focus on verifying or finding more details
            name = certification.name or ""
            issuer = certification.issuer or ""

            # For certs, enhancement might mean validation or suggesting keywords
            # Placeholder: Return original data or a simple message
            return Response({
                "message": "Enhancement for certifications is not yet implemented.",
                "name": name,
                "issuer": issuer
            }, status=status.HTTP_200_OK)

        except Certification.DoesNotExist: # Handled by get_object
            return Response(
                {'error': 'Certification not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error enhancing certification: {e}")
            return Response(
                {'error': 'Failed to enhance certification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CustomSectionViewSet(viewsets.ModelViewSet):
    serializer_class = CustomSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return CustomSection.objects.filter(resume__user_id=user.id)
        return CustomSection.objects.none()

    def perform_create(self, serializer):
        resume_id = self.request.data.get('resume')
        try:
            resume = Resume.objects.get(id=resume_id, user_id=self.request.user.id)
            # Note: CustomSectionSerializer might need modification if it handles items itself
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add custom section to this resume.")
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Invalid resume ID format.")

class CustomSectionItemViewSet(viewsets.ModelViewSet):
    serializer_class = CustomSectionItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Filter based on the custom_section__resume__user_id relationship
            return CustomSectionItem.objects.filter(custom_section__resume__user_id=user.id)
        return CustomSectionItem.objects.none()

    def perform_create(self, serializer):
        section_id = self.request.data.get('custom_section')
        try:
            # Validate that the section exists and belongs to a resume owned by the user
            section = CustomSection.objects.get(id=section_id, resume__user_id=self.request.user.id)
            serializer.save(custom_section=section)
        except CustomSection.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cannot add item to this custom section.")
        except ValueError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Invalid custom section ID format.")

    @action(detail=True, methods=['post'])
    def enhance(self, request, pk=None):
        """ Enhance custom section item description. Requires auth and ownership. """
        try:
            item = self.get_object()
            # ... (Enhance logic similar to WorkExperience/Project, using item fields) ...
            title = item.title or ""
            current_description = item.description or ""
            
            client = get_claude_client()
            
            prompt = f"""
            You are an AI career assistant. Enhance the following custom resume section item description.
            Make it more impactful and highlight relevant skills or achievements.

            Item Title: {title}
            Current Description: {current_description}
            
            Provide an enhanced description suitable for a resume.
            Return only the enhanced description text.
            """
            
            message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            enhanced_description = message.content[0].text.strip()
            
            return Response({
                "enhanced_description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except CustomSectionItem.DoesNotExist: # Handled by get_object
            return Response(
                {'error': 'Custom section item not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error enhancing custom section item: {e}")
            return Response(
                {'error': 'Failed to enhance item'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Resume Parser API View using OpenRouter
@api_view(['POST']) # Keep @api_view first
@csrf_exempt        # Add csrf_exempt
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def parse_resume(request):
    """
    Parse a resume file (PDF/Word) and extract structured data using OpenRouter.
    """
    print("Received request for /api/parse-resume/ (Using OpenRouter)")

    # 1. Get file and validate user_id from the request
    resume_files = request.FILES.get('resume')

    print(f"Received File: {resume_files.name if resume_files else 'None'}")

    # 2. Validate input
    if not resume_files:
        return Response(
            {'error': "No resume files were uploaded"}, status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Validate file type
    file_name = resume_files.name.lower()
    if not (file_name.endswith('.pdf') or file_name.endswith('.docx')):
        return Response(
            {"error": f"Unsupported file format: {file_name}. Please upload a PDF or DOCX file."}, status=status.HTTP_400_BAD_REQUEST
        )

    # 4. Extract text from file
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

    # 5. Process raw text with OpenRouter
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

@api_view(['POST']) # Keep @api_view first
@csrf_exempt        # Add csrf_exempt
@permission_classes([IsAuthenticated])
def save_parsed_resume(request):
    """
    Save a parsed resume from the validated data to the database.
    Uses the authenticated user from the JWT.
    """
    try:
        # Get validated data from request
        validated_data = request.data.get('validated_data')
        if not validated_data:
            return Response(
                {"error": "No validated resume data provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- GET USER ID FROM AUTHENTICATED TOKEN --- <<< MODIFY THIS SECTION
        if not request.user.is_authenticated:
             # This check might be redundant due to @permission_classes, but safe to keep
             return Response(
                 {"error": "Authentication required."}, 
                 status=status.HTTP_401_UNAUTHORIZED
             )
        user_id_uuid = request.user.id # Get user ID from the verified token
        # --------------------------------------------

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
        
@extend_schema(
    request=JobDescriptionInputSerializer,
    responses={
        200: OpenApiResponse(description="ATS Score result calculated successfully."),
        400: OpenApiResponse(description="Invalid input data (check job description format). "),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Permission denied (resume does not belong to user)."),
        404: OpenApiResponse(description="Resume not found."),
        500: OpenApiResponse(description="Server error during scoring.")
    },
    summary="Score a Resume against a Job Description",
    description="Takes a resume ID (from URL) and job description details (in request body), verifies ownership, performs ATS scoring, and returns the detailed score."
)
@api_view(['POST']) # Decorator to make it an API view accepting POST
@csrf_exempt        # Exempt from CSRF as it uses JWT auth
@permission_classes([IsAuthenticated]) # Require authentication
def score_resume(request, resume_id):
    """
    Score a resume against a job description.
    Requires authentication and checks resume ownership.
    Takes job description data via POST body, validated by JobDescriptionInputSerializer.
    """
    logger.info(f"score_resume called for resume_id: {resume_id} by user: {request.user.id}")
    
    try:
        # 1. Fetch Resume from DB & Verify Ownership
        try:
            resume_obj = Resume.objects.get(id=resume_id)
            logger.debug(f"Found resume object with ID: {resume_obj.id}")
            
            # --- Authorization Check --- 
            # Convert request.user.id (str) to UUID for comparison
            try:
                request_user_uuid = uuid.UUID(request.user.id)
            except (ValueError, TypeError):
                # Handle cases where request.user.id is not a valid UUID string
                logger.error(f"Invalid UUID format for request.user.id: {request.user.id}")
                raise PermissionDenied("Invalid user identifier format.")

            if resume_obj.user_id != request_user_uuid:
                logger.warning(f"Permission denied: User {request.user.id} ({request_user_uuid}) attempted to score resume {resume_id} owned by {resume_obj.user_id}")
                raise PermissionDenied("You do not have permission to score this resume.")
            logger.debug(f"User {request.user.id} verified as owner of resume {resume_id}.")
            # --- End Authorization Check ---

            # Serialize the resume data
            serializer = ResumeDetailSerializer(resume_obj)
            resume_data = serializer.data
            logger.debug("Resume data serialized successfully.")
            
        except Resume.DoesNotExist:
            logger.warning(f"Resume with ID {resume_id} not found.")
            return Response(
                {"error": f"Resume with ID {resume_id} not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as pd:
             # Re-raise PermissionDenied to be caught by DRF handler (returns 403)
            raise pd
        except Exception as e:
            logger.error(f"Error fetching resume {resume_id}: {e}", exc_info=True)
            return Response({"error": "Error retrieving resume."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # 2. Validate Job Description data from request using the new serializer
        jd_serializer = JobDescriptionInputSerializer(data=request.data)
        if not jd_serializer.is_valid():
            logger.error(f"Invalid job description input: {jd_serializer.errors}")
            return Response(
                {"error": "Invalid job description data provided.", "details": jd_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Use the validated data dictionary
        job_data = jd_serializer.validated_data 
        logger.debug("Job description data validated successfully.")
            
        # 3. Preprocess Resume Data for Scorer (Remains largely the same)
        resume_data_for_scorer = resume_data.copy()
        if 'work_experiences' in resume_data_for_scorer:
            resume_data_for_scorer['experience'] = resume_data_for_scorer.pop('work_experiences')
        else:
            resume_data_for_scorer['experience'] = []
        
        # Construct substitute raw_text if needed (though might be less critical now)
        # Consider if scorer should always rely on structured data if available?
        if not resume_data_for_scorer.get('raw_text'):
            resume_raw_text_parts = [
                resume_data_for_scorer.get('summary', ''),
                resume_data_for_scorer.get('job_title', ''),
            ]
            for exp in resume_data_for_scorer.get('experience', []): # Use 'experience'
                 resume_raw_text_parts.extend(filter(None, [exp.get('position'), exp.get('company'), exp.get('description')]))
            for edu in resume_data_for_scorer.get('educations', []):
                 resume_raw_text_parts.extend(filter(None, [edu.get('degree'), edu.get('school')]))
            # ... (continue for projects, certs, custom sections, skills as before) ...
            for proj in resume_data_for_scorer.get('projects', []):
                resume_raw_text_parts.extend(filter(None,[proj.get('title'), proj.get('description')]))
            for cert in resume_data_for_scorer.get('certifications', []):
                resume_raw_text_parts.extend(filter(None,[cert.get('name'), cert.get('issuer')]))
            for section in resume_data_for_scorer.get('custom_sections', []):
                resume_raw_text_parts.append(section.get('title',''))
                for item in section.get('items', []):
                    resume_raw_text_parts.extend(filter(None,[item.get('title'), item.get('description')]))
            resume_raw_text_parts.extend(resume_data_for_scorer.get('skills', []))
            
            resume_data_for_scorer['raw_text'] = ' '.join(filter(None, resume_raw_text_parts))
            logger.debug("Constructed substitute resume raw_text.")
        else:
             logger.debug("Using existing resume raw_text.")
            
        # 4. Initialize and Run Scorer
        try:
            scorer = ATSScorer()
            logger.debug("ATS Scorer initialized.")
            # Pass the validated job_data dictionary to the scorer
            result = scorer.score_resume(resume_data_for_scorer, job_data)
            logger.info(f"Scoring complete for resume {resume_id}. Overall score: {result.get('overall_score', 'N/A')}")
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during scoring for resume {resume_id}: {e}", exc_info=True)
            return Response(
                {"error": f"Error scoring resume: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        # Catch any unexpected errors in the main try block
        logger.error(f"Unexpected error in score_resume view for resume {resume_id}: {e}", exc_info=True)
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# --- Imports for Job Search Agent API ---
import sys
import os
import json
import asyncio
from django.http import JsonResponse, HttpResponseBadRequest

# --- Job Search Agent API View ---

# Ensure the agent-sdkk directory is findable
AGENT_SDK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'agent-sdkk'))

@extend_schema(
    # Replace the manual request definition with the serializer
    request=JobSearchQuerySerializer,
    responses={
        200: OpenApiResponse(description="Job search results."),
        400: OpenApiResponse(description="Invalid JSON or missing/invalid query parameter."),
        500: OpenApiResponse(description="Server error during job search.")
    },
    summary="Perform a job search using the JobSearchPal agent.",
    description="Takes a JSON POST body with a 'query' field and returns job search results from the agent."
)
@api_view(['POST'])
def job_search_api(request):
    """API endpoint to interact with the JobSearchPal agent."""
    # Use the serializer to validate and parse input
    serializer = JobSearchQuerySerializer(data=request.data)
    if serializer.is_valid():
        query = serializer.validated_data['query']
    else:
        # Return serializer errors for invalid input
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # The rest of your logic remains largely the same, but uses the validated 'query'
    # Temporarily add agent-sdkk path to sys.path to allow import
    original_sys_path = list(sys.path)
    if AGENT_SDK_DIR not in sys.path:
        sys.path.insert(0, AGENT_SDK_DIR)

    try:
        # Import the agent and runner dynamically
        from jobsearch import job_search_agent, Runner

        # Run the agent asynchronously
        runner = Runner()
        result = asyncio.run(runner.run(job_search_agent, query))

        # Extract the final output
        final_output = result.get('final_output', "Agent did not produce final output.")

        return JsonResponse({"result": final_output})

    except ImportError as e:
        logger.error(f"Could not import from jobsearch.py: {e}. Check path: {AGENT_SDK_DIR}")
        return JsonResponse({"error": f"Server configuration error: Could not load job search module. {e}"}, status=500)
    except Exception as e:
        logger.error(f"Error running job search agent: {e}")
        logger.exception("Job search agent error details:")
        return JsonResponse({"error": f"Error processing job search: {str(e)}"}, status=500)
    finally:
        # Restore original sys.path
        sys.path = original_sys_path

# --- Generate Cover Letter View ---

# Helper to serialize UUIDs for JSON dumping in prompt
def serialize_uuid(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

@extend_schema(
    request=GenerateCoverLetterInputSerializer,
    responses={
        200: OpenApiResponse(response=GeneratedCoverLetterSerializer, description="Cover letter generated and saved successfully."),
        400: OpenApiResponse(description="Invalid input data."),
        401: OpenApiResponse(description="Authentication required."),
        403: OpenApiResponse(description="Permission denied (e.g., resume not found or doesn't belong to user)."),
        404: OpenApiResponse(description="Resume or Profile not found."),
        500: OpenApiResponse(description="Server error during generation or saving."),
        503: OpenApiResponse(description="AI Service (OpenRouter) unavailable or returned an error.")
    },
    summary="Generate a tailored cover letter using AI.",
    description="Takes a resume ID and job details, generates a cover letter using AI based on mapping resume content to the job description, saves it, and returns the result."
)
@api_view(['POST'])
@csrf_exempt
@permission_classes([IsAuthenticated])
def generate_cover_letter(request):
    """API endpoint to generate a cover letter based on a resume and job description."""
    logger.info("generate_cover_letter endpoint called.")

    # 1. Validate Input
    input_serializer = GenerateCoverLetterInputSerializer(data=request.data)
    if not input_serializer.is_valid():
        logger.error(f"Invalid input data: {input_serializer.errors}")
        return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = input_serializer.validated_data
    resume_id = validated_data['resume_id']
    job_title = validated_data['job_title']
    company_name = validated_data['company_name']
    job_description = validated_data['job_description']
    user_id = request.user.id # Get authenticated user ID

    logger.debug(f"Input validated for user {user_id}, resume {resume_id}")

    # 2. Fetch Resume Data
    try:
        resume = Resume.objects.get(pk=resume_id, user_id=user_id)
        resume_serializer = ResumeDetailSerializer(resume)
        resume_data_json = json.dumps(resume_serializer.data, indent=2, default=serialize_uuid)
        logger.debug("Resume data fetched and serialized.")
    except Resume.DoesNotExist:
        logger.warning(f"Resume not found or access denied for user {user_id}, resume {resume_id}")
        return Response({"error": "Resume not found or you do not have permission to access it."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching resume {resume_id} for user {user_id}: {e}")
        return Response({"error": "Failed to retrieve resume data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 3. Fetch Profile Data & Generate Date
    user_profile = {}
    try:
        profile = Profile.objects.get(pk=user_id)
        user_profile = {
            "name": profile.full_name or None, # Use None if empty
            "email": profile.email or None,
            # Add address fields here IF they existed in the Profile model
            # "address": profile.address_line1 or None,
            # "city": profile.city or None,
            # etc.
        }
        logger.debug("Profile data fetched.")
    except Profile.DoesNotExist:
        logger.warning(f"Profile not found for user {user_id}. Placeholders will be used.")
        pass # Continue with empty user_profile dict
    except Exception as e:
        logger.error(f"Error fetching profile for user {user_id}: {e}")
        pass # Non-fatal, continue with empty user_profile dict

    # Generate current date
    current_date_str = date.today().strftime("%B %d, %Y") # e.g., April 10, 2025

    # Prepare placeholders, using fetched data or generic placeholders if None/missing
    # Important: Decide on consistent placeholders if data is missing
    placeholder_name = user_profile.get('name') or "[Your Name]"
    placeholder_email = user_profile.get('email') or "[Your Email]"
    placeholder_phone = resume.phone or "[Your Phone Number]" # Get phone from Resume model
    # Address details are missing from Profile model based on schema
    placeholder_address = "[Your Address]"
    placeholder_city_state_zip = f"{resume.city or '[City]'}, {resume.country or '[Country]'}" # Combine from Resume

    # 4. Construct AI Prompt (Refined)
    prompt = f"""
You are an expert career advisor and professional writer crafting a persuasive cover letter.
Your task is to generate a tailored cover letter based on the provided resume data and job details.

**Instructions:**
1.  Analyze the **Job Description** for key requirements, skills, keywords, and company values.
2.  Review the structured **Resume Data**.
3.  **Crucially**, generate the cover letter body by **directly mapping specific examples, achievements, projects, and skills** from the Resume Data to the **key requirements** identified in the Job Description. Demonstrate skills using evidence; quantify achievements if possible.
4.  Structure the letter with:
    *   **Header:** Include sender contact details (Name, Address, City/State/Zip, Email, Phone) and the current Date ({current_date_str}). **Only include address lines if address data is available in the User Profile Data section below; otherwise, omit the address lines.** Use the provided contact details. Use placeholder brackets (e.g., `[Hiring Manager Name]`, `[Company Address]`) for recipient details if not known.
    *   **Introduction:** State the position ({job_title}), company ({company_name}), and express specific enthusiasm.
    *   **Body Paragraph(s) (1-3):** Focus each paragraph on 1-2 key job requirements and showcase how specific resume experiences/skills/projects directly meet them. Use strong action verbs.
    *   **Company Fit Paragraph:** Explain interest in *this specific company* ({company_name}). Connect the user's background to the company's mission/culture if possible.
    *   **Closing:** Reiterate enthusiasm, express confidence, call to action (e.g., discuss further).
    *   **Signature:** Use the user's name.
5.  Maintain a professional, confident, enthusiastic, and tailored tone. Avoid generic clichés.
6.  Format as a standard professional letter.
7.  Return ONLY the full text of the cover letter as a single string, with appropriate line breaks (\\n).

**Job Details:**
*   Job Title: {job_title}
*   Company Name: {company_name}
*   Job Description:
{job_description}

**Resume Data (JSON):**
{resume_data_json}

**User Profile Data (for placeholders):**
*   Name: {placeholder_name}
*   Email: {placeholder_email}
*   Phone: {placeholder_phone}
*   Address: {placeholder_address} 
*   City/State/Zip: {placeholder_city_state_zip}
*   Date: {current_date_str}

Now, generate the cover letter text:
"""

    logger.debug(f"Prompt constructed (length: {len(prompt)} chars). First 500 chars: {prompt[:500]}")

    # 5. Call OpenRouter API
    try:
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            logger.error("OpenRouter API key not found in environment variables.")
            return Response({"error": "AI service configuration error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"Calling OpenRouter API (model: openai/gpt-4o) for user {user_id}")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
                # Optional: Add Helicone headers if needed
                # "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}"
            },
            json={
                # Consider using a slightly cheaper/faster model if acceptable, e.g., claude-3-haiku, mistral models
                # Or stick with a powerful one like gpt-4o or claude-3-sonnet/opus
                "model": "openai/gpt-4o", # Or "anthropic/claude-3-sonnet-20240229", "google/gemini-pro-1.5"
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500, # Adjust as needed
                "temperature": 0.7, # Adjust for creativity vs. predictability
            },
            timeout=90 # Increase timeout for potentially long generation
        )

        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        ai_data = response.json()
        generated_text = ai_data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

        if not generated_text:
            logger.error(f"OpenRouter response missing content for user {user_id}. Response: {ai_data}")
            return Response({"error": "AI service returned empty content."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        logger.info(f"Successfully received generated cover letter text from OpenRouter for user {user_id}. Length: {len(generated_text)}")

    except requests.exceptions.Timeout:
        logger.error(f"OpenRouter API request timed out for user {user_id}.")
        return Response({"error": "AI service request timed out."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenRouter API request failed for user {user_id}: {e}")
        error_detail = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json() or e.response.text
            except json.JSONDecodeError:
                error_detail = e.response.text
        return Response({"error": "Failed to communicate with AI service.", "detail": error_detail}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        logger.error(f"Unexpected error during OpenRouter call for user {user_id}: {e}", exc_info=True)
        return Response({"error": "An unexpected error occurred during AI processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 6. Save Generated Cover Letter
    try:
        saved_letter = SavedCoverLetter.objects.create(
            user_id=user_id,
            cover_letter=generated_text,
            job_title=job_title,
            company_name=company_name
        )
        logger.info(f"Generated cover letter saved with ID {saved_letter.id} for user {user_id}.")
    except Exception as e:
        logger.error(f"Failed to save generated cover letter for user {user_id}: {e}", exc_info=True)
        # Non-fatal? Return the text anyway, but maybe log warning/error
        # Or return a specific error if saving is critical
        return Response({
            "error": "Failed to save the generated cover letter, but generation was successful.",
            "cover_letter_text": generated_text # Still return the text
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 7. Return Response
    output_serializer = GeneratedCoverLetterSerializer({
        'saved_cover_letter_id': saved_letter.id,
        'cover_letter_text': generated_text
    })

    logger.info(f"Successfully generated and saved cover letter {saved_letter.id} for user {user_id}.")
    return Response(output_serializer.data, status=status.HTTP_200_OK)

# --- ViewSet for SavedCoverLetter CRUD ---

class SavedCoverLetterViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing saved cover letters (CRUD).
    Ensures users can only access their own saved letters.
    """
    serializer_class = SavedCoverLetterSerializer
    # Rely on default authentication from settings
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter results to only include cover letters owned by the requesting user."""
        user = self.request.user
        if user and user.is_authenticated:
            # Filter SavedCoverLetter objects by the user_id field
            # logger.debug(f"Filtering SavedCoverLetters for user {user.id}") # Optional: Remove debug log
            return SavedCoverLetter.objects.filter(user_id=user.id)
        # logger.warning("User not authenticated in SavedCoverLetterViewSet.get_queryset") # Optional: Remove debug log
        return SavedCoverLetter.objects.none()

    def perform_create(self, serializer):
        """
        Associate the saved cover letter with the logged-in user.
        Note: Creation is typically handled by generate_cover_letter, 
        but this allows direct POST if needed.
        """
        # logger.info(f"Performing create for SavedCoverLetter for user {self.request.user.id}") # Optional: Remove debug log
        serializer.save(user_id=self.request.user.id)

    # Remove the overridden update method
    # def update(self, request, *args, **kwargs):
    #    ...

    # Remove the overridden http_method_not_allowed method
    # def http_method_not_allowed(self, request, *args, **kwargs):
    #    ...

    # Default ModelViewSet methods for update/delete will be used, relying on get_queryset for security

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'position': {
                    'type': 'string',
                    'description': 'Job position/title'
                },
                'company': {
                    'type': 'string',
                    'description': 'Company name'
                },
                'startDate': {
                    'type': 'string',
                    'format': 'date',
                    'description': 'Start date of the position'
                },
                'endDate': {
                    'type': 'string',
                    'format': 'date',
                    'description': 'End date of the position'
                },
                'description': {
                    'type': 'string',
                    'description': 'Current work experience description to enhance'
                }
            },
            'required': ['description']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Enhanced description generated.", 
            response={'type': 'object', 'properties': {'enhanced_description': {'type': 'string'}}}
        ),
        400: OpenApiResponse(description="Invalid input data."),
        500: OpenApiResponse(description="Server error during enhancement.")
    },
    summary="Enhance work experience description using AI",
    description="Takes work experience description and uses AI to generate an improved description. No authentication required."
)
@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def enhance_work_experience(request):
    """API endpoint to enhance a work experience description without requiring an ID."""
    try:
        # Validate that description is provided
        if not request.data or 'description' not in request.data:
            return Response(
                {'error': 'You must provide a description to enhance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        position = request.data.get('position', "Not specified")
        company = request.data.get('company', "Not specified")
        start_date = request.data.get('startDate', "Not specified")
        end_date = request.data.get('endDate', "Not specified")
        current_description = request.data.get('description', "")
        
        client = get_claude_client()
        
        # Prepare prompt for Claude
        prompt = f"""
        You are an AI career assistant. Enhance the following work experience description for a resume.
        Make it more impactful, achievement-oriented, and use strong action verbs.
        Focus on quantifiable achievements and skills demonstrated.
        
        Position: {position}
        Company: {company}
        Duration: {start_date} to {end_date}
        Current Description: {current_description}
        
        Provide an enhanced description that:
        1. Starts with strong action verbs
        2. Includes specific accomplishments with metrics when possible
        3. Demonstrates skills and impact
        4. Is concise yet comprehensive
        5. Is relevant to the position
        
        Return the response as a JSON object with a 'description' field containing bullet points with line breaks.

        Example format:
        {{
          "description": "• Led development of a full-stack web application using React and Node.js, resulting in 40% faster load times\\\\n• Managed a team of 5 developers, implementing agile methodologies that improved sprint velocity by 25%\\\\n• Architected and deployed microservices infrastructure reducing system downtime by 60%"
        }}

        Guidelines:
        - Start each bullet point with •
        - Use \\n for new lines
        - Focus on achievements and impact
        - Use strong action verbs
        - Include metrics and numbers
        - Highlight leadership and collaboration
        - Keep it to 3-5 bullet points
        - Only return the JSON response, no other text
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
        response_text = message.content[0].text.strip()
        
        # Parse the JSON response
        try:
            # Try to parse the JSON response from Claude
            import json
            response_json = json.loads(response_text)
            
            # Get the description value from the response
            enhanced_description = response_json.get("description", "")
            
            # Return only the description value, not nested in another JSON object
            return Response({
                "description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract using regex
            import re
            match = re.search(r'"description":\s*"([^"]*)"', response_text)
            if match:
                enhanced_description = match.group(1)
                return Response({
                    "description": enhanced_description
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Failed to parse AI response",
                    "raw_response": response_text
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        # Log the error
        print(f"Error enhancing work experience: {e}")
        return Response(
            {'error': 'Failed to enhance work experience'}, # Generic error for client
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@extend_schema(
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'title': {
                    'type': 'string',
                    'description': 'Project title'
                },
                'shortDescription': {
                    'type': 'string',
                    'description': 'Brief description of the project'
                },
                'startDate': {
                    'type': 'string',
                    'format': 'date',
                    'description': 'Start date of the project'
                },
                'endDate': {
                    'type': 'string',
                    'format': 'date',
                    'description': 'End date of the project'
                },
                'description': {
                    'type': 'string',
                    'description': 'Current project description to enhance'
                }
            },
            'required': ['description']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Enhanced description generated.", 
            response={'type': 'object', 'properties': {'description': {'type': 'string'}}}
        ),
        400: OpenApiResponse(description="Invalid input data."),
        500: OpenApiResponse(description="Server error during enhancement.")
    },
    summary="Enhance project description using AI",
    description="Takes project details and uses AI to generate an improved description. Can be used by either authenticated or non-authenticated users."
)
@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def enhance_project(request):
    """API endpoint to enhance a project description without requiring an ID."""
    try:
        # Validate that description is provided
        if not request.data or 'description' not in request.data:
            return Response(
                {'error': 'You must provide a description to enhance'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        title = request.data.get('title', "Not specified")
        short_description = request.data.get('shortDescription', "")
        start_date = request.data.get('startDate', "Not specified")
        end_date = request.data.get('endDate', "Not specified")
        current_description = request.data.get('description', "")
        
        client = get_claude_client()
        
        # Prepare prompt for Claude
        prompt = f"""
        You are an AI career assistant. Enhance the following project description for a resume.
        Make it more impactful, achievement-oriented, and focus on skills demonstrated.
        
        Project Title: {title}
        Short Description: {short_description}
        Duration: {start_date} to {end_date}
        Current Description: {current_description}
        
        Provide an enhanced description that:
        1. Clearly explains the project purpose
        2. Highlights the technologies or methodologies used
        3. Emphasizes your specific contributions
        4. Mentions any challenges overcome
        5. Notes the impact or outcomes of the project
        
        Return the response as a JSON object with a 'description' field containing bullet points with line breaks.

        Example format:
        {{
          "description": "• Developed a responsive web application with React and Node.js that streamlined data processing by 40%\\\\n• Implemented RESTful API endpoints that improved system reliability and reduced client-side errors by 35%\\\\n• Engineered a user authentication system with JWT, enhancing security and user experience"
        }}

        Guidelines:
        - Start each bullet point with •
        - Use \\n for new lines
        - Focus on achievements and impact
        - Use strong action verbs
        - Include metrics and numbers when possible
        - Highlight technical skills and problem-solving
        - Keep it to 3-5 bullet points
        - Only return the JSON response, no other text
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
        response_text = message.content[0].text.strip()
        
        # Parse the JSON response
        try:
            # Try to parse the JSON response from Claude
            import json
            response_json = json.loads(response_text)
            
            # Get the description value from the response
            enhanced_description = response_json.get("description", "")
            
            # Return only the description value, not nested in another JSON object
            return Response({
                "description": enhanced_description
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract using regex
            import re
            match = re.search(r'"description":\s*"([^"]*)"', response_text)
            if match:
                enhanced_description = match.group(1)
                return Response({
                    "description": enhanced_description
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Failed to parse AI response",
                    "raw_response": response_text
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        # Log the error
        print(f"Error enhancing project: {e}")
        return Response(
            {'error': 'Failed to enhance project'}, # Generic error for client
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
