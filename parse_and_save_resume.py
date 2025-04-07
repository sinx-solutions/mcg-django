import requests
import sys
import os
import json

# --- Configuration ---
BASE_API_URL = "http://127.0.0.1:8000/api/"  # Adjust if your server runs elsewhere
PARSE_ENDPOINT = BASE_API_URL + "parse-resume/"
SAVE_ENDPOINT = BASE_API_URL + "save-parsed-resume/"
# ---------------------

def print_usage():
    """Prints instructions on how to run the script."""
    print("Usage: python parse_and_save_resume.py <user_id> <path_to_resume_pdf_or_docx>")
    print("Example: python parse_and_save_resume.py f47ac10b-58cc-4372-a567-0e02b2c3d479 /path/to/my_resume.pdf")

def parse_and_save(user_id, file_path):
    """Parses the resume file and then saves the structured data via API calls."""

    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return

    file_name = os.path.basename(file_path)

    # --- Step 1: Call Parse Endpoint ---
    print(f"Step 1: Sending '{file_name}' to {PARSE_ENDPOINT} for parsing...")
    try:
        with open(file_path, 'rb') as resume_file:
            files = {'resume': (file_name, resume_file)}
            data = {'user_id': user_id}
            response_parse = requests.post(PARSE_ENDPOINT, files=files, data=data)
            response_parse.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to parse endpoint: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred during parsing request: {e}")
        return

    print(f"Parse request successful (Status: {response_parse.status_code})")

    try:
        parsed_data = response_parse.json()
        # print("\n--- Raw Parse Response ---")
        # print(json.dumps(parsed_data, indent=2))
        # print("------------------------\n")

        if 'validated_data' not in parsed_data or not parsed_data.get('ready_for_db'):
            print("Error: 'validated_data' not found or not ready in parse response.")
            print("API Response:", json.dumps(parsed_data, indent=2))
            return

        validated_data = parsed_data['validated_data']
        print("Successfully received validated data from parse endpoint.")

    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from parse endpoint.")
        print("Raw response:", response_parse.text)
        return
    except Exception as e:
        print(f"An unexpected error occurred processing parse response: {e}")
        return


    # --- Step 2: Call Save Endpoint ---
    print(f"\nStep 2: Sending validated data to {SAVE_ENDPOINT} for saving...")
    try:
        payload = {
            'user_id': user_id,
            'validated_data': validated_data
        }
        response_save = requests.post(SAVE_ENDPOINT, json=payload)
        response_save.raise_for_status() # Raise HTTPError for bad responses

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to save endpoint: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred during saving request: {e}")
        return

    print(f"Save request successful (Status: {response_save.status_code})")

    try:
        saved_data = response_save.json()
        print("\n--- Saved Resume Data ---")
        print(json.dumps(saved_data, indent=2))
        print("-------------------------\n")
        print("Resume parsed and saved successfully!")

    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from save endpoint.")
        print("Raw response:", response_save.text)
        return
    except Exception as e:
        print(f"An unexpected error occurred processing save response: {e}")
        return


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print_usage()
        sys.exit(1)

    user_id_arg = sys.argv[1]
    file_path_arg = sys.argv[2]

    # Basic validation (could add UUID format check if needed)
    if not user_id_arg:
        print("Error: User ID cannot be empty.")
        print_usage()
        sys.exit(1)

    if not file_path_arg:
        print("Error: File path cannot be empty.")
        print_usage()
        sys.exit(1)

    parse_and_save(user_id_arg, file_path_arg) 