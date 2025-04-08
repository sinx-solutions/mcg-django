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
    score_resume
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'resumes', ResumeViewSet)
router.register(r'work-experiences', WorkExperienceViewSet)
router.register(r'educations', EducationViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'certifications', CertificationViewSet)
router.register(r'custom-sections', CustomSectionViewSet)
router.register(r'custom-section-items', CustomSectionItemViewSet)

# Wire up our API using automatic URL routing
urlpatterns = [
    path('', include(router.urls)),
    path('parse-resume/', parse_resume, name='parse-resume'),
    path('adapt-resume/', adapt_resume, name='adapt-resume'),
    path('save-parsed-resume/', save_parsed_resume, name='save-parsed-resume'),
    path('resumes/<uuid:resume_id>/score/', score_resume, name='score-resume'),
]
