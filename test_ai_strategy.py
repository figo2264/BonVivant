# AI 강화 전략 테스트 모드 (strategy.py와 완전 호환)

import pandas as pd
import time
import json
from datetime import datetime
import numpy as np
import yaml
import os

# AI 모델 임포트
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import lightgbm as lgb
import ta
import warnings
warnings.filterwarnings('ignore')

# 테스트 모드 설정
TEST_MODE = True

print("🧪 AI 강화 전략 테스트 모드로 실행 중...")
print("📝 실제 API 연결 없이 strategy.py와 동일한 로직을 테스트합니다.")

# 더미 설정 생성
config = {
    'hantu': {
        'api_key': 'test_key',
        'secret_key': 'test_secret',
        'account_id': 'test_account'
    }
}

# 더미 HantuStock 클래스 (strategy.py와 동일한 인터페이스)
class TestHantuStock:
    def __init__(self, api_key, secret_key, account_id):
        print("✅ 테스트 HantuStock 초기화 완료")
        
    def activate_slack(self, token):
        """슬랙 활성화 (테스트 모드)"""
        print("📱 테스트 모드: 슬랙 연결 시뮬레이션")
        
    def post_message(self, message, channel_id):
        """슬랙 메시지 전송 (테스트 모드)"""
        print(f"📱 [테스트 슬랙] {message}")
        
    def get_past_data(self, ticker, n=100):
        """테스트용 더미 데이터 생성 (strategy.py와 동일한 형식)"""
        dates = pd.date_range(end=datetime.now(), periods=n, freq='D')
        np.random.seed(hash(ticker) % 2**32)  # 종목별 일관된 데이터
        
        # 현실적인 주가 패턴 생성
        base_price = 30000 + (hash(ticker) % 50000)  # 30,000 ~ 80,000
        prices = []
        volumes = []
        current_price = base_price
        
        for i in range(n):
            # 트렌드 + 노이즈
            trend = 0.0005 if i > n//2 else -0.0003  # 중간부터 상승 트렌드
            noise = np.random.normal(0, 0.015)  # 1.5% 일일 변동성
            change = trend + noise
            
            current_price *= (1 + change)
            prices.append(current_price)
            
            # 거래량 (가격 변동과 약간 상관관계)
            volume_base = 500000
            volume_factor = 1 + abs(change) * 3  # 변동성 클수록 거래량 증가
            volume = int(volume_base * volume_factor * np.random.uniform(0.5, 2.0))
            volumes.append(volume)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [p * (1 + np.random.normal(0, 0.003)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.008))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.008))) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        return data
    
    def get_past_data_total(self, n=100):
        """테스트용 전체 시장 데이터 (strategy.py와 동일한 형식)"""
        tickers = ['005930', '000660', '035420', '051910', '006400', 
                  '068270', '035720', '012330', '003550', '017670',
                  '000270', '207940', '005380', '006800', '000720',
                  '010130', '096770', '028260', '066570', '323410']
        
        all_data = []
        
        # 여러 날짜 데이터 생성
        for days_ago in range(n):
            current_date = (datetime.now() - pd.Timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            for ticker in tickers:
                np.random.seed(hash(ticker + current_date) % 2**32)
                
                base_price = 40000 + (hash(ticker) % 30000)
                daily_change = np.random.normal(0, 0.02)
                close_price = base_price * (1 + daily_change)
                
                data = {
                    'ticker': ticker,
                    'timestamp': current_date,
                    'open': close_price * (1 + np.random.normal(0, 0.005)),
                    'high': close_price * (1 + abs(np.random.normal(0, 0.01))),
                    'low': close_price * (1 - abs(np.random.normal(0, 0.01))),
                    'close': close_price,
                    'volume': np.random.randint(100000, 5000000),
                    'trade_amount': np.random.randint(1000000000, 50000000000)
                }
                all_data.append(data)
        
        df = pd.DataFrame(all_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values(['timestamp', 'ticker']).reset_index(drop=True)
    
    def get_holding_stock(self):
        """테스트용 보유 종목 (strategy.py와 동일한 형식)"""
        return {'005930': 10, '000660': 5, '035420': 3}
    
    def get_holding_cash(self):
        """테스트용 현금 잔고"""
        return 10_000_000  # 1000만원
    
    def bid(self, ticker, price_type, quantity, stock_type):
        """테스트용 매수 (strategy.py와 동일한 시그니처)"""
        print(f"📥 [테스트 매수] {ticker} {quantity}주 ({price_type})")
        return 'test_order_001', quantity
    
    def ask(self, ticker, price_type, quantity, stock_type):
        """테스트용 매도 (strategy.py와 동일한 시그니처)"""
        print(f"📤 [테스트 매도] {ticker} {quantity}주 ({price_type})")
        return 'test_order_002', quantity

# 테스트용 HantuStock 인스턴스 생성
ht = TestHantuStock(
    api_key=config['hantu']['api_key'],
    secret_key=config['hantu']['secret_key'],
    account_id=config['hantu']['account_id']
)

# 슬랙 활성화 (테스트)
ht.activate_slack("test_slack_token")

# 테스트용 채널 ID
HANLYANG_CHANNEL_ID = "TEST_CHANNEL"

# strategy.py와 동일한 데이터 구조 로드/초기화
try:
    with open('test_technical_strategy_data.json', 'r') as f:
        strategy_data = json.load(f)
    print("📁 기존 테스트 전략 데이터 로드 완료")
except:
    # strategy.py와 동일한 초기 구조
    strategy_data = {
        'holding_period': {'005930': 2, '000660': 1, '035420': 4},
        'technical_analysis': {},
        'enhanced_analysis_enabled': True,
        'performance_log': [],
        'purchase_info': {}  # strategy.py와 동일한 매수 정보 저장
    }
    print("🆕 새로운 테스트 전략 데이터 생성")

def create_technical_features(data):
    """기술적 분석을 위한 지표 생성 (strategy.py와 동일)"""
    try:
        # 수익률 계산
        for period in [1, 3, 5, 10, 20]:
            data[f'return_{period}d'] = data['close'].pct_change(period)
        
        # 이동평균 및 비율
        for ma_period in [5, 10, 20]:
            data[f'ma_{ma_period}'] = data['close'].rolling(ma_period).mean()
            data[f'price_ma_ratio_{ma_period}'] = data['close'] / data[f'ma_{ma_period}']
        
        # 기술적 지표
        data['rsi_14'] = ta.momentum.rsi(data['close'], window=14)
        data['volume_ratio_5d'] = data['volume'] / data['volume'].rolling(5).mean()
        data['volatility_10d'] = data['close'].pct_change().rolling(10).std()
        
        # 볼린저 밴드 위치
        bb_middle = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        data['bb_position'] = (data['close'] - bb_middle) / (2 * bb_std)
        
        return data
    except Exception as e:
        print(f"기술적 지표 생성 오류: {e}")
        return data

def get_technical_score(ticker):
    """규칙 기반 기술적 분석 점수 계산 (strategy.py와 동일)"""
    try:
        data = ht.get_past_data(ticker, n=50)
        if len(data) < 30:
            return 0.5
        
        data = create_technical_features(data)
        latest = data.iloc[-1]
        
        if pd.isna(latest.get('rsi_14', np.nan)) or pd.isna(latest.get('price_ma_ratio_20', np.nan)):
            return 0.5
        
        score = 0.5
        
        # 1. RSI 기반 과매도 판단
        rsi = latest['rsi_14']
        if rsi < 25:
            score += 0.25  # 강한 과매도
        elif rsi < 35:
            score += 0.15  # 과매도
        elif rsi > 75:
            score -= 0.2   # 과매수
        
        # 2. 이동평균 대비 위치
        ma_signals = 0
        for period in [5, 10, 20]:
            if latest[f'price_ma_ratio_{period}'] < 0.98:
                ma_signals += 1
        
        if ma_signals >= 2:
            score += 0.2
        
        # 3. 단기 반등 시그널
        if latest['return_1d'] > 0.01 and latest.get('return_3d', 0) < -0.02:
            score += 0.15
        
        # 4. 거래량 급증
        volume_ratio = latest.get('volume_ratio_5d', 1.0)
        if volume_ratio > 1.8:
            score += 0.1
        elif volume_ratio > 1.3:
            score += 0.05
        
        # 5. 변동성 조정
        if latest.get('volatility_10d', 0) > 0.05:
            score -= 0.1
        
        # 6. 볼린저 밴드 하단 근처
        if latest.get('bb_position', 0) < -0.8:
            score += 0.15
        
        return max(0.0, min(1.0, score))
        
    except Exception as e:
        print(f"기술적 점수 계산 오류 ({ticker}): {e}")
        return 0.5

def get_technical_hold_signal(ticker):
    """보유 종목에 대한 규칙 기반 홀드/매도 시그널 (strategy.py와 동일)"""
    try:
        data = ht.get_past_data(ticker, n=30)
        if len(data) < 20:
            return 0.5
        
        data = create_technical_features(data)
        latest = data.iloc[-1]
        
        hold_score = 0.5
        
        # 1. 단기 모멘텀
        if latest['return_1d'] > 0.02:
            hold_score += 0.3  # 강한 상승
        elif latest['return_1d'] > 0:
            hold_score += 0.1  # 약한 상승
        
        # 2. RSI 과매수 체크
        if latest['rsi_14'] > 80:
            hold_score -= 0.3  # 과매수시 매도 신호
        elif latest['rsi_14'] > 70:
            hold_score -= 0.1
        
        # 3. 볼린저 밴드 상단 근처
        if latest['bb_position'] > 0.8:
            hold_score -= 0.2
        
        return max(0.0, min(1.0, hold_score))
        
    except:
        return 0.5

def prepare_training_data(lookback_days=100):
    """AI 모델 학습용 데이터 준비 (strategy.py와 동일)"""
    print("📚 AI 모델 학습 데이터 준비 중...")
    
    try:
        historical_data = ht.get_past_data_total(n=lookback_days)
        
        if len(historical_data) < 50:
            print("❌ 학습 데이터 부족")
            return None, None
        
        all_features = []
        all_targets = []
        
        for ticker in historical_data['ticker'].unique():
            ticker_data = historical_data[historical_data['ticker'] == ticker].sort_values('timestamp')
            
            if len(ticker_data) < 30:
                continue
                
            ticker_data = create_technical_features(ticker_data.copy())
            
            # 3일 후 수익률 계산
            ticker_data['future_3d_return'] = ticker_data['close'].shift(-3) / ticker_data['close'] - 1
            
            valid_data = ticker_data.dropna()
            
            if len(valid_data) < 10:
                continue
            
            feature_columns = [
                'return_1d', 'return_3d', 'return_5d', 'return_10d',
                'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
                'rsi_14', 'volume_ratio_5d', 'volatility_10d', 'bb_position'
            ]
            
            available_features = [col for col in feature_columns if col in valid_data.columns]
            
            if len(available_features) < 8:
                continue
            
            features = valid_data[available_features].values
            targets = (valid_data['future_3d_return'] > 0.02).astype(int).values
            
            if len(features) > 3:
                features = features[:-3]
                targets = targets[:-3]
                
                all_features.extend(features)
                all_targets.extend(targets)
        
        if len(all_features) < 50:
            print("❌ 충분한 학습 데이터 확보 실패")
            return None, None
        
        print(f"✅ 학습 데이터 준비 완료: {len(all_features)}개 샘플")
        return np.array(all_features), np.array(all_targets)
        
    except Exception as e:
        print(f"❌ 데이터 준비 오류: {e}")
        return None, None

def train_ai_model():
    """AI 모델 훈련 (strategy.py와 동일)"""
    print("🤖 AI 모델 훈련 시작...")
    
    X, y = prepare_training_data()
    
    if X is None or len(X) < 50:
        print("❌ 학습 데이터 부족으로 모델 훈련 불가")
        return None
    
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        lgb_params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'num_leaves': 15,
            'learning_rate': 0.1,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_data_in_leaf': 10,
            'verbose': -1,
            'random_state': 42
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        model = lgb.train(
            lgb_params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=100,
            callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(0)]
        )
        
        y_pred = (model.predict(X_test) > 0.5).astype(int)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ 모델 훈련 완료!")
        print(f"📊 테스트 정확도: {accuracy:.3f}")
        print(f"📊 양성 예측 비율: {np.mean(y_pred):.3f}")
        print(f"📊 실제 양성 비율: {np.mean(y_test):.3f}")
        
        # 테스트 모드에서는 테스트 전용 파일명 사용
        model.save_model('test_ai_price_prediction_model.txt')
        print("💾 테스트 모델 저장: test_ai_price_prediction_model.txt")
        
        return model
        
    except Exception as e:
        print(f"❌ 모델 훈련 오류: {e}")
        return None

def load_ai_model():
    """저장된 AI 모델 로드 (strategy.py와 동일 로직)"""
    try:
        if os.path.exists('test_ai_price_prediction_model.txt'):
            model = lgb.Booster(model_file='test_ai_price_prediction_model.txt')
            print("📁 기존 테스트 모델 로드 완료")
            return model
        else:
            print("📝 저장된 모델이 없어 새로 훈련합니다...")
            return train_ai_model()
    except Exception as e:
        print(f"❌ 모델 로드 오류: {e}")
        return None

def get_ai_prediction_score(ticker, model):
    """AI 모델을 사용한 실제 예측 점수 (strategy.py와 동일)"""
    try:
        data = ht.get_past_data(ticker, n=50)
        if len(data) < 30:
            return 0.5
        
        data = create_technical_features(data)
        latest = data.iloc[-1]
        
        feature_columns = [
            'return_1d', 'return_3d', 'return_5d', 'return_10d',
            'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
            'rsi_14', 'volume_ratio_5d', 'volatility_10d', 'bb_position'
        ]
        
        features = []
        for col in feature_columns:
            if col in latest.index and not pd.isna(latest[col]):
                features.append(latest[col])
            else:
                features.append(0.0)
        
        prediction_prob = model.predict([features])[0]
        
        return float(prediction_prob)
        
    except Exception as e:
        print(f"❌ AI 예측 오류 ({ticker}): {e}")
        return 0.5

def enhanced_stock_selection():
    """기술적 분석 강화 종목 선정 (strategy.py와 동일)"""
    print("📊 기술적 분석 강화 종목 분석 시작...")
    
    data = ht.get_past_data_total(n=20)
    
    # 5일 종가 최저값, 20일 이동평균 계산하기
    data['5d_min_close'] = data.groupby('ticker')['close'].rolling(5).min().reset_index().set_index('level_1')['close']
    data['20d_ma'] = data.groupby('ticker')['close'].rolling(20).mean().reset_index().set_index('level_1')['close']

    # 기존 조건에 맞는 종목 찾기
    today_data = data[data['timestamp'] == data['timestamp'].max()]
    traditional_candidates = today_data[
        (today_data['5d_min_close'] == today_data['close']) & 
        (today_data['20d_ma'] > today_data['close'])
    ]
    
    print(f"📊 전통적 조건 후보: {len(traditional_candidates)}개")
    
    # 기술적 분석 점수 추가 분석
    enhanced_candidates = []
    
    for _, row in traditional_candidates.iterrows():
        ticker = row['ticker']
        
        # 기술적 분석 점수 계산
        technical_score = get_technical_score(ticker)
        
        # 결합 점수: 기존 거래량 가중치 + 기술적 분석 보정
        technical_multiplier = 0.5 + technical_score  # 0.5 ~ 1.5 배수
        combined_score = row['trade_amount'] * technical_multiplier
        
        enhanced_candidates.append({
            'ticker': ticker,
            'trade_amount': row['trade_amount'],
            'technical_score': technical_score,
            'combined_score': combined_score
        })
        
        # 기술적 분석 정보 저장
        strategy_data['technical_analysis'][ticker] = {
            'score': technical_score,
            'timestamp': datetime.now().isoformat(),
            'traditional_rank': int(row['trade_amount'])
        }
    
    # 기술적 분석 강화 점수로 정렬
    enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # 결과 출력 및 선정
    selected_tickers = []
    for i, candidate in enumerate(enhanced_candidates[:15]):  # 상위 15개 확인
        ticker = candidate['ticker']
        technical_score = candidate['technical_score']
        
        print(f"{i+1:2d}. {ticker}: 기술점수={technical_score:.3f}, 거래량={candidate['trade_amount']:>10.0f}, 결합점수={candidate['combined_score']:>12.0f}")
        
        # 기술적 점수가 0.6 이상이고 상위 10개만 선정
        if technical_score >= 0.6 and len(selected_tickers) < 10:
            selected_tickers.append(ticker)
    
    print(f"🎯 기술적 분석 최종 선정: {len(selected_tickers)}개 종목")
    return selected_tickers

def ai_enhanced_final_selection(entry_tickers):
    """AI를 활용한 최종 종목 선정 (strategy.py와 동일)"""
    print("🤖 AI 최종 종목 선정 시작...")
    
    ai_model = load_ai_model()
    if ai_model is None:
        print("❌ AI 모델을 사용할 수 없어 기존 선정 결과 반환")
        return entry_tickers[:5]
    
    ai_scored_tickers = []
    
    for ticker in entry_tickers:
        ai_score = get_ai_prediction_score(ticker, ai_model)
        ai_scored_tickers.append({
            'ticker': ticker,
            'ai_score': ai_score
        })
        
        print(f"🎯 {ticker}: AI 예측 점수 = {ai_score:.3f}")
    
    ai_scored_tickers.sort(key=lambda x: x['ai_score'], reverse=True)
    
    final_selection = []
    for item in ai_scored_tickers:
        if item['ai_score'] >= 0.6 and len(final_selection) < 5:
            final_selection.append(item['ticker'])
    
    if len(final_selection) == 0:
        final_selection = [item['ticker'] for item in ai_scored_tickers[:3]]
        print("⚠️ AI 조건 만족 종목 없음, 상위 3개 선정")
    
    print(f"🏆 AI 최종 선정: {len(final_selection)}개 종목")
    
    # strategy.py와 동일한 키 구조 사용
    strategy_data['ai_predictions'] = {
        item['ticker']: {
            'score': item['ai_score'],
            'timestamp': datetime.now().isoformat(),
            'selected': item['ticker'] in final_selection
        }
        for item in ai_scored_tickers
    }
    
    return final_selection

def test_morning_sell_strategy():
    """아침 매도 전략 테스트 (strategy.py와 동일한 로직)"""
    print("🌅 아침 매도 전략 테스트 시작!")
    
    holdings = ht.get_holding_stock()
    print(f"📊 현재 보유: {len(holdings)}개")
    
    # holding_period를 하루씩 높여줌
    for ticker in holdings:
        if ticker not in strategy_data['holding_period']:
            strategy_data['holding_period'][ticker] = 1
        else:
            strategy_data['holding_period'][ticker] += 1
    
    # 기술적 분석 강화 매도 전략
    ticker_to_sell = []
    for ticker in holdings:
        holding_days = strategy_data['holding_period'][ticker]
        should_sell = False
        
        print(f"\n🔍 {ticker} 분석 (보유 {holding_days}일)")
        
        # 기본 3일 룰
        if holding_days >= 3:
            should_sell = True
            
            # 기술적 홀드 시그널 체크 (3일차에만)
            if holding_days == 3 and strategy_data['enhanced_analysis_enabled']:
                hold_signal = get_technical_hold_signal(ticker)
                
                if hold_signal >= 0.75:
                    should_sell = False
                    print(f"  📊 기술적 분석 강홀드 신호로 1일 연장 (신호강도: {hold_signal:.3f})")
                elif hold_signal <= 0.25:
                    print(f"  ⚠️ 기술적 분석 매도 신호 (신호강도: {hold_signal:.3f})")
                else:
                    print(f"  📊 기술적 신호: {hold_signal:.3f} (보통)")
        
        # 안전장치: 5일 이상은 무조건 매도
        if holding_days >= 5:
            should_sell = True
            print(f"  ⏰ 5일 안전룰 적용")
        
        if should_sell:
            ticker_to_sell.append(ticker)
            print(f"  📤 매도 결정!")
        else:
            print(f"  📊 보유 유지")
    
    print(f"\n📤 매도 예정: {len(ticker_to_sell)}개")
    
    # 수익률 추적 매도 실행
    sold_tickers = []
    total_sell_profit = 0
    
    for ticker in ticker_to_sell:
        holding_days = strategy_data['holding_period'][ticker]
        
        try:
            # 매도 전 수익률 계산
            purchase_info = strategy_data.get('purchase_info', {}).get(ticker, {})
            try:
                current_data = ht.get_past_data(ticker, n=1)
                current_price = current_data['close'].iloc[-1]
            except:
                current_price = None
            
            profit_info = ""
            if purchase_info and current_price:
                buy_price = purchase_info.get('buy_price', 0)
                quantity = holdings[ticker]
                
                if buy_price > 0:
                    sell_value = quantity * current_price
                    buy_value = quantity * buy_price
                    profit = sell_value - buy_value
                    profit_rate = (profit / buy_value) * 100
                    
                    total_sell_profit += profit
                    profit_info = f" | 수익률: {profit_rate:+.2f}% ({profit:+,}원)"
            
            print(f"📤 {ticker} 매도 (보유기간: {holding_days}일{profit_info})")
            order_id, quantity = ht.ask(ticker, 'market', holdings[ticker], 'STOCK')
            
            if order_id:
                sold_tickers.append(ticker)
                
                # 슬랙 알림: 매도 체결 (수익률 포함)
                sell_message = f"📤 **아침 매도 체결**\n"
                sell_message += f"종목: {ticker}\n"
                sell_message += f"수량: {quantity}주\n"
                sell_message += f"보유기간: {holding_days}일"
                
                if profit_info:
                    sell_message += f"\n수익률: {profit_rate:+.2f}%"
                    sell_message += f"\n손익: {profit:+,}원"
                    if purchase_info:
                        confidence = purchase_info.get('confidence_level', 'Unknown')
                        sell_message += f"\n신뢰도: {confidence}"
                
                ht.post_message(sell_message, HANLYANG_CHANNEL_ID)
                
                # 매도 완료 후 구매 정보 정리
                if ticker in strategy_data.get('purchase_info', {}):
                    del strategy_data['purchase_info'][ticker]
            
            strategy_data['holding_period'][ticker] = 0
            
        except Exception as e:
            print(f"❌ {ticker} 매도 처리 오류: {e}")
    
    return sold_tickers, total_sell_profit

def test_afternoon_buy_strategy():
    """오후 매수 전략 테스트 (strategy.py와 동일한 로직)"""
    print("🚀 오후 매수 전략 테스트 시작!")
    
    holdings = ht.get_holding_stock()
    print(f"📊 현재 보유: {len(holdings)}개")
    
    # 기술적 분석 강화 매수 실행
    entry_tickers = enhanced_stock_selection()
    
    # AI 최종 선정 추가
    final_entry_tickers = ai_enhanced_final_selection(entry_tickers)
    
    # 현재 보유중인 종목은 매수후보에서 제외
    current_holdings = set(holdings.keys())
    final_buy_tickers = [t for t in final_entry_tickers if t not in current_holdings]
    
    print(f"📥 최종 매수 대상: {len(final_buy_tickers)}개")
    
    # 슬랙 알림: 최종 선정 종목
    if final_buy_tickers:
        selection_message = f"🎯 **AI 종목 선정 완료!**\n"
        selection_message += f"📊 분석 완료: {len(entry_tickers)}개 → AI 선정: {len(final_entry_tickers)}개\n"
        selection_message += f"📥 매수 예정: {len(final_buy_tickers)}개\n\n"
        selection_message += "**선정 종목:**\n"
        for i, ticker in enumerate(final_buy_tickers, 1):
            selection_message += f"{i}. {ticker}\n"
        
        ht.post_message(selection_message, HANLYANG_CHANNEL_ID)
    
    # AI 신뢰도 기반 차등 투자 매수
    bought_tickers = []
    total_invested = 0
    
    # 현재 계좌 잔고 조회
    current_balance = ht.get_holding_cash()
    print(f"💰 현재 계좌 잔고: {current_balance:,}원")
    
    for ticker in final_buy_tickers:
        try:
            # AI 점수 가져오기
            ai_score = strategy_data.get('ai_predictions', {}).get(ticker, {}).get('score', 0.5)
            
            # AI 신뢰도 기반 투자 금액 계산
            if ai_score >= 0.8:
                investment_amount = 400_000    # 고신뢰: 40만원
                confidence_level = "고신뢰"
            elif ai_score >= 0.7:
                investment_amount = 300_000    # 중신뢰: 30만원
                confidence_level = "중신뢰"
            elif ai_score >= 0.6:
                investment_amount = 200_000    # 저신뢰: 20만원
                confidence_level = "저신뢰"
            else:
                investment_amount = 100_000      # 매우 저신뢰: 10만원
                confidence_level = "매우저신뢰"
            
            # 투자 가능 금액 계산 (400만원 안전자금 제외)
            available_balance = current_balance - total_invested - 4_000_000
            
            # 투자 가능 금액이 0 이하면 바로 건너뛰기
            if available_balance <= 0:
                print(f"⚠️ {ticker}: 투자 가능 금액 부족 (남은 금액: {available_balance:,}원)")
                continue
            
            # 투자 가능 금액이 계획된 금액보다 작으면 조정
            if available_balance < investment_amount:
                # 최소 투자금액(10만원) 확인
                if available_balance < 100_000:
                    print(f"⚠️ {ticker}: 최소 투자금액 부족 (가능: {available_balance:,}원, 최소: 100,000원)")
                    continue
                investment_amount = available_balance
            
            # 현재가 조회
            try:
                current_data = ht.get_past_data(ticker, n=1)
                current_price = current_data['close'].iloc[-1]
            except:
                current_price = None
            
            if not current_price or current_price <= 0:
                print(f"❌ {ticker}: 현재가 조회 실패")
                continue
            
            # 매수 수량 계산 (소수점 버림)
            quantity_to_buy = int(investment_amount // current_price)
            
            if quantity_to_buy <= 0:
                print(f"⚠️ {ticker}: 투자금액 부족 (필요: {current_price:,}원)")
                continue
            
            actual_investment = quantity_to_buy * current_price
            
            print(f"📥 {ticker} AI 신뢰도 기반 매수:")
            print(f"   AI점수: {ai_score:.3f} ({confidence_level})")
            print(f"   투자금액: {actual_investment:,}원")
            print(f"   수량: {quantity_to_buy:,}주")
            print(f"   단가: {current_price:,}원")
            
            # 매수 주문 실행
            order_id, actual_quantity = ht.bid(ticker, 'market', quantity_to_buy, 'STOCK')
            
            if order_id:
                bought_tickers.append({
                    'ticker': ticker,
                    'quantity': actual_quantity,
                    'investment': actual_investment,
                    'ai_score': ai_score,
                    'confidence_level': confidence_level
                })
                total_invested += actual_investment
                
                # 매수 정보 저장 (수익률 계산용)
                strategy_data.setdefault('purchase_info', {})[ticker] = {
                    'buy_price': current_price,
                    'quantity': actual_quantity,
                    'investment': actual_investment,
                    'buy_date': datetime.now().isoformat(),
                    'ai_score': ai_score,
                    'confidence_level': confidence_level
                }
                
                # 슬랙 알림: 매수 체결
                buy_message = f"📥 **오후 매수 체결**\n"
                buy_message += f"종목: {ticker}\n"
                buy_message += f"수량: {actual_quantity:,}주\n"
                buy_message += f"투자금액: {actual_investment:,}원\n"
                buy_message += f"AI점수: {ai_score:.3f} ({confidence_level})\n"
                buy_message += f"단가: {current_price:,}원"
                
                ht.post_message(buy_message, HANLYANG_CHANNEL_ID)
            else:
                print(f"❌ {ticker} 매수 주문 실패")
                
        except Exception as e:
            print(f"❌ {ticker} 매수 처리 오류: {e}")
    
    return bought_tickers, total_invested

def save_test_strategy_data():
    """테스트 전략 데이터 저장 (strategy.py와 동일한 형식)"""
    def convert_to_serializable(obj):
        """numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
        if isinstance(obj, dict):
            return {key: convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    serializable_data = convert_to_serializable(strategy_data)
    
    with open('test_technical_strategy_data.json', 'w') as f:
        json.dump(serializable_data, f, indent=2, ensure_ascii=False)
    
    print("💾 테스트 전략 데이터 저장 완료")

def run_full_strategy_test():
    """전체 전략 테스트 실행 (매도 + 매수)"""
    print("=" * 80)
    print("🚀 AI 강화 전략 전체 테스트 실행!")
    print("=" * 80)
    
    # 아침 매도 전략 테스트
    print("\n" + "="*50)
    print("🌅 아침 매도 전략 테스트")
    print("="*50)
    
    sold_tickers, total_sell_profit = test_morning_sell_strategy()
    
    # 아침 매도 완료 슬랙 알림
    holdings = ht.get_holding_stock()
    morning_summary_message = f"🌅 **아침 매도 완료!**\n"
    morning_summary_message += f"📤 매도: {len(sold_tickers)}개"
    if total_sell_profit != 0:
        morning_summary_message += f" (손익: {total_sell_profit:+,}원)"
    morning_summary_message += f"\n📊 현재 보유: {len(holdings) - len(sold_tickers)}개"
    morning_summary_message += f"\n⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    morning_summary_message += f"\n🔔 오후 3시 20분에 매수 전략 실행 예정"
    
    ht.post_message(morning_summary_message, HANLYANG_CHANNEL_ID)
    
    # 오후 매수 전략 테스트
    print("\n" + "="*50)
    print("🚀 오후 매수 전략 테스트")
    print("="*50)
    
    bought_tickers, total_invested = test_afternoon_buy_strategy()
    
    # 오후 매수 완료 슬랙 알림
    evening_summary_message = f"🚀 **오후 매수 완료!**\n"
    evening_summary_message += f"📥 매수: {len(bought_tickers)}개"
    if total_invested > 0:
        evening_summary_message += f" (투자: {total_invested:,}원)"
    evening_summary_message += f"\n📊 현재 보유: {len(holdings) - len(sold_tickers) + len(bought_tickers)}개\n"
    
    # AI 신뢰도별 투자 현황
    if bought_tickers:
        evening_summary_message += "\n**신뢰도별 투자:**\n"
        confidence_stats = {}
        for stock in bought_tickers:
            level = stock['confidence_level']
            if level not in confidence_stats:
                confidence_stats[level] = {'count': 0, 'amount': 0}
            confidence_stats[level]['count'] += 1
            confidence_stats[level]['amount'] += stock['investment']
        
        for level, stats in confidence_stats.items():
            evening_summary_message += f"• {level}: {stats['count']}개 ({stats['amount']:,}원)\n"
    
    evening_summary_message += f"\n⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    evening_summary_message += f"\n🔔 내일 오전 8시 30분에 매도 검토 예정"
    
    ht.post_message(evening_summary_message, HANLYANG_CHANNEL_ID)
    
    # 성과 로깅
    strategy_data['performance_log'].append({
        'timestamp': datetime.now().isoformat(),
        'strategy_type': 'full_test',
        'sold_count': len(sold_tickers),
        'sell_profit': total_sell_profit,
        'technical_candidates': len(strategy_data.get('technical_analysis', {})),
        'ai_selected': len(strategy_data.get('ai_predictions', {})),
        'bought_count': len(bought_tickers),
        'total_invested': total_invested,
        'current_holdings': len(holdings) - len(sold_tickers) + len(bought_tickers),
        'enhanced_analysis_enabled': strategy_data['enhanced_analysis_enabled'],
        'ai_confidence_strategy': True
    })
    
    # 전략 데이터 저장
    save_test_strategy_data()
    
    # 최종 결과 요약
    print("\n" + "="*80)
    print("✅ AI 강화 전략 테스트 완료!")
    print("="*80)
    print(f"📤 매도: {len(sold_tickers)}개 (손익: {total_sell_profit:+,}원)")
    print(f"📥 매수: {len(bought_tickers)}개 (투자: {total_invested:,}원)")
    print(f"📊 예상 보유 종목: {len(holdings) - len(sold_tickers) + len(bought_tickers)}개")
    
    # AI 예측 결과 요약
    if strategy_data.get('ai_predictions'):
        print(f"\n🤖 AI 예측 결과:")
        for ticker, pred in strategy_data['ai_predictions'].items():
            status = "✅선정" if pred['selected'] else "❌제외"
            print(f"  {ticker}: {pred['score']:.3f} {status}")
    
    print("="*80)

def cleanup_test_files():
    """테스트 파일 정리"""
    test_files = ['test_ai_price_prediction_model.txt', 'test_technical_strategy_data.json']
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 테스트 파일 삭제: {file}")

if __name__ == "__main__":
    try:
        # 전체 전략 테스트 실행
        run_full_strategy_test()
        
        # 개별 기능 테스트도 가능
        print("\n" + "="*50)
        print("🔬 개별 기능 테스트 예제")
        print("="*50)
        
        # 기술적 점수 테스트
        test_ticker = '005930'
        tech_score = get_technical_score(test_ticker)
        print(f"📊 {test_ticker} 기술적 점수: {tech_score:.3f}")
        
        # AI 모델 테스트
        ai_model = load_ai_model()
        if ai_model:
            ai_score = get_ai_prediction_score(test_ticker, ai_model)
            print(f"🤖 {test_ticker} AI 예측 점수: {ai_score:.3f}")
        
        print("\n✅ 모든 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 테스트 파일 정리 (선택사항)
        # cleanup_test_files()
        print("🧪 테스트 모드 종료")
