"""GPT-5 모델 응답 디버깅"""
import sys
sys.path.insert(0, '.')

from openai import OpenAI
from app.utils.config import Config
import json

client = OpenAI(api_key=Config.OPENAI_API_KEY)

print(f'\n=== GPT-5 모델 테스트 ===')
print(f'모델: {Config.OPENAI_MODEL}\n')

try:
    response = client.chat.completions.create(
        model=Config.OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a professional stock market analyst."
            },
            {
                "role": "user",
                "content": "Analyze this news and respond in JSON format: Tesla announces record deliveries"
            }
        ],
        max_completion_tokens=500
    )
    
    content = response.choices[0].message.content
    print(f'응답 타입: {type(content)}')
    print(f'응답 길이: {len(content) if content else 0}')
    print(f'응답 내용: {repr(content)}')
    
    if content:
        print(f'\n실제 텍스트:\n{content}')
    
except Exception as e:
    print(f'❌ 에러: {e}')
