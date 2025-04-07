import os
import json
import re
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("CLAUDE_API_KEY")

if not api_key:
    raise ValueError("CLAUDE_API_KEY environment variable not found")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=api_key)

# Sample resume data
sample_resume = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "123-456-7890",
    "summary": "Experienced software engineer with 5+ years developing web applications.",
    "skills": ["Python", "Django", "JavaScript", "React", "Docker", "AWS"],
    "work_experiences": [
        {
            "position": "Senior Software Developer",
            "company": "Tech Solutions Inc.",
            "start_date": "2020-01-01",
            "end_date": "2023-01-01",
            "description": "Led a team of 5 developers building high-traffic web applications. Improved system performance by 40% through code optimization."
        },
        {
            "position": "Software Developer",
            "company": "Web Innovations",
            "start_date": "2018-03-01",
            "end_date": "2019-12-31",
            "description": "Developed RESTful APIs and implemented front-end components using React. Participated in Agile development cycles."
        }
    ],
    "educations": [
        {
            "degree": "B.S. Computer Science",
            "school": "University of Technology",
            "start_date": "2014-09-01",
            "end_date": "2018-05-01"
        }
    ]
}

# Sample job posting
sample_job = {
    "title": "Full Stack Developer",
    "company": "Innovative Solutions",
    "description": """
    We are looking for a Full Stack Developer to join our growing team. The ideal candidate will have experience with Python, Django, and React. Responsibilities include developing and maintaining web applications, collaborating with cross-functional teams, and ensuring high-quality code through testing and code reviews.

    Requirements:
    - 3+ years of experience with Python
    - Experience with Django or similar web frameworks
    - Familiarity with React or other front-end frameworks
    - Understanding of RESTful APIs and web services
    - Experience with database design and SQL
    - Knowledge of containerization (Docker) and cloud services (preferably AWS)
    """
}

# Craft the prompt for Claude
prompt = f"""
You are an AI career assistant that helps tailor resumes for specific job postings.
I'll provide you with a resume and a job posting. Please analyze the resume against the job requirements and:

1. Create an improved summary section that highlights relevant experience
2. Prioritize and reorder skills based on job relevance
3. Enhance work experience descriptions to emphasize relevant achievements
4. Suggest any additional sections or information that should be added
5. Provide a brief explanation of the changes you made

Resume:
{json.dumps(sample_resume, indent=2)}

Job Posting:
Title: {sample_job["title"]}
Company: {sample_job["company"]}
Description: {sample_job["description"]}

Please format your response as a valid JSON object with the following structure:
{{
  "tailored_summary": "...",
  "prioritized_skills": ["skill1", "skill2", ...],
  "enhanced_work_experiences": [{{position, company, start_date, end_date, enhanced_description}}, ...],
  "additional_suggestions": "...",
  "explanation": "..."
}}

Return only the JSON object without any markdown formatting or other text.
"""

# Call Claude API
try:
    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Print the response
    print("Claude Response:")
    print(message.content)
    
    # Extract JSON from the response
    # The content is an array of content blocks, we need to access the text property
    raw_text = message.content[0].text
    
    # Extract JSON using regex pattern in case Claude wraps it in markdown
    json_pattern = re.compile(r'```(?:json)?\s*(.*?)```', re.DOTALL)
    json_match = json_pattern.search(raw_text)
    
    if json_match:
        # Use the extracted JSON string
        json_str = json_match.group(1).strip()
        claude_response = json.loads(json_str)
    else:
        # Try parsing the whole response directly
        claude_response = json.loads(raw_text)
        
    print("\nParsed JSON response:")
    print(json.dumps(claude_response, indent=2))
        
except Exception as e:
    print(f"Error: {e}") 