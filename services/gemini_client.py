import google.generativeai as genai
from config import settings

def get_model():
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    return genai.GenerativeModel(settings.GEMINI_MODEL_ID)

def ask_gemini(prompt: str, json_mode: bool = False) -> str:
    model = get_model()
    
    # Add system instructions to improve handling of finance data
    system_instruction = """
    You are a financial advisor AI that:
    1. Analyzes transaction data provided
    2. Provides specific insights based on real data
    3. Clearly states when data is missing rather than making assumptions
    4. Uses specific numbers and dates from the data when giving advice
    5. Focuses on actionable financial advice
    6. Please answer directly without adding headings or section titles. Answer in plain text

    """
    
    if json_mode:
        resp = model.generate_content(
            [system_instruction, prompt],
            generation_config={"response_mime_type": "application/json"}
        )
    else:
        resp = model.generate_content([system_instruction, prompt])
    
    return resp.text or ""
