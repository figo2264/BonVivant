# 뉴스 크롤러 모듈

모듈화된 뉴스 크롤링 시스템으로 다양한 뉴스 소스에서 주식 관련 뉴스를 수집합니다.

## 구조

```
crawlers/
├── __init__.py                  # 패키지 초기화
├── news_crawler_base.py         # 베이스 클래스 및 데이터 구조
├── news_crawler_factory.py      # 크롤러 팩토리
├── multi_source_crawler.py      # 멀티 소스 통합 크롤러
├── naver_finance_crawler.py     # 네이버 증권 크롤러
├── mk_economy_crawler.py        # 매일경제 크롤러
└── custom/                      # 커스텀 크롤러 디렉토리
    └── __init__.py
```

## 주요 클래스

### NewsItem
뉴스 데이터를 담는 데이터 클래스
```python
@dataclass
class NewsItem:
    title: str          # 뉴스 제목
    date: str          # 날짜
    url: str           # URL
    source: str        # 언론사
    content: Optional[str] = None  # 본문 (선택)
```

### NewsCrawlerBase
모든 크롤러가 상속받는 추상 베이스 클래스
- `fetch_news()`: 뉴스 수집 메서드 (구현 필요)
- `filter_by_quality()`: 품질 기준 필터링
- `_get_quality_sources()`: 신뢰할 수 있는 소스 정의

### MultiSourceCrawler
여러 소스에서 뉴스를 통합 수집
- 병렬 처리 지원
- 중복 제거
- 소스별 통계

## 사용법

### 1. 기본 사용 (네이버 증권)
```python
from hanlyang_stock.analysis.news_sentiment import NewsAnalyzer

analyzer = NewsAnalyzer(debug=True)
news_list = analyzer.fetch_ticker_news("005930", "삼성전자", "2024-01-15")
```

### 2. 여러 소스 사용
```python
from hanlyang_stock.analysis.crawlers import NewsSource

analyzer = NewsAnalyzer(
    debug=True,
    news_sources=[NewsSource.NAVER_FINANCE, NewsSource.MK_ECONOMY]
)
```

### 3. 동적 소스 관리
```python
# 소스 추가
analyzer.add_news_source(NewsSource.MK_ECONOMY)

# 소스 제거
analyzer.remove_news_source(NewsSource.NAVER_FINANCE)
```

### 4. 커스텀 크롤러 추가
```python
from hanlyang_stock.analysis.crawlers import NewsCrawlerBase, NewsCrawlerFactory

class MyCustomCrawler(NewsCrawlerBase):
    def _get_quality_sources(self):
        return ["신뢰할 소스1", "신뢰할 소스2"]
    
    def fetch_news(self, ticker, company_name, date, max_items=10):
        # 구현
        return news_items

# 팩토리에 등록
NewsCrawlerFactory.register_crawler("my_source", MyCustomCrawler)

# 사용
analyzer = NewsAnalyzer(news_sources=["my_source"])
```

## 크롤러별 특징

### NaverFinanceCrawler
- 네이버 증권 뉴스 크롤링
- iframe 처리
- 경제 전문지 필터링
- Selenium 사용

### MKEconomyCrawler  
- 매일경제 AI 검색 활용
- 동적 컨텐츠 로딩
- 더보기 버튼 처리
- 회사명 자동 조회

## 설정 옵션

### 디버그 모드
```python
analyzer = NewsAnalyzer(debug=True)  # 상세 로그 출력
```

### 병렬 처리
```python
crawler = MultiSourceCrawler(
    sources=sources,
    parallel=True,      # 병렬 처리 활성화
    max_workers=3       # 최대 워커 수
)
```

## 주의사항

1. **Selenium 드라이버**: Chrome 드라이버가 자동 설치됩니다.
2. **속도**: 크롤링은 시간이 걸릴 수 있습니다. 캐싱을 고려하세요.
3. **로봇 정책**: 각 사이트의 robots.txt를 준수하세요.
4. **API 비용**: Claude API 사용 시 비용이 발생합니다.

## 문제 해결

### 크롤링 실패 시
1. 네트워크 연결 확인
2. 사이트 구조 변경 확인
3. 디버그 모드로 상세 로그 확인

### 느린 속도
1. 병렬 처리 활성화
2. 이미지 로딩 비활성화 (이미 적용됨)
3. 필요한 소스만 선택 사용

## 확장 가이드

새로운 크롤러를 추가하려면:

1. `NewsCrawlerBase`를 상속받는 클래스 생성
2. `fetch_news()`와 `_get_quality_sources()` 구현
3. `NewsCrawlerFactory`에 등록
4. `NewsSource`에 상수 추가 (선택)

자세한 예시는 `naver_finance_crawler.py`를 참고하세요.
