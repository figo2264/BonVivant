# 🚀 모듈화된 백테스트 엔진

백테스트 엔진을 hanlyang_stock 모듈 구조와 통합한 모듈화된 백테스팅 시스템입니다.

## 🎯 개요

기존의 단일 파일 백테스트 엔진을 모듈화하여 재사용성, 확장성, 유지보수성을 크게 향상시킨 새로운 백테스트 시스템입니다.

### ✨ 주요 특징

- 🧩 **완전 모듈화**: 기능별로 분리된 독립적인 모듈들
- 🔄 **기존 시스템과 완전 호환**: 동일한 알고리즘과 결과 보장
- 🚀 **성능 최적화**: 데이터 캐싱 및 효율적인 메모리 관리
- 🧪 **테스트 용이성**: 각 모듈별 단위 테스트 가능
- ⚙️ **설정 관리**: 유연한 설정 시스템

## 🏗️ 아키텍처

```
hanlyang_stock/
├── backtest/                    # 🆕 백테스트 핵심 모듈
│   ├── engine.py               # 메인 백테스트 엔진
│   ├── portfolio.py            # 포트폴리오 관리
│   ├── performance.py          # 성과 분석
│   └── data_validator.py       # 데이터 검증
├── analysis/                   # ✅ 분석 모듈 (강화됨)
│   ├── ai_model.py            # AI 모델 관리
│   └── technical.py           # 기술적 분석
├── data/                      # ✅ 데이터 모듈 (최적화됨)
│   ├── fetcher.py            # 데이터 수집 (캐싱 기능 추가)
│   └── preprocessor.py       # 데이터 전처리
├── strategy/                  # ✅ 전략 모듈 (확장됨)
│   ├── selector.py           # 종목 선정 (백테스트 모드 지원)
│   ├── executor.py           # 실제 거래 실행
│   └── backtester.py         # 🆕 백테스트 전용 전략
├── config/                   # ⚙️ 설정 관리
│   ├── settings.py          # 기본 설정
│   └── backtest_settings.py # 🆕 백테스트 전용 설정
└── utils/                   # 🛠️ 유틸리티
    ├── storage.py          # 데이터 저장
    └── notification.py     # 알림 기능

# 실행 스크립트들
run_modular_backtest.py         # 🆕 모듈화된 백테스트 실행기
test_modular_backtest.py        # 🧪 통합 테스트
benchmark_backtest.py           # 🏁 성능 벤치마크
```

## 🚀 빠른 시작

### 1. 기본 백테스트 실행

```python
from hanlyang_stock.backtest import BacktestEngine

# 백테스트 엔진 생성
engine = BacktestEngine(
    initial_capital=10_000_000,  # 1000만원
    transaction_cost=0.003       # 0.3% 수수료
)

# 백테스트 실행
results = engine.run_backtest(
    start_date='2025-05-01',
    end_date='2025-06-01',
    ai_enabled=True
)

# 결과 출력 및 저장
engine.performance_analyzer.print_performance_summary()
engine.save_results('backtest_result.json')
```

### 2. 대화형 실행

```bash
python run_modular_backtest.py
```

### 3. 통합 테스트

```bash
python test_modular_backtest.py
```

### 4. 성능 벤치마크

```bash
python benchmark_backtest.py
```

## 📊 모듈별 상세 가이드

### 🔧 BacktestEngine - 메인 엔진

```python
from hanlyang_stock.backtest import BacktestEngine
from hanlyang_stock.config.backtest_settings import get_backtest_config

# 설정 기반 엔진 생성
config = get_backtest_config('conservative')  # 보수적 설정
engine = BacktestEngine(
    initial_capital=config.initial_capital,
    transaction_cost=config.transaction_cost
)

# 백테스트 실행
results = engine.run_backtest(
    start_date='2025-05-01',
    end_date='2025-06-01',
    ai_enabled=True
)
```

### 💼 Portfolio - 포트폴리오 관리

```python
from hanlyang_stock.backtest import Portfolio

portfolio = Portfolio(
    initial_capital=10_000_000,
    transaction_cost=0.003
)

# 매수
success = portfolio.buy_stock(
    ticker='005930',        # 삼성전자
    price=70000,           # 매수가
    investment_amount=1_000_000,  # 투자금액
    current_date='2025-06-01',
    additional_info={
        'ai_score': 0.85,
        'confidence_level': '고신뢰',
        'technical_score': 0.72
    }
)

# 매도
success = portfolio.sell_stock(
    ticker='005930',
    price=72000,
    current_date='2025-06-04',
    sell_reason='3일 보유 룰'
)

# 포트폴리오 가치 계산
current_prices = {'005930': 72000}
total_value = portfolio.calculate_portfolio_value(current_prices)

# 거래 내역 및 통계
trade_history = portfolio.get_trade_history()
summary_stats = portfolio.get_summary_stats()
```

### 📈 PerformanceAnalyzer - 성과 분석

```python
from hanlyang_stock.backtest import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()

# 성과 지표 계산
metrics = analyzer.calculate_performance_metrics(
    portfolio_history=portfolio.get_portfolio_history(),
    trade_history=portfolio.get_trade_history(),
    initial_capital=10_000_000
)

# AI 성과 분석
ai_performance = analyzer.analyze_ai_performance(trade_history)

# 결과 출력
analyzer.print_performance_summary()
analyzer.print_ai_performance_summary(ai_performance)

# 월별 리포트
monthly_report = analyzer.generate_monthly_report(portfolio_history)
print(f"최고 수익 월: {monthly_report['best_month']}")

# 결과 저장
analyzer.save_results_to_json('performance_analysis.json')
```

### 🔍 DataValidator - 데이터 검증

```python
from hanlyang_stock.backtest import DataValidator

validator = DataValidator()

# 단일 종목 검증
is_valid = validator.validate_ticker_data(
    ticker='005930',
    current_date='2025-06-01',
    min_days=30
)

# 여러 종목 일괄 검증
tickers = ['005930', '000660', '035420']
valid_tickers = validator.validate_multiple_tickers(
    tickers, 
    current_date='2025-06-01'
)

# 손실 제한 체크
should_sell, current_price, loss_rate = validator.check_stop_loss(
    ticker='005930',
    buy_price=70000,
    current_date='2025-06-01',
    stop_loss_rate=-0.05
)

# AI 피처 생성 가능 여부 확인
ai_ready = validator.validate_ai_features('005930', '2025-06-01')
```

### 🎯 BacktestStrategy - 백테스트 전용 전략

```python
from hanlyang_stock.strategy.backtester import BacktestStrategy

strategy = BacktestStrategy(stop_loss_rate=-0.05)

# 매도 여부 결정
holding_info = {
    'buy_price': 70000,
    'quantity': 14,
    'buy_date': '2025-06-01'
}

should_sell, reason = strategy.should_sell_stock(
    ticker='005930',
    holding_info=holding_info,
    current_date='2025-06-04'
)

# 매수 후보 선정
candidates = strategy.select_buy_candidates(
    current_date='2025-06-01',
    excluded_tickers=['005930']  # 현재 보유 종목 제외
)

# 최적 포지션 사이즈 계산
position_size = strategy.calculate_optimal_position_size(
    ticker='000660',
    available_cash=5_000_000,
    ai_score=0.75
)

# 시장 상황 평가
market_condition = strategy.evaluate_market_condition('2025-06-01')
print(f"시장 상황: {market_condition['condition']}")
```

## ⚙️ 설정 시스템

### 기본 설정 프리셋

```python
from hanlyang_stock.config.backtest_settings import get_backtest_config

# 균형잡힌 설정 (기본)
balanced = get_backtest_config('balanced')

# 보수적 설정 (낮은 리스크)
conservative = get_backtest_config('conservative')
print(f"손실제한: {conservative.stop_loss_rate*100}%")
print(f"최대 보유: {conservative.max_positions}개 종목")

# 공격적 설정 (높은 리스크)
aggressive = get_backtest_config('aggressive')
print(f"포지션 비율: {aggressive.position_size_ratio*100}%")
```

### 커스텀 설정

```python
from hanlyang_stock.config.backtest_settings import create_custom_config

# 나만의 설정 생성
my_config = create_custom_config(
    initial_capital=20_000_000,     # 2000만원
    max_positions=7,                # 7개 종목까지
    stop_loss_rate=-0.04,          # -4% 손실제한
    ai_enabled=True,
    min_ai_confidence=0.70,         # 높은 신뢰도만
    investment_amounts={
        '최고신뢰': 1_200_000,      # AI 점수 0.8+ → 120만원
        '고신뢰': 1_000_000,        # AI 점수 0.7-0.8 → 100만원
        '중신뢰': 800_000,          # AI 점수 0.65-0.7 → 80만원
        '저신뢰': 600_000           # AI 점수 0.65 미만 → 60만원
    }
)

# AI 점수별 투자 금액 확인
amount, level = my_config.get_investment_amount(0.85)
print(f"AI 점수 0.85 → {amount:,}원 ({level})")
```

## 🔄 실제 거래 시스템과의 통합

모듈화된 구조 덕분에 백테스트와 실제 거래 시스템 간의 코드 공유가 매우 쉽습니다:

```python
# 백테스트에서 검증된 전략을 실제 거래에 적용
from hanlyang_stock.strategy.selector import get_stock_selector
from hanlyang_stock.strategy.executor import execute_buy_strategy, execute_sell_strategy

# 종목 선정 로직 (백테스트와 동일)
selector = get_stock_selector()
selector.set_backtest_mode(False)  # 실시간 모드
selected_stocks = selector.select_stocks_for_buy()

# 실제 거래 실행
buy_results = execute_buy_strategy()
sell_results = execute_sell_strategy()
```

## 📊 성과 분석 예시

### 기본 성과 지표

```python
# 백테스트 실행 후
results = engine.run_backtest('2025-05-01', '2025-06-01', ai_enabled=True)

print(f"📈 총 수익률: {results['total_return']*100:+.2f}%")
print(f"📈 연환산 수익률: {results['annualized_return']*100:+.2f}%")
print(f"📉 최대 낙폭: {results['max_drawdown']*100:.2f}%")
print(f"📊 샤프 비율: {results['sharpe_ratio']:.3f}")
print(f"🔄 총 거래: {results['total_trades']}회")
print(f"🎯 승률: {results['win_rate']*100:.1f}%")
print(f"💰 거래당 평균 손익: {results['avg_profit_per_trade']:+,.0f}원")
print(f"📅 평균 보유: {results['avg_holding_days']:.1f}일")
```

### AI 성과 분석

```python
if 'ai_performance' in results:
    ai_perf = results['ai_performance']
    
    # 신뢰도별 성과
    print("\n🤖 AI 신뢰도별 성과:")
    for level, data in ai_perf['confidence_performance'].items():
        if data['trade_count'] > 0:
            print(f"   {level}: {data['trade_count']}회 거래")
            print(f"      승률: {data['win_rate']*100:.1f}%")
            print(f"      평균 수익률: {data['avg_profit_rate']:+.2f}%")
    
    # AI 점수별 성과
    print("\n📊 AI 점수 구간별 성과:")
    score_ranges = ai_perf['ai_score_performance']
    for range_name, data in score_ranges.items():
        if data['trade_count'] > 0:
            range_labels = {
                'very_high': '매우 높음 (0.8+)',
                'high': '높음 (0.7-0.8)',
                'medium': '중간 (0.6-0.7)',
                'low': '낮음 (0.6 미만)'
            }
            label = range_labels.get(range_name, range_name)
            print(f"   {label}: {data['trade_count']}회")
            print(f"      승률: {data['win_rate']*100:.1f}%")
            print(f"      총 손익: {data['total_profit']:+,.0f}원")
```

## 🧪 테스트 및 검증

### 통합 테스트

```bash
# 전체 시스템 테스트
python test_modular_backtest.py

# 결과 예시:
# 🧪 테스트 결과 요약
# ==================
# 총 테스트: 8개
# 통과: 8개
# 실패: 0개
# 성공률: 100.0%
```

### 성능 벤치마크

```bash
# 기존 엔진과 성능 비교
python benchmark_backtest.py

# 결과 예시:
# 🏁 벤치마크 결과 요약
# ==================
# 🔸 단기 테스트 (5일)
#    🔧 모듈화된 엔진: 12.5초
#    📊 기존 엔진: 13.8초
#    🚀 9.4% 더 빠름
```

## 🎮 대화형 사용법

```bash
python run_modular_backtest.py
```

```
🚀 모듈화된 백테스트 엔진
==========================================

실행할 백테스트를 선택하세요:
1) 간단한 백테스트 (기본 설정, 10일)
2) 커스텀 백테스트 (사용자 설정, 1개월)  
3) 비교 백테스트 (AI vs 기술적 분석)
4) 대화형 백테스트 (사용자 입력)
5) 종료

선택 (1-5): 4

📅 백테스트 기간 설정:
1) 최근 1주일  2) 최근 1개월  3) 직접 입력 (1/2/3): 2

💰 초기 자본 설정:
1) 1000만원  2) 2000만원  3) 직접 입력 (1/2/3): 2

🤖 AI 기능 설정:
AI 기능 사용? (y/n): y

📋 설정 확인:
   기간: 2025-05-15 ~ 2025-06-15
   초기 자본: 20,000,000원
   AI 기능: 활성화

실행하시겠습니까? (y/n): y

🚀 백테스팅 시작...
```

## 🔄 기존 시스템 대비 개선 사항

### ✅ 기능적 개선

1. **모듈화**: 기능별 독립적인 모듈로 분리
2. **재사용성**: 각 모듈을 다른 프로젝트에서도 활용 가능
3. **확장성**: 새로운 전략이나 지표 추가가 용이
4. **테스트 용이성**: 각 모듈별 단위 테스트 가능
5. **캐싱**: 데이터 조회 성능 최적화
6. **설정 관리**: 유연한 설정 시스템

### 🚀 성능 개선

- **데이터 캐싱**: 중복 조회 최소화로 속도 향상
- **메모리 최적화**: 효율적인 메모리 사용
- **병렬 처리**: 가능한 부분에서 동시 실행
- **코드 최적화**: 불필요한 연산 제거

### 🔧 유지보수성 개선

- **명확한 책임 분리**: 각 모듈의 역할이 명확
- **의존성 관리**: 모듈 간 결합도 최소화
- **문서화**: 각 모듈별 상세한 문서
- **테스트 커버리지**: 포괄적인 테스트 suite

## 🚀 향후 확장 계획

### Phase 4: 고급 기능 추가

1. **실시간 백테스트**: 실제 거래와 동시 실행
2. **다중 전략**: 여러 전략 동시 테스트 및 비교
3. **포트폴리오 최적화**: 현대 포트폴리오 이론 적용
4. **고급 리스크 관리**: VaR, CVaR 등 리스크 지표
5. **시각화 대시보드**: 실시간 성과 모니터링

### Phase 5: 클라우드 및 분산 처리

1. **클라우드 배포**: AWS, GCP 등 클라우드 환경 지원
2. **분산 백테스트**: 대용량 데이터 병렬 처리
3. **API 서비스**: RESTful API로 서비스화
4. **웹 인터페이스**: 브라우저 기반 사용자 인터페이스

## 📚 추가 리소스

- **API 문서**: 각 모듈의 상세 API 문서
- **예제 코드**: 다양한 사용 사례별 예제
- **성능 가이드**: 최적 성능을 위한 설정 가이드
- **문제 해결**: 자주 발생하는 문제와 해결책

---

> 💡 **시작하기**: `python run_modular_backtest.py`를 실행하여 대화형 인터페이스로 쉽게 백테스트를 시작해보세요!

> 🔧 **개발자**: 각 모듈을 독립적으로 import하여 자신만의 백테스트 시스템을 구축할 수 있습니다.

> 📊 **분석가**: 다양한 설정과 시나리오로 전략을 검증하고 최적화할 수 있습니다.
