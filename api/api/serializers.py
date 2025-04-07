from rest_framework import serializers
from .models import (
    Resume,
    WorkExperience,
    Education,
    Project,
    Certification,
    CustomSection,
    CustomSectionItem
)

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
        fields = '__all__'


class CustomSectionSerializer(serializers.ModelSerializer):
    items = CustomSectionItemSerializer(many=True, read_only=True)

    class Meta:
        model = CustomSection
        fields = '__all__'


# Basic Resume serializer (without related data)
class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = '__all__'


# Detailed Resume serializer (with related data)
class ResumeDetailSerializer(serializers.ModelSerializer):
    work_experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    projects = ProjectSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    custom_sections = CustomSectionSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = '__all__'


# Complete Resume serializer with nested write capabilities
class ResumeCompleteSerializer(serializers.ModelSerializer):
    work_experiences = WorkExperienceSerializer(many=True, required=False)
    educations = EducationSerializer(many=True, required=False)
    projects = ProjectSerializer(many=True, required=False)
    certifications = CertificationSerializer(many=True, required=False)
    custom_sections = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = '__all__'

    def get_custom_sections(self, obj):
        custom_sections = obj.custom_sections.all()
        custom_section_data = []

        for section in custom_sections:
            items = section.items.all()
            section_data = {
                'id': section.id,
                'title': section.title,
                'items': [
                    {
                        'id': item.id,
                        'title': item.title,
                        'description': item.description,
                        'start_date': item.start_date,
                        'end_date': item.end_date
                    }
                    for item in items
                ]
            }
            custom_section_data.append(section_data)

        return custom_section_data

    def create(self, validated_data):
        # Extract nested data
        work_experiences_data = validated_data.pop('work_experiences', [])
        educations_data = validated_data.pop('educations', [])
        projects_data = validated_data.pop('projects', [])
        certifications_data = validated_data.pop('certifications', [])
        custom_sections_data = validated_data.pop('custom_sections', [])

        # Create resume
        resume = Resume.objects.create(**validated_data)

        # Create related objects
        for work_exp_data in work_experiences_data:
            WorkExperience.objects.create(resume=resume, **work_exp_data)
            
        for education_data in educations_data:
            Education.objects.create(resume=resume, **education_data)
            
        for project_data in projects_data:
            Project.objects.create(resume=resume, **project_data)
            
        for cert_data in certifications_data:
            Certification.objects.create(resume=resume, **cert_data)
            
        for section_data in custom_sections_data:
            items_data = section_data.pop('items', [])
            custom_section = CustomSection.objects.create(resume=resume, **section_data)
            
            for item_data in items_data:
                CustomSectionItem.objects.create(custom_section=custom_section, **item_data)
        
        return resume

    def update(self, instance, validated_data):
        # Extract nested data
        work_experiences_data = validated_data.pop('work_experiences', [])
        educations_data = validated_data.pop('educations', [])
        projects_data = validated_data.pop('projects', [])
        certifications_data = validated_data.pop('certifications', [])
        custom_sections_data = validated_data.pop('custom_sections', [])

        # Update resume data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update or create related objects
        # For this example, we're using a replace approach (delete existing and create new)
        
        # Work experiences
        instance.work_experiences.all().delete()
        for work_exp_data in work_experiences_data:
            WorkExperience.objects.create(resume=instance, **work_exp_data)
        
        # Education
        instance.educations.all().delete()
        for education_data in educations_data:
            Education.objects.create(resume=instance, **education_data)
        
        # Projects
        instance.projects.all().delete()
        for project_data in projects_data:
            Project.objects.create(resume=instance, **project_data)
        
        # Certifications
        instance.certifications.all().delete()
        for cert_data in certifications_data:
            Certification.objects.create(resume=instance, **cert_data)
        
        # Custom sections
        instance.custom_sections.all().delete()
        for section_data in custom_sections_data:
            items_data = section_data.pop('items', [])
            custom_section = CustomSection.objects.create(resume=instance, **section_data)
            
            for item_data in items_data:
                CustomSectionItem.objects.create(custom_section=custom_section, **item_data)
        
        return instance
