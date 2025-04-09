from django.db import models
import uuid
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

# --- User Profile Model (Unmanaged - for potential read-only access) ---
# Only needed if Django needs to READ data directly from the original 'profiles' table.
# Django will NOT create or manage migrations for this table.
class Profile(models.Model):
    id = models.UUIDField(primary_key=True, editable=False) # Matches Supabase auth.users.id / public.profiles.id
    # Map Django fields to actual DB columns based on Prisma schema
    full_name = models.CharField(max_length=255, blank=True, null=True, db_column='full_name') # Prisma 'full_name'
    email = models.EmailField(unique=True, blank=True, null=True, db_column='email') # Prisma 'email'
    avatar_url = models.URLField(blank=True, null=True, db_column='avatar_url') # Prisma 'avatar_url'

    class Meta:
        managed = False # <= Tells Django NOT to create/alter/delete this table
        db_table = 'profiles' # <= MUST match the exact table name in Supabase DB

    def __str__(self):
        return self.email or str(self.id)

# Create your models here.
class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    user_id = models.UUIDField(editable=False, db_index=True, db_column='userId')
    title = models.CharField(max_length=255, blank=True, null=True, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    photo_url = models.URLField(blank=True, null=True, db_column='photoUrl')
    color_hex = models.CharField(max_length=10, default="#000000", db_column='colorHex')
    border_style = models.CharField(max_length=50, default="squircle", db_column='borderStyle')
    font_family = models.CharField(max_length=50, default="Arial", db_column='fontFamily')
    section_order = ArrayField(models.CharField(max_length=100, blank=True), default=list, db_column='sectionOrder')
    summary = models.TextField(blank=True, null=True, db_column='summary')
    first_name = models.CharField(max_length=100, blank=True, null=True, db_column='firstName')
    last_name = models.CharField(max_length=100, blank=True, null=True, db_column='lastName')
    job_title = models.CharField(max_length=100, blank=True, null=True, db_column='jobTitle')
    city = models.CharField(max_length=100, blank=True, null=True, db_column='city')
    template = models.CharField(max_length=50, default="classic", db_column='template')
    country = models.CharField(max_length=100, blank=True, null=True, db_column='country')
    phone = models.CharField(max_length=50, blank=True, null=True, db_column='phone')
    email = models.EmailField(blank=True, null=True, db_column='email')
    skills = ArrayField(models.CharField(max_length=100, blank=True), default=list, db_column='skills')
    extra_sections = ArrayField(models.CharField(max_length=100, blank=True), default=list, db_column='extraSections')
    font_size = models.IntegerField(default=16, db_column='fontSize')
    section_spacing = models.IntegerField(default=24, db_column='sectionSpacing')
    line_height = models.FloatField(default=1.5, db_column='lineHeight')
    content_margin = models.IntegerField(default=32, db_column='contentMargin')
    created_at = models.DateTimeField(default=timezone.now, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')

    def __str__(self):
        return f"{self.title or 'Untitled Resume'} ({self.user_id})"
    
    class Meta:
        managed = False
        db_table = "resumes"
        ordering = ['-updated_at']


class WorkExperience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="work_experiences", db_column='resumeId')
    position = models.CharField(max_length=255, blank=True, null=True, db_column='position')
    company = models.CharField(max_length=255, blank=True, null=True, db_column='company')
    start_date = models.DateTimeField(blank=True, null=True, db_column='startDate')
    end_date = models.DateTimeField(blank=True, null=True, db_column='endDate')
    description = models.TextField(blank=True, null=True, db_column='description')
    created_at = models.DateTimeField(default=timezone.now, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')

    def __str__(self):
        return f"{self.position or 'N/A'} at {self.company or 'N/A'}"
    
    class Meta:
        managed = False
        db_table = "work_experiences"
        ordering = ['-start_date', '-end_date']


class Education(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="educations", db_column='resumeId')
    degree = models.CharField(max_length=255, blank=True, null=True, db_column='degree')
    school = models.CharField(max_length=255, blank=True, null=True, db_column='school')
    start_date = models.DateTimeField(blank=True, null=True, db_column='startDate')
    end_date = models.DateTimeField(blank=True, null=True, db_column='endDate')
    created_at = models.DateTimeField(default=timezone.now, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')

    def __str__(self):
        return f"{self.degree or 'N/A'} at {self.school or 'N/A'}"
    
    class Meta:
        managed = False
        db_table = "educations"
        ordering = ['-start_date', '-end_date']


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="projects", db_column='resumeId')
    title = models.CharField(max_length=255, blank=True, null=True, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    start_date = models.DateTimeField(blank=True, null=True, db_column='startDate')
    end_date = models.DateTimeField(blank=True, null=True, db_column='endDate')

    def __str__(self):
        return self.title or "Untitled Project"
    
    class Meta:
        managed = False
        db_table = "projects"
        ordering = ['-start_date', '-end_date']


class Certification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="certifications", db_column='resumeId')
    name = models.CharField(max_length=255, blank=True, null=True, db_column='name')
    issuer = models.CharField(max_length=255, blank=True, null=True, db_column='issuer')
    issue_date = models.DateTimeField(blank=True, null=True, db_column='issueDate')
    expiry_date = models.DateTimeField(blank=True, null=True, db_column='expiryDate')

    def __str__(self):
        return self.name or "Untitled Certification"
    
    class Meta:
        managed = False
        db_table = "certifications"
        ordering = ['-issue_date']


class CustomSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="custom_sections", db_column='resumeId')
    title = models.CharField(max_length=255, db_column='title')

    def __str__(self):
        return self.title
    
    class Meta:
        managed = False
        db_table = "custom_sections"


class CustomSectionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    custom_section = models.ForeignKey(CustomSection, on_delete=models.CASCADE, related_name="items", db_column='customSectionId')
    title = models.CharField(max_length=255, blank=True, null=True, db_column='title')
    description = models.TextField(blank=True, null=True, db_column='description')
    start_date = models.DateTimeField(blank=True, null=True, db_column='startDate')
    end_date = models.DateTimeField(blank=True, null=True, db_column='endDate')

    def __str__(self):
        return self.title or "Untitled Item"
    
    class Meta:
        managed = False
        db_table = "custom_section_items"
        ordering = ['-start_date', '-end_date']


# --- Saved Cover Letter Model (Unmanaged - Reads/Writes to EXISTING table) ---

class SavedCoverLetter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column='id')
    # User relationship (Stores Supabase auth.users.id)
    user_id = models.UUIDField(editable=False, db_index=True, db_column='userId') # Prisma 'userId'

    # Cover Letter Content and Context
    cover_letter = models.TextField(db_column='coverLetter') # Prisma 'coverLetter' @db.Text
    job_title = models.CharField(max_length=255, blank=True, null=True, db_column='jobTitle') # Prisma 'jobTitle'?
    company_name = models.CharField(max_length=255, blank=True, null=True, db_column='companyName') # Prisma 'companyName'?

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now, db_column='createdAt') # Prisma 'createdAt'
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt') # Prisma 'updatedAt'

    class Meta:
        managed = False
        db_table = "saved_cover_letters" # Prisma @@map("saved_cover_letters")
        ordering = ['-created_at']

    def __str__(self):
        return f"Cover Letter for {self.company_name or '?'} ({self.user_id}) - {self.created_at.strftime('%Y-%m-%d')}"
