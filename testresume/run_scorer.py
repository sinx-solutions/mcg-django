import sys
import os
import json
import glob # To find sample files
import traceback # Import traceback module
import ast # For potential future use
import logging

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(script_dir) # Assumes script is in 'testresume' at root

# Add the scoring directory to the Python path
scoring_dir = os.path.join(script_dir, 'scoring')

# Add the parent directory (workspace_root) to sys.path if needed
# This helps if imports are relative to the workspace root in the scoring module
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

# Add the scoring directory itself to sys.path
if scoring_dir not in sys.path:
     sys.path.insert(0, scoring_dir)


# Adjust import based on where ATSScorer is defined relative to the added paths
# Try importing assuming 'scoring' is a package relative to script dir
try:
    from scoring.ats_scorer import ATSScorer
except ImportError:
    # Fallback: Try importing assuming ats_scorer.py is directly in scoring_dir
    # (and scoring_dir was added to path)
    try:
        from ats_scorer import ATSScorer
    except ImportError as e:
        print(f"Error importing ATSScorer: {e}")
        print(f"Current sys.path: {sys.path}")
        print(f"Checked script directory: {script_dir}")
        print(f"Checked scoring directory: {scoring_dir}")
        # Let's check the contents to be sure
        try:
            print(f"Contents of scoring dir: {os.listdir(scoring_dir)}")
        except FileNotFoundError:
             print("Scoring directory not found.")
        sys.exit(1)

logger = logging.getLogger(__name__)

def load_data_from_file(filepath):
    """Loads a single dictionary literal from a file using ast.literal_eval."""
    content = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
             print(f"Error: File {filepath} is empty.")
             return None

        # Safely evaluate the string content as a Python literal (expecting a dict)
        evaluated_data = ast.literal_eval(content.strip())

        if not isinstance(evaluated_data, dict):
            print(f"Error: Content of {filepath} did not evaluate to a dictionary.")
            return None

        # Basic check for expected keys
        if 'resume' not in evaluated_data or 'jd' not in evaluated_data:
             print(f"Warning: Loaded dictionary from {filepath} missing 'resume' or 'jd' key.")
             # Return it anyway, let the caller handle missing keys

        return evaluated_data

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing literal data from {filepath}: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Unexpected error loading data from {filepath}: {type(e).__name__}")
        traceback.print_exc()
        return None

# --- Main execution ---
if __name__ == "__main__":
    # Define sample directory - it's the same directory as the script
    sample_dir = script_dir # Use script's directory
    sample_files = glob.glob(os.path.join(sample_dir, 'sample*.txt'))

    if not sample_files:
        print(f"Error: No sample*.txt files found in {sample_dir}") # Use updated variable
        sys.exit(1)

    print(f"Found sample files: {[os.path.basename(f) for f in sample_files]}") # Show just filenames

    # Initialize scorer (outside the loop)
    print("Initializing ATS Scorer...")
    try:
        # Make sure spacy model is downloaded, handle potential errors
        try:
             import spacy
             spacy.load('en_core_web_lg')
        except OSError:
             print("Spacy model 'en_core_web_lg' not found. Attempting download...")
             try:
                  spacy.cli.download('en_core_web_lg')
                  print("Model downloaded successfully.")
             except Exception as download_e:
                  print(f"Failed to download spacy model 'en_core_web_lg': {download_e}")
                  print("Please install it manually: python -m spacy download en_core_web_lg")
                  sys.exit(1)

        scorer = ATSScorer()
    except Exception as e:
        print(f"Error initializing ATSScorer: {e}")
        sys.exit(1)

    print("Scorer initialized.")

    # Loop through each sample file
    for sample_path in sorted(sample_files): # Sort for consistent order
        print(f"\n--- Processing {os.path.basename(sample_path)} ---")

        # Load data
        print(f"Loading data from {sample_path}...")
        loaded_data = load_data_from_file(sample_path)
        if not loaded_data:
            print(f"Failed to load data from {sample_path}. Skipping.")
            continue
        print("Data loaded successfully.")

        # Extract resume and JD data from the top-level dictionary
        resume_data = loaded_data.get('resume')
        job_data = loaded_data.get('jd')

        if not resume_data or not job_data:
            print(f"Error: Dictionary in {sample_path} missing 'resume' or 'jd' key. Skipping.")
            continue

        # Determine a display name (e.g., from resume name or jd title, fallback to filename)
        display_name = f"{resume_data.get('contact_info', {}).get('name', '')} vs {job_data.get('title', '')}"
        if display_name == " vs ":
            display_name = os.path.basename(sample_path)

        print(f"Scoring: {display_name}")
        result = scorer.score_resume(resume_data, job_data)
        print(json.dumps(result, indent=2))

    print("\nScoring complete for all sample files.") 