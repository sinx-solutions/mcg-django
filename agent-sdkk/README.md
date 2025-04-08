# SerpApi Google Jobs Client & Demo

## Overview

This Python script provides a robust and flexible client class, `SerpApiGoogleJobsClient`, for interacting with the [SerpApi Google Jobs API](https://serpapi.com/google-jobs-api). It is designed with AI agent usability (e.g., OpenAI Assistants, CrewAI tools) in mind, offering both explicitly defined common parameters and the flexibility to pass any other valid API parameters.

The script includes:
1.  The `SerpApiGoogleJobsClient` class for making API calls.
2.  Helper functions for analyzing and printing results.
3.  A comprehensive test suite within the `if __name__ == "__main__":` block demonstrating various usage patterns and parameter combinations.

## Features

*   **Object-Oriented Design:** Encapsulates API interaction within the `SerpApiGoogleJobsClient` class.
*   **Agent-Friendly Methods:** Clear methods (`search`, `search_paginated`) with detailed docstrings.
*   **Explicit Parameters:** Common API parameters (`query`, `location`, `language`, `country`, `google_domain`, `no_cache`, etc.) are explicit method arguments.
*   **Maximum Flexibility:** Supports *any* valid SerpApi parameter via the `other_params` dictionary argument.
*   **Automatic Pagination:** The `search_paginated` method handles fetching multiple pages of results and aggregates the job listings.
*   **Robust Error Handling:** Includes network timeout handling and attempts to parse specific error messages from SerpApi responses.
*   **Session Management:** Uses `requests.Session` for potential performance improvements with multiple calls.
*   **Demonstration Suite:** Includes extensive examples covering various API features and parameter combinations.

## Requirements

*   Python 3.7+
*   `requests` library
*   `python-dotenv` library
*   A valid SerpApi API Key

## Setup

1.  **Get API Key:** Obtain your API key from your [SerpApi Dashboard](https://serpapi.com/dashboard).
2.  **Create `.env` File:** In the same directory as the script (`apps/mcg/`), create a file named `.env`.
3.  **Add API Key to `.env`:** Add your API key to the `.env` file like this:
    ```dotenv
    SERP_API_KEY=your_actual_api_key_here
    ```
4.  **Install Dependencies:** Open your terminal in your project's root directory or the `apps/mcg` directory and run:
    ```bash
    pip install requests python-dotenv
    ```

## Usage (`SerpApiGoogleJobsClient` Class)

### Initialization

First, import and initialize the client, passing your API key.

```python
import os
from dotenv import load_dotenv
# Assuming the client class is in a file named serpapi_client.py for import example
# from .serpapi_client import SerpApiGoogleJobsClient 

# If running the demo script directly:
from test_serpapi_google_jobs import SerpApiGoogleJobsClient

load_dotenv()
SERP_API_KEY = os.getenv("SERP_API_KEY")

if not SERP_API_KEY:
    raise ValueError("SERP_API_KEY not found in environment variables.")

# Initialize the client
client = SerpApiGoogleJobsClient(api_key=SERP_API_KEY)
```

### Methods

#### 1. `client.search(...)`

Performs a search for a *single page* of results.

**Parameters:**

*   `query` (str): The primary search term for the job (e.g., "Software Engineer", "Barista"). **REQUIRED**.
*   `location` (Optional[str]): Geographic location (e.g., "Austin, TX", "London, UK", "Remote"). Mutually exclusive with `uule` in `other_params`.
*   `google_domain` (Optional[str]): Google domain to use (e.g., "google.co.uk", "google.de"). Defaults to google.com.
*   `language` (Optional[str]): Two-letter language code (maps to 'hl', e.g., "en", "es").
*   `country` (Optional[str]): Two-letter country code (maps to 'gl', e.g., "us", "gb").
*   `work_from_home` (bool): If True, filters for remote jobs (maps to 'ltype=1'). Defaults to False.
*   `no_cache` (bool): If True, forces fresh results (maps to 'no_cache=true'). Defaults to False.
*   `radius_km` (Optional[int]): Search radius in kilometers (maps to 'lrad').
*   `filter_uds` (Optional[str]): Specific Google filter code from previous results (maps to 'uds').
*   `next_page_token` (Optional[str]): Token from previous results to fetch the next page.
*   `other_params` (Optional[Dict[str, Any]]): **Crucial for flexibility.** A dictionary for *any other* valid SerpApi parameters (e.g., `{"uule": "...", "async": "true", "output": "html"}`). Keys here might override explicitly set parameters.

**Returns:**

*   `Optional[Dict[str, Any]]`:
    *   On success (JSON): The full parsed JSON dictionary response from SerpApi.
    *   On success (HTML): A dictionary `{'search_metadata': {'status': 'Success_HTML_Received'}, 'html_content': '...'}` if `output=html` was passed in `other_params`.
    *   On Failure: `None`. Check console logs for detailed errors.

#### 2. `client.search_paginated(...)`

Performs a search and automatically fetches *multiple pages* of results, aggregating the actual job listings.

**Parameters:**

*   `query` (str): The core search term. **REQUIRED**.
*   `max_pages` (int): Maximum number of pages to fetch. Defaults to 3.
*   `location` (Optional[str]): Geographic location.
*   `google_domain` (Optional[str]): Google domain.
*   `language` (Optional[str]): Language code ('hl').
*   `country` (Optional[str]): Country code ('gl').
*   `work_from_home` (bool): Remote job filter ('ltype=1').
*   `no_cache` (bool): Force fresh results ('no_cache=true').
*   `radius_km` (Optional[int]): Search radius ('lrad').
*   `filter_uds` (Optional[str]): Google filter code ('uds'). Applied to all pages.
*   `other_params` (Optional[Dict[str, Any]]): Other parameters applied to each page request (e.g., `{"uule": "..."}`). Avoid `output=html`.

**Returns:**

*   `List[Dict[str, Any]]`: A list containing all the job dictionaries found in the `jobs_results` field across successfully fetched pages. Returns an empty list if the initial search fails, no jobs are found, or a non-JSON response is encountered during pagination.

## Examples (Based on Test Suite)

**(Note: Output snippets are abbreviated for brevity. API Key is omitted in logs.)**

### Example 1: Basic Search

```python
print("--- Test 1: Basic Search (New York) ---")
test1_raw = client.search(query="Site Reliability Engineer", location="New York, NY")
# ... analyze and print ...
```

**Expected Output Snippet:**

```
--- Results Summary: Test 1: Basic SRE (NY) ---
  API Status: Success
  Jobs Found This Page: 10
  Displaying first 2 job summaries:
    --- Job: Site Reliability Engineer (SRE) - Claroty FedRAMP AWS GovCloud ... at Claroty ---
      Location: Anywhere
      Posted: 8 days ago
      # ... more job details ...
    -------------------------
    --- Job: Site Reliability Engineer (SRE), TikTok Ads Serving- USDS at TikTok ---
      Location: New York, NY
      # ... more job details ...
    -------------------------
  Next Page Token available: eyJmYyI6IkVyY0RDdmNDUVVFdFMxUm...
  Available Filters (Top level):
    - Salary
    - Remote
    - Date posted
------------------------------------------
```

### Example 2: UK Domain + No Cache (Known API Issue)

```python
print("--- Test 2: UK Domain + No Cache ---")
test2_raw = client.search(
    query="Project Manager",
    location="London, UK", # This location string caused issues in testing
    google_domain="google.co.uk",
    no_cache=True,
    language="en",
    country="uk"
)
# ... analyze and print ...
```

**Expected Output Snippet (Shows API Error):**

```
--- Results Summary: Test 2: PM (London, UK Domain, No Cache) ---
  No analyzed data provided (Request likely failed). 
------------------------------------------------------------
# Console Logs show:
# ERROR: HTTP Error during API request: 400 Client Error: Bad Request ...
# ERROR: Status Code: 400, SerpApi Error Message: Unsupported `London, UK` location - location parameter.
```

### Example 3: Paginated Remote Search

```python
print("--- Test 3: Paginated Remote Search (Max 2 Pages) ---")
all_paginated_jobs = client.search_paginated(
    query="Customer Support Specialist",
    work_from_home=True,
    max_pages=2
)
# ... analyze and print aggregated jobs ...
```

**Expected Output Snippet:**

```
# INFO logs showing page fetches...
INFO: Paginated search finished. Total jobs collected: 20.
--- Test 3 Analysis --- 
Total jobs found across up to 2 pages: 20
Displaying first 4 job summaries:
    --- Job: Part-Time Customer Service Specialist at Segerstrom Center For The Arts ---
      # ... job details ...
    -------------------------
    --- Job: Customer Support Specialist - Now Hiring at Uline, Inc. ---
      # ... job details ...
    -------------------------
    # ... more jobs ...
------------------------------
```

### Example 4: Radius + Work From Home

```python
print("--- Test 4: Radius Search + Work From Home ---")
test4_raw = client.search(
    query="Nurse Practitioner",
    location="Boston, MA",
    radius_km=75,
    work_from_home=True
)
# ... analyze and print ...
```

**Expected Output Snippet:**

```
--- Results Summary: Test 4: Remote NP (Boston +75km) ---
  API Status: Success
  Jobs Found This Page: 10
  Displaying first 2 job summaries:
    --- Job: Urgent Care - New Grad - Nurse Practitioner (NP) at ConvenientMD ---
      Location: Manchester, NH
      # ... job details ...
    -------------------------
    --- Job: Locum Nurse Practitioner (NP) - Administration... at LocumJobsOnline ---
      Location: Manchester, NH
      # ... job details ...
    -------------------------
  Next Page Token available: eyJmYyI6IkVvd0RDc3dDUVVFdFMxUm...
  Available Filters (Top level):
    - Salary
    - Remote
    - Date posted
----------------------------------------------------
```

### Example 5: Language/Country + No Cache

```python
print("--- Test 5: German Language/Country + No Cache ---")
test5_raw = client.search(
    query="Softwareentwickler",
    location="Berlin, Germany",
    language="de",
    country="de",
    no_cache=True
)
# ... analyze and print ...
```

**Expected Output Snippet:**

```
--- Results Summary: Test 5: German Dev (Berlin, No Cache) ---
  API Status: Success
  Jobs Found This Page: 0
  No job results found on this page.
  Available Filters (Top level):
    - Gehalt
    - Ausbildung
    - Berlin
---------------------------------------------------------
```

### Example 6: UDS Filter (Dependent)

```python
# (Code depends on finding a UDS code in test1_raw results)
print("--- Test 6: UDS Filter Application (from Test 1) ---")
# ... code to extract uds_code ...
if uds_code:
    test6_raw = client.search(
        query="Site Reliability Engineer",
        location="New York, NY",
        filter_uds=uds_code
    )
    # ... analyze and print ...
else:
     print("INFO: Skipping Test 6 (no UDS code found in Test 1 results).")

```

**Expected Output Snippet (If UDS not found):**

```
--- Test 6: UDS Filter Application (from Test 1) ---
INFO: Skipping Test 6 (no UDS code found in Test 1 results).

```

### Example 7: UULE Location

```python
print("--- Test 7: UULE Search (London) ---")
uule_london = "w+CAIQICIaTG9uZG9uLEVudGVycHJpc2UsVW5pdGVkIEtpbmdkb20="
test7_raw = client.search(
    query="Financial Analyst",
    other_params={"uule": uule_london, "gl": "uk"} # Pass uule via other_params
)
# ... analyze and print ...
```

**Expected Output Snippet:**

```
--- Results Summary: Test 7: Fin Analyst (UULE London) ---
  API Status: Success
  Jobs Found This Page: 0
  No job results found on this page.
-----------------------------------------------------
```

### Example 8: Async Request

```python
print("--- Test 8: Async Parameter Demonstration ---")
test8_raw = client.search(
    query="Data Engineer",
    location="Chicago, IL",
    other_params={"async": "true"} # Pass async via other_params
)
# ... analyze and print special async summary ...
```

**Expected Output Snippet:**

```
--- Async Request Submission Result --- 
  API Status: Success # Note: API returns success on *submission*
  Search ID submitted for async processing: 67f514ec067f9670d1e55c9f # Example ID
  (Full job results would need to be retrieved later using the Search Archive API)
-----------------------------------
```

### Example 9: HTML Output

```python
print("--- Test 9: HTML Output Parameter Demonstration ---")
test9_raw = client.search(
    query="UX Designer",
    location="New York, NY", # Using a location known to work with output=html
    other_params={"output": "html"} # Pass output=html via other_params
)
# ... analyze and print special HTML summary ...
```

**Expected Output Snippet:**

```
--- Results Summary: Test 9: UX Designer (HTML Output - NY) ---
  API Status: Success_HTML_Received
  Received non-JSON content as requested. No job summaries to display.
----------------------------------------------------------

  Received HTML Content Snippet (first 200 chars):
<!doctype html><html itemscope="" itemtype="http://schema.org/SearchResultsPage" lang="en"><head>
<meta http-equiv="Content-Security-Policy" content="connect-src 'none';">
<base href="https://www.goog...
-----------------------------------
```

## Running the Demo Script

You can run the entire test suite included in the `test_serpapi_google_jobs.py` file directly from your terminal:

```bash
python apps/mcg/test_serpapi_google_jobs.py
```

This will execute all the examples shown above and print detailed logs and results summaries to your console.

## Error Handling

*   Network errors (timeouts, connection issues) and API errors (bad requests, invalid keys) are caught.
*   Error messages are printed to the console (`stderr` implicitly).
*   The `search` and `_make_request` methods return `None` upon failure. The `search_paginated` method returns an empty list if errors occur during pagination.
*   Check the console output for `ERROR:` or `WARN:` prefixes for details when troubleshooting.
