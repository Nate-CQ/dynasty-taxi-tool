from dotenv import load_dotenv
import os

load_dotenv()

cfbd_key = os.getenv("CFBD_API_KEY")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")

print("CFBD key loaded:", cfbd_key is not None)
print("Anthropic key loaded:", anthropic_key is not None)