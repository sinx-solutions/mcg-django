from rest_framework import serializers
from .models import (
    Resume,
    WorkExperience,
    Education,
    Project,
    Certification,
    CustomSection,
    CustomSectionItem,
    SavedCoverLetter
)
import uuid # Added import for UUID validation if needed later

# Nested serializers used for writing within ResumeCompleteSerializer
# We define them explicitly here to control fields if needed,
# otherwise using fields = '__all__' in the main serializers is fine too.

class WorkExperienceNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        # Exclude 'resume' as it will be set automatically
        exclude = ('resume',)

class EducationNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        exclude = ('resume',)

class ProjectNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        exclude = ('resume',)

class CertificationNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        exclude = ('resume',)

class CustomSectionItemNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomSectionItem
        # Exclude 'custom_section' as it will be set automatically
        exclude = ('custom_section',)

class CustomSectionNestedSerializer(serializers.ModelSerializer):
    items = CustomSectionItemNestedSerializer(many=True, required=False)
    class Meta:
        model = CustomSection
        # Exclude 'resume' as it will be set automatically
        exclude = ('resume',)


# Serializers for general use (e.g., listing, simple retrieve)
# These can remain as they are or be refined later if needed.

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = '__all__'

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = '__all__'

class CustomSectionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomSectionItem
        fields = '__all__' # Keep section ID for detail views

class CustomSectionSerializer(serializers.ModelSerializer):
    items = CustomSectionItemSerializer(many=True, read_only=True) # read_only for detail views

    class Meta:
        model = CustomSection
        fields = '__all__' # Keep resume ID for detail views


# Basic Resume serializer (without related data)
class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = '__all__'


# Detailed Resume serializer (Read-Only, includes related data)
# Used for GET responses after create/update
class ResumeDetailSerializer(serializers.ModelSerializer):
    # Use the standard serializers for read-only nested representation
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    # Use the CustomSectionSerializer which correctly nests items read-only
    custom_sections = CustomSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = [ # Explicitly list fields for clarity and security
            'id', 'user_id', 'title', 'description', 'photo_url', 'color_hex',
            'border_style', 'font_family', 'section_order', 'summary',
            'first_name', 'last_name', 'job_title', 'city', 'template',
            'country', 'phone', 'email', 'skills', 'extra_sections',
            'font_size', 'section_spacing', 'line_height', 'content_margin',
            'created_at', 'updated_at',
            # Nested read-only fields
            'work_experiences', 'educations', 'projects', 'certifications', 'custom_sections'
        ]


# Complete Resume serializer with nested write capabilities
# Used for POST/PUT/PATCH requests in the ViewSet
class ResumeCompleteSerializer(serializers.ModelSerializer):
    # Use nested serializers that exclude the FK for writes
    work_experiences = WorkExperienceNestedSerializer(many=True, required=False)
    educations = EducationNestedSerializer(many=True, required=False)
    projects = ProjectNestedSerializer(many=True, required=False)
    certifications = CertificationNestedSerializer(many=True, required=False)
    custom_sections = CustomSectionNestedSerializer(many=True, required=False)

    # Explicitly define array fields to allow empty lists
    section_order = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=True),
        required=False,
        allow_empty=True
    )
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=True),
        required=False,
        allow_empty=True
    )
    extra_sections = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=True),
        required=False,
        allow_empty=True # Explicitly allow empty list []
    )

    class Meta:
        model = Resume
        # Explicitly list fields, including nested ones for writes
        fields = [
            'id', 'user_id', 'title', 'description', 'photo_url', 'color_hex',
            'border_style', 'font_family', 'section_order', 'summary',
            'first_name', 'last_name', 'job_title', 'city', 'template',
            'country', 'phone', 'email', 'skills', 'extra_sections',
            'font_size', 'section_spacing', 'line_height', 'content_margin',
            # Writable nested fields
            'work_experiences', 'educations', 'projects', 'certifications', 'custom_sections'
            # created_at and updated_at are handled by Django
        ]
        # user_id should be set by the view based on request.user
        read_only_fields = ('id', 'user_id', 'created_at', 'updated_at')

    def _create_nested_items(self, resume, items_data, model_class, related_manager_name):
        """Helper to create nested items for a given resume."""
        items_to_create = []
        if items_data:
            for item_data in items_data:
                # Special handling for CustomSection which has nested items itself
                if model_class == CustomSection:
                    custom_items_data = item_data.pop('items', [])
                    section = CustomSection.objects.create(resume=resume, **item_data)
                    for custom_item_data in custom_items_data:
                        CustomSectionItem.objects.create(custom_section=section, **custom_item_data)
                else:
                    # Standard handling for other nested models
                    model_class.objects.create(resume=resume, **item_data)


    def _update_nested_items(self, resume, items_data, model_class, related_manager_name):
        """Helper to delete existing and create new nested items for updates."""
        # Delete existing items first
        related_manager = getattr(resume, related_manager_name)
        related_manager.all().delete() # This cascades if applicable

        # Create new items using the same logic as _create_nested_items
        self._create_nested_items(resume, items_data, model_class, related_manager_name)


    def create(self, validated_data):
        # Pop nested data
        work_experiences_data = validated_data.pop('work_experiences', [])
        educations_data = validated_data.pop('educations', [])
        projects_data = validated_data.pop('projects', [])
        certifications_data = validated_data.pop('certifications', [])
        custom_sections_data = validated_data.pop('custom_sections', [])

        # Create the main Resume instance (user_id is expected to be passed from view)
        resume = Resume.objects.create(**validated_data)

        # Create nested objects using the helper
        self._create_nested_items(resume, work_experiences_data, WorkExperience, 'work_experiences')
        self._create_nested_items(resume, educations_data, Education, 'educations')
        self._create_nested_items(resume, projects_data, Project, 'projects')
        self._create_nested_items(resume, certifications_data, Certification, 'certifications')
        self._create_nested_items(resume, custom_sections_data, CustomSection, 'custom_sections')

        return resume

    def update(self, instance, validated_data):
        # Pop nested data - use None default to detect if the key was present
        work_experiences_data = validated_data.pop('work_experiences', None)
        educations_data = validated_data.pop('educations', None)
        projects_data = validated_data.pop('projects', None)
        certifications_data = validated_data.pop('certifications', None)
        custom_sections_data = validated_data.pop('custom_sections', None)

        # Update direct fields on the Resume instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save() # Save changes to direct fields

        # Use helper to delete existing and create new nested objects if data was provided
        if work_experiences_data is not None:
            self._update_nested_items(instance, work_experiences_data, WorkExperience, 'work_experiences')
        if educations_data is not None:
            self._update_nested_items(instance, educations_data, Education, 'educations')
        if projects_data is not None:
            self._update_nested_items(instance, projects_data, Project, 'projects')
        if certifications_data is not None:
            self._update_nested_items(instance, certifications_data, Certification, 'certifications')
        if custom_sections_data is not None:
            self._update_nested_items(instance, custom_sections_data, CustomSection, 'custom_sections')

        return instance


# Serializer for job_search_api input
class JobSearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="The search query string for jobs."
    )

# --- Serializers for Cover Letter Generation ---

class GenerateCoverLetterInputSerializer(serializers.Serializer):
    resume_id = serializers.UUIDField(
        required=True,
        help_text="The UUID of the resume to base the cover letter on."
    )
    job_title = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=255,
        help_text="The title of the job being applied for."
    )
    company_name = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=255,
        help_text="The name of the company."
    )
    job_description = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="The full text of the job description."
    )

class GeneratedCoverLetterSerializer(serializers.Serializer):
    saved_cover_letter_id = serializers.UUIDField(
        read_only=True,
        help_text="The UUID of the saved cover letter record."
    )
    cover_letter_text = serializers.CharField(
        read_only=True,
        help_text="The generated cover letter text."
    )

# --- Serializer for SavedCoverLetter CRUD ---

class SavedCoverLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedCoverLetter
        fields = '__all__' # Include all fields: id, user_id, cover_letter, job_title, company_name, created_at, updated_at
        read_only_fields = ('id', 'user_id', 'created_at', 'updated_at') # User ID is set automatically

# --- Serializer for ATS Scoring Input ---

class JobDescriptionInputSerializer(serializers.Serializer):
    """Serializer to validate the input for the ATS scoring endpoint."""
    title = serializers.CharField(
        required=False, # Title might be optional
        allow_blank=True,
        max_length=255,
        help_text="The title of the job."
    )
    raw_text = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="The full raw text of the job description."
    )
    required_skills = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        required=False, # Make optional, scorer can extract if missing
        allow_empty=True,
        help_text="List of required skills for the job."
    )
    preferred_skills = serializers.ListField(
        child=serializers.CharField(max_length=100, allow_blank=False),
        required=False, # Make optional, scorer can extract if missing
        allow_empty=True,
        help_text="List of preferred skills for the job."
    )
