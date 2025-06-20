# 🎯 적응형 전략 (Adaptive Strategy)

## 📋 개요

**목적**: 시장 상황에 따라 매매 전략을 동적으로 조정하여 수익은 극대화하고 손실은 최소화

**핵심 개념**: 
- 시장 추세 자동 판단 (상승/하락/횡보)
- 변동성 수준 측정
- 상황별 파라미터 자동 조정
- 위험 시장에서 매매 중단

## 🌊 시장 상황 분류

### 1. 시장 추세 판단

```python
class MarketCondition:
    """시장 상황 판단 클래스"""
    
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
    
    def get_market_trend(self, lookback_days=20):
        """시장 추세 판단"""
        # KOSPI 지수 데이터 가져오기
        kospi_data = self.data_fetcher.get_index_data('KOSPI', days=lookback_days+5)
        
        if len(kospi_data) < lookback_days:
            return 'UNKNOWN'
        
        # 이동평균선 계산
        ma5 = kospi_data['close'].rolling(5).mean().iloc[-1]
        ma20 = kospi_data['close'].rolling(20).mean().iloc[-1]
        current_price = kospi_data['close'].iloc[-1]
        
        # 20일 수익률
        return_20d = (current_price - kospi_data['close'].iloc[-20]) / kospi_data['close'].iloc[-20]
        
        # 추세 판단
        if ma5 > ma20 and current_price > ma20:
            if return_20d > 0.05:
                return 'STRONG_BULL'  # 강한 상승장
            else:
                return 'BULL'  # 상승장
        elif ma5 < ma20 and current_price < ma20:
            if return_20d < -0.05:
                return 'STRONG_BEAR'  # 강한 하락장
            else:
                return 'BEAR'  # 하락장
        else:
            return 'SIDEWAYS'  # 횡보장
```

### 2. 변동성 측정

```python
def calculate_market_volatility(self, days=20):
    """시장 변동성 계산 (KOSPI 기준)"""
    kospi_data = self.data_fetcher.get_index_data('KOSPI', days=days+5)
    
    # 일간 수익률의 표준편차
    daily_returns = kospi_data['close'].pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252)  # 연율화
    
    # VIX 지수 활용 (가능한 경우)
    vix = self.get_vix_index()
    
    # 변동성 레벨 분류
    if vix:
        if vix > 30:
            return 'EXTREME'
        elif vix > 20:
            return 'HIGH'
        elif vix > 15:
            return 'NORMAL'
        else:
            return 'LOW'
    else:
        # VIX 없으면 역사적 변동성으로 판단
        if volatility > 0.25:
            return 'HIGH'
        elif volatility > 0.15:
            return 'NORMAL'
        else:
            return 'LOW'
```

## 🔧 상황별 전략 조정

### 1. 시장 추세별 매개변수

```python
MARKET_PARAMS = {
    'STRONG_BULL': {
        'max_positions': 5,          # 최대 보유 종목 (공격적)
        'stop_loss_rate': -0.07,     # 손절선 완화
        'holding_days': 5,           # 보유 기간 연장
        'min_technical_score': 0.60, # 진입 기준 완화
        'position_size_multiplier': 1.2,  # 포지션 크기 증가
        'enable_pyramiding': True    # 피라미딩 활성화
    },
    'BULL': {
        'max_positions': 4,
        'stop_loss_rate': -0.05,
        'holding_days': 4,
        'min_technical_score': 0.65,
        'position_size_multiplier': 1.0,
        'enable_pyramiding': True
    },
    'SIDEWAYS': {
        'max_positions': 3,
        'stop_loss_rate': -0.04,     # 손절선 강화
        'holding_days': 3,
        'min_technical_score': 0.70, # 진입 기준 강화
        'position_size_multiplier': 0.8,
        'enable_pyramiding': False
    },
    'BEAR': {
        'max_positions': 2,
        'stop_loss_rate': -0.03,
        'holding_days': 2,
        'min_technical_score': 0.75,
        'position_size_multiplier': 0.6,
        'enable_pyramiding': False
    },
    'STRONG_BEAR': {
        'max_positions': 0,          # 매매 중단
        'stop_loss_rate': -0.02,
        'holding_days': 1,
        'min_technical_score': 0.85,
        'position_size_multiplier': 0.0,
        'enable_pyramiding': False
    }
}
```

### 2. 변동성별 조정

```python
VOLATILITY_ADJUSTMENTS = {
    'LOW': {
        'stop_loss_multiplier': 1.2,    # 손절선 완화
        'position_size_multiplier': 1.1,
        'min_volume_surge': 1.3         # 거래량 기준 완화
    },
    'NORMAL': {
        'stop_loss_multiplier': 1.0,
        'position_size_multiplier': 1.0,
        'min_volume_surge': 1.5
    },
    'HIGH': {
        'stop_loss_multiplier': 0.8,    # 손절선 강화
        'position_size_multiplier': 0.7,
        'min_volume_surge': 2.0         # 거래량 기준 강화
    },
    'EXTREME': {
        'stop_loss_multiplier': 0.5,
        'position_size_multiplier': 0.3,
        'min_volume_surge': 2.5,
        'trade_enabled': False          # 극단적 변동성 시 매매 중단
    }
}
```

## 📊 통합 구현

### 1. MarketAdaptiveStrategy 클래스

```python
class MarketAdaptiveStrategy:
    """시장 적응형 전략 관리자"""
    
    def __init__(self):
        self.market_condition = MarketCondition()
        self.base_params = self._load_base_params()
    
    def get_current_params(self):
        """현재 시장 상황에 맞는 파라미터 반환"""
        # 시장 추세 판단
        trend = self.market_condition.get_market_trend()
        volatility = self.market_condition.calculate_market_volatility()
        
        print(f"📊 시장 상황: {trend} / 변동성: {volatility}")
        
        # 기본 파라미터 로드
        params = self.base_params.copy()
        
        # 추세별 조정
        trend_params = MARKET_PARAMS.get(trend, MARKET_PARAMS['SIDEWAYS'])
        params.update(trend_params)
        
        # 변동성별 조정
        vol_adjustments = VOLATILITY_ADJUSTMENTS.get(volatility, VOLATILITY_ADJUSTMENTS['NORMAL'])
        
        # 손절선 조정
        params['stop_loss_rate'] *= vol_adjustments['stop_loss_multiplier']
        
        # 포지션 크기 조정
        params['position_size_multiplier'] *= vol_adjustments['position_size_multiplier']
        
        # 극단적 상황 체크
        if trend == 'STRONG_BEAR' or volatility == 'EXTREME':
            params['trade_enabled'] = False
            print("⚠️ 위험 시장 - 매매 중단")
        else:
            params['trade_enabled'] = True
        
        return params, trend, volatility
```

### 2. Executor 수정

```python
# executor.py의 BuyExecutor.execute() 메서드 수정
def execute(self) -> Dict[str, Any]:
    """매수 전략 실행 (적응형)"""
    # 시장 상황 체크
    adaptive_strategy = MarketAdaptiveStrategy()
    current_params, market_trend, volatility = adaptive_strategy.get_current_params()
    
    # 매매 가능 여부 확인
    if not current_params.get('trade_enabled', True):
        print(f"🚫 시장 상황 불안정 - 매수 중단 (추세: {market_trend}, 변동성: {volatility})")
        self.notifier.notify_trade_suspended(market_trend, volatility)
        return {'bought_count': 0, 'total_invested': 0, 'reason': 'market_unstable'}
    
    # 파라미터 적용
    self.max_positions = current_params['max_positions']
    self.min_technical_score = current_params['min_technical_score']
    self.position_size_multiplier = current_params['position_size_multiplier']
    
    print(f"📊 적응형 파라미터 적용:")
    print(f"   - 최대 포지션: {self.max_positions}")
    print(f"   - 최소 기술점수: {self.min_technical_score}")
    print(f"   - 포지션 크기 배수: {self.position_size_multiplier}")
    
    # 기존 매수 로직 계속...
```

## 🎯 특수 상황 대응

### 1. 급락장 대응

```python
def check_market_crash(self):
    """시장 급락 감지"""
    kospi_1d_return = self.get_index_return('KOSPI', 1)
    kospi_3d_return = self.get_index_return('KOSPI', 3)
    
    # 급락 조건
    if kospi_1d_return < -0.03 or kospi_3d_return < -0.05:
        return True, "market_crash_detected"
    
    return False, None
```

### 2. 섹터 로테이션

```python
def get_sector_strength(self):
    """섹터별 강도 분석"""
    sectors = ['IT', 'BIO', 'FINANCE', 'MANUFACTURE', 'CONSUMER']
    sector_scores = {}
    
    for sector in sectors:
        # 섹터 지수 또는 대표 종목들의 평균 성과
        sector_performance = self.calculate_sector_performance(sector)
        sector_scores[sector] = sector_performance
    
    # 강한 섹터 우선 선정
    return sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
```

## 📈 예상 효과

### 장점
1. **위험 관리**: 하락장/고변동성 시장에서 손실 최소화
2. **수익 극대화**: 상승장에서 공격적 운용으로 수익 증대
3. **자동 조정**: 매일 시장 상황 판단하여 자동 대응

### 단점
1. **복잡성 증가**: 시스템 복잡도 상승
2. **지표 의존성**: KOSPI 지수 데이터 필요
3. **후행성**: 시장 변화 감지에 시차 존재

## 🧪 백테스트 시나리오

1. **2020년 코로나 급락장**
   - 매매 중단 시점
   - 재진입 시점
   - 전체 수익률 비교

2. **2021년 상승장**
   - 포지션 확대 효과
   - 수익률 개선도

3. **2022년 하락장**
   - 손실 방어 효과
   - 현금 비중 변화

## 📅 구현 일정

- **개발**: 4-5시간
  - 시장 지수 데이터 수집: 1시간
  - MarketCondition 클래스: 2시간
  - Executor 통합: 1-2시간
- **테스트**: 2시간
- **백테스트**: 3시간
- **실전 적용**: Phase 2 (Phase 1 완료 후)

## 🔍 모니터링 지표

적용 후 추적할 지표:
- 일별 시장 상황 판단 로그
- 파라미터 조정 이력
- 매매 중단 횟수 및 기간
- 시장 상황별 수익률
- 최대 낙폭(MDD) 변화

## 🚀 추가 개선 아이디어

1. **AI 시장 예측**: 머신러닝으로 시장 방향 예측
2. **다중 지표 활용**: KOSDAQ, 달러 지수, 금리 등
3. **적응 속도 조절**: 시장 변화 감지 민감도 조정
4. **개별 종목 베타**: 시장 대비 민감도 고려
