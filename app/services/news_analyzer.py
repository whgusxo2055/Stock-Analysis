"""
뉴스 분석 서비스
- ChatGPT API를 통한 다국어 요약
- 호재/악재 감성 분석
- FR-018~020 구현
- SRS v1.1: analyzed_date, metadata 필드 추가
"""

import logging
import json
from typing import Dict, Optional, List
from datetime import datetime, timezone

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from app.utils.config import Config

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """
    뉴스 분석 엔진
    ChatGPT API를 사용한 다국어 요약 및 감성 분석
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = Config.OPENAI_MODEL or "gpt-4o-mini"
        # gpt-5 계열은 빈 응답 사례가 있어 기본 모델로 강제
        if self.model.startswith("gpt-5"):
            logger.warning(f"Unsupported/unstable model '{self.model}' detected. Falling back to gpt-4o-mini.")
            self.model = "gpt-4o-mini"
        
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        elif OpenAI is None:
            logger.error("openai package not installed")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("NewsAnalyzer initialized with OpenAI client")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    def analyze_news(
        self,
        title: str,
        content: str,
        ticker: str,
        company_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        뉴스 분석 수행
        
        Args:
            title: 뉴스 제목
            content: 뉴스 본문
            ticker: 티커 심볼
            company_name: 회사명 (옵션)
        
        Returns:
            분석 결과 딕셔너리:
            {
                'summary': {
                    'ko': '한국어 요약',
                    'en': 'English summary',
                    'es': 'Resumen en español',
                    'ja': '日本語の要約'
                },
                'sentiment': {
                    'classification': 'Positive/Negative/Neutral',
                    'score': -10 ~ +10
                }
            }
        """
        if not self.client:
            logger.error("OpenAI client not available")
            return self._generate_fallback_analysis(title, content)
        
        try:
            prompt = self._build_prompt(title, content, ticker, company_name)
            
            logger.debug(f"Analyzing news for {ticker}: {title[:50]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional stock market analyst."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=800   # 4개 언어 요약 + 감성
            )
            
            # 응답 파싱
            choice = response.choices[0]
            result_text = (choice.message.content or "").strip()
            finish_reason = getattr(choice, "finish_reason", None)
            usage = getattr(response, "usage", None)
            logger.debug(
                "ChatGPT raw response: %s...",
                result_text[:200] if result_text else "<empty>"
            )
            
            if not result_text:
                logger.warning(
                    f"Empty response from ChatGPT (model={response.model}, finish_reason={finish_reason}, usage={usage})"
                )
                return self._generate_fallback_analysis(title, content)
            
            # 마크다운 코드 블록 제거 (```json ... ```)
            result_text = result_text.strip()
            if result_text.startswith('```'):
                # 첫 번째 줄 제거 (```json)
                lines = result_text.split('\n')
                if len(lines) > 2:
                    # 마지막 줄 제거 (```)
                    result_text = '\n'.join(lines[1:-1])
            
            result = json.loads(result_text)
            
            # 검증
            validated = self._validate_result(result)
            
            if validated:
                logger.info(
                    f"Analysis completed for {ticker}: "
                    f"{validated['sentiment']['classification']} "
                    f"(score: {validated['sentiment']['score']})"
                )
                return validated
            else:
                logger.warning(f"Invalid analysis result for {ticker}")
                return self._generate_fallback_analysis(title, content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ChatGPT response: {e}")
            return self._generate_fallback_analysis(title, content)
        except Exception as e:
            logger.error(f"Analysis failed for {ticker}: {e}", exc_info=True)
            return self._generate_fallback_analysis(title, content)

    def _build_prompt(
        self,
        title: str,
        content: str,
        ticker: str,
        company_name: Optional[str]
    ) -> str:
        """
        ChatGPT 프롬프트 생성 (FR-020)
        
        Args:
            title: 뉴스 제목
            content: 뉴스 본문
            ticker: 티커 심볼
            company_name: 회사명
        
        Returns:
            프롬프트 문자열
        """
        stock_info = f"{ticker}"
        if company_name:
            stock_info += f" ({company_name})"
        
        # 본문이 너무 길면 자르기 (토큰 제한 고려)
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""You are a professional stock market analyst. Analyze the following news article and provide:

1. Summary in Korean (한국어): A natural and fluent summary in Korean (2-3 sentences)
2. Summary in English: A natural and fluent summary in English (2-3 sentences)
3. Summary in Spanish (Español): A natural and fluent summary in Spanish (2-3 sentences)
4. Summary in Japanese (日本語): A natural and fluent summary in Japanese (2-3 sentences)
5. Sentiment Analysis:
   - Classification: Positive (호재) / Negative (악재) / Neutral (중립)
   - Score: -10 to +10 (-10: very negative, 0: neutral, +10: very positive)

News Article:
Title: {title}
Content: {content}
Stock: {stock_info}

Please provide the response in JSON format:
{{
  "summary_ko": "...",
  "summary_en": "...",
  "summary_es": "...",
  "summary_ja": "...",
  "sentiment": {{
    "classification": "Positive/Negative/Neutral",
    "score": 0
  }}
}}"""
        
        return prompt

    def _validate_result(self, result: Dict) -> Optional[Dict]:
        """
        분석 결과 검증
        
        Args:
            result: ChatGPT 응답
        
        Returns:
            검증된 결과 또는 None
        """
        try:
            # 필수 필드 확인
            summary_ko = result.get('summary_ko', '').strip()
            summary_en = result.get('summary_en', '').strip()
            summary_es = result.get('summary_es', '').strip()
            summary_ja = result.get('summary_ja', '').strip()
            
            sentiment = result.get('sentiment', {})
            classification = sentiment.get('classification', '').strip()
            score = sentiment.get('score')
            
            # 검증
            if not all([summary_ko, summary_en, summary_es, summary_ja]):
                logger.warning("Missing summary in one or more languages")
                return None
            
            if classification not in ['Positive', 'Negative', 'Neutral']:
                logger.warning(f"Invalid classification: {classification}")
                classification = 'Neutral'
            
            # SRS v1.1: classification을 lowercase로 저장
            classification = classification.lower()
            
            # 점수 범위 검증 (-10 ~ +10)
            try:
                score = int(score)
                if not -10 <= score <= 10:
                    logger.warning(f"Score {score} out of range, clipping")
                    score = max(-10, min(10, score))
            except (TypeError, ValueError):
                logger.warning(f"Invalid score: {score}, defaulting to 0")
                score = 0
            
            return {
                'summary': {
                    'ko': summary_ko,
                    'en': summary_en,
                    'es': summary_es,
                    'ja': summary_ja
                },
                'sentiment': {
                    'classification': classification,
                    'score': score
                }
            }
            
        except Exception as e:
            logger.error(f"Result validation failed: {e}")
            return None

    def _generate_fallback_analysis(
        self,
        title: str,
        content: str
    ) -> Dict:
        """
        API 실패 시 기본 분석 생성
        
        Args:
            title: 뉴스 제목
            content: 뉴스 본문
        
        Returns:
            기본 분석 결과
        """
        # 간단한 규칙 기반 요약: 제목 + 본문 첫 문장
        first_sentence = content.split('.')[0] if content else title
        fallback_summary = f"{title}. {first_sentence}."
        
        # 길이 제한
        if len(fallback_summary) > 200:
            fallback_summary = fallback_summary[:197] + "..."
        
        logger.debug("Using fallback analysis")
        
        # 간단한 키워드 기반 감성 (제목+본문)
        text_lower = f"{title} {content}".lower()
        positive_keywords = ['beat', 'growth', 'surge', 'gain', 'soar', 'strong', 'record', 'upgrade', 'outperform', 'buy']
        negative_keywords = ['miss', 'drop', 'fall', 'decline', 'loss', 'down', 'weak', 'cut', 'downgrade', 'sell', 'bankruptcy']
        score = 0
        for kw in positive_keywords:
            if kw in text_lower:
                score += 1
        for kw in negative_keywords:
            if kw in text_lower:
                score -= 1
        if score > 0:
            classification = 'positive'
        elif score < 0:
            classification = 'negative'
        else:
            classification = 'neutral'

        return {
            'summary': {
                'ko': fallback_summary,
                'en': fallback_summary,
                'es': fallback_summary,
                'ja': fallback_summary
            },
            'sentiment': {
                'classification': classification,
                'score': score
            }
        }

    def batch_analyze(
        self,
        news_items: List[Dict]
    ) -> List[Dict]:
        """
        뉴스 배치 분석
        
        Args:
            news_items: 뉴스 리스트
                [{
                    'title': '...',
                    'content': '...',
                    'ticker': 'TSLA',
                    'company_name': '...',
                    'source_url': '...',
                    'date': '...'
                }, ...]
        
        Returns:
            분석 결과가 추가된 뉴스 리스트 (SRS v1.1 필드 포함)
        """
        if not news_items:
            return []
        
        logger.info(f"Batch analyzing {len(news_items)} news items")
        
        analyzed = []
        
        for item in news_items:
            try:
                content = item.get('content', '')
                
                analysis = self.analyze_news(
                    title=item.get('title', ''),
                    content=content,
                    ticker=item.get('ticker', ''),
                    company_name=item.get('company_name')
                )
                
                if analysis:
                    # 분석 결과 추가
                    item['summary'] = analysis['summary']
                    item['sentiment'] = analysis['sentiment']
                    
                    # SRS v1.1: analyzed_date, metadata 필드 추가
                    item['analyzed_date'] = datetime.now(timezone.utc).isoformat()
                    item['metadata'] = {
                        'word_count': len(content.split()) if content else 0,
                        'language': 'en',  # 원문 언어 (기본: 영어)
                        'gpt_model': Config.OPENAI_MODEL
                    }
                    
                    analyzed.append(item)
                else:
                    logger.warning(
                        f"Analysis failed for: {item.get('title', 'N/A')}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"Error analyzing item: {e}",
                    exc_info=True
                )
                continue
        
        logger.info(
            f"Batch analysis completed: {len(analyzed)}/{len(news_items)} successful"
        )
        
        return analyzed


# 싱글톤 인스턴스
_analyzer: Optional[NewsAnalyzer] = None


def get_news_analyzer() -> NewsAnalyzer:
    """
    NewsAnalyzer 싱글톤 인스턴스 반환
    
    Returns:
        NewsAnalyzer 인스턴스
    """
    global _analyzer
    
    if _analyzer is None:
        _analyzer = NewsAnalyzer()
    
    return _analyzer
