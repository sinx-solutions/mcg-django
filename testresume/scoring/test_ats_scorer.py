import unittest
import sys
import os

# Add parent directory to sys.path to allow importing ats_scorer
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, parent_dir)

# Import the functions/class to test
# Assuming parse_duration is moved inside the class or imported if kept global
try:
    from ats_scorer import ATSScorer, parse_duration # Adjust if parse_duration is elsewhere
except ImportError as e:
    print(f"Failed to import ATSScorer or parse_duration: {e}")
    # Fallback if parse_duration remained global and not easily importable
    try:
        # If run_scorer is executable, maybe import from there?
        # This is awkward, suggests parse_duration should be in the class or its own util file
        print("Attempting fallback import strategy - this might fail")
        # from run_scorer import parse_duration # Example, likely needs adjustment
        raise ImportError("Cannot reliably import parse_duration for testing if it's not in ats_scorer.py or a utils module")
    except ImportError:
        ATSScorer = None # To avoid errors later if class not loaded
        parse_duration = lambda x: 0 # Dummy function if import fails

# Dummy logger for testing without real logging setup
class DummyLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): print(f"TEST WARNING: {msg}") # Print warnings
    def error(self, msg): pass

# Test Suite
class TestATSExtraction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        "Set up a dummy scorer instance for tests that need it."
        if ATSScorer:
            cls.scorer = ATSScorer()
            # Replace logger with dummy to suppress excessive test output
            cls.scorer.logger = DummyLogger()
        else:
            cls.scorer = None

    def test_parse_duration(self):
        "Test the duration string parsing."
        self.assertAlmostEqual(parse_duration("3 years 4 months"), 3 + 4/12)
        self.assertAlmostEqual(parse_duration("1 year"), 1.0)
        self.assertAlmostEqual(parse_duration("6 months"), 0.5)
        self.assertAlmostEqual(parse_duration("2 Years 0 months"), 2.0)
        self.assertEqual(parse_duration("Present"), 0) # Should not parse
        self.assertEqual(parse_duration(""), 0)
        self.assertEqual(parse_duration("Invalid string"), 0)

    def test_extract_years_of_experience(self):
        "Test extraction of years of experience."
        if not self.scorer:
            self.skipTest("ATSScorer class not loaded")

        self.assertEqual(self.scorer.extract_years_of_experience("Requires 5+ years of experience"), 5)
        self.assertEqual(self.scorer.extract_years_of_experience("Minimum 3 years professional experience"), 3)
        self.assertEqual(self.scorer.extract_years_of_experience("Experience: 10 years"), 10)
        self.assertEqual(self.scorer.extract_years_of_experience("Must have 1 year in the industry"), 1)
        self.assertEqual(self.scorer.extract_years_of_experience("3-5 years relevant experience needed"), 3) # Assuming lower bound - CHECK REGEX
        self.assertEqual(self.scorer.extract_years_of_experience("Senior role, 15+ years"), 15)
        self.assertEqual(self.scorer.extract_years_of_experience("No specific years required"), 0)
        self.assertEqual(self.scorer.extract_years_of_experience("Experience with Python"), 0)

    def test_extract_education_level(self):
        "Test extraction of education level."
        if not self.scorer:
            self.skipTest("ATSScorer class not loaded")

        self.assertEqual(self.scorer.extract_education_level("PhD in Physics"), 5)
        self.assertEqual(self.scorer.extract_education_level("Completed Doctorate"), 5)
        self.assertEqual(self.scorer.extract_education_level("Juris Doctor (J.D.)"), 5)
        self.assertEqual(self.scorer.extract_education_level("MD degree"), 5)

        self.assertEqual(self.scorer.extract_education_level("Master of Science (MS)"), 4)
        self.assertEqual(self.scorer.extract_education_level("Holds an MBA"), 4)
        self.assertEqual(self.scorer.extract_education_level("Graduate program completed"), 4)
        self.assertEqual(self.scorer.extract_education_level("M.Eng degree"), 4)

        self.assertEqual(self.scorer.extract_education_level("Bachelor's degree required"), 3)
        self.assertEqual(self.scorer.extract_education_level("B.S. Computer Science"), 3)
        self.assertEqual(self.scorer.extract_education_level("BA in English"), 3)
        self.assertEqual(self.scorer.extract_education_level("Undergraduate degree in engineering"), 3)

        self.assertEqual(self.scorer.extract_education_level("Associate's degree (A.A.)"), 2)
        self.assertEqual(self.scorer.extract_education_level("Some college coursework completed"), 2)

        self.assertEqual(self.scorer.extract_education_level("High School Diploma"), 1)
        self.assertEqual(self.scorer.extract_education_level("GED equivalent"), 1)

        self.assertEqual(self.scorer.extract_education_level("Relevant certifications"), 0)
        self.assertEqual(self.scorer.extract_education_level("Learning new skills"), 0)

# Add more test classes for other components (scoring logic, etc.) later

if __name__ == '__main__':
    unittest.main() 