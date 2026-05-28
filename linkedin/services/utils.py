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


import json
import re

def parse_json_robustly(text: str) -> dict:
    """
    Parse a JSON string robustly:
    - Strips markdown code block wrappers (```json ... ```)
    - Locates the outermost curly braces to isolate the JSON object
    - Cleans raw unescaped newlines/control chars inside double quotes
    """
    text = text.strip()
    
    # 1. Strip markdown wrapper
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        
    # 2. Extract content between first '{' and last '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]

    # 3. Clean up raw newlines inside double-quoted string values
    def replace_newlines(match):
        return match.group(0).replace("\n", "\\n").replace("\r", "\\r")
    
    text = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', replace_newlines, text)

    # 4. Try parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON even after cleaning. Text: {text}. Error: {e}")
        raise e
