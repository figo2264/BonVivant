# 📈 추세 강도 필터 (Trend Strength Filter)

## 📋 개요

**목적**: 단순한 7일 최저점 + 양봉 조건을 넘어서, 진정한 추세 반전을 확인하는 강화된 필터링 시스템

**핵심 개선점**: 
- 양봉의 크기와 품질 검증
- 거래량 증가 확인
- RSI 반등 신호 확인
- 지지선 근처 여부 확인

## 🎯 구현 상세

### 1. 양봉 품질 검증

**현재 로직**:
```python
(today_data['close'] > today_data['open'])  # 단순 양봉 여부만 확인
```

**개선된 로직**:
```python
def validate_bullish_candle(row):
    """품질 높은 양봉 확인"""
    # 1. 양봉 크기: 최소 2% 이상 상승
    candle_size = (row['close'] - row['open']) / row['open']
    if candle_size < 0.02:
        return False
    
    # 2. 긴 아래꼬리 확인 (망치형 캔들)
    lower_wick = (row['open'] - row['low']) / row['open']
    upper_wick = (row['high'] - row['close']) / row['close']
    
    if lower_wick > upper_wick * 2:  # 아래꼬리가 위꼬리의 2배 이상
        return True
    
    # 3. 실체가 전체 캔들의 60% 이상
    body_ratio = abs(row['close'] - row['open']) / (row['high'] - row['low'])
    return body_ratio >= 0.6
```

### 2. 거래량 급증 확인

**추가할 조건**:
```python
def check_volume_surge(data, ticker):
    """거래량 급증 여부 확인"""
    ticker_data = data[data['ticker'] == ticker].sort_values('timestamp')
    
    # 5일 평균 거래량
    avg_volume_5d = ticker_data['volume'].tail(6).iloc[:-1].mean()
    current_volume = ticker_data['volume'].iloc[-1]
    
    # 조건:
    # 1. 당일 거래량이 5일 평균의 1.5배 이상
    # 2. 거래대금도 함께 증가 (허수 거래 방지)
    volume_ratio = current_volume / avg_volume_5d
    
    avg_trade_amount_5d = ticker_data['trade_amount'].tail(6).iloc[:-1].mean()
    current_trade_amount = ticker_data['trade_amount'].iloc[-1]
    trade_amount_ratio = current_trade_amount / avg_trade_amount_5d
    
    return volume_ratio >= 1.5 and trade_amount_ratio >= 1.3
```

### 3. RSI 반등 신호

**추가할 조건**:
```python
def check_rsi_reversal(data, ticker):
    """RSI 반등 신호 확인"""
    ticker_data = data[data['ticker'] == ticker].sort_values('timestamp')
    
    # 최근 3일간 RSI 추세
    recent_rsi = ticker_data['rsi_14'].tail(3).values
    
    # 조건:
    # 1. RSI가 30 근처에서 반등 (과매도 → 상승)
    # 2. RSI가 상승 추세
    if len(recent_rsi) < 3:
        return False
    
    # RSI 30~40 구간에서 상승 중
    if 30 <= recent_rsi[-1] <= 40:
        return recent_rsi[-1] > recent_rsi[-2] > recent_rsi[-3]
    
    # RSI가 30 미만에서 반등
    if recent_rsi[-2] < 30 and recent_rsi[-1] > recent_rsi[-2]:
        return True
    
    return False
```

### 4. 지지선 근처 확인

**추가할 조건**:
```python
def check_near_support(row, market_data, ticker):
    """지지선 근처 여부 확인"""
    ticker_data = market_data[market_data['ticker'] == ticker]
    
    # 최근 20일 저점들 추출
    recent_lows = ticker_data['low'].tail(20).values
    current_price = row['close']
    
    # 지지선 후보: 2번 이상 터치한 가격대
    support_levels = []
    for i in range(len(recent_lows)):
        count = sum(1 for low in recent_lows if abs(low - recent_lows[i])/recent_lows[i] < 0.01)
        if count >= 2:
            support_levels.append(recent_lows[i])
    
    if not support_levels:
        return True  # 지지선이 없으면 통과
    
    # 현재가가 가장 가까운 지지선의 3% 이내
    nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
    distance_ratio = abs(current_price - nearest_support) / nearest_support
    
    return distance_ratio <= 0.03
```

## 🔧 통합 구현

**selector.py의 enhanced_stock_selection 메서드 수정 위치**:

```python
# 기존 코드 이후에 추가 필터 적용
traditional_candidates = today_data[
    (today_data[f'{min_close_days}d_min_close'] == today_data['close']) &
    (today_data[f'{ma_period}d_ma'] > today_data['close']) &
    (today_data['close'] > today_data['open'])
].copy()

# 추세 강도 필터 적용
print("🔍 추세 강도 필터 적용 중...")
strong_candidates = []

for _, row in traditional_candidates.iterrows():
    ticker = row['ticker']
    
    # 1. 양봉 품질 검증
    if not validate_bullish_candle(row):
        print(f"   ❌ {ticker}: 양봉 품질 부족")
        continue
    
    # 2. 거래량 급증 확인
    if not check_volume_surge(market_data, ticker):
        print(f"   ❌ {ticker}: 거래량 증가 부족")
        continue
    
    # 3. RSI 반등 신호
    if not check_rsi_reversal(market_data, ticker):
        print(f"   ❌ {ticker}: RSI 반등 신호 없음")
        continue
    
    # 4. 지지선 근처 확인
    if not check_near_support(row, market_data, ticker):
        print(f"   ❌ {ticker}: 지지선에서 멀음")
        continue
    
    print(f"   ✅ {ticker}: 모든 추세 강도 필터 통과")
    strong_candidates.append(row)

traditional_candidates = pd.DataFrame(strong_candidates)
```

## 📊 예상 효과

### 장점
1. **정확도 향상**: 가짜 반등 신호 필터링으로 승률 10-15% 향상 예상
2. **손실 감소**: 추세가 약한 종목 제외로 평균 손실률 감소
3. **신뢰도 증가**: 다각도 검증으로 매매 신호의 신뢰성 향상

### 단점
1. **기회 감소**: 엄격한 필터로 매매 기회 30-40% 감소 가능
2. **후행성**: 확실한 신호를 기다리다 초기 상승 구간 놓칠 수 있음

## 🧪 백테스트 검증 항목

1. **필터 적용 전후 비교**
   - 승률 변화
   - 평균 수익률 변화
   - 최대 손실 감소율

2. **각 필터의 기여도**
   - 필터별 단독 적용 시 효과
   - 조합 시 시너지 효과

3. **시장 상황별 성과**
   - 상승장/하락장/횡보장별 효과

## 📅 구현 일정

- **개발**: 2-3시간
- **테스트**: 1시간
- **백테스트**: 2시간
- **실전 적용**: Phase 1 완료 후

## 🔍 모니터링 지표

적용 후 다음 지표를 2-3주간 추적:
- 일평균 선정 종목 수
- 선정 종목의 익일 수익률
- 가짜 신호 비율 (3일 내 재하락)
- 전체 포트폴리오 수익률 변화
