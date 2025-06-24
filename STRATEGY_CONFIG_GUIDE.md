# 전략 설정 관리 가이드

## 개요

기존의 JSON 파일 기반 설정 관리에서 Python 코드 기반 설정 관리로 전환하여:
- **형상관리(Git)에 포함**되어 설정 변경 이력 추적 가능
- **타입 안정성** 보장 (type hints 사용)
- **설정값 그룹화** 및 구조화
- **프리셋 제공** (conservative, balanced, aggressive)
- **IDE 자동완성** 지원

## 파일 구조

```
hanlyang_stock/
├── config/
│   ├── strategy_settings.py    # 전략 설정 관리 (신규)
│   └── backtest_settings.py    # 백테스트 설정 관리
├── utils/
│   └── storage.py              # 런타임 데이터만 관리
└── strategy_data.json          # 런타임 데이터만 저장
```

## 설정 파일 분리

### 1. 설정값 (strategy_settings.py에서 관리)
- 전략 파라미터
- 기술적 분석 설정
- 하이브리드 전략 설정
- 피라미딩 설정
- 품질 필터 설정

### 2. 런타임 데이터 (strategy_data.json에서 관리)
- holding_period: 종목별 보유 기간
- performance_log: 성과 로그
- purchase_info: 매수 정보

## 사용 방법

### 1. 기본 사용 (balanced 프리셋)
```python
from hanlyang_stock.utils.storage import get_data_manager

# 기본 설정으로 사용
data_manager = get_data_manager()
strategy_data = data_manager.get_data()
```

### 2. 프리셋 변경
```python
# 보수적 전략 사용
data_manager = get_data_manager(preset='conservative')

# 공격적 전략 사용
data_manager = get_data_manager(preset='aggressive')
```

### 3. 환경변수로 프리셋 설정
```bash
# 보수적 전략으로 실행
export STRATEGY_PRESET=conservative
python strategy_v2.py

# 공격적 전략으로 실행
export STRATEGY_PRESET=aggressive
python strategy_v2.py
```

### 4. 커스텀 설정 생성
`strategy_settings.py`에서 직접 수정:
```python
# 커스텀 프리셋 추가
CUSTOM_STRATEGY = StrategyConfig(
    max_selections=4,
    stop_loss_rate=-0.06,
    technical_params=TechnicalParameters(
        min_technical_score=0.70,
        min_close_days=6
    )
)

STRATEGY_PRESETS['custom'] = CUSTOM_STRATEGY
```

## 프리셋 비교

| 설정 항목 | Conservative | Balanced | Aggressive |
|---------|-------------|----------|-----------|
| 최대 선정 종목 | 2개 | 3개 | 5개 |
| 손실 제한 | -3% | -5% | -8% |
| 최대 보유기간 (기본) | 3일 | 5일 | 7일 |
| 최소 기술점수 | 0.75 | 0.65 | 0.60 |
| 최소 시가총액 | 5000억 | 1000억 | 500억 |
| 피라미딩 | 비활성화 | 활성화 | 활성화 (50%까지) |

## 마이그레이션 가이드

### 1. 기존 strategy.py 사용자
```bash
# 기존 파일 백업
cp strategy.py strategy_backup.py

# 새 버전 사용
python strategy_v2.py
```

### 2. 기존 설정값 확인
```python
# 기존 JSON 설정값 확인
cat strategy_data.json

# 새 설정 시스템에서 확인
python -c "from hanlyang_stock.config.strategy_settings import get_strategy_config; print(get_strategy_config().to_dict())"
```

### 3. 설정값 커스터마이징
기존에 JSON을 직접 수정했다면, 이제는 `strategy_settings.py`에서 수정:
- 특정 값만 변경: 해당 프리셋의 값 수정
- 새로운 프리셋 추가: CUSTOM_STRATEGY 생성

## 장점

1. **버전 관리**: Git으로 설정 변경 이력 추적
2. **타입 안정성**: 잘못된 타입 입력 방지
3. **구조화**: 관련 설정들을 그룹으로 관리
4. **재사용성**: 여러 환경에서 동일한 설정 사용
5. **문서화**: 각 설정값에 대한 주석과 설명
6. **유지보수**: 중앙화된 설정 관리

## 주의사항

1. `strategy_data.json`은 이제 런타임 데이터만 저장
2. 설정값 변경은 `strategy_settings.py`에서만 수행
3. 프리셋 변경 시 기존 포지션에는 영향 없음
4. 백테스트와 실전략 설정 분리 관리
