# /Users/sanchaythalnerkar/Downloads/mcg-django/agent-sdkk/job_search_agent.py
import asyncio
import os
import json # Added for potentially richer error details if needed
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Import the necessary components from the Agents SDK
# Assuming 'agents' is the library name based on the docs
# You might need to install it: pip install agents-sdk (or similar)
try:
    from agents import Agent, Runner, function_tool, ModelSettings
except ImportError:
    print("Please install the OpenAI Agents SDK library (e.g., 'pip install agents-sdk')")
    exit()

# Import the SerpApi client from your existing script
try:
    from test_serpapi_google_jobs import SerpApiGoogleJobsClient
except ImportError:
    print("Could not import SerpApiGoogleJobsClient from test_serpapi_google_jobs.py")
    print("Ensure the file exists in the same directory or adjust the import path.")
    exit()

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    exit()
if not SERP_API_KEY:
    print("Error: SERP_API_KEY environment variable not set.")
    exit()

# --- Tool Definition ---

@function_tool
def search_jobs_via_serpapi(query: str, location: Optional[str] = None) -> str:
    """
    Searches for job listings using the SerpApi Google Jobs service based on a query and optional location.

    Use this tool whenever a user asks to find jobs, look for job openings, or similar requests.

    Args:
        query: The job title, keywords, or company to search for (e.g., 'Python Developer', 'Software Engineer remote', 'Data Scientist at Google'). This is mandatory.
        location: The city, state, or country to search within (e.g., 'London, UK', 'Austin, Texas', 'Canada'). This is optional. If the user specifies a location, include it.
    """
    print(f"--- Calling SerpApi Tool ---")
    print(f"   Query: {query}")
    print(f"   Location: {location}")

    client = SerpApiGoogleJobsClient(api_key=SERP_API_KEY) # Instantiate client here for simplicity
    try:
        # Use the client's search method
        results = client.search(query=query, location=location)

        # --- Process Results ---
        if not results:
             print("   SerpApi returned no result.")
             return "The job search API returned no results. Please try again."

        search_metadata = results.get("search_metadata", {})
        api_status = search_metadata.get("status")

        if api_status == "Success":
            job_results = results.get("jobs_results", [])
            if not job_results:
                print("   SerpApi returned Success but no job listings found.")
                return f"No job listings found for '{query}'" + (f" in '{location}'." if location else ".")

            # Create a concise summary
            summary = f"Found {len(job_results)} jobs matching '{query}'"
            if location:
                summary += f" in '{location}'"
            summary += ". Here are the top results:\n"

            for i, job in enumerate(job_results[:5]): # Show top 5
                title = job.get('title', 'N/A')
                company = job.get('company_name', 'N/A')
                loc = job.get('location', 'N/A')
                via = job.get('via', 'N/A')
                detected_extensions = job.get('detected_extensions', {})
                posted_at = detected_extensions.get('posted_at', 'N/A')
                schedule_type = detected_extensions.get('schedule_type', 'N/A')

                summary += f"  {i+1}. {title} at {company} ({loc})\n"
                summary += f"     Posted: {posted_at}, Type: {schedule_type}, Via: {via}\n"

            if len(job_results) > 5:
                summary += "  ...\n"

            # Optionally add link to full results if available
            search_info = results.get("search_information", {})
            if search_info.get("jobs_results_page_url"):
                 summary += f"\nView full results page: {search_info['jobs_results_page_url']}\n"

            print(f"   SerpApi call successful. Returning summary.")
            return summary.strip()

        else:
            # Handle API errors reported by SerpApi
            error_message = search_metadata.get("error", "Unknown API error")
            print(f"   SerpApi returned an error: {error_message}")
            return f"Job search failed. API Error: {error_message}"

    except requests.exceptions.RequestException as req_err:
        error_details = f"Network error connecting to SerpApi: {str(req_err)}"
        print(f"   ERROR: {error_details}")
        return f"Job search failed: {error_details}"
    except Exception as e:
        # Catch other potential exceptions during client interaction or result processing
        error_details = f"An unexpected error occurred during job search: {str(e)}"
        print(f"   ERROR: {error_details}")
        return f"Job search failed: {error_details}"
    finally:
        print(f"--- Finished SerpApi Tool Call ---")


# --- Agent Definition ---
job_search_agent = Agent(
   name="JobSearchAssistant",
   instructions="""You are a helpful job search assistant. Your goal is to help users find job listings.

   When a user asks you to find jobs, search for job openings, or asks about specific roles or companies in certain locations, use the `search_jobs_via_serpapi` tool.

   Provide the required `query` argument to the tool based on the user's request (e.g., job title, skills, company).
   If the user specifies a location, provide it as the `location` argument. If not, call the tool without the location.

   After the tool returns the results, present them clearly to the user.
   If the tool reports an error or no results, inform the user politely.
   Do not make up job listings. Only report what the tool finds.
   Keep your responses concise and focused on the job search task.
   """,
   tools=[search_jobs_via_serpapi],
   model="gpt-4o", # Or another suitable model like gpt-3.5-turbo
   # model_settings=ModelSettings(temperature=0.2) # Optional: Adjust creativity
)


# --- Agent Execution ---
async def run_job_search(user_query: str):
    print(f"\n--- Running Agent for Query: '{user_query}' ---")
    # The Runner typically handles the interaction flow including tool calls
    # Based on the docs, Runner might manage the output verbosity.
    # We added print statements in the tool function for explicit confirmation.
    result = await Runner.run(job_search_agent, user_query)

    print("\n--- Agent Final Output ---")
    # The final output from the agent after processing tool results (or answering directly)
    if result and hasattr(result, 'final_output'):
         print(result.final_output)
    else:
         print("Agent did not produce a final output.")
    print("-" * 26)


async def main():
    # Example queries to test the agent
    await run_job_search("Find me Python developer jobs in London")
    await run_job_search("Are there any remote Data Scientist roles available?")
    await run_job_search("What about marketing manager positions in New York City?")
    await run_job_search("Tell me a joke about programming") # Test non-tool query


if __name__ == "__main__":
    # Ensure requests is installed as it's used by the SerpApi client
    try:
        import requests
    except ImportError:
        print("Please install the 'requests' library: pip install requests")
        exit()

    asyncio.run(main())