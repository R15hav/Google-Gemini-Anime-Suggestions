import os
from urllib import response
from google import genai
from google.genai.errors import ClientError
from dotenv import load_dotenv
import json
import re

load_dotenv()

def call_gemini(prompt: str, model: str = "gemini-1.5-flash", api_key: str = None):
    client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text

def safe_json_parse(text: str):
    # remove ```json ``` blocks if present
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # extract first JSON array [...]
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        print(text)
        raise ValueError(f"No JSON array found in response:\n{text}")

    return json.loads(match.group(0))

def get_search_params(user_completed, user_dropped, model, api_key):
    prompt = f"""
    Based on these favorites: {user_completed} 
    And these dropped shows: {user_dropped}
    
    Identify 3 distinct 'vibe' categories to search for.
    Return ONLY valid JSON (no markdown, no explanation).
    Output must start with [ and end with ] hence,
    Return ONLY a JSON list of objects: [{{"genre": "Action", "tag": "Cyberpunk"}}, ...]
    """
    # Call Gemini...
    response = call_gemini(prompt, model, api_key)

    return safe_json_parse(response)

def finalize_recommendations(candidates, user_history, model, api_key):
    prompt = f"""
    From this pool of {len(candidates)} anime, select 5 unique recommendations.
    User History to avoid: {user_history}
    
    Ensure the selection feels fresh and explain why each was chosen.
    Return JSON: {{ "recommendations": [{{ "title": str, "reason": str }}] }}
    """
    # Call Gemini...
    response = call_gemini(prompt, model, api_key)

    return safe_json_parse(response)