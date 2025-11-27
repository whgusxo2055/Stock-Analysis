#!/usr/bin/env python3
"""뉴스 데이터 수정 스크립트 - 비어있는 요약과 URL 채우기"""
import os
import sys
import json

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from openai import OpenAI

def main():
    es = Elasticsearch(['http://localhost:9200'])
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # 모든 뉴스 조회
    result = es.search(index='news_analysis', query={'match_all': {}}, size=20)
    print(f"Total docs: {len(result['hits']['hits'])}")
    
    updated = 0
    for hit in result['hits']['hits']:
        doc = hit['_source']
        news_id = doc.get('news_id')
        url = doc.get('url')
        summary = doc.get('summary', {})
        summary_ko = summary.get('ko', '') if summary else ''
        
        # URL이 없거나 요약이 비어있는 경우만 처리
        if not url or not summary_ko:
            title = doc.get('title', '')
            content = doc.get('content', title)
            ticker = doc.get('ticker_symbol', 'AAPL')
            company = doc.get('company_name', 'Apple Inc.')
            
            print(f"\n[{updated+1}] Analyzing: {title[:50]}...")
            
            prompt = f"""Analyze this stock news and provide summaries.

Title: {title}
Content: {content[:400] if content else title}
Stock: {ticker} - {company}

Respond with ONLY valid JSON (no markdown):
{{"summary_ko": "한국어로 2-3문장 요약", "summary_en": "English summary 2-3 sentences", "summary_es": "Resumen en español 2-3 oraciones", "summary_ja": "日本語で2-3文の要約"}}"""

            try:
                response = client.chat.completions.create(
                    model='gpt-4',
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=0.7,
                    max_tokens=800
                )
                
                text = response.choices[0].message.content.strip()
                
                # JSON 추출
                if '```' in text:
                    parts = text.split('```')
                    for part in parts:
                        if part.strip().startswith('{'):
                            text = part.strip()
                            break
                        elif part.strip().startswith('json'):
                            text = part.strip()[4:].strip()
                            break
                
                analysis = json.loads(text)
                
                # 업데이트
                doc['summary'] = {
                    'ko': analysis.get('summary_ko', ''),
                    'en': analysis.get('summary_en', ''),
                    'es': analysis.get('summary_es', ''),
                    'ja': analysis.get('summary_ja', '')
                }
                
                if not url:
                    doc['url'] = f'https://www.investing.com/news/stock-market-news/{news_id}'
                
                es.index(index='news_analysis', id=news_id, document=doc)
                updated += 1
                print(f"  ✅ {doc['summary']['ko'][:50]}...")
                
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON Error: {e}")
                print(f"     Raw text: {text[:100]}")
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print(f"\n=== Updated {updated} documents ===")

if __name__ == '__main__':
    main()
