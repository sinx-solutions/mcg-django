# Resume Management API with Django REST Framework

This project implements a Resume Management API with Django REST Framework that matches the functionality from the original frontend application. The API supports creating and managing resumes with different sections, parsing resume files, and adapting resumes for specific job postings using Claude AI.

## Features

- Complete CRUD operations for resumes and all their components:
  - Personal information
  - Work experience
  - Education
  - Skills
  - Projects
  - Certifications
  - Custom sections
- Resume parsing from uploaded files
- AI-powered resume adaptation for job postings using Claude AI
- Comprehensive test suite to validate all endpoints

## Project Structure

```
apps/api/
├── api/                        # Django app
│   ├── admin.py                # Admin interface configuration
│   ├── models.py               # Database models
│   ├── serializers.py          # REST Framework serializers
│   ├── tests.py                # Unit tests for models
│   ├── test_api.py             # API endpoint tests
│   ├── urls.py                 # URL routing
│   └── views.py                # API views and logic
├── backend/                    # Django project settings
├── env/                        # Virtual environment (not in repo)
├── manage.py                   # Django management script
├── test_adapt_resume.py        # Test script for resume adaptation
├── test_claude.py              # Test script for Claude API
├── test_endpoints.py           # Comprehensive API test script
├── resume_builder_demo.py      # Interactive demonstration script
└── requirements.txt            # Project dependencies
```

## Setup Instructions

1. Make sure you have Python 3.9+ installed

2. Set up a virtual environment and install dependencies:

   ```bash
   cd apps/api
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the `apps/api` directory with your Claude API key:

   ```
   CLAUDE_API_KEY=your_api_key_here
   ```

4. Run migrations to set up the database:

   ```bash
   python manage.py migrate
   ```

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Running the Demonstration

The project includes a rich, interactive demonstration script that walks through the entire resume creation process and shows the AI-powered resume adaptation in action.

To run the demonstration:

```bash
# Make sure your Django server is running in another terminal
python resume_builder_demo.py
```

This script will:

1. Guide you through each stage of resume creation (General info -> Personal info -> Work experience -> Education -> Skills -> Projects -> Certifications -> Summary -> Custom sections)
2. Show a realistic example of creating a complete resume through the API
3. Demonstrate AI-powered resume adaptation for a specific job posting
4. Clean up created resources automatically

## API Endpoints

- `/api/resumes/` - CRUD operations for resumes
- `/api/work-experiences/` - CRUD operations for work experiences
- `/api/educations/` - CRUD operations for education entries
- `/api/projects/` - CRUD operations for projects
- `/api/certifications/` - CRUD operations for certifications
- `/api/custom-sections/` - CRUD operations for custom sections
- `/api/custom-section-items/` - CRUD operations for custom section items
- `/api/parse-resume/` - Parse resume files and extract structured data
- `/api/adapt-resume/` - Adapt resumes for specific job postings using AI

## Testing

To run the complete test suite:

```bash
# Make sure your Django server is running
python test_endpoints.py
```

For specific tests:

```bash
# Test resume adaptation
python test_adapt_resume.py

# Test Claude API integration
python test_claude.py
```

## Integration with Frontend

This API is designed to be a drop-in replacement for the original Next.js API routes. All endpoints match the expected request and response formats from the frontend application, ensuring seamless integration.

## License

This project is licensed under the MIT License.
