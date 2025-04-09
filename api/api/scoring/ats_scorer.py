import re
import string
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import json
import logging
import math
from datetime import datetime, timezone
import calendar
from accelerate import init_empty_weights

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

MONTH_MAP = {name.lower(): num for num, name in enumerate(calendar.month_name) if name}
MONTH_MAP.update({abbr.lower(): num for num, abbr in enumerate(calendar.month_abbr) if abbr})

def parse_duration(duration_str):
    years = 0
    months = 0
    try:
        year_match = re.search(r'(\d+)\s+years?', duration_str, re.IGNORECASE)
        if year_match:
            years = int(year_match.group(1))
        month_match = re.search(r'(\d+)\s+months?', duration_str, re.IGNORECASE)
        if month_match:
            months = int(month_match.group(1))
        total_years = years + (months / 12.0)
        return total_years
    except Exception as e:
        logger.warning(f"Could not parse duration string '{duration_str}': {e}")
        return 0

def parse_date_string(date_str):
    date_str = date_str.strip().lower()
    year, month = None, None
    match = re.match(r'(\d{4})[/-](\d{1,2})', date_str)
    if match:
        year, month = int(match.group(1)), int(match.group(2))
        return year, month
    match = re.match(r'([a-z]+)\s+(\d{4})', date_str)
    if match:
        month_name = match.group(1)
        month = MONTH_MAP.get(month_name)
        if month:
            year = int(match.group(2))
            return year, month
    match = re.match(r'^(\d{4})$', date_str)
    if match:
        year = int(match.group(1))
        return year, 12
    logger.warning(f"Could not parse date string: {date_str}")
    return None, None

def calculate_years_from_dates(start_str, end_str):
    try:
        if end_str.strip().lower() == 'present':
            end_date_dt = datetime.now()
        else:
            year_end, month_end = parse_date_string(end_str)
            if not year_end:
                return 0
            month_end_calc = month_end + 1
            year_end_calc = year_end
            if month_end_calc > 12:
                month_end_calc = 1
                year_end_calc += 1
            try:
                end_date_dt = datetime(year_end_calc, month_end_calc, 1)
            except ValueError:
                logger.warning(f"Invalid date created for end date {end_str}, using year end: {year_end}-12-31")
                end_date_dt = datetime(year_end, 12, 31)
        year_start, month_start = parse_date_string(start_str)
        if not year_start:
            return 0
        try:
            start_date_dt = datetime(year_start, month_start, 1)
        except ValueError:
            logger.warning(f"Invalid date created for start date {start_str}, using year start: {year_start}-01-01")
            start_date_dt = datetime(year_start, 1, 1)
        if end_date_dt < start_date_dt:
            logger.warning(f"End date {end_str} is before start date {start_str}")
            return 0
        delta = end_date_dt - start_date_dt
        total_years = delta.days / 365.25
        logger.debug(f"Calculated years between '{start_str}' and '{end_str}' as {total_years:.2f}")
        return total_years
    except Exception as e:
        logger.error(f"Error calculating years from dates ('{start_str}' to '{end_str}'): {e}")
        return 0

class ATSScorer:
    def __init__(self, config=None):
        self.config = config or {
            'weights': {
                'keyword_match': 0.20,
                'skill_match': 0.35,
                'semantic_match': 0.20,
                'experience_match': 0.15,
                'education_match': 0.10
            },
            'models': {
                'embedding': 'all-MiniLM-L6-v2',
                'spacy': 'en_core_web_lg'
            }
        }
        logger.info("Initializing ATS scoring engine...")
        self.nlp = spacy.load(self.config['models']['spacy'])
        self.stop_words = set(stopwords.words('english'))
        self.tfidf_vectorizer = TfidfVectorizer(
            stop_words='english',
            min_df=1,
            max_df=0.85,
            ngram_range=(1, 2)
        )
        logger.info(f"Loading sentence transformer model: {self.config['models']['embedding']}")
        self.sentence_transformer = SentenceTransformer(self.config['models']['embedding'])
        logger.info("ATS scoring engine initialized successfully")
    
    def preprocess_text(self, text):
        if not text:
            return ""
        text = text.lower()
        text = re.sub(f'[{string.punctuation}]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def extract_skills_from_text(self, text, skill_list=None):
        if not text:
            return set()
        if skill_list:
            found_skills = set()
            text_lower = text.lower()
            for skill in skill_list:
                if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text_lower):
                    found_skills.add(skill.lower())
            return found_skills
        return set()
    
    def extract_required_skills(self, jd_text):
        required_skills = set()
        preferred_skills = set()
        req_pattern = r'(?:requirements|qualifications|what you\'ll need|required skills|we require)(?:[\s\S]*?)(?:preferred|nice to have|bonus|benefits|why join|about us|$)'
        req_match = re.search(req_pattern, jd_text.lower(), re.IGNORECASE)
        pref_pattern = r'(?:preferred|nice to have|bonus points|plus|additionally)(?:[\s\S]*?)(?:benefits|why join|about us|$)'
        pref_match = re.search(pref_pattern, jd_text.lower(), re.IGNORECASE)
        if req_match:
            req_text = req_match.group(0)
            skill_items = re.findall(r'(?:•|○|◦|▪|■|⦁|►|[\d]+\.)\s*(.*?)(?=(?:•|○|◦|▪|■|⦁|►|[\d]+\.)|$)', req_text)
            if skill_items:
                for item in skill_items:
                    phrases = re.findall(r'\b[A-Za-z]+(?:\s+[A-Za-z]+){0,2}\b', item)
                    for phrase in phrases:
                        if len(phrase) > 3 and phrase.lower() not in self.stop_words:
                            required_skills.add(phrase.lower())
        if pref_match:
            pref_text = pref_match.group(0)
            skill_items = re.findall(r'(?:•|○|◦|▪|■|⦁|►|[\d]+\.)\s*(.*?)(?=(?:•|○|◦|▪|■|⦁|►|[\d]+\.)|$)', pref_text)
            if skill_items:
                for item in skill_items:
                    phrases = re.findall(r'\b[A-Za-z]+(?:\s+[A-Za-z]+){0,2}\b', item)
                    for phrase in phrases:
                        if len(phrase) > 3 and phrase.lower() not in self.stop_words:
                            preferred_skills.add(phrase.lower())
        return required_skills, preferred_skills
    
    def calculate_keyword_match(self, resume_text, jd_text):
        resume_clean = self.preprocess_text(resume_text)
        jd_clean = self.preprocess_text(jd_text)
        if not resume_clean or not jd_clean:
            logger.info("Keyword match: 0.0 (missing text)")
            return 0.0
        try:
            vectorizer = TfidfVectorizer(
                stop_words='english',
                min_df=1,
                ngram_range=(1, 2)
            )
            corpus = [resume_clean, jd_clean]
            tfidf_matrix = vectorizer.fit_transform(corpus)
            if tfidf_matrix.shape[0] < 2 or tfidf_matrix.shape[1] == 0:
                logger.info("Keyword match: 0.0 (empty vocabulary or matrix)")
                return 0.0
            cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            keyword_score = max(0.0, min(cosine_sim, 1.0))
            logger.info(f"Keyword match (TF-IDF Cosine Sim): {keyword_score:.2f}")
        except Exception as e:
            logger.error(f"Error calculating keyword match: {e}")
            keyword_score = 0.0
        return keyword_score
    
    def calculate_skill_match(self, resume_skills, jd_required_skills, jd_preferred_skills):
        if not resume_skills:
            return 0.0, [], list(jd_required_skills), list(jd_preferred_skills)
        if not jd_required_skills and not jd_preferred_skills:
            return 1.0, list(resume_skills), [], []
        resume_skills_lower = {s.lower() for s in resume_skills}
        req_skills_lower = {s.lower() for s in jd_required_skills}
        pref_skills_lower = {s.lower() for s in jd_preferred_skills}
        req_matched = resume_skills_lower.intersection(req_skills_lower)
        pref_matched = resume_skills_lower.intersection(pref_skills_lower)
        missing_req = req_skills_lower - resume_skills_lower
        missing_pref = pref_skills_lower - resume_skills_lower
        req_weight = 0.8
        pref_weight = 0.2
        if req_skills_lower:
            req_score = len(req_matched) / len(req_skills_lower)
        else:
            req_score = 1.0
        if pref_skills_lower:
            pref_score = len(pref_matched) / len(pref_skills_lower)
        else:
            pref_score = 1.0
        skill_score = (req_weight * req_score) + (pref_weight * pref_score)
        logger.info(f"Skill match: Required={req_score:.2f}, Preferred={pref_score:.2f}, Combined={skill_score:.2f}")
        logger.info(f"Matched {len(req_matched)}/{len(req_skills_lower)} required skills")
        logger.info(f"Matched {len(pref_matched)}/{len(pref_skills_lower)} preferred skills")
        matched_skills = list(req_matched.union(pref_matched))
        return skill_score, matched_skills, list(missing_req), list(missing_pref)
    
    def calculate_semantic_match(self, resume_text, jd_text):
        if not resume_text or not jd_text:
            return 0.0
        resume_embedding = self.sentence_transformer.encode(resume_text, convert_to_tensor=True)
        jd_embedding = self.sentence_transformer.encode(jd_text, convert_to_tensor=True)
        from torch import nn
        cos = nn.CosineSimilarity(dim=0)
        similarity = cos(resume_embedding, jd_embedding).item()
        similarity = max(0, min(similarity, 1.0))
        logger.info(f"Semantic match score: {similarity:.2f}")
        return similarity
    
    def extract_years_of_experience(self, text):
        required_patterns = [
            r'(\d+)\s*-\s*(\d+)\s*years?',
            r'(?:minimum|at least|requires?).*?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?(?:\s+of)?\s+(?:\w+\s+)?(?:experience|professional|relevant|industry)\s*(?:required|needed)?',
            r'(\d+)\+?\s*years?',
        ]
        max_years = 0
        min_years_range = 0
        text_lower = text.lower()
        logger.debug(f"Attempting to extract experience from text: {text_lower[:500]}...")
        found_match = False
        for pattern in required_patterns:
            years_found_in_pattern = []
            try:
                matches = re.findall(pattern, text_lower)
                if matches:
                    logger.debug(f"Pattern '{pattern}' found matches: {matches}")
                    found_match = True
                    for match in matches:
                        years = 0
                        if isinstance(match, tuple) and len(match) == 2 and match[0].isdigit() and match[1].isdigit():
                            min_years_range = int(match[0])
                            years = int(match[0])
                            logger.debug(f"Extracted range: {match}, using lower bound: {years}")
                        elif isinstance(match, tuple) and len(match) > 0 and match[0].isdigit():
                            years = int(match[0])
                        elif isinstance(match, str) and match.isdigit():
                            years = int(match)
                        else:
                            continue
                        if years > 0:
                            logger.debug(f"Extracted years: {years} from match: {match} using pattern: {pattern}")
                            years_found_in_pattern.append(years)
                    if years_found_in_pattern:
                        max_years = max(years_found_in_pattern)
                        logger.debug(f"Using max_years={max_years} from pattern '{pattern}' and stopping search.")
                        break
            except re.error as e:
                logger.warning(f"Regex error in extract_years_of_experience: {e} for pattern {pattern}")
                continue
        if not found_match:
            logger.debug("No experience year patterns matched.")
        if max_years > 30:
            logger.warning(f"Extracted unusually high experience years ({max_years}), capping at 30.")
            max_years = 30
        logger.debug(f"Final extracted max_years: {max_years}")
        return max_years
    
    def calculate_experience_match(self, resume_data, job_data):
        jd_years_required = self.extract_years_of_experience(job_data.get('raw_text', ''))
        logger.debug(f"JD requires ~{jd_years_required} years based on text extraction.")
        
        # Initialize years calculated from different sources
        years_from_structured_dates = 0
        # years_from_duration = 0 # Keep commented if duration field not used from DB
        # years_from_raw_text = 0 # Keep commented if we prioritize structured data

        # --- NEW LOGIC: Prioritize structured start_date/end_date from DB --- START ---
        if 'experience' in resume_data and isinstance(resume_data['experience'], list):
            logger.debug("Attempting experience calculation from structured start_date/end_date fields...")
            calculated_total_duration = 0
            now = datetime.now(timezone.utc)

            for job in resume_data['experience']:
                if isinstance(job, dict):
                    start_date_str = job.get('start_date')
                    end_date_str = job.get('end_date') # Can be None or date string

                    if start_date_str: # Must have a start date
                        try:
                            # Replace Z with +00:00 for better fromisoformat compatibility
                            start_iso_str = start_date_str.replace('Z', '+00:00')
                            start_date_dt = datetime.fromisoformat(start_iso_str)

                            if end_date_str:
                                end_iso_str = end_date_str.replace('Z', '+00:00')
                                end_date_dt = datetime.fromisoformat(end_iso_str)
                            else:
                                # If end_date is None or empty string, assume 'Present'
                                # Make 'now' timezone-aware (UTC) for consistent comparison
                                now = datetime.now(timezone.utc)
                                end_date_dt = now

                            # Ensure both dates are timezone-aware (UTC) or both naive before comparison
                            # fromisoformat with +00:00 makes them aware.
                            # If start_date was naive and end_date is aware 'now', make start_date aware.
                            # (This part might need refinement based on actual data variance,
                            # but assuming ISO format with Z or None/Present is the primary case)

                            if end_date_dt >= start_date_dt:
                                delta = end_date_dt - start_date_dt
                                duration = delta.days / 365.25 # Approximate years
                                logger.debug(f"  Calculated duration {duration:.2f} years for job '{job.get('position')}' ({start_date_str} to {end_date_str or 'Present'}).")
                                calculated_total_duration += duration
                            else:
                                logger.warning(f"  End date {end_date_str} is before start date {start_date_str} for job '{job.get('position')}. Skipping duration.")

                        except ValueError as date_err:
                            # Keep the original warning if fromisoformat fails
                            logger.warning(f"  Could not parse ISO date for job '{job.get('position')}': '{start_date_str}' or '{end_date_str}'. Error: {date_err}")
                        except Exception as e:
                             logger.error(f"  Unexpected error processing dates for job '{job.get('position')}': {e}")
                    else:
                         logger.warning(f"  Missing start_date for job '{job.get('position')}'. Skipping duration calculation.")
            
            if calculated_total_duration > 0:
                years_from_structured_dates = math.floor(calculated_total_duration)
                logger.debug(f"Total experience from structured start/end dates: {years_from_structured_dates} years (floored).")
            else:
                 logger.debug("Could not calculate any duration from structured start/end dates.")
        # --- NEW LOGIC: Prioritize structured start_date/end_date from DB --- END ---

        # --- ORIGINAL LOGIC (Commented out or used as fallback) --- START ---
        # Original logic tried parsing 'dates' string and 'duration' string
        # We can keep it commented out if the new logic is sufficient
        # Or add it as a fallback if years_from_structured_dates is 0
        '''
        years_from_dates_string_parse = 0 # Original variable name
        if years_from_structured_dates == 0 and 'experience' in resume_data and isinstance(resume_data['experience'], list):
            logger.debug("Fallback: Attempting experience calculation from legacy 'dates' string parsing...")
            calculated_total_duration = 0
            date_separators = r'\s+(?:to|-|until|–)\s+'
            for job in resume_data['experience']:
                if isinstance(job, dict) and 'dates' in job and isinstance(job['dates'], str):
                    date_parts = re.split(date_separators, job['dates'], maxsplit=1)
                    if len(date_parts) == 2:
                        start_str, end_str = date_parts[0].strip(), date_parts[1].strip()
                        duration = calculate_years_from_dates(start_str, end_str) # Uses the old helper
                        if duration > 0:
                            logger.debug(f" Calculated duration {duration:.2f} years for legacy 'dates': '{job['dates']}'.")
                            calculated_total_duration += duration
                        else:
                            logger.warning(f"Could not calculate valid duration for legacy dates string: {job['dates']}")
                    else:
                        logger.warning(f"Could not split legacy dates string '{job['dates']}' into start/end using separators: {date_separators}")
            if calculated_total_duration > 0:
                years_from_dates_string_parse = math.floor(calculated_total_duration)
                logger.debug(f"Total experience from legacy 'dates' string parsing: {years_from_dates_string_parse} years (floored).")

        years_from_duration_field = 0 # Original variable name
        if years_from_structured_dates == 0 and years_from_dates_string_parse == 0 and 'experience' in resume_data and isinstance(resume_data['experience'], list):
            logger.debug("Fallback: Attempting experience calculation from legacy 'duration' fields...")
            calculated_total_duration = 0
            for job in resume_data['experience']:
                if isinstance(job, dict) and 'duration' in job:
                    duration_years = parse_duration(job['duration']) # Uses the old helper
                    if duration_years > 0:
                        logger.debug(f" Parsed legacy duration field '{job['duration']}' as {duration_years:.2f} years.")
                        calculated_total_duration += duration_years
            if calculated_total_duration > 0:
                years_from_duration_field = math.floor(calculated_total_duration)
                logger.debug(f"Total experience from legacy 'duration' fields: {years_from_duration_field} years (floored).")
        '''
        # --- ORIGINAL LOGIC (Commented out or used as fallback) --- END ---

        # --- Fallback to Raw Text Extraction (Optional) ---
        # Only use if structured data yields 0 years
        years_from_raw_text_extract = 0
        if years_from_structured_dates == 0: # and years_from_dates_string_parse == 0 and years_from_duration_field == 0:
            logger.debug("Fallback: Attempting experience calculation from resume raw text extraction...")
            years_from_raw_text_extract = self.extract_years_of_experience(resume_data.get('raw_text', ''))
            logger.debug(f"Experience years found in resume raw text: {years_from_raw_text_extract}")

        # --- Determine Final Resume Years --- #
        # Prioritize the calculation from structured start/end dates
        resume_total_years = max(years_from_structured_dates, years_from_raw_text_extract)
        # If using other fallbacks, include them in max():
        # resume_total_years = max(years_from_structured_dates, years_from_dates_string_parse, years_from_duration_field, years_from_raw_text_extract)

        logger.info(f"Experience: JD requires ~{jd_years_required} years. Resume best estimate: ~{resume_total_years} years (from structured dates: {years_from_structured_dates}, from raw text: {years_from_raw_text_extract})")

        # --- Calculate Score --- #
        if jd_years_required == 0:
            # If JD doesn't specify years, assume candidate meets requirement
            logger.info("JD does not specify required years of experience. Score: 1.0")
            return 1.0
        
        if resume_total_years == 0:
            logger.warning("Could not determine resume years of experience from any reliable source.")
            # Assign a low score if JD requires experience but resume shows none
            return 0.1 

        # Calculate score based on ratio, capping at 1.0
        if resume_total_years >= jd_years_required:
            score = 1.0
        else:
            score = resume_total_years / jd_years_required 
        
        score = max(0.0, min(score, 1.0)) # Ensure score is between 0 and 1
        logger.info(f"Experience score: {resume_total_years} / {jd_years_required} = {score:.2f}")
        return score
    
    def extract_education_level(self, text):
        education_patterns = [
            (r'\bph\.?d\.?\b|\bdoctorate?\b|doctoral', 5),
            (r'\bj\.?d\.?\b|juris doctor', 5),
            (r'\bm\.?d\.?\b|doctor of medicine', 5),
            (r'\bmaster\'?s?\b|\bm\.?s\.?\b|\bm\.?a\.?\b|\bm\.?b\.?a\.?\b|\bm\.?eng\b|(?<!under)graduate\s+(?:degree|diploma|program)', 4),
            (r'\bbachelor\'?s?\b|\bb\.?s\.?\b|\bb\.?a\.?\b|\bb\.?eng\b|undergraduate\s+(?:degree|diploma|program)', 3),
            (r'\bassociate\'?s?\b|\ba\.?a\.?\b|\ba\.?s\.?\b|some college|college credit', 2),
            (r'\bhigh\s*school\b|secondary\s*education|\bged\b', 1)
        ]
        highest_level = 0
        matched_text = ""
        text_lower = text.lower()
        logger.debug(f"Attempting to extract education level from text: {text_lower[:500]}...")
        for pattern, level in education_patterns:
            try:
                match = re.search(pattern, text_lower)
                if match:
                    current_match_text = match.group(0)
                    logger.debug(f"Level {level} pattern '{pattern}' matched text: '{current_match_text}'")
                    if level > highest_level:
                        highest_level = level
                        matched_text = current_match_text
                        logger.debug(f"Updated highest_level to {highest_level} based on '{matched_text}'")
                        if highest_level == 5:
                            break
            except re.error as e:
                logger.warning(f"Regex error in extract_education_level: {e} for pattern {pattern}")
                continue
        if matched_text:
             logger.debug(f"Final education level {highest_level} detected based on: '{matched_text}'")
        else:
             logger.debug("No specific education level detected.")
        return highest_level
    
    def calculate_education_match(self, resume_text, jd_text):
        jd_education_level = self.extract_education_level(jd_text)
        resume_education_level = self.extract_education_level(resume_text)
        logger.info(f"Education: JD requires level ~{jd_education_level}, Resume text shows level ~{resume_education_level}")
        if jd_education_level == 0:
            return 1.0
        if resume_education_level == 0:
            logger.warning("Resume text does not clearly indicate education level.")
            return 0.1
        if resume_education_level >= jd_education_level:
            return 1.0
        else:
            logger.warning(f"Candidate education level ({resume_education_level}) is below required ({jd_education_level})")
            return 0.2
    
    def score_resume(self, resume_data, job_data):
        logger.info("Scoring resume against job description...")
        resume_text = resume_data.get('raw_text', '')
        jd_text = job_data.get('raw_text', '')
        if not resume_text or not jd_text:
            logger.error("Missing raw text data for resume or job description")
            return {
                'overall_score': 0,
                'error': 'Missing text data'
            }
        resume_skills = set(resume_data.get('skills', []))
        jd_required_skills = set(job_data.get('required_skills', []))
        jd_preferred_skills = set(job_data.get('preferred_skills', []))
        if not resume_skills:
            resume_skills = self.extract_skills_from_text(resume_text)
        if not jd_required_skills or not jd_preferred_skills:
            jd_required_skills, jd_preferred_skills = self.extract_required_skills(jd_text)
        keyword_score = self.calculate_keyword_match(resume_text, jd_text)
        skill_score, matched_skills, missing_req_skills, missing_pref_skills = self.calculate_skill_match(
            resume_skills, jd_required_skills, jd_preferred_skills
        )
        semantic_score = self.calculate_semantic_match(resume_text, jd_text)
        experience_score = self.calculate_experience_match(resume_data, job_data)
        education_score = self.calculate_education_match(resume_text, jd_text)
        weights = self.config['weights']
        overall_score = (
            weights['keyword_match'] * keyword_score +
            weights['skill_match'] * skill_score +
            weights['semantic_match'] * semantic_score +
            weights['experience_match'] * experience_score +
            weights['education_match'] * education_score
        )
        overall_score = max(0, min(overall_score, 1.0))
        percentage_score = int(overall_score * 100)
        logger.info(f"Final ATS match score: {percentage_score}%")
        result = {
            'overall_score': percentage_score,
            'component_scores': {
                'keyword_match': int(keyword_score * 100),
                'skill_match': int(skill_score * 100),
                'semantic_match': int(semantic_score * 100),
                'experience_match': int(experience_score * 100),
                'education_match': int(education_score * 100)
            },
            'skill_analysis': {
                'matched_skills': matched_skills,
                'missing_required_skills': missing_req_skills,
                'missing_preferred_skills': missing_pref_skills
            }
        }
        return result 