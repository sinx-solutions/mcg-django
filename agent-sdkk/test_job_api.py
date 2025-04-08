import requests
import json

# Replace with your actual Django development server URL if different
API_URL = "http://127.0.0.1:8000/api/job-search/"

def test_job_search(query: str):
    """Sends a query to the job search API endpoint and prints the result."""
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({"query": query})
    
    print(f"--- Sending query to {API_URL}: '{query}' ---")
    
    try:
        response = requests.post(API_URL, headers=headers, data=payload)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        result = response.json()
        print("--- API Response ---")
        # Pretty print the 'result' part of the JSON response
        if 'result' in result:
            print(result['result'])
        else:
            print(json.dumps(result, indent=2))
            
    except requests.exceptions.RequestException as e:
        print(f"\n--- Error contacting API --- ")
        print(f"Error: {e}")
        if e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            try:
                print(f"Response Body: {e.response.text}")
            except Exception:
                print("Could not decode error response body.")
    except json.JSONDecodeError:
        print("\n--- Error: Could not decode JSON response --- ")
        print(f"Raw response: {response.text}")
    except Exception as e:
        print(f"\n--- An unexpected error occurred ---")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query = "python developer in New York"
    # You can add more test queries here if needed
    # test_query_2 = "remote data scientist"
    
    test_job_search(test_query)
    # test_job_search(test_query_2)
    print("\n--- Test finished ---")
