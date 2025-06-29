# 소액 투자(100만원) 백테스트 문제 분석 보고서

## 1. 문제 상황

### 1.1 오류 로그
```
📊 기술적 분석 상위 1개 선정
   사용 가능 현금: 800,000원
   종목당 기본 투자: 114,286원
   종목당 최대 포지션: 300,000원
   ⚠️ 086820: 최소 투자금액 부족
```

### 1.2 설정한 값
- 초기 자본: 1,000,000원
- 안전 자금: 100,000원 
- 투자 비율: 80%
- 최대 보유 종목: 3개
- 투자 금액:
  - 최고신뢰: 120,000원
  - 고신뢰: 90,000원
  - 중신뢰: 60,000원
  - 저신뢰: 40,000원

## 2. 문제 원인 분석

### 2.1 백테스트 엔진(engine.py)의 하드코딩된 값들

#### 투자금액 계산 로직 (316-320행)
```python
# 종목당 투자 금액 계산
available_cash = self.portfolio.cash * 0.8  # 현금의 80% 사용
investment_per_stock = available_cash / max(available_slots + len(current_holdings), 1)
```
- **문제**: `investment_amounts` 설정을 무시하고 단순 나눗셈으로 계산
- **결과**: 800,000원 ÷ 7 = 114,286원

#### 안전자금 하드코딩 (428-433행)
```python
remaining_balance = self.portfolio.cash - total_invested - 2_000_000  # 200만원 안전자금
if remaining_balance < investment_amount:
    if remaining_balance < 300_000:  # 최소 투자금액
        print(f"   ⚠️ {ticker}: 최소 투자금액 부족")
```
- **문제**: 200만원 안전자금은 100만원 투자금에 비해 과도함
- **문제**: 30만원 최소 투자금액도 높음

### 2.2 실행 모듈(executor.py)의 하드코딩된 값들

#### 안전자금 (823-824행)
```python
remaining_balance = current_balance - total_invested - 2_000_000  # 200만원 안전자금
```

#### 최소 투자금액 (843-845행)
```python
if remaining_balance < 300_000:  # 최소 투자금액
    print(f"⚠️ {ticker}: 최소 투자금액 부족")
```

#### 투자금액 결정 로직 (1000-1048행)
```python
if score >= 0.80:           # 최고신뢰: 80만원
    investment_amount = 800_000    
elif score >= 0.70:         # 고신뢰: 60만원
    investment_amount = 600_000    
elif score >= 0.65:         # 중신뢰: 40만원
    investment_amount = 400_000    
else:                       # 저신뢰: 30만원
    investment_amount = 300_000
```

### 2.3 근본 원인
**백테스트 엔진과 실행 모듈이 우리가 설정한 `investment_amounts`와 `safety_cash_amount`를 읽어오지 않고 하드코딩된 값을 사용**

## 3. 해결 방안

### 3.1 코드 수정이 필요한 부분

#### engine.py 수정 필요
```python
# 현재 (하드코딩)
remaining_balance = self.portfolio.cash - total_invested - 2_000_000

# 수정 후 (설정에서 읽기)
from ..utils.storage import get_data_manager
data_manager = get_data_manager()
strategy_data = data_manager.get_data()
safety_cash_amount = strategy_data.get('safety_cash_amount', 1_000_000)
remaining_balance = self.portfolio.cash - total_invested - safety_cash_amount
```

#### executor.py 수정 필요
```python
# 현재 (하드코딩)
if score >= 0.80:
    investment_amount = 800_000

# 수정 후 (설정에서 읽기)
investment_amounts = strategy_data.get('investment_amounts', {})
investment_amount, confidence_level = self._get_investment_amount_from_config(score, investment_amounts)
```

### 3.2 임시 해결책 (코드 수정 없이)

#### 방법 1: 최적화된 설정 사용
```python
SMALL_CAPITAL_CONFIG = BacktestConfig(
    initial_capital=1_000_000,
    max_positions=2,            # 2개로 줄임
    position_size_ratio=0.9,    # 90%로 늘림
    safety_cash_amount=50_000,  # 5만원으로 줄임
    investment_amounts={
        '최고신뢰': 200_000,    # 20만원
        '고신뢰': 150_000,      # 15만원
        '중신뢰': 100_000,      # 10만원
        '저신뢰': 80_000       # 8만원
    }
)
```

#### 방법 2: 스케일링 방식
```python
def run_scaled_backtest():
    """10배로 실행 후 결과를 1/10로 스케일링"""
    # 1000만원으로 실행
    results = run_backtest_with_10x_capital()
    
    # 결과 스케일링
    results['initial_capital'] /= 10
    results['final_value'] /= 10
    results['total_profit'] /= 10
    
    return results
```

#### 방법 3: Wrapper 함수
```python
def create_small_capital_engine():
    """백테스트 엔진을 감싸서 설정 주입"""
    engine = BacktestEngine(1_000_000, 0.003)
    
    # 메서드 오버라이드로 설정값 주입
    # ... (상세 구현)
    
    return engine
```

## 4. 권장사항

### 4.1 단기 해결책
1. **최소 200만원 이상**으로 백테스트 실행
2. 스케일링 방식으로 100만원 시뮬레이션
3. 투자 종목 수를 1-2개로 제한

### 4.2 장기 해결책
1. engine.py와 executor.py 수정
2. strategy_data에서 모든 설정을 읽어오도록 리팩토링
3. 하드코딩된 값들을 설정 가능한 파라미터로 변경

## 5. 검증 필요 사항

### 5.1 설정값 전달 확인
- `strategy_data['investment_amounts']`가 제대로 저장되는지
- `strategy_data['safety_cash_amount']`가 제대로 저장되는지
- 백테스트 엔진이 이 값들을 읽을 수 있는지

### 5.2 계산 로직 확인
- 종목당 투자금액 계산 방식
- 안전자금 차감 로직
- 최소 투자금액 체크 로직

## 6. 결론

현재 시스템은 **1000만원 이상의 투자금을 가정**하고 설계되어 있으며, 소액 투자(100만원)를 지원하려면:

1. **즉시 적용 가능**: 200만원 이상으로 투자금 증액
2. **부분 수정 필요**: 하드코딩된 값들을 설정에서 읽도록 수정
3. **전체 리팩토링**: 모든 금액 관련 로직을 동적으로 처리

백테스트의 신뢰성을 위해서는 **코드 수정이 필수적**입니다.