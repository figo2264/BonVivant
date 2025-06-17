# 뉴스 크롤러 개선 사항 (업데이트)

## 변경 내용 요약

### 1. 크롤링 대상 변경
- **기존**: 매일경제 AI 검색 페이지 (Selenium 필수)
- **변경**: 네이버 증권 종목별 뉴스 페이지 (Selenium으로 iframe 처리)

### 2. 주요 개선사항

#### 2.1 네이버 증권 iframe 처리
- **문제점**: 네이버 증권 뉴스가 iframe 내부에 동적 로드됨
- **해결책**: Selenium으로 iframe 전환 후 크롤링
- **최적화**: 
  - 이미지 로딩 비활성화로 속도 향상
  - 경제 전문지만 필터링하여 품질 향상

#### 2.2 경제 전문지 필터링
선별된 경제 전문 매체만 수집:
- 한국경제, 한경
- 연합인포맥스, 인포맥스
- 매일경제, 매경
- 서울경제, 이데일리
- 머니투데이, 파이낸셜뉴스
- 아시아경제, 헤럴드경제
- 조선비즈, 뉴스1, 뉴시스

#### 2.3 대체 솔루션
네이버 검색 API 크롤러도 제공 (별도 파일):
- 가장 안정적이고 빠른 방법
- API 키 필요 (무료 25,000건/일)
- `naver_search_api_crawler.py` 참조

#### 2.4 API 비용 절감
- 최대 10개 뉴스만 반환 (중복 제거 후)
- 소스별 통계 제공
- 효율적인 Claude API 사용

## 사용 방법

### 기존 코드 호환성
모든 기존 코드는 수정 없이 자동으로 새로운 크롤러를 사용합니다:

```python
from hanlyang_stock.analysis.news_sentiment import NewsAnalyzer

analyzer = NewsAnalyzer()
news_list = analyzer.fetch_ticker_news("005930", "삼성전자", "2024-01-15")
```

### 테스트 실행

새로운 테스트 스크립트로 크롤러 성능을 확인할 수 있습니다:

테스트 메뉴:
1. 크롤러 비교 테스트 (새로운 vs 기존)
2. 다중 종목 테스트

### 디버그 모드

디버그 모드를 활성화하면 상세한 크롤링 과정을 확인할 수 있습니다:

```python
analyzer = NewsAnalyzer(debug=True)
```

## 네이버 검색 API 사용법 (권장)

더 안정적인 크롤링을 원한다면 네이버 검색 API를 사용하세요:

1. **API 키 발급**
   - https://developers.naver.com 접속
   - 애플리케이션 등록
   - 검색 API 사용 신청

2. **환경 변수 설정**
   ```bash
   # .env 파일에 추가
   NAVER_CLIENT_ID=your_client_id
   NAVER_CLIENT_SECRET=your_client_secret
   ```

3. **사용 예시**
   ```python
   from naver_search_api_crawler import NaverSearchAPINews
   
   crawler = NaverSearchAPINews()
   news = crawler.fetch_ticker_news("005930", "삼성전자")
   ```

## 영향받는 파일

1. 자동으로 새 크롤러를 사용하는 파일들:
   - `hanlyang_stock/strategy/executor.py`
   - `hanlyang_stock/backtest/engine.py`
   - `run_news_backtest.py`

## 성능 비교

| 항목 | 기존 (매일경제) | 개선 (네이버 증권) |
|------|----------------|-------------------|
| 속도 | 보통 | 보통 (Selenium 사용) |
| 안정성 | 보통 | 높음 |
| 뉴스 품질 | 다양함 | 경제지 중심 |
| 기간 검색 | 제한적 | 가능 |
| API 비용 | 높음 (많은 뉴스) | 낮음 (10개 제한) |

## 주의사항

1. **Selenium 필수**: 네이버 증권의 iframe 구조로 인해 Selenium이 필요합니다
2. **속도**: Selenium 사용으로 인해 속도가 느릴 수 있습니다
3. **안정성**: 네이버 증권 페이지 구조 변경 시 업데이트 필요

## 권장 사항

1. **프로덕션 환경**: 네이버 검색 API 사용 권장 (안정성, 속도)
2. **개발/테스트**: 현재 Selenium 크롤러 사용
3. **백업 플랜**: 크롤링 실패 시 자동으로 기존 매일경제 크롤러로 폴백

## 향후 개선 가능 사항

1. **캐싱 메커니즘**: 동일 종목/날짜 재요청 시 캐시 활용
2. **병렬 처리**: 여러 종목 동시 크롤링
3. **추가 소스**: 다음 금융, 팍스넷 등 추가 뉴스 소스 통합
4. **본문 분석**: 뉴스 제목뿐만 아니라 본문 내용도 수집하여 더 정확한 감정 분석
