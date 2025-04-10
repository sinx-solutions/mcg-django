from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResumeViewSet,
    WorkExperienceViewSet,
    EducationViewSet,
    ProjectViewSet,
    CertificationViewSet,
    CustomSectionViewSet,
    CustomSectionItemViewSet,
    parse_resume,
    adapt_resume,
    save_parsed_resume,
    score_resume,
    job_search_api,
    generate_cover_letter,
    SavedCoverLetterViewSet,
    enhance_work_experience,
    enhance_project,
    enhance_certification,
    enhance_custom_section_item
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'resumes', ResumeViewSet, basename='resume')
router.register(r'work-experiences', WorkExperienceViewSet, basename='work-experience')
router.register(r'educations', EducationViewSet, basename='education')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'certifications', CertificationViewSet, basename='certification')
router.register(r'custom-sections', CustomSectionViewSet, basename='custom-section')
router.register(r'custom-section-items', CustomSectionItemViewSet, basename='custom-section-item')
router.register(r'saved-cover-letters', SavedCoverLetterViewSet, basename='saved-cover-letter')

# Wire up our API using automatic URL routing
urlpatterns = [
    path('', include(router.urls)),
    path('parse-resume/', parse_resume, name='parse-resume'),
    path('adapt-resume/', adapt_resume, name='adapt-resume'),
    path('save-parsed-resume/', save_parsed_resume, name='save-parsed-resume'),
    path('resumes/<uuid:resume_id>/score/', score_resume, name='score-resume'),
    path('job-search/', job_search_api, name='job_search_api'),
    path('generate-cover-letter/', generate_cover_letter, name='generate-cover-letter'),
    path('enhance-work-experience/', enhance_work_experience, name='enhance-work-experience'),
    path('enhance-project/', enhance_project, name='enhance-project'),
    path('enhance-certification/', enhance_certification, name='enhance-certification'),
    path('enhance-custom-section-item/', enhance_custom_section_item, name='enhance-custom-section-item'),
]
