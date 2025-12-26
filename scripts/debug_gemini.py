import google.generativeai as genai
import os
import sys

def test_gemini():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not set")
        return

    print(f"Testing API Key: {api_key[:5]}...{api_key[-5:]}")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content('Responde solo con la palabra OK')
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Caught Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_gemini()
