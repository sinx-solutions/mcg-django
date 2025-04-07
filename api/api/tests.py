from django.test import TestCase
import uuid
from .models import (
    Resume,
    WorkExperience,
    Education,
    Project,
    Certification,
    CustomSection,
    CustomSectionItem
)


class CheckTests(TestCase):
    def setup(self):
        self.user_id = uuid.uuid4()
        self.resume = Resume.objects.create(
            user_id = self.user_id,
            title= "Test Resume",
            first_name = "John",
            last_name="Doe"
        )

class ResumeModelTest(TestCase):
    def setUp(self):
        # Create a sample resume
        self.user_id = uuid.uuid4()
        self.resume = Resume.objects.create(
            user_id=self.user_id,
            title="Test Resume",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            skills=["Python", "Django", "JavaScript"]
        )

    def test_resume_creation(self):
        """Test that a resume is created correctly"""
        self.assertEqual(self.resume.title, "Test Resume")
        self.assertEqual(self.resume.first_name, "John")
        self.assertEqual(self.resume.last_name, "Doe")
        self.assertEqual(self.resume.email, "john@example.com")
        self.assertEqual(self.resume.skills, ["Python", "Django", "JavaScript"])
        self.assertEqual(self.resume.template, "classic")  # Default value
        self.assertEqual(self.resume.font_size, 16)  # Default value
        self.assertEqual(self.resume.user_id, self.user_id)

    def test_resume_string_representation(self):
        """Test the string representation of a resume"""
        self.assertEqual(str(self.resume), f"Test Resume ({self.resume.id})")

    def test_resume_default_values(self):
        """Test that default values are set correctly"""
        self.assertEqual(self.resume.color_hex, "#000000")
        self.assertEqual(self.resume.border_style, "squircle")
        self.assertEqual(self.resume.font_family, "Arial")
        self.assertEqual(self.resume.section_spacing, 24)
        self.assertEqual(self.resume.line_height, 1.5)
        self.assertEqual(self.resume.content_margin, 32)


class WorkExperienceModelTest(TestCase):
    def setUp(self):
        # Create a sample resume and work experience
        self.user_id = uuid.uuid4()
        self.resume = Resume.objects.create(
            user_id=self.user_id,
            title="Test Resume"
        )
        self.work_experience = WorkExperience.objects.create(
            resume=self.resume,
            position="Software Developer",
            company="Tech Company",
            description="Developed web applications"
        )

    def test_work_experience_creation(self):
        """Test that a work experience is created correctly"""
        self.assertEqual(self.work_experience.position, "Software Developer")
        self.assertEqual(self.work_experience.company, "Tech Company")
        self.assertEqual(self.work_experience.description, "Developed web applications")
        self.assertEqual(self.work_experience.resume, self.resume)

    def test_work_experience_string_representation(self):
        """Test the string representation of a work experience"""
        self.assertEqual(str(self.work_experience), "Software Developer at Tech Company")

    def test_cascade_delete(self):
        """Test that work experiences are deleted when the resume is deleted"""
        work_exp_id = self.work_experience.id
        self.resume.delete()
        with self.assertRaises(WorkExperience.DoesNotExist):
            WorkExperience.objects.get(id=work_exp_id)


class EducationModelTest(TestCase):
    def setUp(self):
        # Create a sample resume and education
        self.user_id = uuid.uuid4()
        self.resume = Resume.objects.create(
            user_id=self.user_id,
            title="Test Resume"
        )
        self.education = Education.objects.create(
            resume=self.resume,
            degree="Computer Science",
            school="University of Technology"
        )

    def test_education_creation(self):
        """Test that an education entry is created correctly"""
        self.assertEqual(self.education.degree, "Computer Science")
        self.assertEqual(self.education.school, "University of Technology")
        self.assertEqual(self.education.resume, self.resume)

    def test_education_string_representation(self):
        """Test the string representation of an education entry"""
        self.assertEqual(str(self.education), "Computer Science at University of Technology")

    def test_cascade_delete(self):
        """Test that education entries are deleted when the resume is deleted"""
        education_id = self.education.id
        self.resume.delete()
        with self.assertRaises(Education.DoesNotExist):
            Education.objects.get(id=education_id)


class ProjectModelTest(TestCase):
    def setUp(self):
        # Create a sample resume and project
        self.user_id = uuid.uuid4()
        self.resume = Resume.objects.create(
            user_id=self.user_id,
            title="Test Resume"
        )
        self.project = Project.objects.create(
            resume=self.resume,
            title="Web App",
            description="Built a web application using Django"
        )

    def test_project_creation(self):
        """Test that a project is created correctly"""
        self.assertEqual(self.project.title, "Web App")
        self.assertEqual(self.project.description, "Built a web application using Django")
        self.assertEqual(self.project.resume, self.resume)

    def test_project_string_representation(self):
        """Test the string representation of a project"""
        self.assertEqual(str(self.project), "Web App")

    def test_cascade_delete(self):
        """Test that projects are deleted when the resume is deleted"""
        project_id = self.project.id
        self.resume.delete()
        with self.assertRaises(Project.DoesNotExist):
            Project.objects.get(id=project_id)


class CustomSectionModelTest(TestCase):
    def setUp(self):
        # Create a sample resume, custom section, and custom section item
        self.user_id = uuid.uuid4()
        self.resume = Resume.objects.create(
            user_id=self.user_id,
            title="Test Resume"
        )
        self.custom_section = CustomSection.objects.create(
            resume=self.resume,
            title="Publications"
        )
        self.custom_section_item = CustomSectionItem.objects.create(
            custom_section=self.custom_section,
            title="Research Paper",
            description="Published in a top journal"
        )

    def test_custom_section_creation(self):
        """Test that a custom section is created correctly"""
        self.assertEqual(self.custom_section.title, "Publications")
        self.assertEqual(self.custom_section.resume, self.resume)

    def test_custom_section_item_creation(self):
        """Test that a custom section item is created correctly"""
        self.assertEqual(self.custom_section_item.title, "Research Paper")
        self.assertEqual(self.custom_section_item.description, "Published in a top journal")
        self.assertEqual(self.custom_section_item.custom_section, self.custom_section)

    def test_custom_section_string_representation(self):
        """Test the string representation of a custom section"""
        self.assertEqual(str(self.custom_section), "Publications")

    def test_custom_section_item_string_representation(self):
        """Test the string representation of a custom section item"""
        self.assertEqual(str(self.custom_section_item), "Research Paper")

    def test_cascade_delete_section(self):
        """Test that custom section items are deleted when the section is deleted"""
        item_id = self.custom_section_item.id
        self.custom_section.delete()
        with self.assertRaises(CustomSectionItem.DoesNotExist):
            CustomSectionItem.objects.get(id=item_id)

    def test_cascade_delete_resume(self):
        """Test that custom sections are deleted when the resume is deleted"""
        section_id = self.custom_section.id
        item_id = self.custom_section_item.id
        self.resume.delete()
        with self.assertRaises(CustomSection.DoesNotExist):
            CustomSection.objects.get(id=section_id)
        with self.assertRaises(CustomSectionItem.DoesNotExist):
            CustomSectionItem.objects.get(id=item_id)


class createApiSuite(TestCase):
    def check1(self):
        self.auth = "string-manuplitation-simplified"
        self.api_key = "sk-101mainsubnetconfig"
        self.time = resume.object()