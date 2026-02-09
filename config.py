import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")


print("API key loaded:", bool(OPENAI_API_KEY))
print("Model:", OPENAI_MODEL)

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Check your .env file.")
