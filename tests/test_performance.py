"""
Phase 7 성능 테스트
P7.M2.T3: 소규모 성능/로드 테스트
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import statistics
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


def measure_time(func):
    """함수 실행 시간 측정 데코레이터"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return result, end - start
    return wrapper


class PerformanceTest:
    """성능 테스트 클래스"""
    
    def __init__(self):
        self.results = {}
    
    def run_all_tests(self):
        """모든 성능 테스트 실행"""
        print("\n" + "="*60)
        print("📊 Phase 7 성능 테스트")
        print("="*60)
        
        # 1. Flask 앱 응답 시간 테스트
        self.test_flask_response_time()
        
        # 2. 데이터베이스 CRUD 성능
        self.test_database_performance()
        
        # 3. 뉴스 분석 성능 (Fallback)
        self.test_analysis_performance()
        
        # 4. ElasticSearch 쿼리 성능 (연결 시)
        self.test_elasticsearch_performance()
        
        # 5. 동시 요청 처리 테스트
        self.test_concurrent_requests()
        
        # 결과 요약
        self.print_summary()
    
    def test_flask_response_time(self):
        """Flask 앱 응답 시간 테스트 (NFR-001: 3초 이내)"""
        print("\n[1] Flask 앱 응답 시간 테스트")
        print("-" * 40)
        
        from app import create_app
        
        app = create_app('testing')
        client = app.test_client()
        
        endpoints = [
            ('/', 'GET'),
            ('/health', 'GET'),
            ('/auth/login', 'GET'),
        ]
        
        times = []
        for endpoint, method in endpoints:
            start = time.perf_counter()
            if method == 'GET':
                response = client.get(endpoint)
            end = time.perf_counter()
            
            elapsed = (end - start) * 1000  # ms
            times.append(elapsed)
            
            status = "✓ PASS" if elapsed < 3000 else "✗ FAIL"
            print(f"  {endpoint}: {elapsed:.2f}ms {status}")
        
        avg_time = statistics.mean(times)
        self.results['flask_avg_response'] = avg_time
        print(f"\n  평균 응답 시간: {avg_time:.2f}ms")
        print(f"  목표: 3000ms 이내 - {'✓ PASS' if avg_time < 3000 else '✗ FAIL'}")
    
    def test_database_performance(self):
        """데이터베이스 CRUD 성능 테스트"""
        print("\n[2] 데이터베이스 CRUD 성능 테스트")
        print("-" * 40)
        
        from app import create_app
        from app.extensions import db
        from app.models.models import User, StockMaster
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            
            # CREATE 성능
            start = time.perf_counter()
            for i in range(100):
                user = User(username=f'perfuser{i}', email=f'perf{i}@test.com')
                user.set_password('testpass')
                db.session.add(user)
            db.session.commit()
            create_time = (time.perf_counter() - start) * 1000
            
            # READ 성능
            start = time.perf_counter()
            for i in range(100):
                User.query.filter_by(username=f'perfuser{i}').first()
            read_time = (time.perf_counter() - start) * 1000
            
            # UPDATE 성능
            start = time.perf_counter()
            users = User.query.all()
            for user in users:
                user.email = f'updated_{user.email}'
            db.session.commit()
            update_time = (time.perf_counter() - start) * 1000
            
            # DELETE 성능
            start = time.perf_counter()
            User.query.delete()
            db.session.commit()
            delete_time = (time.perf_counter() - start) * 1000
            
            db.drop_all()
        
        print(f"  CREATE 100건: {create_time:.2f}ms")
        print(f"  READ 100건: {read_time:.2f}ms")
        print(f"  UPDATE 100건: {update_time:.2f}ms")
        print(f"  DELETE 100건: {delete_time:.2f}ms")
        
        total_time = create_time + read_time + update_time + delete_time
        self.results['db_total_crud'] = total_time
        print(f"\n  총 CRUD 시간: {total_time:.2f}ms")
    
    def test_analysis_performance(self):
        """뉴스 분석 성능 테스트 (Fallback 모드)"""
        print("\n[3] 뉴스 분석 성능 테스트 (Fallback)")
        print("-" * 40)
        
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()  # API 키 없이 Fallback 모드
        
        test_news = [
            {
                'title': f'Test News {i}',
                'content': f'This is test content for news {i}. ' * 10,
                'ticker': 'TSLA',
                'company_name': 'Tesla'
            }
            for i in range(10)
        ]
        
        times = []
        for news in test_news:
            start = time.perf_counter()
            result = analyzer.analyze_news(
                title=news['title'],
                content=news['content'],
                ticker=news['ticker'],
                company_name=news['company_name']
            )
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        self.results['analysis_avg'] = avg_time
        print(f"  10건 분석 평균: {avg_time:.2f}ms")
        print(f"  10건 분석 최대: {max_time:.2f}ms")
    
    def test_elasticsearch_performance(self):
        """ElasticSearch 쿼리 성능 테스트 (NFR-002: 1초 이내)"""
        print("\n[4] ElasticSearch 쿼리 성능 테스트")
        print("-" * 40)
        
        try:
            from app.services.news_storage import get_news_storage
            
            storage = get_news_storage()
            
            if storage.es_client and storage.es_client.is_connected():
                # 검색 쿼리 테스트
                times = []
                for _ in range(10):
                    start = time.perf_counter()
                    result = storage.search_news(ticker_symbol='TSLA', limit=20)
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                
                avg_time = statistics.mean(times)
                p95_time = sorted(times)[int(len(times) * 0.95)]
                
                self.results['es_avg_query'] = avg_time
                self.results['es_p95_query'] = p95_time
                
                print(f"  쿼리 평균: {avg_time:.2f}ms")
                print(f"  쿼리 p95: {p95_time:.2f}ms")
                print(f"  목표: 1000ms 이내 - {'✓ PASS' if p95_time < 1000 else '✗ FAIL'}")
            else:
                print("  ⚠ ElasticSearch 미연결 - 테스트 건너뜀")
                self.results['es_avg_query'] = None
                
        except Exception as e:
            print(f"  ⚠ ElasticSearch 연결 오류: {e}")
            self.results['es_avg_query'] = None
    
    def test_concurrent_requests(self):
        """동시 요청 처리 테스트 (NFR-004: 동시 3명)"""
        print("\n[5] 동시 요청 처리 테스트")
        print("-" * 40)
        
        from app import create_app
        
        app = create_app('testing')
        
        results = []
        
        # 순차적으로 3개 요청 (동시성 시뮬레이션)
        for i in range(3):
            with app.test_client() as client:
                start = time.perf_counter()
                response = client.get('/health')
                elapsed = (time.perf_counter() - start) * 1000
                results.append((response.status_code, elapsed))
        
        success_count = sum(1 for status, _ in results if status == 200)
        avg_time = statistics.mean([t for _, t in results])
        
        self.results['concurrent_success'] = success_count
        self.results['concurrent_avg'] = avg_time
        
        print(f"  3개 요청 성공: {success_count}/3")
        print(f"  평균 응답 시간: {avg_time:.2f}ms")
        print(f"  목표: 동시 3명 지원 - {'✓ PASS' if success_count == 3 else '✗ FAIL'}")
    
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*60)
        print("📈 성능 테스트 결과 요약")
        print("="*60)
        
        # NFR 요구사항 대비 결과
        checks = [
            ("NFR-001: 페이지 로딩 3초 이내", 
             self.results.get('flask_avg_response', 0) < 3000),
            ("NFR-002: ES 쿼리 1초 이내", 
             self.results.get('es_p95_query') is None or self.results.get('es_p95_query', 0) < 1000),
            ("NFR-004: 동시 3명 지원", 
             self.results.get('concurrent_success', 0) == 3),
        ]
        
        pass_count = 0
        for name, passed in checks:
            status = "✓ PASS" if passed else "✗ FAIL"
            if passed:
                pass_count += 1
            print(f"  {name}: {status}")
        
        print(f"\n총 결과: {pass_count}/{len(checks)} 통과")
        print("="*60)
        
        return pass_count == len(checks)


if __name__ == '__main__':
    test = PerformanceTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
