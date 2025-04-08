# fetch_resume_data.py
import json
import django
import os
from decimal import Decimal # Import Decimal for JSON serialization if needed
import uuid # Import uuid to handle UUID serialization explicitly

# Set up Django environment
# Adjust 'backend.settings' if your settings file is located differently
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import Resume
from api.serializers import ResumeDetailSerializer

# Custom JSON encoder to handle Decimal, Date/Time, and UUID types
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj) # Convert UUID to string
        if isinstance(obj, Decimal):
            return float(obj) # Convert Decimal to float
        if hasattr(obj, 'isoformat'): # Handle date/datetime objects
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# Fetch the first 5 resume objects
resumes = Resume.objects.all()[:5] # Limit to first 5

print(f"Found {len(resumes)} resumes (showing up to 5).")

if resumes:
    for i, resume in enumerate(resumes):
        print(f"\\n--- Resume {i+1} (ID: {resume.id}) ---")
        # Serialize the resume data
        serializer = ResumeDetailSerializer(resume)
        resume_data = serializer.data

        # Print the data as JSON
        try:
            print(json.dumps(resume_data, indent=2, cls=CustomEncoder))
        except Exception as e:
            print(f"Error serializing resume data for ID {resume.id}: {e}")
            # Print the raw serializer data if JSON dump fails
            print("\\n--- Raw Serializer Data ---")
            print(resume_data)
            print("--- End Raw Serializer Data ---")
        print(f"--- End Resume {i+1} ---")

else:
    print("No resumes found in the database.") 