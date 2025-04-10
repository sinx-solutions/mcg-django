from rest_framework.throttling import AnonRateThrottle

class AIEndpointRateThrottle(AnonRateThrottle):
    """
    Throttle for AI-powered endpoints to limit usage to 10 requests per hour per IP.
    """
    scope = 'ai_endpoints' 