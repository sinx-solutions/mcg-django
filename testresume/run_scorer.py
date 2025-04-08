import sys
import os
import json
import traceback # Import traceback module
import logging
from datetime import datetime # Import datetime for potential date parsing
import django # Import Django
from decimal import Decimal
import uuid

# --- Django Setup --- Start --- #
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level from testresume/ to the workspace root
workspace_root = os.path.dirname(script_dir)
# Path to the directory containing manage.py (api/)
api_dir = os.path.join(workspace_root, 'api')

# Add api directory and workspace root to sys.path to find modules
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)
if workspace_root not in sys.path:
     sys.path.insert(0, workspace_root)

# Set the DJANGO_SETTINGS_MODULE environment variable
# Assumes settings are in api/backend/settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Setup Django
try:
    django.setup()
    print("Django environment set up successfully.")
except Exception as e:
    print(f"Error setting up Django environment: {e}")
    print("Please ensure the script is run from the correct directory structure")
    print(f"and DJANGO_SETTINGS_MODULE is pointing to the correct settings file.")
    print(f"api_dir: {api_dir}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)

# Import models and serializers *after* django.setup()
from api.models import Resume
from api.serializers import ResumeDetailSerializer
# --- Django Setup --- End --- #


# --- ATS Scorer Setup --- Start --- #
# Add the scoring directory to the Python path
scoring_dir = os.path.join(script_dir, 'scoring')
if scoring_dir not in sys.path:
     sys.path.insert(0, scoring_dir)

# Import the scorer
try:
    from scoring.ats_scorer import ATSScorer
except ImportError:
    try:
        from ats_scorer import ATSScorer # Fallback
    except ImportError as e:
        print(f"Error importing ATSScorer: {e}")
        sys.exit(1)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG) # Set log level to DEBUG
# --- ATS Scorer Setup --- End --- #

# Custom JSON encoder (needed for printing the final result if it contains non-serializable types)
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# --- Main execution ---
if __name__ == "__main__":
    print("--- Running ATS Scorer Simulation with Live DB Fetch ---")

    # 1. Fetch Resume Data from DB
    resume_id_to_fetch = "7293c0bf-7b73-4bff-bd9b-5994bf67e723"
    print(f"Fetching resume with ID: {resume_id_to_fetch}")
    try:
        resume_obj = Resume.objects.get(id=resume_id_to_fetch)
        print("Resume object fetched successfully.")
        # Serialize the data
        serializer = ResumeDetailSerializer(resume_obj)
        fetched_resume_data = serializer.data
        print("Resume data serialized.")
    except Resume.DoesNotExist:
        print(f"Error: Resume with ID {resume_id_to_fetch} not found in the database.")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching or serializing resume: {e}")
        traceback.print_exc()
        sys.exit(1)

    # 2. Preprocess Fetched Resume Data for Scorer
    resume_data_for_scorer = fetched_resume_data.copy() # Work on a copy

    # Rename 'work_experiences' to 'experience'
    if 'work_experiences' in resume_data_for_scorer:
        resume_data_for_scorer['experience'] = resume_data_for_scorer.pop('work_experiences')
        print("Renamed 'work_experiences' to 'experience'.")
    else:
        resume_data_for_scorer['experience'] = [] # Ensure key exists

    # Construct substitute raw_text from structured data
    resume_raw_text_parts = [
        resume_data_for_scorer.get('summary', ''),
        resume_data_for_scorer.get('job_title', ''),
    ]
    # Use 'experience' key now
    for exp in resume_data_for_scorer.get('experience', []):
        resume_raw_text_parts.append(exp.get('position', ''))
        resume_raw_text_parts.append(exp.get('company', ''))
        resume_raw_text_parts.append(exp.get('description', ''))
    for edu in resume_data_for_scorer.get('educations', []):
        resume_raw_text_parts.append(edu.get('degree', ''))
        resume_raw_text_parts.append(edu.get('school', ''))
    for proj in resume_data_for_scorer.get('projects', []):
        resume_raw_text_parts.append(proj.get('title', ''))
        resume_raw_text_parts.append(proj.get('description', ''))
    for cert in resume_data_for_scorer.get('certifications', []):
        resume_raw_text_parts.append(cert.get('name', ''))
        resume_raw_text_parts.append(cert.get('issuer', ''))
    for section in resume_data_for_scorer.get('custom_sections', []):
        resume_raw_text_parts.append(section.get('title',''))
        for item in section.get('items', []):
            resume_raw_text_parts.append(item.get('title', ''))
            resume_raw_text_parts.append(item.get('description', ''))
    resume_raw_text_parts.extend(resume_data_for_scorer.get('skills', []))

    resume_data_for_scorer['raw_text'] = ' '.join(filter(None, resume_raw_text_parts))
    print(f"Constructed substitute raw_text (length: {len(resume_data_for_scorer['raw_text'])})")

    # 3. Define Job Data
    job_data = {
        'title': 'Lead Full Stack Engineer (React/Node)',
        'raw_text': """
        Tech Innovations Inc. is hiring a Lead Full Stack Engineer.
        Lead a team to design, develop, and deploy scalable web applications using React and Node.js.
        Requires 7+ years of professional software development experience, including team leadership.
        Must demonstrate expertise in JavaScript, React, Node.js, and building RESTful APIs.
        Strong experience with CI/CD pipelines (GitHub Actions preferred) and automated testing is essential.
        Proven ability to optimize application performance and architecture.
        Master's or Bachelor's degree in Computer Science or a related field is required.
        Experience with cloud platforms (AWS) and database management (MongoDB) is a plus.
        Excellent communication and leadership skills required.
        """,
        'required_skills': [
            'JavaScript', 'React', 'Node.js', 'RESTful APIs', 'CI/CD', 'Automated Testing', 'Leadership', 'Software Architecture'
        ],
        'preferred_skills': [
            'GitHub Actions', 'AWS', 'MongoDB', 'TypeScript'
        ]
    }
    print("Defined sample job description data.")

    # 4. Initialize and Run Scorer
    print("\nInitializing ATS Scorer...")
    try:
        # Ensure spacy model is available
        try:
             import spacy
             spacy.load('en_core_web_lg')
             logger.info("Spacy model 'en_core_web_lg' loaded.")
        except OSError:
             logger.error("Spacy model 'en_core_web_lg' not found.")
             print("Attempting download...")
             try:
                  # Use the absolute path to python in the venv if needed
                  # venv_python = os.path.join(api_dir, 'env', 'bin', 'python')
                  # Or rely on the activated environment
                  spacy.cli.download('en_core_web_lg')
                  print("Model downloaded successfully.")
                  spacy.load('en_core_web_lg')
                  logger.info("Spacy model 'en_core_web_lg' loaded after download.")
             except Exception as download_e:
                  print(f"Failed to download spacy model 'en_core_web_lg': {download_e}")
                  print("Please ensure the virtual environment is activated and run manually:")
                  print("  python -m spacy download en_core_web_lg")
                  sys.exit(1)

        scorer = ATSScorer()
        print("Scorer initialized.")

        # Score the resume
        print("\nScoring the resume against the job description...")
        result = scorer.score_resume(resume_data_for_scorer, job_data)

        # Print the result
        print("\n--- ATS Score Result ---")
        # Use custom encoder for printing
        print(json.dumps(result, indent=2, cls=CustomEncoder))
        print("--- End ATS Score Result ---")

    except Exception as e:
        print("\n--- Error during scoring ---")
        print(f"An error occurred: {type(e).__name__} - {e}")
        traceback.print_exc() # Print full traceback for debugging
        print("--- End Error ---")

    print("\n--- Simulation Complete ---")

# Remove the old file loading function if it exists and is unused
# def load_data_from_file(filepath): ... 