import os
from google import genai

client = genai.Client()
print("Available Models:")
for m in client.models.list():
    print(m.name)

