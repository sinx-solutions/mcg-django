import requests
import os
import json
import time
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

# --- Configuration ---
# Load environment variables from .env file
# Ensure you have python-dotenv installed: pip install python-dotenv
load_dotenv()

SERP_API_KEY = os.getenv("SERP_API_KEY")
BASE_URL = "https://serpapi.com/search.json"
JOBS_TO_DISPLAY_PER_PAGE = 2 # Reduce display count for more tests
DEFAULT_TIMEOUT = 45 # Seconds
DELAY_BETWEEN_PAGES = 1.1 # Seconds to wait between paginated requests (slight increase)

# Define standard test scenarios
# Each dictionary contains a name and the parameters for the API call
# We'll handle pagination and UDS tests separately as they depend on prior results
STANDARD_TEST_SCENARIOS = [
    {
        "name": "Basic Query",
        "params": {"q": "Python Developer"}
    },
    {
        "name": "Query with Location",
        "params": {"q": "React Developer", "location": "Austin, Texas, United States"}
    },
    {
        "name": "Localization (FR)",
        "params": {"q": "Ingénieur Logiciel", "location": "Paris, France", "hl": "fr", "gl": "fr"}
    },
    {
        "name": "Work From Home",
        "params": {"q": "Marketing Manager", "ltype": "1"}
    },
    # Add scenarios needed for dependent tests
    {
        "name": "Pagination - Initial Search", # Name clearly indicates purpose
        "params": {"q": "Data Analyst", "location": "Chicago, Illinois, United States"}
    },
    {
        "name": "UDS Filter - Initial Search", # Name clearly indicates purpose
        "params": {"q": "Data Scientist", "location": "New York, NY"}
    },
    # --- Add more scenarios as needed ---
    # Example: Search within a radius
    # {
    #     "name": "Radius Search",
    #     "params": {"q": "Nurse", "location": "Boston, MA", "lrad": "50"} # 50 km radius
    # },
]

# --- SerpApi Client Class (Agent-Focused Design v2) ---

class SerpApiGoogleJobsClient:
    """Client for interacting with the SerpApi Google Jobs endpoint.

    Designed for use as a tool by AI agents (e.g., OpenAI Assistants, CrewAI).
    Handles common search parameters explicitly and allows passing any other valid
    API parameters via the `other_params` dictionary for maximum flexibility.
    Provides methods for single searches and automatic pagination.
    """

    def __init__(self, api_key: str, base_url: str = BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        """Initializes the SerpApi Google Jobs client.

        This should typically be done once when setting up agent tools.

        Args:
            api_key (str): Your unique SerpApi API key. This is REQUIRED.
                           It should be securely retrieved (e.g., from environment variables).
            base_url (str): The base URL for the SerpApi search endpoint.
                           Defaults to 'https://serpapi.com/search.json'.
            timeout (int): Network request timeout duration in seconds.
        """
        if not api_key:
            raise ValueError("API key is required for SerpApiGoogleJobsClient.")
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def _prepare_params(self, 
                         base_params: Dict[str, Any], 
                         other_params: Optional[Dict[str, Any]] = None
                         ) -> Dict[str, Any]:
        """Merges base parameters with other arbitrary parameters."""
        final_params = base_params.copy()
        if other_params:
            final_params.update(other_params)
        return final_params

    def _make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Internal method to make the API request and handle basic responses/errors."""
        request_params = {
            "api_key": self.api_key,
            "engine": "google_jobs", # Fixed engine for this specific client
        }
        request_params.update(params)

        print(f"DEBUG: Making API request with params: {request_params}")

        try:
            response = self.session.get(self.base_url, params=request_params, timeout=self.timeout)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                 # Standard success case
                 return response.json()
            elif 'text/html' in content_type:
                 # Success case when HTML output was explicitly requested
                 print("WARN: Received HTML response as requested via 'output' parameter. Returning structure with raw HTML.")
                 return {"search_metadata": {"status": "Success_HTML_Received"}, "html_content": response.text}
            else:
                 # Fallback for unexpected content types
                 print(f"WARN: Received unexpected content-type: {content_type}. Returning structure with raw content.")
                 return {"search_metadata": {"status": "Success_UnknownContentType"}, "raw_content": response.text}
                 
        except requests.exceptions.Timeout:
            print(f"ERROR: API request timed out after {self.timeout} seconds.")
            # Return structured error info if needed by agent
            # return {"error": "API request timed out", "status_code": None}
            return None 
        except requests.exceptions.RequestException as e:
            # Handle HTTP errors (4xx, 5xx)
            status_code = e.response.status_code if e.response is not None else "N/A"
            error_details = "No response body or failed to parse error."
            # Attempt to get specific error message from SerpApi response body
            if e.response is not None:
                try:
                    err_json = e.response.json()
                    error_details = err_json.get('error', 'Error JSON present but no specific message.')
                except json.JSONDecodeError:
                    # If response is not JSON, use raw text (limit length)
                    error_details = f"Non-JSON response: {e.response.text[:200]}..."
            
            print(f"ERROR: HTTP Error during API request: {e}")
            print(f"ERROR: Status Code: {status_code}, SerpApi Error Message: {error_details}")
            # Return structured error info if needed by agent
            # return {"error": error_details, "status_code": status_code}
            return None
        # Note: JSONDecodeError on a 2xx response is unlikely but would be caught generally if needed

    def search(self,
               query: str,
               location: Optional[str] = None,
               google_domain: Optional[str] = None,
               language: Optional[str] = None,
               country: Optional[str] = None,
               work_from_home: bool = False,
               no_cache: bool = False,
               radius_km: Optional[int] = None,
               filter_uds: Optional[str] = None,
               next_page_token: Optional[str] = None,
               other_params: Optional[Dict[str, Any]] = None
               ) -> Optional[Dict[str, Any]]:
        """Performs a single Google Jobs search via the SerpApi service.

        Use this method to fetch one page of results. For multiple pages, use `search_paginated`.

        Args:
            query (str): The primary search term for the job (e.g., "Software Engineer", "Barista"). REQUIRED.
            location (Optional[str]): The geographic location to search from (e.g., "Austin, TX", "London, UK", "Remote").
                                      Note: Using "Remote" might be unsupported with some parameter combinations.
                                      Mutually exclusive with `uule` in `other_params`.
            google_domain (Optional[str]): The Google domain to use for the search (e.g., "google.co.uk", "google.de", "google.com"). 
                                           Defaults to google.com if not specified.
            language (Optional[str]): The two-letter language code for the search results (e.g., "en", "es", "fr"). Maps to the API's 'hl' parameter.
            country (Optional[str]): The two-letter country code to associate the search with (e.g., "us", "gb", "de"). Maps to the API's 'gl' parameter.
            work_from_home (bool): Set to True to filter specifically for 'Work from home' jobs. Maps to the API's 'ltype=1' parameter. Defaults to False.
            no_cache (bool): Set to True to force SerpApi to bypass its cache and fetch fresh results. Maps to the API's 'no_cache=true' parameter. Defaults to False.
            radius_km (Optional[int]): Defines a search radius in kilometers around the specified `location`. Maps to the API's 'lrad' parameter.
            filter_uds (Optional[str]): A specific filter code obtained from the 'filters' section of a previous search result. Maps to the API's 'uds' parameter.
                                        Use this to apply filters like 'Full-time' or 'Past 3 days'.
            next_page_token (Optional[str]): The token provided in a previous search result's 'serpapi_pagination' section to retrieve the subsequent page.
            other_params (Optional[Dict[str, Any]]): A dictionary for any other valid parameters supported by the SerpApi Google Jobs endpoint
                                                     (e.g., {"uule": "...", "async": "true", "output": "html"}).
                                                     Use this for less common or advanced parameters not listed explicitly.
                                                     Note: Keys here might override explicitly set parameters if conflicts exist.

        Returns:
            Optional[Dict[str, Any]]: 
              - On success with JSON response: A dictionary representing the parsed JSON result from SerpApi.
              - On success with non-JSON response (if `output` in `other_params` was used): 
                A dictionary containing metadata and the raw content (e.g., {'search_metadata': {'status': 'Success_HTML_Received'}, 'html_content': '...'}).
              - On failure (network error, API error, timeout): None. Check logs for error details.
        """
        base_params = {"q": query}
        if location:
            base_params["location"] = location
        if google_domain:
            base_params["google_domain"] = google_domain
        if language:
            base_params["hl"] = language
        if country:
            base_params["gl"] = country
        if work_from_home:
            base_params["ltype"] = "1"
        if no_cache:
            base_params["no_cache"] = "true"
        if radius_km is not None:
            base_params["lrad"] = str(radius_km)
        if filter_uds:
            base_params["uds"] = filter_uds
        if next_page_token:
            base_params["next_page_token"] = next_page_token
            
        final_params = self._prepare_params(base_params, other_params)
        return self._make_request(final_params)

    def search_paginated(self,
                         query: str,
                         max_pages: int = 3,
                         location: Optional[str] = None,
                         google_domain: Optional[str] = None,
                         language: Optional[str] = None,
                         country: Optional[str] = None,
                         work_from_home: bool = False,
                         no_cache: bool = False,
                         radius_km: Optional[int] = None,
                         filter_uds: Optional[str] = None,
                         other_params: Optional[Dict[str, Any]] = None
                         ) -> List[Dict[str, Any]]:
        """Performs a Google Jobs search via SerpApi, automatically handling pagination.

        Fetches multiple pages of results (up to `max_pages`) and aggregates 
        only the job listings found in the 'jobs_results' array from each successful page.
        
        Args:
            query (str): The core search term for the job. REQUIRED.
            max_pages (int): Maximum number of result pages to fetch. Defaults to 3.
                           Set higher to get more results, respecting potential API rate limits/costs.
            location (Optional[str]): Geographic location (e.g., "Austin, TX", "Remote").
            google_domain (Optional[str]): Google domain to use (e.g., "google.co.uk").
            language (Optional[str]): Language code ('hl').
            country (Optional[str]): Country code ('gl').
            work_from_home (bool): Filter for remote jobs ('ltype=1'). Defaults to False.
            no_cache (bool): Force fresh results ('no_cache=true'). Defaults to False.
            radius_km (Optional[int]): Search radius in kilometers ('lrad').
            filter_uds (Optional[str]): Specific Google filter code ('uds'). Applied to all pages.
            other_params (Optional[Dict[str, Any]]): Other parameters applied to each page request 
                                                     (e.g., {"uule": "..."}). Avoid using `output=html` here
                                                     as job aggregation requires JSON.

        Returns:
            List[Dict[str, Any]]: A list containing all the job dictionaries extracted from the 
                                   'jobs_results' field across the successfully fetched pages.
                                   Returns an empty list if the initial search fails, 
                                   no jobs are found, or a non-JSON response is encountered.
        """
        all_jobs = []
        current_page = 1
        current_next_page_token = None

        print(f"INFO: Executing paginated search for '{query}', max_pages={max_pages}")

        while current_page <= max_pages:
            print(f"INFO: Fetching page {current_page}...")
            # Pass all relevant parameters, including no_cache, domain etc to the underlying search
            result_data = self.search(
                query=query,
                location=location,
                google_domain=google_domain,
                language=language,
                country=country,
                work_from_home=work_from_home,
                no_cache=no_cache, # Pass no_cache setting to each page request
                radius_km=radius_km,
                filter_uds=filter_uds,
                next_page_token=current_next_page_token,
                other_params=other_params
            )

            if not result_data:
                print(f"WARN: Error fetching page {current_page}. Stopping pagination.")
                break
                
            metadata = result_data.get("search_metadata", {})
            status = metadata.get("status", "Error")

            if status != "Success":
                 if not result_data.get("jobs_results"):
                     # Handle non-JSON success codes (like HTML received) or actual errors
                     if status in ["Success_HTML_Received", "Success_UnknownContentType"]:
                         print(f"WARN: Received non-JSON content on page {current_page}. Cannot aggregate jobs. Stopping pagination.")
                     else:
                         print(f"WARN: API status '{status}' on page {current_page}: {result_data.get('error', 'No jobs found/Error')}. Stopping pagination.")
                     break 
                 else:
                     print(f"WARN: API status '{status}' on page {current_page} but jobs array exists. Continuing cautiously.")

            page_jobs = result_data.get("jobs_results", [])
            if not page_jobs:
                if status == "Success_HTML_Received" or status == "Success_UnknownContentType":
                    print(f"INFO: Received non-JSON content as requested on page {current_page}. Stopping pagination as job results cannot be extracted.")
                else:
                    print(f"INFO: No more job results found on page {current_page}. Stopping pagination.")
                break
            
            all_jobs.extend(page_jobs)
            print(f"INFO: Found {len(page_jobs)} jobs on page {current_page}. Total jobs so far: {len(all_jobs)}.")

            current_next_page_token = result_data.get("serpapi_pagination", {}).get("next_page_token")
            if not current_next_page_token:
                print("INFO: No next_page_token found. Stopping pagination.")
                break

            current_page += 1
            if current_page <= max_pages:
                 print(f"INFO: Waiting {DELAY_BETWEEN_PAGES}s before fetching next page...")
                 time.sleep(DELAY_BETWEEN_PAGES)

        print(f"INFO: Paginated search finished. Total jobs collected: {len(all_jobs)}.")
        return all_jobs


# --- Result Processing & Display Functions (Remain Separate) ---

def analyze_response(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Analyzes a single raw API response dictionary."""
    if not data:
        return None
    return {
        "status": data.get("search_metadata", {}).get("status", "Error"),
        "error_message": data.get("error"),
        "jobs": data.get("jobs_results", []),
        "next_page_token": data.get("serpapi_pagination", {}).get("next_page_token"),
        "filters": data.get("filters", [])
    }

def print_job_summary(job: Dict[str, Any]):
    """Prints a detailed summary of a single job dictionary."""
    title = job.get('title', 'N/A')
    company = job.get('company_name', 'N/A')
    location = job.get('location', 'N/A')
    posted_at = job.get('detected_extensions', {}).get('posted_at', 'N/A')
    schedule_type = job.get('detected_extensions', {}).get('schedule_type', 'N/A')
    via = job.get('via', 'N/A')
    share_link = job.get('share_link', 'N/A')
    description = job.get('description', 'N/A')
    apply_options = job.get('apply_options', [])

    print(f"    --- Job: {title} at {company} ---")
    print(f"      Location: {location}")
    print(f"      Posted: {posted_at}")
    print(f"      Type: {schedule_type}")
    print(f"      Via: {via}")
    print(f"      Google Link: {share_link}")
    if apply_options:
        print("      Apply Options:")
        for option in apply_options:
            print(f"        - {option.get('title', 'N/A')}: {option.get('link', 'N/A')}")
    else:
        print("      Apply Options: Not found")
    if description != 'N/A':
        print(f"      Description (truncated): {description[:100]}...")
    else:
        print("      Description: N/A")
    print("    " + "-" * 25)

def print_search_results_summary(analyzed_data: Optional[Dict[str, Any]], title: str):
    """Prints a summary for the results of a single API call."""
    print(f"--- Results Summary: {title} ---")
    if not analyzed_data:
        print("  No analyzed data provided (Request likely failed). ")
        print("-" * (len(title) + 20))
        return

    status = analyzed_data.get('status', 'Status Unknown')
    print(f"  API Status: {status}")

    if status == "Success":
        jobs = analyzed_data.get('jobs', [])
        print(f"  Jobs Found This Page: {len(jobs)}")
        if jobs:
            print(f"  Displaying first {min(len(jobs), JOBS_TO_DISPLAY_PER_PAGE)} job summaries:")
            for job in jobs[:JOBS_TO_DISPLAY_PER_PAGE]:
                print_job_summary(job)
        else:
            print("  No job results found on this page.")
        if analyzed_data.get('next_page_token'):
            print(f"  Next Page Token available: {analyzed_data['next_page_token'][:30]}...")
        filters = analyzed_data.get('filters', [])
        if filters:
             print("  Available Filters (Top level):")
             for f in filters[:3]:
                 print(f"    - {f.get('name', 'Unknown Filter')}")
    elif status in ["Success_HTML_Received", "Success_UnknownContentType"]:
        print("  Received non-JSON content as requested. No job summaries to display.")
    elif status == "Processing":
         print("  Search submitted for asynchronous processing.")
    else:
        print(f"  API Error: {analyzed_data.get('error_message', 'Unknown error details')}")
        
    print("-" * (len(title) + 20))
    print()


# --- Main Execution (More Comprehensive Examples) --- 

if __name__ == "__main__":
    if not SERP_API_KEY:
        print("Fatal Error: SERP_API_KEY not found in environment variables.")
        print("Set it in your .env file.")
        exit(1)

    print("Initializing SerpApiGoogleJobsClient...")
    client = SerpApiGoogleJobsClient(api_key=SERP_API_KEY)
    print("Client Initialized.")
    print("="*50)

    all_results = {}

    print("--- Test 1: Basic Search (New York) ---")
    test1_raw = client.search(query="Site Reliability Engineer", location="New York, NY") 
    all_results["test1"] = analyze_response(test1_raw)
    print_search_results_summary(all_results["test1"], "Test 1: Basic SRE (NY)")

    print("--- Test 2: UK Domain + No Cache ---")
    test2_raw = client.search(
        query="Project Manager", 
        location="London, UK", 
        google_domain="google.co.uk",
        no_cache=True,
        language="en",
        country="uk"
    )
    all_results["test2"] = analyze_response(test2_raw)
    print_search_results_summary(all_results["test2"], "Test 2: PM (London, UK Domain, No Cache)")

    print("--- Test 3: Paginated Remote Search (Max 2 Pages) ---")
    all_paginated_jobs = client.search_paginated(
        query="Customer Support Specialist",
        work_from_home=True,
        max_pages=2
    )
    print(f"--- Test 3 Analysis --- ")
    print(f"Total jobs found across up to 2 pages: {len(all_paginated_jobs)}")
    if all_paginated_jobs:
        print(f"Displaying first {min(len(all_paginated_jobs), JOBS_TO_DISPLAY_PER_PAGE * 2)} job summaries:")
        for job in all_paginated_jobs[:JOBS_TO_DISPLAY_PER_PAGE * 2]: 
            print_job_summary(job)
    print("-" * 30)
    print()

    print("--- Test 4: Radius Search + Work From Home ---")
    test4_raw = client.search(
        query="Nurse Practitioner", 
        location="Boston, MA", 
        radius_km=75, 
        work_from_home=True 
    )
    all_results["test4"] = analyze_response(test4_raw)
    print_search_results_summary(all_results["test4"], "Test 4: Remote NP (Boston +75km)")

    print("--- Test 5: German Language/Country + No Cache ---")
    test5_raw = client.search(
        query="Softwareentwickler",
        location="Berlin, Germany",
        language="de",
        country="de",
        no_cache=True
    )
    all_results["test5"] = analyze_response(test5_raw)
    print_search_results_summary(all_results["test5"], "Test 5: German Dev (Berlin, No Cache)")

    print("--- Test 6: UDS Filter Application (from Test 1) ---")
    uds_code = None
    filter_name = "N/A"
    if all_results.get("test1") and all_results["test1"]["status"] == "Success":
        for f in all_results["test1"].get("filters", []):
            options = f.get("options", [])
            if options and options[0].get("uds"):
                uds_code = options[0]["uds"]
                filter_name = f"{f.get('name', '?')} - {options[0].get('name', '?')}"
                print(f"INFO: Found UDS code for filter '{filter_name}' from Test 1.")
                break
    
    if uds_code:
        test6_raw = client.search(
            query="Site Reliability Engineer",
            location="New York, NY",
            filter_uds=uds_code
        )
        all_results["test6"] = analyze_response(test6_raw)
        print_search_results_summary(all_results["test6"], f"Test 6: SRE (NY) with UDS: {filter_name}")
    else:
        print("INFO: Skipping Test 6 (no UDS code found in Test 1 results).")
        print()

    print("--- Test 7: UULE Search (London) ---")
    uule_london = "w+CAIQICIaTG9uZG9uLEVudGVycHJpc2UsVW5pdGVkIEtpbmdkb20=" 
    test7_raw = client.search(
        query="Financial Analyst", 
        other_params={"uule": uule_london, "gl": "uk"}
    )
    all_results["test7"] = analyze_response(test7_raw)
    print_search_results_summary(all_results["test7"], "Test 7: Fin Analyst (UULE London)")

    print("--- Test 8: Async Parameter Demonstration ---")
    test8_raw = client.search(
        query="Data Engineer", 
        location="Chicago, IL", 
        other_params={"async": "true"} 
    )
    all_results["test8"] = analyze_response(test8_raw)
    print("--- Async Request Submission Result --- ")
    if all_results.get("test8"):
        print(f"  API Status: {all_results['test8'].get('status')}")
        if test8_raw:
             search_id = test8_raw.get("search_metadata", {}).get("id")
             print(f"  Search ID submitted for async processing: {search_id}")
        print("  (Full job results would need to be retrieved later using the Search Archive API)")
    else:
        print("  Async request submission failed.")
    print("-" * 35)
    print()

    print("--- Test 9: HTML Output Parameter Demonstration ---")
    test9_raw = client.search(
        query="UX Designer", 
        location="New York, NY",
        other_params={"output": "html"} 
    )
    all_results["test9"] = analyze_response(test9_raw)
    print_search_results_summary(all_results["test9"], "Test 9: UX Designer (HTML Output - NY)")
    if test9_raw and test9_raw.get("search_metadata", {}).get("status") == "Success_HTML_Received":
        html_content = test9_raw.get("html_content", "")
        print(f"  Received HTML Content Snippet (first 200 chars):\n{html_content[:200]}...")
        print("-" * 35)
        print()


    print("="*50)
    print("SerpApi Google Jobs Client Test Suite Completed.") 