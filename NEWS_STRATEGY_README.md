# 뉴스 감정 분석 기반 매매 전략 사용 가이드

## 📰 개요

이 시스템은 기술적 지표로 1차 선정된 종목들에 대해 뉴스 감정 분석을 수행하여 매매 결정을 내리는 전략을 구현합니다.

## 🚀 주요 기능

### 1. **종목 선정 프로세스**
   - **1단계**: 기술적 지표로 최대 10개 종목 선정
   - **2단계**: 각 종목의 최근 뉴스 수집
   - **3단계**: Claude/ChatGPT API로 뉴스 감정 분석
   - **4단계**: 예측 확률이 임계값 이상인 종목만 매수

### 2. **매매 알고리즘**
   - n일 후 상승 확률이 threshold 이상이면 다음날 매수
   - 최적 보유 기간(n일) 동안 보유 후 매도
   - 손실 제한선(-5%) 도달 시 즉시 매도

### 3. **파라미터 최적화**
   - 과거 데이터(2010~2019)로 최적 파라미터 학습
   - 최적 보유 기간(n): 1, 3, 5, 7, 10, 20일 중 선택
   - 최적 매수 기준(threshold): 50%~80% 범위에서 탐색

## 📋 사용법

### 1. **환경 설정**

```bash
# Claude API 사용 시
export ANTHROPIC_API_KEY='your-api-key'

# OpenAI API 사용 시 (코드 수정 필요)
export OPENAI_API_KEY='your-api-key'
```

### 2. **뉴스 전략 백테스트 실행**

```bash
python run_news_backtest.py
```

메뉴 옵션:
1. **파라미터 최적화**: 과거 데이터로 최적 n과 threshold 찾기
2. **백테스트 실행**: 최근 30일 데이터로 성과 평가
3. **전략 비교**: 기술적 분석 vs 뉴스 분석 성과 비교

### 3. **코드에서 직접 사용**

```python
from hanlyang_stock.strategy.news_based_selector import get_news_based_selector

# 뉴스 기반 선택기 생성
selector = get_news_based_selector()

# 최적 파라미터 설정 (선택사항)
selector.set_optimal_parameters(holding_days=5, threshold=0.65)

# 종목 선정
buy_signals = selector.select_stocks_by_news("2025-06-16")

# 결과 확인
for signal in buy_signals:
    print(f"{signal['ticker']}: 신뢰도={signal['confidence']:.2%}")
```

## 📊 백테스트 결과 해석

### 주요 지표
- **총 수익률**: 전체 기간 수익률
- **거래 횟수**: 매수/매도 총 횟수
- **승률**: 수익 거래 비율
- **최대 손실(MDD)**: 최대 낙폭

### 결과 파일
- `news_strategy_backtest.json`: 상세 백테스트 결과
- 거래 내역, 일별 포트폴리오 가치 등 포함

## 🔧 커스터마이징

### 1. **뉴스 소스 변경**
`news_sentiment.py`의 `fetch_ticker_news()` 메서드 수정

### 2. **API 변경 (OpenAI 사용)**
```python
# news_sentiment.py에서
from openai import OpenAI

class NewsAnalyzer:
    def __init__(self, api_key=None):
        self.client = OpenAI(api_key=api_key)
    
    def analyze_news_sentiment(self, ...):
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
```

### 3. **매매 규칙 수정**
`news_based_selector.py`의 `_should_buy()` 메서드 수정

## ⚠️ 주의사항

1. **API 비용**: 뉴스 분석 시 API 호출 비용 발생
2. **속도**: 뉴스 수집 및 분석으로 백테스트 속도 저하
3. **데이터 품질**: 뉴스 수집 실패 시 기본값(50%) 사용

## 📈 기대 효과

- 기술적 지표와 시장 심리 결합
- 뉴스 이벤트 기반 매매 타이밍 포착
- 최적 보유 기간 자동 결정

## 🤝 기여하기

개선 사항이나 버그를 발견하시면 이슈를 등록해주세요!
