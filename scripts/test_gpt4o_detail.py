"""GPT-4o 상세 응답 분석"""
import sys
sys.path.insert(0, '.')

from openai import OpenAI
from app.utils.config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)

print(f'\n=== GPT-4o 상세 분석 ===')
print(f'모델: {Config.OPENAI_MODEL}\n')

response = client.chat.completions.create(
    model=Config.OPENAI_MODEL,
    messages=[
        {
            "role": "system",
            "content": "You are a professional stock market analyst. Respond in JSON format."
        },
        {
            "role": "user",
            "content": """Analyze this news in JSON format with these fields:
- summary: dict with ko, en, es, ja keys (Korean, English, Spanish, Japanese summaries)
- sentiment: dict with classification (Positive/Negative/Neutral) and score (-10 to 10)

News: "Tesla announces record Q4 deliveries, stock surges 8%"
"""
        }
    ],
    max_completion_tokens=500
)

print(f'Response object: {type(response)}')
print(f'Choices: {len(response.choices)}')
print(f'Message: {response.choices[0].message}')
print(f'\nContent type: {type(response.choices[0].message.content)}')
print(f'Content: {repr(response.choices[0].message.content)}')

if response.choices[0].message.content:
    print(f'\n실제 내용:\n{response.choices[0].message.content}')
