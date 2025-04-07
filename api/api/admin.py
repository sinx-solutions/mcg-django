from django.contrib import admin
from .models import (
    Resume, 
    WorkExperience, 
    Education, 
    Project, 
    Certification, 
    CustomSection, 
    CustomSectionItem
)

# Register your models here.
class WorkExperienceInline(admin.TabularInline):
    model = WorkExperience
    extra = 0

class EducationInline(admin.TabularInline):
    model = Education
    extra = 0

class ProjectInline(admin.TabularInline):
    model = Project
    extra = 0

class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 0

class CustomSectionItemInline(admin.TabularInline):
    model = CustomSectionItem
    extra = 0

class CustomSectionInline(admin.TabularInline):
    model = CustomSection
    extra = 0

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user_id', 'template', 'created_at', 'updated_at')
    search_fields = ('title', 'user_id', 'first_name', 'last_name', 'email')
    list_filter = ('template', 'created_at')
    inlines = [
        WorkExperienceInline,
        EducationInline,
        ProjectInline,
        CertificationInline,
        CustomSectionInline,
    ]

@admin.register(CustomSection)
class CustomSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'resume')
    inlines = [CustomSectionItemInline]

# Register remaining models
admin.site.register(WorkExperience)
admin.site.register(Education)
admin.site.register(Project)
admin.site.register(Certification)
admin.site.register(CustomSectionItem)
