from rest_framework.throttling import AnonRateThrottle

class EnhanceWorkExperienceRateThrottle(AnonRateThrottle):
    """
    Throttle for enhance_work_experience endpoint - 10 requests per hour per IP.
    """
    scope = 'enhance_work_experience'

class EnhanceProjectRateThrottle(AnonRateThrottle):
    """
    Throttle for enhance_project endpoint - 10 requests per hour per IP.
    """
    scope = 'enhance_project'

class EnhanceCertificationRateThrottle(AnonRateThrottle):
    """
    Throttle for enhance_certification endpoint - 10 requests per hour per IP.
    """
    scope = 'enhance_certification'

class EnhanceCustomSectionItemRateThrottle(AnonRateThrottle):
    """
    Throttle for enhance_custom_section_item endpoint - 10 requests per hour per IP.
    """
    scope = 'enhance_custom_section_item'

class SuggestSkillsRateThrottle(AnonRateThrottle):
    """
    Throttle for suggest_skills endpoint - 10 requests per hour per IP.
    """
    scope = 'suggest_skills' 