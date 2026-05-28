"""
Utility functions for LinkedIn AI Strategist services.
"""
import os
import logging

logger = logging.getLogger(__name__)


def get_env_or_secret(key: str) -> str:
    """
    Retrieve configuration key from environment variables.
    Falls back to PyRunner's encrypted Secrets store in the database if not found in env.
    """
    # 1. Check environment variables
    val = os.environ.get(key)
    if val:
        return val

    # 2. Check PyRunner Secrets database model
    try:
        from core.models import Secret
        secret = Secret.objects.get(key=key)
        return secret.get_decrypted_value()
    except ImportError:
        # Django settings might not be initialized in some stand-alone test runs
        pass
    except Exception:
        # Secret not in database
        pass

    return ""
