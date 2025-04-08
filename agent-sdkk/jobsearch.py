import asyncio
import os
import json # Added for potentially richer error details if needed
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import sys # Import sys for flushing output

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
    # Assuming test_serpapi_google_jobs.py is in the same directory
    from test_serpapi_google_jobs import SerpApiGoogleJobsClient, analyze_response, print_job_summary
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

    Use this tool whenever a user asks to find jobs, look for job openings, or similar requests about employment opportunities.

    Args:
        query: The job title, keywords, or company to search for (e.g., 'Python Developer', 'Software Engineer remote', 'Data Scientist at Google'). This is mandatory.
        location: The city, state, or country to search within (e.g., 'London, UK', 'Austin, Texas', 'Canada'). This is optional. If the user specifies a location, include it. Only include location if explicitly mentioned.
    """
    print(f"\n--- Calling SerpApi Tool ---")
    print(f"   Query: {query}")
    print(f"   Location: {location if location else 'Not specified'}")
    sys.stdout.flush() # Ensure prints appear before potential delays

    # Instantiate client here - consider moving instantiation outside if performance becomes an issue
    client = SerpApiGoogleJobsClient(api_key=SERP_API_KEY)
    try:
        # Use the client's search method
        # Note: The original client's search method does *not* return the processed job list directly.
        # We need to call analyze_response or process results manually here.
        raw_results = client.search(query=query, location=location)

        # --- Process Results ---
        if not raw_results:
             print("   SerpApi returned no result.")
             return "The job search API returned no results. Please try asking differently or with a different location."

        # Use analyze_response or similar logic to check status and extract jobs
        # Let's simplify and check the raw dictionary directly for 'jobs_results'
        api_status = raw_results.get("search_metadata", {}).get("status")
        job_results = raw_results.get("jobs_results", [])

        if api_status == "Success" and job_results:
            # Create a concise summary including links
            summary = f"Okay, I found {len(job_results)} job(s) matching '{query}'"
            if location:
                summary += f" in '{location}'"
            summary += ". Here are the top results I could retrieve:\n\n"

            for i, job in enumerate(job_results[:5]): # Show top 5 with links
                title = job.get('title', 'N/A')
                company = job.get('company_name', 'N/A')
                loc = job.get('location', 'N/A')
                # Corrected link extraction: Use 'share_link' based on test_serpapi_google_jobs.py
                google_link = job.get('share_link', 'No direct link found') 

                detected_extensions = job.get('detected_extensions', {})
                posted_at = detected_extensions.get('posted_at', 'N/A')
                schedule_type = detected_extensions.get('schedule_type', 'N/A')

                summary += f"{i+1}. {title} at {company} ({loc})\n"
                summary += f"   - Posted: {posted_at}, Type: {schedule_type}\n"
                summary += f"   - Link: {google_link}\n\n" # Add the Google link

            if len(job_results) > 5:
                summary += "  ... (more results might be available)\n"

            print(f"   SerpApi call successful. Returning summary with links.")
            return summary.strip()

        elif api_status == "Success" and not job_results:
            print("   SerpApi returned Success but no job listings found.")
            return f"I couldn't find any job listings matching '{query}'" + (f" in '{location}'." if location else ".")

        else:
            # Handle API errors reported by SerpApi
            error_message = raw_results.get("search_metadata", {}).get("error", "Unknown API error occurred")
            print(f"   SerpApi returned an error: {error_message}")
            return f"Sorry, the job search failed. The API reported: {error_message}"

    except requests.exceptions.RequestException as req_err:
        error_details = f"Network error connecting to SerpApi: {str(req_err)}"
        print(f"   ERROR: {error_details}")
        return f"Sorry, I couldn't connect to the job search service right now. Please try again later."
    except Exception as e:
        # Catch other potential exceptions during client interaction or result processing
        error_details = f"An unexpected error occurred while searching for jobs: {str(e)}"
        print(f"   ERROR: {error_details}")
        return f"Sorry, an unexpected error occurred. I couldn't complete the job search."
    finally:
        print(f"--- Finished SerpApi Tool Call ---")
        sys.stdout.flush()


# --- Agent Definition ---
job_search_agent = Agent(
   name="JobSearchPal",
   instructions="""You are JobSearchPal, a friendly and helpful AI assistant specializing in finding job opportunities.

   Your primary goal is to understand the user's job search requirements (like job title, skills, company, location) and use the `search_jobs_via_serpapi` tool to find relevant listings.

   **Interaction Flow:**
   1.  Start the conversation with a friendly greeting and ask the user what kind of job they are looking for. For example: "Hi there! I'm JobSearchPal. What kind of job are you looking for today?"
   2.  Analyze the user's request. If it's about finding jobs, identify the core query (job title, keywords) and any specified location.
   3.  Call the `search_jobs_via_serpapi` tool with the extracted `query` (mandatory) and `location` (optional). Be precise with the arguments passed to the tool based *only* on the user's request. Do not guess locations if not provided.
   4.  Once the tool returns results (a summary string with job details and links), present this information clearly and directly to the user.
   5.  If the tool reports an error or finds no results, inform the user politely and explain the situation based on the tool's message.
   6.  If the user asks a question not related to job searching, politely state that your expertise is in finding job listings and you cannot help with other topics.
   7.  Continue the conversation, asking if they need help with another search or if the results were helpful.

   **Important:**
   - Only use the provided tool for job searches.
   - Do not make up information or job listings. Rely solely on the tool's output.
   - Keep your responses focused and related to the job search task.
   """,
   tools=[search_jobs_via_serpapi],
   model="gpt-4o", # Using a capable model is good for instruction following
   model_settings=ModelSettings(temperature=0.3) # Slightly creative but still focused
)


# --- Interactive Chat Loop ---
async def interactive_chat():
    print("Initializing JobSearchPal...")
    runner = Runner() # Initialize runner once

    # Initial greeting from the agent (can be triggered by an empty initial message)
    # Or print a static greeting here
    print("-" * 30)
    print("JobSearchPal: Hi there! I'm JobSearchPal. What kind of job are you looking for today? (Type 'quit' or 'exit' to end)")
    print("-" * 30)

    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                print("JobSearchPal: Goodbye! Happy job hunting!")
                break
            if not user_input:
                continue

            print("JobSearchPal: Thinking...", end='\r') # Indicate activity
            sys.stdout.flush()

            # Run the agent with the user's input
            result = await runner.run(job_search_agent, user_input)

            # Clear the "Thinking..." message
            print(" " * 20, end='\r')
            sys.stdout.flush()

            # Print the agent's final response
            if result and hasattr(result, 'final_output'):
                print(f"JobSearchPal: {result.final_output}")
            else:
                print("JobSearchPal: Sorry, I encountered an issue and couldn't get a response.")

        except KeyboardInterrupt:
            print("\nJobSearchPal: Goodbye! Happy job hunting!")
            break
        except Exception as e:
            print(f"\nAn error occurred in the chat loop: {e}")
            # Optionally break or try to continue
            break # Safer to exit on unexpected loop errors


async def main():
    # Start the interactive chat
    await interactive_chat()


if __name__ == "__main__":
    # Ensure requests is installed as it's used by the SerpApi client
    try:
        import requests
    except ImportError:
        print("Please install the 'requests' library: pip install requests")
        exit()

    print("Starting interactive job search agent...")
    asyncio.run(main())