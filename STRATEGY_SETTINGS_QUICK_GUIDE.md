# 전략 설정 간단 가이드

## 변경 사항
- `strategy.py`가 이제 설정 파일 기반으로 작동합니다
- 설정값은 `hanlyang_stock/config/strategy_settings.py`에서 관리
- JSON 파일(`strategy_data.json`)은 런타임 데이터만 저장

## 사용법

### 1. 기본 실행 (balanced 프리셋)
```bash
python strategy.py
```

### 2. 보수적 전략으로 실행
```bash
export STRATEGY_PRESET=conservative
python strategy.py
```

### 3. 공격적 전략으로 실행
```bash
export STRATEGY_PRESET=aggressive
python strategy.py
```

## 프리셋 비교

| 설정 | Conservative | Balanced | Aggressive |
|-----|--------------|----------|------------|
| 최대 종목 | 2개 | 3개 | 5개 |
| 손실 제한 | -3% | -5% | -8% |
| 최소 시가총액 | 5000억 | 1000억 | 500억 |
| 피라미딩 | 비활성화 | 활성화 | 활성화(50%) |

## 설정 변경하기

`hanlyang_stock/config/strategy_settings.py` 파일을 직접 수정:

```python
# 예: Balanced 설정 수정
BALANCED_STRATEGY = StrategyConfig(
    max_selections=4,  # 3 → 4개로 변경
    stop_loss_rate=-0.04,  # -5% → -4%로 변경
)
```

## 런타임 데이터
- `holding_period`: 종목별 보유 기간
- `performance_log`: 매매 기록
- `purchase_info`: 매수 정보

이 데이터들은 계속 `strategy_data.json`에 저장됩니다.
