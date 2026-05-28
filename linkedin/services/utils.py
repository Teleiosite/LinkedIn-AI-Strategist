"""
Utility functions for LinkedIn AI Strategist services.
"""
import os
import logging
import json
import re

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


def parse_json_via_regex(text: str, keys: list[str]) -> dict:
    """
    Fallback parser that extracts values for known keys using regex.
    Useful when LLM returns malformed JSON with unescaped double quotes inside values.
    """
    result = {}
    positions = []
    for key in keys:
        pattern = rf'"{key}"\s*:\s*"'
        match = re.search(pattern, text)
        if match:
            positions.append((key, match.start(), match.end()))
            
    if not positions:
        return {}
        
    # Sort keys by their starting position in the text
    positions.sort(key=lambda x: x[1])
    
    # Extract values between keys
    for i in range(len(positions)):
        current_key, current_start, current_val_start = positions[i]
        
        # If it's the last key, it goes until the last double quote before the closing brace
        if i == len(positions) - 1:
            val_end = len(text)
            brace_pos = text.rfind('}')
            if brace_pos != -1:
                quote_before = text.rfind('"', 0, brace_pos)
                if quote_before != -1:
                    val_end = quote_before
            val = text[current_val_start:val_end]
        else:
            # Otherwise, it goes until the starting quote of the next key
            next_key, next_start, next_val_start = positions[i+1]
            val_end = text.rfind('"', 0, next_start)
            comma_pos = text.rfind(',', 0, next_start)
            if comma_pos != -1 and comma_pos < val_end:
                quote_before_comma = text.rfind('"', 0, comma_pos)
                if quote_before_comma != -1:
                    val_end = quote_before_comma + 1
            val = text[current_val_start:val_end]
            
            # Clean trailing quote/comma
            val = val.strip()
            if val.endswith('"'):
                val = val[:-1]
            elif val.endswith('",') or val.endswith('",\n'):
                val = val[:-2]
                
        val = val.strip()
        if val.endswith('"'):
            val = val[:-1]
        
        # Unescape quotes and newlines
        val = val.replace('\\"', '"').replace('\\n', '\n')
        result[current_key] = val
        
    return result


def parse_json_robustly(text: str, expected_keys: list[str] = None) -> dict:
    """
    Parse a JSON string robustly:
    - Strips markdown code block wrappers (```json ... ```)
    - Locates the outermost curly braces to isolate the JSON object
    - Cleans raw unescaped newlines/control chars inside double quotes
    - Falls back to regex-based extraction if standard json.loads fails
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

    # 3. Try parsing directly first
    try:
        # Clean up raw newlines inside double-quoted string values (basic cleanup)
        def replace_newlines(match):
            return match.group(0).replace("\n", "\\n").replace("\r", "\\r")
        cleaned_text = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', replace_newlines, text)
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        logger.warning(f"Standard JSON parsing failed: {e}. Falling back to regex extraction.")
        
        if not expected_keys:
            expected_keys = [
                "hook", "post_text", "hashtags", "core_message", "target_emotion",
                "core_emotion", "key_metaphor", "symbolic_element", "color_mood",
                "suggested_palette", "image_format", "avoid"
            ]
            
        try:
            result = parse_json_via_regex(text, expected_keys)
            if result:
                # If suggested_palette is expected, extract its sub-object manually
                if "suggested_palette" in expected_keys and "suggested_palette" not in result:
                    palette_match = re.search(r'"suggested_palette"\s*:\s*(\{[\s\S]*?\})', text)
                    if palette_match:
                        try:
                            result["suggested_palette"] = json.loads(palette_match.group(1))
                        except Exception:
                            pass
                return result
        except Exception as regex_err:
            logger.error(f"Regex extraction fallback also failed: {regex_err}")
            
        raise e
