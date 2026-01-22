import google.generativeai as genai
import os

api_key = os.environ.get("GEMINI_API_KEY") or "AIzaSyAK9EkYlwI_JC2rwg4QSfPL-BEHp9Kcq7I"
genai.configure(api_key=api_key)

print("Listing available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
