# AI 강화된 6-7 전략 테스트 모드

import pandas as pd
import time
import json
from datetime import datetime
import numpy as np
import yaml

# AI 모델
from sklearn.tree import DecisionTreeClassifier
import warnings
warnings.filterwarnings('ignore')

# 테스트 모드 설정
TEST_MODE = True

print("🧪 테스트 모드로 실행 중...")
print("📝 실제 API 연결 없이 전략 로직을 테스트합니다.")

# 더미 설정 생성
config = {
    'hantu': {
        'api_key': 'test_key',
        'secret_key': 'test_secret',
        'account_id': 'test_account'
    }
}

# 더미 HantuStock 클래스 (테스트용)
class TestHantuStock:
    def __init__(self, api_key, secret_key, account_id):
        print("✅ 테스트 HantuStock 초기화 완료")
        
    def get_past_data(self, ticker, n=100):
        """테스트용 더미 데이터 생성"""
        dates = pd.date_range(end=datetime.now(), periods=n, freq='D')
        np.random.seed(hash(ticker) % 2**32)  # 종목별 일관된 데이터
        
        # 가상의 주가 데이터
        base_price = 50000 + (hash(ticker) % 20000)  # 50,000 ~ 70,000
        prices = []
        current_price = base_price
        
        for i in range(n):
            change = np.random.normal(0, 0.02)  # 2% 표준편차
            current_price *= (1 + change)
            prices.append(current_price)
        
        # 거래량 (임의)
        volumes = np.random.randint(10000, 1000000, n)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        return data
    
    def get_past_data_total(self, n=10):
        """테스트용 전체 시장 데이터"""
        tickers = ['005930', '000660', '035420', '051910', '006400', 
                  '068270', '035720', '012330', '003550', '017670']
        
        all_data = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for ticker in tickers:
            np.random.seed(hash(ticker) % 2**32)
            
            data = {
                'ticker': ticker,
                'open': 50000 + np.random.randint(-5000, 5000),
                'high': 52000 + np.random.randint(-3000, 3000),
                'low': 48000 + np.random.randint(-3000, 3000),
                'close': 50000 + np.random.randint(-4000, 4000),
                'volume': np.random.randint(100000, 10000000),
                'trade_amount': np.random.randint(1000000000, 50000000000),
                'timestamp': current_date
            }
            all_data.append(data)
        
        return pd.DataFrame(all_data)
    
    def get_holding_stock(self):
        """테스트용 보유 종목"""
        return {'005930': 10, '000660': 5}  # 삼성전자 10주, SK하이닉스 5주
    
    def bid(self, ticker, price, quantity, quantity_scale):
        """테스트용 매수"""
        print(f"📥 테스트 매수: {ticker} {quantity}주")
        return 'test_order_001', quantity
    
    def ask(self, ticker, price, quantity, quantity_scale):
        """테스트용 매도"""
        print(f"📤 테스트 매도: {ticker} {quantity}주")
        return 'test_order_002', quantity

# 테스트용 HantuStock 인스턴스 생성
ht = TestHantuStock(
    api_key=config['hantu']['api_key'],
    secret_key=config['hantu']['secret_key'],
    account_id=config['hantu']['account_id']
)

# AI 강화 전략 데이터 초기화
strategy_data = {
    'holding_period': {'005930': 2, '000660': 1},  # 테스트 보유 기간
    'ai_predictions': {},
    'ai_enabled': True,
    'performance_log': []
}

def create_ai_features_simple(data):
    """AI를 위한 간단한 기술적 지표 생성"""
    try:
        # 수익률 계산
        for period in [1, 3, 5, 10, 20]:
            data[f'return_{period}d'] = data['close'].pct_change(period)
        
        # 이동평균 및 비율
        for ma_period in [5, 10, 20]:
            data[f'ma_{ma_period}'] = data['close'].rolling(ma_period).mean()
            data[f'price_ma_ratio_{ma_period}'] = data['close'] / data[f'ma_{ma_period}']
        
        # 볼린저 밴드 위치
        bb_middle = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        data['bb_position'] = (data['close'] - bb_middle) / (2 * bb_std)
        
        return data
    except Exception as e:
        print(f"AI 피처 생성 오류: {e}")
        return data

def get_ai_score(ticker):
    """AI 기반 매수 점수 계산 (0.0~1.0)"""
    try:
        # 최근 데이터 가져오기
        data = ht.get_past_data(ticker, n=50)
        if len(data) < 30:
            return 0.5  # 데이터 부족시 중립
        
        data = create_ai_features_simple(data)
        latest = data.iloc[-1]
        
        score = 0.5  # 기본점수
        
        # 이동평균 대비 위치 점수
        ma_signals = 0
        for period in [5, 10, 20]:
            if latest[f'price_ma_ratio_{period}'] < 0.98:
                ma_signals += 1
        
        if ma_signals >= 2:
            score += 0.2
        
        # 랜덤 요소 추가 (테스트용)
        np.random.seed(hash(ticker) % 2**32)
        random_factor = np.random.uniform(-0.15, 0.15)
        score += random_factor
        
        return max(0.0, min(1.0, score))
        
    except Exception as e:
        print(f"AI 점수 계산 오류 ({ticker}): {e}")
        return 0.5

def get_ai_hold_signal(ticker):
    """보유 종목에 대한 AI 홀드/매도 시그널"""
    try:
        np.random.seed(hash(ticker + str(datetime.now().day)) % 2**32)
        hold_score = np.random.uniform(0.3, 0.8)  # 테스트용 랜덤 신호
        return hold_score
    except:
        return 0.5

def enhanced_stock_selection():
    """AI 강화 종목 선정 (테스트 모드)"""
    print("🤖 AI 강화 종목 분석 시작...")
    
    # 테스트 데이터로 후보 종목 생성
    test_tickers = ['001230', '002310', '003490', '004020', '005490']
    
    print(f"📊 테스트 후보: {len(test_tickers)}개")
    
    # AI 점수 추가 분석
    ai_enhanced_candidates = []
    
    for ticker in test_tickers:
        # AI 점수 계산
        ai_score = get_ai_score(ticker)
        
        # 가상 거래량
        np.random.seed(hash(ticker) % 2**32)
        trade_amount = np.random.randint(1000000000, 2147483647)  # int32 범위 내
        
        # 결합 점수
        ai_multiplier = 0.5 + ai_score
        combined_score = trade_amount * ai_multiplier
        
        ai_enhanced_candidates.append({
            'ticker': ticker,
            'trade_amount': trade_amount,
            'ai_score': ai_score,
            'combined_score': combined_score
        })
        
        # AI 예측 정보 저장
        strategy_data['ai_predictions'][ticker] = {
            'score': ai_score,
            'timestamp': datetime.now().isoformat(),
            'traditional_rank': int(trade_amount)
        }
    
    # AI 강화 점수로 정렬
    ai_enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # 결과 출력 및 선정
    selected_tickers = []
    for i, candidate in enumerate(ai_enhanced_candidates[:10]):
        ticker = candidate['ticker']
        ai_score = candidate['ai_score']
        
        print(f"{i+1:2d}. {ticker}: AI={ai_score:.3f}, 거래량={candidate['trade_amount']:>10.0f}, 결합점수={candidate['combined_score']:>12.0f}")
        
        # AI 점수가 0.6 이상이고 상위 5개만 선정
        if ai_score >= 0.6 and len(selected_tickers) < 5:
            selected_tickers.append(ticker)
    
    print(f"🎯 AI 최종 선정: {len(selected_tickers)}개 종목")
    return selected_tickers

def run_test_strategy():
    """테스트 전략 실행"""
    print("=" * 60)
    print("🚀 AI 강화 전략 테스트 실행!")
    print("=" * 60)
    
    # 현재 보유중인 종목 조회
    holdings = ht.get_holding_stock()
    print(f"📊 현재 보유 종목: {holdings}")
    
    # holding_period를 하루씩 높여줌
    for ticker in holdings:
        if ticker not in strategy_data['holding_period']:
            strategy_data['holding_period'][ticker] = 1
        else:
            strategy_data['holding_period'][ticker] += 1
    
    # AI 강화 매도 전략
    ticker_to_sell = []
    for ticker in holdings:
        holding_days = strategy_data['holding_period'][ticker]
        should_sell = False
        
        print(f"\n🔍 {ticker} 분석 (보유 {holding_days}일)")
        
        # 기본 3일 룰
        if holding_days >= 3:
            should_sell = True
            
            # AI 홀드 시그널 체크
            if holding_days == 3 and strategy_data['ai_enabled']:
                hold_signal = get_ai_hold_signal(ticker)
                
                if hold_signal >= 0.75:
                    should_sell = False
                    print(f"  🤖 AI 강홀드 신호로 1일 연장 (신호강도: {hold_signal:.3f})")
                elif hold_signal <= 0.25:
                    print(f"  ⚠️ AI 매도 신호 (신호강도: {hold_signal:.3f})")
                else:
                    print(f"  📊 AI 신호: {hold_signal:.3f} (중립)")
        
        # 안전장치: 5일 이상은 무조건 매도
        if holding_days >= 5:
            should_sell = True
            print(f"  ⏰ 5일 안전룰 적용")
        
        if should_sell:
            ticker_to_sell.append(ticker)
            print(f"  📤 매도 결정!")
        else:
            print(f"  📊 보유 유지")
    
    print(f"\n📊 매도 예정: {len(ticker_to_sell)}개")
    
    # === 매도 실행 ===
    for ticker in ticker_to_sell:
        print(f"📤 {ticker} 매도 (보유기간: {strategy_data['holding_period'][ticker]}일)")
        ht.ask(ticker, 'market', holdings[ticker], 'STOCK')
        strategy_data['holding_period'][ticker] = 0
    
    # === AI 강화 매수 실행 ===
    print(f"\n{'=' * 40}")
    entry_tickers = enhanced_stock_selection()
    
    # 현재 보유중인 종목은 매수후보에서 제외
    current_holdings = set(holdings.keys())
    final_entry_tickers = [t for t in entry_tickers if t not in current_holdings]
    
    print(f"\n📥 최종 매수 대상: {len(final_entry_tickers)}개")
    
    # 선정한 종목 매수
    for ticker in final_entry_tickers:
        print(f"📥 {ticker} AI 추천 매수")
        ht.bid(ticker, 'market', 1, 'STOCK')
    
    # 성과 로깅
    strategy_data['performance_log'].append({
        'timestamp': datetime.now().isoformat(),
        'sold_count': len(ticker_to_sell),
        'bought_count': len(final_entry_tickers),
        'total_holdings': len(holdings) - len(ticker_to_sell) + len(final_entry_tickers),
        'ai_enabled': strategy_data['ai_enabled']
    })
    
    print(f"\n{'=' * 60}")
    print("✅ AI 강화 전략 테스트 완료!")
    print(f"💾 매도: {len(ticker_to_sell)}개, 매수: {len(final_entry_tickers)}개")
    print(f"📈 예상 보유 종목: {len(holdings) - len(ticker_to_sell) + len(final_entry_tickers)}개")
    print("=" * 60)

if __name__ == "__main__":
    run_test_strategy()
