from pydantic import BaseModel
from typing import List, Optional
import datetime


class WorkExperiencSection(BaseModel):
   position: Optional[str] = None
   company : Optional[str] = None

class WorkExperienceSchema(BaseModel):
    position: Optional[str]
    company: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    description: Optional[str]

class EducationSchema(BaseModel):
    degree: Optional[str]
    school: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]

class ProjectSchema(BaseModel):
    title: Optional[str]
    description: Optional[str]
    # Add dates if common in your resumes
    # start_date: Optional[str] = None
    # end_date: Optional[str] = None

class CertificationSchema(BaseModel):
    name: Optional[str]
    issuer: Optional[str]
    issue_date: Optional[str]
    # expiry_date: Optional[str] = None # Often not present

# --- Main Schema for Gemini Output ---
class ParsedResumeSchema(BaseModel):
    # Personal Info
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str] # Combining city/country for simplicity

    # Core Content
    summary: Optional[str]
    skills: Optional[List[str]]

    # Nested Sections (using the schemas defined above)
    work_experiences: Optional[List[WorkExperienceSchema]]
    educations: Optional[List[EducationSchema]]
    projects: Optional[List[ProjectSchema]]
    certifications: Optional[List[CertificationSchema]]

    class Config:
        # Optional: If you want Pydantic to handle fields not defined here gracefully
         extra = 'ignore' 