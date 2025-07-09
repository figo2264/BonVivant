# 기술적 점수 가중치 시스템 업데이트

## 개요
기술적 점수 계산에 사용되는 가중치를 백테스트/전략 설정에서 조정할 수 있도록 수정했습니다.

## 변경사항

### 1. 수정된 파일
- `hanlyang_stock/analysis/technical.py`
- `hanlyang_stock/config/backtest_settings.py`
- `hanlyang_stock/config/strategy_settings.py`
- `hanlyang_stock/strategy/selector.py`
- `run_modular_backtest.py`

### 2. 주요 변경내용

#### TechnicalAnalyzer 클래스
- `get_technical_score()` 메서드가 `config` 파라미터를 받을 수 있도록 수정
- 설정이 전달되면 설정의 가중치를 사용하고, 없으면 기본값 사용

```python
def get_technical_score(self, ticker: str, holding_days: int = 0, 
                      entry_price: Optional[float] = None, config: Any = None) -> float:
```

#### BacktestConfig/StrategyConfig
- `technical_score_weights` 속성 추가
- 프리셋별로 다른 가중치 설정

## 가중치 시스템

### 기본 가중치
```python
{
    'trend': 0.25,           # 추세 (25%)
    'momentum': 0.20,        # 모멘텀 (20%)
    'oversold': 0.20,        # 과매도 (20%)
    'parabolic_sar': 0.20,   # 파라볼릭 SAR (20%)
    'volume': 0.10,          # 거래량 (10%)
    'volatility': 0.05       # 변동성 (5%)
}
```

### 프리셋별 가중치

#### Conservative (보수적)
- 추세와 SAR을 중시 (안정성 위주)
- trend: 30%, parabolic_sar: 25%

#### Aggressive (공격적)
- 모멘텀과 과매도를 중시 (단기 수익 위주)
- momentum: 25%, oversold: 25%

#### Balanced (균형)
- 모든 지표를 균형있게 사용
- trend: 25%, momentum: 20%, oversold: 20%, parabolic_sar: 20%, volume: 10%, volatility: 5%

#### Small Capital (소액투자)
- 기본 가중치와 동일 (균형 유지)

## 사용 방법

### 백테스트에서
```python
from hanlyang_stock.config.backtest_settings import get_backtest_config

# 프리셋 사용
config = get_backtest_config('conservative')  # 보수적 가중치 자동 적용

# 커스텀 가중치
from hanlyang_stock.config.backtest_settings import create_custom_config
custom_config = create_custom_config(
    technical_score_weights={
        'trend': 0.10,
        'momentum': 0.30,
        'oversold': 0.30,
        'parabolic_sar': 0.20,
        'volume': 0.05,
        'volatility': 0.05
    }
)
```

### 전략 실행에서
```python
from hanlyang_stock.config.strategy_settings import get_strategy_config

# 프리셋 사용
config = get_strategy_config('aggressive')  # 공격적 가중치 자동 적용
```

## 영향

1. **백테스트**: 프리셋별로 다른 기술적 점수가 계산되어 종목 선정에 영향
2. **실제 전략**: 전략 설정에 따라 기술적 점수 계산 방식이 달라짐
3. **최적화**: 가중치를 조정하여 전략을 최적화할 수 있음

## 테스트 결과

삼성전자(005930) 기준:
- 기본: 0.619
- Conservative: 0.649 (+3.0%)
- Balanced: 0.619 (+0.0%)
- Aggressive: 0.589 (-3.0%)

프리셋에 따라 같은 종목도 다른 점수를 받게 되어, 전략의 특성을 더 잘 반영할 수 있습니다.
