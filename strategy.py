# 기술적 분석 강화된 6-7 전략 (기존 이동평균 + 규칙 기반 분석)

import pandas as pd
import time
import json
from datetime import datetime
import numpy as np

import yaml
import ta

# AI 모델 임포트
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import lightgbm as lgb
import os
import warnings
warnings.filterwarnings('ignore')

with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

api_key = config['hantu']['api_key']
secret_key = config['hantu']['secret_key']
account_id = config['hantu']['account_id']

# HantuStock 패키지 불러오기
from HantuStock import HantuStock

ht = HantuStock(api_key=api_key, secret_key=secret_key, account_id=account_id)

# 슬랙 설정
SLACK_API_TOKEN = "SLACK_TOKEN_REMOVED"
HANLYANG_CHANNEL_ID = "C090JHC30CU"

# 슬랙 활성화
ht.activate_slack(SLACK_API_TOKEN)

# 기술적 분석 전략 데이터 로드
try:
    with open('technical_strategy_data.json', 'r') as f:
        strategy_data = json.load(f)
except:
    # 기존 ai_strategy_data.json과 호환성 유지
    try:
        with open('ai_strategy_data.json', 'r') as f:
            old_data = json.load(f)
            strategy_data = {
                'holding_period': old_data.get('holding_period', {}),
                'technical_analysis': old_data.get('ai_predictions', {}),
                'enhanced_analysis_enabled': old_data.get('ai_enabled', True),
                'performance_log': old_data.get('performance_log', [])
            }
    except:
        # legacy strategy_data.json과 호환성 유지
        try:
            with open('strategy_data.json', 'r') as f:
                old_data = json.load(f)
                strategy_data = {
                    'holding_period': old_data.get('holding_period', {}),
                    'technical_analysis': {},
                    'enhanced_analysis_enabled': True,
                    'performance_log': []
                }
        except:
            strategy_data = {
                'holding_period': {},
                'technical_analysis': {},
                'enhanced_analysis_enabled': True,
                'performance_log': []
            }

def get_past_data_enhanced(ticker, n=100):
    """개별 종목 과거 원시 데이터 조회 (HantuStock 래퍼)"""
    try:
        data = ht.get_past_data(ticker, n=n)
        return data
    except Exception as e:
        print(f"❌ {ticker} 데이터 조회 실패: {e}")
        return pd.DataFrame()

def create_technical_features(data):
    """강화된 기술적 분석을 위한 지표 생성 (백테스팅 엔진 개선 버전)"""
    try:
        if len(data) < 30:
            # 데이터가 부족하면 기본 지표만 생성
            # 기본 수익률 계산
            data['return_1d'] = data['close'].pct_change(1)
            
            # 추가 지표들
            # 양봉/음봉 연속성
            data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
            data['candle_streak'] = data['candle_type'].rolling(3).sum()

            # 거래량 가격 상관성
            data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])

            # 가격 가속도
            data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)

            # 심리적 저항선 근접도 (천원 단위)
            data['round_number_proximity'] = (data['close'] % 1000) / 1000

            return data
            
        # 기본 수익률 계산 (더 많은 기간)
        for period in [1, 2, 3, 5, 7, 10, 14, 20, 30]:
            data[f'return_{period}d'] = data['close'].pct_change(period)

        # 이동평균 및 비율 (더 다양한 기간)
        for ma_period in [5, 10, 15, 20, 30, 60, 120]:
            data[f'ma_{ma_period}'] = data['close'].rolling(ma_period).mean()
            data[f'price_ma_ratio_{ma_period}'] = data['close'] / data[f'ma_{ma_period}']
            
            # 이동평균 기울기 (추세 강도)
            if ma_period <= 30:
                data[f'ma_slope_{ma_period}'] = data[f'ma_{ma_period}'].diff(5) / data[f'ma_{ma_period}'].shift(5)

        # 확장된 RSI 지표
        for rsi_period in [7, 14, 21, 30]:
            data[f'rsi_{rsi_period}'] = ta.momentum.rsi(data['close'], window=rsi_period)
            
        # RSI 오버바이/오버솔드 지표
        data['rsi_oversold'] = (data['rsi_14'] < 30).astype(int)
        data['rsi_overbought'] = (data['rsi_14'] > 70).astype(int)

        # 확장된 거래량 지표
        for vol_period in [3, 5, 10, 20, 30]:
            data[f'volume_ratio_{vol_period}d'] = data['volume'] / data['volume'].rolling(vol_period).mean()
            
        # 거래량 가중 수익률
        data['volume_weighted_return'] = data['return_1d'] * data['volume_ratio_5d']
        
        # 확장된 변동성 지표
        for vol_period in [5, 10, 20, 30]:
            data[f'volatility_{vol_period}d'] = data['close'].pct_change().rolling(vol_period).std()
            
        # 변동성 비율 (현재 vs 과거)
        data['volatility_ratio'] = data['volatility_10d'] / data['volatility_30d']

        # 확장된 볼린저 밴드
        for bb_period in [10, 20, 30]:
            bb_middle = data['close'].rolling(bb_period).mean()
            bb_std = data['close'].rolling(bb_period).std()
            data[f'bb_upper_{bb_period}'] = bb_middle + (2 * bb_std)
            data[f'bb_lower_{bb_period}'] = bb_middle - (2 * bb_std)
            data[f'bb_position_{bb_period}'] = (data['close'] - bb_middle) / (2 * bb_std)
            data[f'bb_width_{bb_period}'] = (data[f'bb_upper_{bb_period}'] - data[f'bb_lower_{bb_period}']) / bb_middle
            
        # 기본 볼린저 밴드 (하위 호환성)
        data['bb_position'] = data['bb_position_20']
        data['bb_width'] = data['bb_width_20']
            
        # 볼린저 밴드 스퀴즈 감지
        data['bb_squeeze'] = (data['bb_width_20'] < data['bb_width_20'].rolling(20).quantile(0.2)).astype(int)

        # 확장된 MACD
        try:
            for fast, slow, signal in [(12, 26, 9), (5, 35, 5), (19, 39, 9)]:
                macd_line = ta.trend.macd(data['close'], window_fast=fast, window_slow=slow)
                macd_signal = ta.trend.macd_signal(data['close'], window_fast=fast, window_slow=slow, window_sign=signal)
                data[f'macd_{fast}_{slow}'] = macd_line
                data[f'macd_signal_{fast}_{slow}'] = macd_signal
                data[f'macd_histogram_{fast}_{slow}'] = macd_line - macd_signal
                # MACD 크로스오버
                data[f'macd_bullish_{fast}_{slow}'] = ((macd_line > macd_signal) & (macd_line.shift(1) <= macd_signal.shift(1))).astype(int)
                data[f'macd_bearish_{fast}_{slow}'] = ((macd_line < macd_signal) & (macd_line.shift(1) >= macd_signal.shift(1))).astype(int)
            
            # 기본 MACD (하위 호환성)
            data['macd'] = data['macd_12_26']
            data['macd_signal'] = data['macd_signal_12_26']
            data['macd_histogram'] = data['macd_histogram_12_26']
        except:
            # 기본 MACD
            data['macd'] = 0
            data['macd_signal'] = 0
            data['macd_histogram'] = 0
            data['macd_12_26'] = 0
            data['macd_signal_12_26'] = 0
            data['macd_histogram_12_26'] = 0

        # 확장된 스토캐스틱
        try:
            for k_period, d_period in [(14, 3), (21, 3), (14, 5)]:
                stoch_k = ta.momentum.stoch(data['high'], data['low'], data['close'], window=k_period)
                data[f'stoch_k_{k_period}'] = stoch_k
                data[f'stoch_d_{k_period}_{d_period}'] = stoch_k.rolling(d_period).mean()
            
            # 기본 스토캐스틱 (하위 호환성)
            data['stoch_k'] = data['stoch_k_14']
            data['stoch_d'] = data['stoch_d_14_3']
        except:
            data['stoch_k'] = 50
            data['stoch_d'] = 50
            data['stoch_k_14'] = 50
            data['stoch_d_14_3'] = 50

        # 고급 모멘텀 지표
        for period in [3, 5, 10, 15, 20, 30]:
            data[f'price_momentum_{period}'] = data['close'] / data['close'].shift(period) - 1
            data[f'volume_momentum_{period}'] = data['volume'] / data['volume'].shift(period) - 1

        # ROC (Rate of Change)
        for period in [5, 10, 20]:
            data[f'roc_{period}'] = ((data['close'] - data['close'].shift(period)) / data['close'].shift(period)) * 100

        # Williams %R
        try:
            for period in [14, 21]:
                data[f'williams_r_{period}'] = ta.momentum.williams_r(data['high'], data['low'], data['close'], lbp=period)
        except:
            data['williams_r_14'] = -50

        # CCI (Commodity Channel Index)
        try:
            for period in [14, 20]:
                data[f'cci_{period}'] = ta.trend.cci(data['high'], data['low'], data['close'], window=period)
        except:
            data['cci_14'] = 0

        # 확장된 VWAP
        try:
            for period in [10, 20, 30]:
                data[f'vwap_{period}'] = (data['close'] * data['volume']).rolling(period).sum() / data['volume'].rolling(period).sum()
                data[f'price_vwap_ratio_{period}'] = data['close'] / data[f'vwap_{period}']
            
            # 기본 VWAP (하위 호환성)
            data['price_vwap_ratio'] = data['price_vwap_ratio_20']
        except:
            for period in [10, 20, 30]:
                data[f'vwap_{period}'] = data['close']
                data[f'price_vwap_ratio_{period}'] = 1.0
            data['price_vwap_ratio'] = 1.0

        # 확장된 변동성 기반 지표
        data['high_low_ratio'] = (data['high'] - data['low']) / data['close']
        data['close_open_ratio'] = data['close'] / data['open'] - 1
        data['high_close_ratio'] = data['high'] / data['close'] - 1
        data['low_close_ratio'] = data['low'] / data['close'] - 1
        
        # 가격 위치 지표 (일중 어디에 위치하는지)
        data['price_position'] = (data['close'] - data['low']) / (data['high'] - data['low'])

        # 확장된 지지/저항 레벨 근접도
        for period in [10, 20, 30, 60]:
            data[f'recent_high_{period}'] = data['high'].rolling(period).max()
            data[f'recent_low_{period}'] = data['low'].rolling(period).min()
            data[f'high_proximity_{period}'] = (data[f'recent_high_{period}'] - data['close']) / data[f'recent_high_{period}']
            data[f'low_proximity_{period}'] = (data['close'] - data[f'recent_low_{period}']) / data[f'recent_low_{period}']

        # 기본 지지/저항 (하위 호환성)
        data['high_proximity'] = data['high_proximity_20']
        data['low_proximity'] = data['low_proximity_20']

        # 추세 강도 지표
        data['trend_strength'] = abs(data['ma_slope_20']) * data['volume_ratio_20d']
        
        # 상대적 성과 지표 (섹터 대비)
        data['relative_volume'] = data['volume'] / data['volume'].rolling(60).mean()
        data['relative_volatility'] = data['volatility_20d'] / data['volatility_20d'].rolling(60).mean()

        # 시간 기반 피처
        if 'timestamp' in data.columns:
            data['timestamp_dt'] = pd.to_datetime(data['timestamp'])
            data['day_of_week'] = data['timestamp_dt'].dt.dayofweek
            data['month'] = data['timestamp_dt'].dt.month
            data['quarter'] = data['timestamp_dt'].dt.quarter
            data['is_month_end'] = (data['timestamp_dt'].dt.is_month_end).astype(int)
            data['is_quarter_end'] = ((data['timestamp_dt'].dt.month % 3 == 0) & 
                                     (data['timestamp_dt'].dt.is_month_end)).astype(int)

        # 연속 상승/하락 일수
        data['is_up'] = (data['close'] > data['close'].shift(1)).astype(int)
        data['consecutive_up'] = data['is_up'].groupby((data['is_up'] != data['is_up'].shift()).cumsum()).cumsum()
        data['consecutive_down'] = (1 - data['is_up']).groupby(((1 - data['is_up']) != (1 - data['is_up']).shift()).cumsum()).cumsum()

        # 갭 분석
        data['gap_up'] = ((data['open'] > data['close'].shift(1)) & 
                         ((data['open'] - data['close'].shift(1)) / data['close'].shift(1) > 0.02)).astype(int)
        data['gap_down'] = ((data['open'] < data['close'].shift(1)) & 
                           ((data['close'].shift(1) - data['open']) / data['close'].shift(1) > 0.02)).astype(int)

        # 라그 피처 (과거 정보)
        for lag in [1, 2, 3, 5, 7]:
            data[f'close_lag_{lag}'] = data['close'].shift(lag)
            data[f'volume_lag_{lag}'] = data['volume'].shift(lag)
            data[f'return_lag_{lag}'] = data['return_1d'].shift(lag)

        # 추가 지표들
        # 양봉/음봉 연속성
        data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
        data['candle_streak'] = data['candle_type'].rolling(3).sum()
        
        # 거래량 가격 상관성
        data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
        
        # 가격 가속도
        data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
        
        # 심리적 저항선 근접도 (천원 단위)
        data['round_number_proximity'] = (data['close'] % 1000) / 1000

        return data
        
    except Exception as e:
        print(f"기술적 지표 생성 오류: {e}")
        # 최소한의 지표라도 생성
        data['return_1d'] = data['close'].pct_change(1)
        # 추가 지표들
        # 양봉/음봉 연속성
        data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
        data['candle_streak'] = data['candle_type'].rolling(3).sum()
        
        # 거래량 가격 상관성
        data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
        
        # 가격 가속도
        data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
        
        # 심리적 저항선 근접도 (천원 단위)
        data['round_number_proximity'] = (data['close'] % 1000) / 1000
        
        return data

def get_technical_score(ticker):
    """규칙 기반 기술적 분석 점수 계산 (0.0~1.0) - 백테스팅 엔진 개선 버전"""
    try:
        # 최근 데이터 가져오기
        data = get_past_data_enhanced(ticker, n=50)
        if len(data) < 30:
            return 0.5  # 데이터 부족시 중립

        # 기술적 지표 생성
        data = create_technical_features(data)
        latest = data.iloc[-1]

        # NaN 체크
        if pd.isna(latest.get('rsi_14', np.nan)) or pd.isna(latest.get('price_ma_ratio_20', np.nan)):
            return 0.5

        score = 0.5  # 기본점수

        # 1. RSI 기반 과매도 판단
        rsi = latest['rsi_14']
        if rsi < 25:
            score += 0.25  # 강한 과매도
        elif rsi < 35:
            score += 0.15  # 과매도
        elif rsi > 75:
            score -= 0.2   # 과매수

        # 2. 이동평균 대비 위치 (현재 전략과 일치)
        ma_signals = 0
        for period in [5, 10, 20]:
            if latest[f'price_ma_ratio_{period}'] < 0.98:  # 이동평균 아래
                ma_signals += 1

        if ma_signals >= 2:
            score += 0.2  # 이동평균 아래에서 매수 기회

        # 3. 단기 반등 시그널
        if latest['return_1d'] > 0.01 and latest.get('return_3d', 0) < -0.02:
            score += 0.15  # 단기 반등

        # 4. 거래량 급증
        volume_ratio = latest.get('volume_ratio_5d', 1.0)
        if volume_ratio > 1.8:
            score += 0.1
        elif volume_ratio > 1.3:
            score += 0.05

        # 5. 변동성 조정
        if latest.get('volatility_10d', 0) > 0.05:  # 고변동성
            score -= 0.1

        # 6. 볼린저 밴드 하단 근처
        if latest.get('bb_position', 0) < -0.8:
            score += 0.15

        return max(0.0, min(1.0, score))

    except Exception as e:
        print(f"기술적 점수 계산 오류 ({ticker}): {e}")
        return 0.5

def get_technical_hold_signal(ticker):
    """보유 종목에 대한 규칙 기반 홀드/매도 시그널 - 백테스팅 엔진 개선 버전"""
    try:
        data = get_past_data_enhanced(ticker, n=30)
        if len(data) < 20:
            return 0.5

        # 기술적 지표 생성
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
        if latest.get('bb_position', 0) > 0.8:
            hold_score -= 0.2

        return max(0.0, min(1.0, hold_score))

    except:
        return 0.5

def prepare_training_data(lookback_days=1000):  # 500일 → 1000일로 확대
    """AI 모델 학습용 데이터 준비 (성능 개선 버전)"""
    print("📚 AI 모델 학습 데이터 준비 중...")

    try:
        # 과거 데이터 수집 (1000일로 확대)
        historical_data = ht.get_past_data_total(n=lookback_days)

        if len(historical_data) < 300:  # 최소 데이터 요구사항 강화
            print("❌ 학습 데이터 부족 (최소 300일 필요)")
            return None, None

        all_features = []
        all_targets = []
        data_quality_stats = {
            'total_tickers': 0,
            'qualified_tickers': 0,
            'total_samples': 0,
            'removed_outliers': 0
        }

        # 종목별로 데이터 처리
        for ticker in historical_data['ticker'].unique():
            data_quality_stats['total_tickers'] += 1
            ticker_data = historical_data[historical_data['ticker'] == ticker].sort_values('timestamp')

            if len(ticker_data) < 100:  # 종목별 최소 데이터 요구사항 강화
                continue

            # 강화된 기술적 지표 생성
            ticker_data = create_technical_features(ticker_data.copy())

            # 다중 기간 미래 수익률 계산
            for future_days in [3, 5, 7]:
                ticker_data[f'future_{future_days}d_return'] = ticker_data['close'].shift(-future_days) / ticker_data['close'] - 1

            # 유효한 데이터만 사용 (NaN 제거)
            valid_data = ticker_data.dropna()

            if len(valid_data) < 50:  # 종목별 최소 유효 샘플 증가
                continue

            # 이상치 제거 (Z-score 기반)
            from scipy import stats
            numeric_columns = valid_data.select_dtypes(include=[np.number]).columns
            z_scores = np.abs(stats.zscore(valid_data[numeric_columns], nan_policy='omit'))
            outlier_mask = (z_scores < 3).all(axis=1)  # Z-score가 3 미만인 행만 유지
            
            initial_count = len(valid_data)
            valid_data = valid_data[outlier_mask]
            data_quality_stats['removed_outliers'] += initial_count - len(valid_data)

            if len(valid_data) < 30:
                continue

            data_quality_stats['qualified_tickers'] += 1

            # 안전한 피처 선택 (기존 이름과 일치)
            available_features = []
            
            # 1단계: 확실히 존재하는 기본 피처들
            basic_features = [
                # 기본 수익률
                'return_1d', 'return_3d', 'return_5d', 'return_10d', 'return_20d',
                
                # 이동평균 비율  
                'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20', 'price_ma_ratio_60',
                
                # RSI 지표
                'rsi_14', 'rsi_30',
                
                # 거래량 지표 (기존 이름)
                'volume_ratio_5d', 'volume_ratio_20d',
                
                # 변동성 지표
                'volatility_10d', 'volatility_20d',
                
                # 볼린저 밴드 (기존 이름)
                'bb_position', 'bb_width',
                
                # MACD (기존 이름)
                'macd', 'macd_signal', 'macd_histogram',
                
                # 스토캐스틱 (기존 이름)
                'stoch_k', 'stoch_d',
                
                # 모멘텀
                'price_momentum_5', 'price_momentum_10', 'price_momentum_20',
                
                # VWAP (기존 이름)
                'price_vwap_ratio',
                
                # 기타 지표
                'high_low_ratio', 'close_open_ratio',
                'high_proximity', 'low_proximity'
            ]
            
            # 기본 피처들 중 존재하는 것들 추가
            for feature in basic_features:
                if feature in valid_data.columns:
                    available_features.append(feature)
            
            print(f"   📊 기본 피처: {len([f for f in basic_features if f in valid_data.columns])}개")
            
            # 2단계: 추가 피처들 (존재할 때만 추가)
            additional_count = 0
            
            # 추가 수익률
            for period in [2, 7, 14, 30]:
                if f'return_{period}d' in valid_data.columns:
                    available_features.append(f'return_{period}d')
                    additional_count += 1
            
            # 추가 이동평균
            for period in [15, 30, 120]:
                if f'price_ma_ratio_{period}' in valid_data.columns:
                    available_features.append(f'price_ma_ratio_{period}')
                    additional_count += 1
            
            # 이동평균 기울기
            for period in [5, 10, 20, 30]:
                if f'ma_slope_{period}' in valid_data.columns:
                    available_features.append(f'ma_slope_{period}')
                    additional_count += 1
            
            # 추가 RSI
            for period in [7, 21]:
                if f'rsi_{period}' in valid_data.columns:
                    available_features.append(f'rsi_{period}')
                    additional_count += 1
            
            # RSI 보조 지표
            for indicator in ['rsi_oversold', 'rsi_overbought']:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
            
            # 추가 거래량 지표
            for period in [3, 10, 30]:
                if f'volume_ratio_{period}d' in valid_data.columns:
                    available_features.append(f'volume_ratio_{period}d')
                    additional_count += 1
            
            # 거래량 가중 수익률
            if 'volume_weighted_return' in valid_data.columns:
                available_features.append('volume_weighted_return')
                additional_count += 1
            
            # 추가 변동성
            for period in [5, 30]:
                if f'volatility_{period}d' in valid_data.columns:
                    available_features.append(f'volatility_{period}d')
                    additional_count += 1
            
            # 변동성 비율
            if 'volatility_ratio' in valid_data.columns:
                available_features.append('volatility_ratio')
                additional_count += 1
            
            # 확장 볼린저 밴드
            for period in [10, 30]:
                for indicator in [f'bb_position_{period}', f'bb_width_{period}']:
                    if indicator in valid_data.columns:
                        available_features.append(indicator)
                        additional_count += 1
            
            # 볼린저 밴드 스퀴즈
            if 'bb_squeeze' in valid_data.columns:
                available_features.append('bb_squeeze')
                additional_count += 1
            
            # 확장 MACD
            for fast, slow in [(5, 35), (19, 39)]:
                for indicator in [f'macd_{fast}_{slow}', f'macd_signal_{fast}_{slow}', f'macd_histogram_{fast}_{slow}']:
                    if indicator in valid_data.columns:
                        available_features.append(indicator)
                        additional_count += 1
            
            # MACD 크로스오버
            for fast, slow in [(12, 26), (5, 35), (19, 39)]:
                for indicator in [f'macd_bullish_{fast}_{slow}', f'macd_bearish_{fast}_{slow}']:
                    if indicator in valid_data.columns:
                        available_features.append(indicator)
                        additional_count += 1
            
            # 확장 스토캐스틱
            for indicator in ['stoch_k_21', 'stoch_d_21_3']:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
            
            # 확장 모멘텀
            for period in [3, 15, 30]:
                for momentum_type in ['price_momentum', 'volume_momentum']:
                    if f'{momentum_type}_{period}' in valid_data.columns:
                        available_features.append(f'{momentum_type}_{period}')
                        additional_count += 1
            
            # 고급 기술적 지표들
            advanced_indicators = ['williams_r_14', 'williams_r_21', 'cci_14', 'cci_20']
            for indicator in advanced_indicators:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
                    
            # ROC
            for period in [5, 10, 20]:
                if f'roc_{period}' in valid_data.columns:
                    available_features.append(f'roc_{period}')
                    additional_count += 1
            
            # 확장 VWAP
            for period in [10, 30]:
                for indicator in [f'vwap_{period}', f'price_vwap_ratio_{period}']:
                    if indicator in valid_data.columns:
                        available_features.append(indicator)
                        additional_count += 1
            
            # 기타 가격 지표들
            price_indicators = ['high_close_ratio', 'low_close_ratio', 'price_position']
            for indicator in price_indicators:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
            
            # 추세 지표들
            trend_indicators = ['trend_strength', 'relative_volume', 'relative_volatility']
            for indicator in trend_indicators:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
            
            # 시간 기반 피처들
            time_features = ['day_of_week', 'month', 'quarter', 'is_month_end', 'is_quarter_end']
            for feature in time_features:
                if feature in valid_data.columns:
                    available_features.append(feature)
                    additional_count += 1
            
            # 연속성 지표
            for indicator in ['consecutive_up', 'consecutive_down']:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
            
            # 갭 분석
            for indicator in ['gap_up', 'gap_down']:
                if indicator in valid_data.columns:
                    available_features.append(indicator)
                    additional_count += 1
            
            # 지지/저항 레벨 (기존 이름 + 추가)
            for period in [10, 30, 60]:
                for proximity_type in ['high_proximity', 'low_proximity']:
                    # 기존 이름 (숫자 없는 버전)은 이미 추가됨
                    if f'{proximity_type}_{period}' in valid_data.columns:
                        available_features.append(f'{proximity_type}_{period}')
                        additional_count += 1
            
            # 라그 피처들
            for lag in [1, 2, 3, 5, 7]:
                for lag_type in ['close_lag', 'volume_lag', 'return_lag']:
                    if f'{lag_type}_{lag}' in valid_data.columns:
                        available_features.append(f'{lag_type}_{lag}')
                        additional_count += 1
            
            # 중복 제거
            available_features = list(set(available_features))
            
            print(f"   📊 추가 피처: {additional_count}개")
            print(f"   📊 총 사용 피처: {len(available_features)}개")

            if len(available_features) < 20:  # 최소 피처 수를 20개로 완화
                print(f"   ⚠️ 피처 부족 ({len(available_features)}개 < 20개): {ticker} 스킵")
                continue

            # 피처 스케일링 (StandardScaler 적용)
            from sklearn.preprocessing import StandardScaler
            
            features = valid_data[available_features].values
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            # 개선된 타겟 생성: 이진 분류로 단순화
            future_5d_return = valid_data['future_5d_return']
            
            # 이진 분류: 0(손실/횡보), 1(수익)
            # 수수료 0.3% × 2 = 0.6% 고려하여 1% 이상을 수익으로 정의
            targets = np.where(future_5d_return >= 0.01, 1, 0)

            # 미래 데이터가 없는 마지막 7개 제외
            if len(features_scaled) > 7:
                features_scaled = features_scaled[:-7]
                targets = targets[:-7]

                all_features.extend(features_scaled)
                all_targets.extend(targets)
                data_quality_stats['total_samples'] += len(features_scaled)

        if len(all_features) < 500:  # 최소 샘플 수 강화
            print("❌ 충분한 학습 데이터 확보 실패")
            print(f"📊 수집된 샘플: {len(all_features)}개 (최소 500개 필요)")
            return None, None

        print(f"✅ 학습 데이터 준비 완료:")
        print(f"   📊 총 샘플: {len(all_features)}개")
        print(f"   📈 분석 종목: {data_quality_stats['qualified_tickers']}/{data_quality_stats['total_tickers']}개")
        print(f"   🎯 타겟 분포: {np.bincount(all_targets)}")
        print(f"   📐 피처 수: {len(available_features)}개")
        print(f"   🚫 제거된 이상치: {data_quality_stats['removed_outliers']}개")

        return np.array(all_features), np.array(all_targets)

    except Exception as e:
        print(f"❌ 데이터 준비 오류: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def train_ai_model():
    """AI 모델 훈련 (백테스팅 엔진 성능 최적화 버전)"""
    print("🤖 AI 모델 훈련 시작...")

    # 학습 데이터 준비
    X, y = prepare_training_data()

    if X is None or len(X) < 500:
        print("❌ 학습 데이터 부족으로 모델 훈련 불가")
        return None

    try:
        from sklearn.model_selection import StratifiedKFold
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
        
        # 데이터 분할 (시계열 고려)
        # 학습:검증:테스트 = 70:15:15
        n_samples = len(X)
        train_end = int(n_samples * 0.7)
        val_end = int(n_samples * 0.85)
        
        X_train = X[:train_end]
        y_train = y[:train_end]
        X_val = X[train_end:val_end]
        y_val = y[train_end:val_end]
        X_test = X[val_end:]
        y_test = y[val_end:]

        # 클래스 불균형 해결을 위한 언더샘플링 (훈련 데이터만)
        from sklearn.utils import resample
        
        # 각 클래스별로 데이터 분리
        X_train_class0 = X_train[y_train == 0]
        X_train_class1 = X_train[y_train == 1]
        
        # 균형잡힌 샘플링
        min_class_size = min(len(X_train_class0), len(X_train_class1))
        
        # 언더샘플링 또는 오버샘플링
        if len(X_train_class0) > len(X_train_class1):
            # 클래스 0이 더 많으면 언더샘플링
            X_train_class0_resampled = resample(X_train_class0, n_samples=int(len(X_train_class1) * 1.5), random_state=42)
            X_train_class1_resampled = X_train_class1
        else:
            # 클래스 1이 더 많으면 언더샘플링
            X_train_class0_resampled = X_train_class0
            X_train_class1_resampled = resample(X_train_class1, n_samples=int(len(X_train_class0) * 1.5), random_state=42)
        
        # 재결합
        X_train = np.vstack([X_train_class0_resampled, X_train_class1_resampled])
        y_train = np.hstack([
            np.zeros(len(X_train_class0_resampled)),
            np.ones(len(X_train_class1_resampled))
        ])
        
        # 셔플
        shuffle_idx = np.random.permutation(len(X_train))
        X_train = X_train[shuffle_idx]
        y_train = y_train[shuffle_idx].astype(int)

        print(f"📊 데이터 분할: 훈련({len(X_train)}) / 검증({len(X_val)}) / 테스트({len(X_test)})")

        # 개선된 LightGBM 파라미터 (이진 분류)
        lgb_params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_data_in_leaf': 30,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'min_gain_to_split': 0.05,
            'max_depth': 6,
            'verbose': -1,
            'random_state': 42,
            'force_col_wise': True,
            'is_unbalance': True,
            'boost_from_average': True,
        }

        # 클래스 가중치 계산 (수동으로 계산하여 적용)
        from sklearn.utils.class_weight import compute_class_weight
        
        class_weights = compute_class_weight(
            'balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        
        print(f"📊 클래스 가중치: {dict(zip(np.unique(y_train), class_weights))}")
        
        # 가중치를 적용한 샘플 가중치 생성
        sample_weights = np.array([class_weights[label] for label in y_train])

        # 데이터셋 생성 (클래스 가중치 적용)
        train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weights)
        valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        # 모델 훈련 (조기 종료 조건 완화)
        model = lgb.train(
            lgb_params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=500,  # 증가
            callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(50)]
        )

        # 다중 성능 평가 (이진 분류)
        y_pred_val_proba = model.predict(X_val)
        y_pred_test_proba = model.predict(X_test)
        
        # 이진 분류 예측
        y_pred_val = (y_pred_val_proba > 0.5).astype(int)
        y_pred_test = (y_pred_test_proba > 0.5).astype(int)
        
        val_accuracy = accuracy_score(y_val, y_pred_val)
        test_accuracy = accuracy_score(y_test, y_pred_test)

        print(f"✅ 모델 훈련 완료!")
        print(f"📊 검증 정확도: {val_accuracy:.3f}")
        print(f"📊 테스트 정확도: {test_accuracy:.3f}")
        
        # 클래스별 성능 분석
        print(f"📊 검증 데이터 클래스별 예측 분포:")
        print(f"   실제: {np.bincount(y_val)}")
        print(f"   예측: {np.bincount(y_pred_val)}")
        
        # 추가 성능 지표 출력
        from sklearn.metrics import roc_auc_score
        try:
            auc_score = roc_auc_score(y_test, y_pred_test_proba)
            print(f"📊 AUC 점수: {auc_score:.3f}")
        except:
            auc_score = 0.5

        # 모델 품질 검증 (이진 분류)
        model_quality_score = 0
        
        # 1. AUC 점수 (0-30점)
        model_quality_score += min(auc_score * 30, 30) if 'auc_score' in locals() else 15
        
        # 2. F1 점수 (0-30점)
        from sklearn.metrics import f1_score, precision_score, recall_score
        f1 = f1_score(y_test, y_pred_test)
        precision = precision_score(y_test, y_pred_test)
        recall = recall_score(y_test, y_pred_test)
        model_quality_score += f1 * 30
        
        # 3. 정밀도 (0-20점) - 거짓 양성을 줄이는 것이 중요
        model_quality_score += precision * 20
        
        # 4. 재현율 (0-20점)
        model_quality_score += recall * 20
        
        print(f"🏆 모델 품질 점수: {model_quality_score:.1f}/100")
        print(f"   📊 AUC: {auc_score:.3f}" if 'auc_score' in locals() else "   📊 AUC: N/A")
        print(f"   📊 정확도: {test_accuracy:.3f}")
        print(f"   📊 정밀도: {precision:.3f}")
        print(f"   📊 재현율: {recall:.3f}")
        print(f"   📊 F1 점수: {f1:.3f}")
        
        # 혼동 행렬 출력
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_test, y_pred_test)
        print(f"   📊 혼동 행렬:")
        print(f"      예측 0    예측 1")
        print(f"   실제 0: {cm[0,0]:6d} {cm[0,1]:6d}")
        print(f"   실제 1: {cm[1,0]:6d} {cm[1,1]:6d}")

        # 모델 저장
        model.save_model('ai_price_prediction_model.txt')
        print("💾 모델 저장 완료: ai_price_prediction_model.txt")

        # 모델 메타데이터 저장 (확장)
        model_metadata = {
            'train_date': datetime.now().isoformat(),
            'model_type': 'LightGBM_Binary_Optimized',
            'train_samples': len(X_train),
            'test_accuracy': float(test_accuracy),
            'val_accuracy': float(val_accuracy),
            'model_quality_score': float(model_quality_score),
            'feature_count': X_train.shape[1],
            'class_count': 2,
            'class_distribution': {
                'train': np.bincount(y_train).tolist(),
                'test': np.bincount(y_test).tolist()
            },
            'prediction_distribution': {
                'val': np.bincount(y_pred_val).tolist(),
                'test': np.bincount(y_pred_test).tolist()
            }
        }
        
        with open('ai_model_metadata.json', 'w') as f:
            json.dump(model_metadata, f, indent=2)

        # 모델 메타데이터 저장
        model.model_quality_score = model_quality_score
        model.test_accuracy = test_accuracy
        model.train_date = datetime.now().isoformat()

        return model

    except Exception as e:
        print(f"❌ 모델 훈련 오류: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def load_ai_model():
    """저장된 AI 모델 로드 (강화된 버전)"""
    try:
        if os.path.exists('ai_price_prediction_model.txt'):
            model = lgb.Booster(model_file='ai_price_prediction_model.txt')
            
            # 모델 메타데이터 검증
            try:
                with open('ai_model_metadata.json', 'r') as f:
                    metadata = json.load(f)
                    
                print(f"📅 모델 훈련일: {metadata.get('train_date', 'Unknown')}")
                print(f"📊 모델 품질: {metadata.get('model_quality_score', 0):.1f}/100")
                print(f"🎯 테스트 정확도: {metadata.get('test_accuracy', 0):.3f}")
                
                # 모델이 너무 오래되었는지 확인 (7일 이상)
                train_date = metadata.get('train_date')
                if train_date:
                    from datetime import datetime, timedelta
                    train_datetime = datetime.fromisoformat(train_date.replace('Z', '+00:00'))
                    days_old = (datetime.now() - train_datetime).days
                    
                    if days_old > 7:
                        print(f"⚠️ 모델이 {days_old}일 전에 훈련됨. 재훈련을 권장합니다.")
                        
                        # 자동 재훈련 여부 결정
                        if days_old > 14:  # 2주 이상 된 모델은 자동 재훈련
                            print("🔄 모델이 너무 오래되어 자동 재훈련 시작...")
                            return train_ai_model()
                
            except FileNotFoundError:
                print("⚠️ 모델 메타데이터 없음")
            except Exception as e:
                print(f"⚠️ 메타데이터 읽기 오류: {e}")
            
            return model
        else:
            print("📝 저장된 모델이 없어 새로 훈련합니다...")
            return train_ai_model()
            
    except Exception as e:
        print(f"❌ 모델 로드 오류: {e}")
        print("🔄 새 모델 훈련 시도...")
        return train_ai_model()

def get_ai_prediction_score(ticker, model):
    """AI 모델을 사용한 실제 예측 점수 (다중 클래스 대응) - 백테스팅 엔진 개선 버전"""
    try:
        # 최근 데이터 가져오기
        data = get_past_data_enhanced(ticker, n=80)  # 더 많은 데이터 확보
        if len(data) < 60:
            return 0.3  # 데이터 부족시 낮은 점수

        # 강화된 기술적 지표 생성
        data = create_technical_features(data)
        latest = data.iloc[-1]

        # 핵심 피처 추출 (훈련시와 동일한 순서 - 25개)
        feature_columns = [
            'return_1d', 'return_3d', 'return_5d', 'return_10d', 'return_20d',
            'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
            'rsi_14', 'volume_ratio_5d', 'volume_ratio_20d',
            'volatility_10d', 'volatility_20d',
            'bb_position', 'bb_width', 'macd_histogram', 'stoch_k',
            'price_momentum_5', 'price_momentum_10', 'low_proximity',
            'candle_streak', 'volume_price_corr', 'price_acceleration', 'round_number_proximity'
        ]

        # 피처 벡터 생성 (결측치 처리 강화)
        features = []
        missing_features = 0
        
        for col in feature_columns:
            if col in latest.index and not pd.isna(latest[col]) and np.isfinite(latest[col]):
                features.append(float(latest[col]))
            else:
                # 피처별 기본값 설정
                if 'return' in col:
                    features.append(0.0)
                elif 'ratio' in col:
                    features.append(1.0)
                elif 'rsi' in col:
                    features.append(50.0)
                elif 'bb_position' in col:
                    features.append(0.0)
                elif 'volume_ratio' in col:
                    features.append(1.0)
                elif 'volatility' in col:
                    features.append(0.02)
                elif 'candle_streak' in col:
                    features.append(0.0)
                elif 'corr' in col:
                    features.append(0.0)
                elif 'acceleration' in col:
                    features.append(0.0)
                elif 'proximity' in col:
                    features.append(0.5)
                else:
                    features.append(0.0)
                missing_features += 1

        # 너무 많은 피처가 누락되면 낮은 점수 반환
        if missing_features > len(feature_columns) * 0.3:  # 30% 이상 누락
            print(f"⚠️ {ticker}: 피처 누락 비율 높음 ({missing_features}/{len(feature_columns)})")
            return 0.2

        # AI 예측 (다중 클래스 확률)
        prediction_probs = model.predict([features])[0]  # [class0_prob, class1_prob, class2_prob]
        
        # 수익 클래스(1, 2)의 확률 합계를 신뢰도 점수로 사용
        profit_probability = prediction_probs[1] + prediction_probs[2]  # 소폭수익 + 큰수익
        
        # 큰 수익(클래스 2)에 가중치 부여
        weighted_score = prediction_probs[1] * 0.6 + prediction_probs[2] * 1.0
        
        # 최종 점수는 가중치 적용된 점수와 단순 수익 확률의 평균
        final_score = (weighted_score + profit_probability) / 2
        
        # 추가 신뢰도 검증
        confidence_bonus = 0
        
        # 1. 예측 확신도 (최대 클래스 확률이 높을수록 보너스)
        max_prob = max(prediction_probs)
        if max_prob > 0.6:
            confidence_bonus += 0.1
        elif max_prob > 0.5:
            confidence_bonus += 0.05
            
        # 2. 큰 수익 클래스 확률이 높으면 추가 보너스
        if prediction_probs[2] > 0.3:
            confidence_bonus += 0.1
            
        final_score = min(1.0, final_score + confidence_bonus)

        return float(final_score)

    except Exception as e:
        print(f"❌ AI 예측 오류 ({ticker}): {e}")
        return 0.2

def ai_enhanced_final_selection(entry_tickers):
    """AI를 활용한 최종 종목 선정 (백테스팅 엔진 강화 버전)"""
    print("🤖 AI 최종 종목 선정 시작...")

    # AI 모델 로드
    ai_model = load_ai_model()
    if ai_model is None:
        print("❌ AI 모델을 사용할 수 없어 빈 리스트 반환")
        return []

    # 모델 메타데이터 확인
    model_quality_score = 60  # 기본값
    try:
        with open('ai_model_metadata.json', 'r') as f:
            metadata = json.load(f)
            model_quality_score = metadata.get('model_quality_score', 60)
            print(f"📊 모델 품질 점수: {model_quality_score:.1f}/100")
    except:
        print("⚠️ 모델 메타데이터 없음, 기본 설정으로 진행")

    # 모델 품질이 너무 낮으면 거래 중단
    if model_quality_score < 40:
        print("❌ 모델 품질이 너무 낮아 거래를 중단합니다.")
        return []

    ai_scored_tickers = []

    # 각 종목에 대해 AI 예측 점수 계산
    for ticker in entry_tickers:
        ai_score = get_ai_prediction_score(ticker, ai_model)
        ai_scored_tickers.append({
            'ticker': ticker,
            'ai_score': ai_score
        })

        print(f"🎯 {ticker}: AI 예측 점수 = {ai_score:.3f}")

    # AI 점수로 정렬
    ai_scored_tickers.sort(key=lambda x: x['ai_score'], reverse=True)

    # 신뢰도 기준 현실화: 모델 품질에 따라 동적 조정
    if model_quality_score >= 65:
        min_score_threshold = 0.55  # 우수한 모델: 0.55 이상
        max_selections = 5
    elif model_quality_score >= 50:
        min_score_threshold = 0.60  # 양호한 모델: 0.60 이상
        max_selections = 4
    else:
        min_score_threshold = 0.65  # 보통 모델: 0.65 이상
        max_selections = 3

    print(f"📏 신뢰도 기준: {min_score_threshold:.2f} 이상 (최대 {max_selections}개)")

    # 기준을 만족하는 종목만 선정
    final_selection = []
    high_confidence_count = 0
    medium_confidence_count = 0
    hybrid_count = 0  # 하이브리드 선정 카운트
    
    for item in ai_scored_tickers:
        if len(final_selection) >= max_selections:
            break
            
        # 고신뢰: AI 점수만으로 선정
        if item['ai_score'] >= min_score_threshold:
            final_selection.append(item['ticker'])
            
            # 신뢰도 분류 (현실적 기준)
            if item['ai_score'] >= 0.65:
                high_confidence_count += 1
            elif item['ai_score'] >= 0.55:
                medium_confidence_count += 1
                
        # 하이브리드 접근: AI 점수가 중간 수준이면 기술적 분석과 결합
        elif item['ai_score'] >= (min_score_threshold - 0.10) and len(final_selection) < max_selections:
            # 해당 종목의 기술적 점수 확인
            ticker = item['ticker']
            technical_score = strategy_data.get('technical_analysis', {}).get(ticker, {}).get('score', 0.6)
            
            # AI 점수와 기술적 점수의 가중 평균
            combined_score = (item['ai_score'] * 0.7) + (technical_score * 0.3)
            
            # 결합 점수가 기준을 만족하면 선정
            if combined_score >= (min_score_threshold - 0.05):
                final_selection.append(ticker)
                hybrid_count += 1
                print(f"🔄 {ticker}: 하이브리드 선정 (AI: {item['ai_score']:.3f}, 기술: {technical_score:.3f}, 결합: {combined_score:.3f})")

    # 선정 결과 출력
    if len(final_selection) == 0:
        print("❌ AI 신뢰도 기준을 만족하는 종목이 없습니다.")
        print("⚠️ 오늘은 매수를 건너뛰겠습니다.")
        
        # 가장 높은 점수라도 출력
        if ai_scored_tickers:
            best_score = ai_scored_tickers[0]['ai_score']
            print(f"📊 최고 점수: {best_score:.3f} (기준: {min_score_threshold:.2f})")
    else:
        print(f"🏆 AI 최종 선정: {len(final_selection)}개 종목")
        print(f"   🟢 고신뢰(0.65+): {high_confidence_count}개")
        print(f"   🟡 중신뢰(0.55+): {medium_confidence_count}개")
        print(f"   🔄 하이브리드: {hybrid_count}개")

    # AI 예측 결과 저장 (모든 종목의 점수 저장)
    strategy_data['ai_predictions'] = {}
    for item in ai_scored_tickers:
        # 개선된 신뢰도 레벨 분류 (현실적 기준)
        if item['ai_score'] >= 0.80:
            confidence_level = "고신뢰"
        elif item['ai_score'] >= 0.70:
            confidence_level = "중신뢰"
        elif item['ai_score'] >= 0.60:
            confidence_level = "저신뢰"
        else:
            confidence_level = "매우저신뢰"
            
        strategy_data['ai_predictions'][item['ticker']] = {
            'score': item['ai_score'],
            'confidence_level': confidence_level,
            'timestamp': datetime.now().isoformat(),
            'selected': item['ticker'] in final_selection,
            'model_quality': model_quality_score
        }

    return final_selection

def enhanced_stock_selection():
    """기술적 분석 강화 종목 선정 (기존 전략 + 규칙 기반 분석)"""
    print("📊 기술적 분석 강화 종목 분석 시작...")

    # 기존 전략 로직
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
        # 기술적 점수가 높을수록 거래량에 추가 가중치
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

# 전략의 시간을 체크할 while문
executed_date = None  # 실행 완료된 날짜 저장

while True:
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')

    # 날짜가 바뀌면 실행 플래그 리셋
    if executed_date != current_date:
        executed_today = False
    else:
        executed_today = True

    # 8시 30분~32분 - 매도 전용 실행 (여유시간 2분)
    if current_time.hour == 8 and 30 <= current_time.minute <= 32 and not executed_today:
    # if True:
        print("🌅 아침 매도 전략 실행 시작!")

        # === 현재 보유중인 종목 조회 ===
        holdings = ht.get_holding_stock()
        print(f"📊 현재 보유: {len(holdings)}개")

        # === holding_period를 하루씩 높여줌 ===
        for ticker in holdings:
            if ticker not in strategy_data['holding_period']:
                strategy_data['holding_period'][ticker] = 1
            else:
                strategy_data['holding_period'][ticker] += 1

        # === 기술적 분석 강화 매도 전략 ===
        ticker_to_sell = []
        for ticker in holdings:
            holding_days = strategy_data['holding_period'][ticker]
            should_sell = False

            # 기본 3일 룰
            if holding_days >= 3:
                should_sell = True

                # 기술적 홀드 시그널 체크 (3일차에만)
                if holding_days == 3 and strategy_data['enhanced_analysis_enabled']:
                    hold_signal = get_technical_hold_signal(ticker)

                    if hold_signal >= 0.75:
                        should_sell = False
                        print(f"📊 {ticker}: 기술적 분석 강홀드 신호로 1일 연장 (신호강도: {hold_signal:.3f})")
                    elif hold_signal <= 0.25:
                        print(f"⚠️ {ticker}: 기술적 분석 매도 신호 (신호강도: {hold_signal:.3f})")

            # 안전장치: 5일 이상은 무조건 매도
            if holding_days >= 5:
                should_sell = True
                print(f"⏰ {ticker}: 5일 안전룰 적용")

            if should_sell:
                ticker_to_sell.append(ticker)

        print(f"📤 매도 예정: {len(ticker_to_sell)}개")

        # === 수익률 추적 매도 실행 ===
        sold_tickers = []
        total_sell_profit = 0

        for ticker in ticker_to_sell:
            holding_days = strategy_data['holding_period'][ticker]

            try:
                # 매도 전 수익률 계산
                purchase_info = strategy_data.get('purchase_info', {}).get(ticker, {})
                try:
                    current_data = ht.get_past_data(ticker, n=1)
                    current_price = current_data['close']
                except:
                    current_price = None

                # 변수 초기화
                profit_info = ""
                profit = 0
                profit_rate = 0.0
                
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

                    try:
                        ht.post_message(sell_message, HANLYANG_CHANNEL_ID)
                        print(f"✅ {ticker} 매도 슬랙 알림 전송")
                    except Exception as e:
                        print(f"❌ {ticker} 매도 슬랙 알림 실패: {e}")

                    # 매도 완료 후 구매 정보 정리
                    if ticker in strategy_data.get('purchase_info', {}):
                        del strategy_data['purchase_info'][ticker]

                strategy_data['holding_period'][ticker] = 0

            except Exception as e:
                print(f"❌ {ticker} 매도 처리 오류: {e}")

        if total_sell_profit != 0:
            print(f"💰 총 매도 손익: {total_sell_profit:+,}원")

        # === 아침 매도 완료 슬랙 알림 ===
        morning_summary_message = f"🌅 **아침 매도 완료!**\n"
        morning_summary_message += f"📤 매도: {len(sold_tickers)}개"
        if total_sell_profit != 0:
            morning_summary_message += f" (손익: {total_sell_profit:+,}원)"
        morning_summary_message += f"\n📊 현재 보유: {len(holdings) - len(sold_tickers)}개"
        morning_summary_message += f"\n⏰ 실행 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        morning_summary_message += f"\n🔔 오후 3시 20분에 매수 전략 실행 예정"

        try:
            ht.post_message(morning_summary_message, HANLYANG_CHANNEL_ID)
            print("✅ 슬랙 아침 매도 완료 알림 전송")
        except Exception as e:
            print(f"❌ 슬랙 알림 실패: {e}")

        # 성과 로깅 (매도 전용)
        strategy_data['performance_log'].append({
            'timestamp': datetime.now().isoformat(),
            'strategy_type': 'sell_only',
            'sold_count': len(sold_tickers),
            'sell_profit': total_sell_profit,
            'current_holdings': len(holdings) - len(sold_tickers),
            'enhanced_analysis_enabled': strategy_data['enhanced_analysis_enabled']
        })

        # 전략 데이터 저장
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

        with open('technical_strategy_data.json', 'w') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

        print("💾 매도 전략 데이터 저장 완료")
        print("✅ 아침 매도 전략 실행 완료!")
        executed_date = current_date  # 실행 완료 표시
        break

    # 15시 20분~22분 - 매수 전용 실행 (여유시간 2분)
    elif current_time.hour == 15 and 20 <= current_time.minute <= 22 and not executed_today:
    # elif True:  # 테스트용
        print("🚀 오후 매수 전략 실행 시작!")

        # === 현재 보유중인 종목 조회 (매수 전) ===
        holdings = ht.get_holding_stock()
        print(f"📊 현재 보유: {len(holdings)}개")

        # === 기술적 분석 강화 매수 실행 ===
        entry_tickers = enhanced_stock_selection()

        # === AI 최종 선정 추가 ===
        final_entry_tickers = ai_enhanced_final_selection(entry_tickers)

        # 현재 보유중인 종목은 매수후보에서 제외
        current_holdings = set(holdings.keys())
        final_buy_tickers = [t for t in final_entry_tickers if t not in current_holdings]

        print(f"📥 최종 매수 대상: {len(final_buy_tickers)}개")

        # === 슬랙 알림: 최종 선정 종목 ===
        if final_buy_tickers:
            selection_message = f"🎯 **AI 종목 선정 완료!**\n"
            selection_message += f"📊 분석 완료: {len(entry_tickers)}개 → AI 선정: {len(final_entry_tickers)}개\n"
            selection_message += f"📥 매수 예정: {len(final_buy_tickers)}개\n\n"
            selection_message += "**선정 종목:**\n"
            for i, ticker in enumerate(final_buy_tickers, 1):
                selection_message += f"{i}. {ticker}\n"

            try:
                ht.post_message(selection_message, HANLYANG_CHANNEL_ID)
                print("✅ 슬랙 종목 선정 알림 전송 완료")
            except Exception as e:
                print(f"❌ 슬랙 알림 전송 실패: {e}")

        # === AI 신뢰도 기반 차등 투자 매수 ===
        bought_tickers = []
        total_invested = 0

        # 현재 계좌 잔고 조회
        current_balance = 0  # 기본값 초기화
        balance_check_success = False

        try:
            current_balance = ht.get_holding_cash()
            balance_check_success = True
            print(f"💰 현재 계좌 잔고: {current_balance:,}원")
        except Exception as e:
            print(f"❌ 계좌 잔고 조회 실패: {e}")
            print("⚠️ 잔고 확인 불가로 매수 전략을 건너뜁니다.")

            # 슬랙 알림: 잔고 조회 실패
            error_message = f"❌ **계좌 잔고 조회 실패**\n"
            error_message += f"오류: {str(e)}\n"
            error_message += f"매수 전략을 건너뛰고 매도만 실행합니다."

            try:
                ht.post_message(error_message, HANLYANG_CHANNEL_ID)
            except:
                pass

        # 잔고 조회가 실패한 경우 매수를 건너뜀
        if not balance_check_success:
            print("⚠️ 계좌 잔고 조회 실패로 매수를 건너뜁니다.")
        else:
            for ticker in final_buy_tickers:
                try:
                    # AI 점수 가져오기
                    ai_score = strategy_data.get('ai_predictions', {}).get(ticker, {}).get('score', 0.5)

                    # 개선된 AI 신뢰도 기반 투자 금액 계산
                    if ai_score >= 0.75:
                        investment_amount = 800_000    # 고신뢰: 80만원
                        confidence_level = "고신뢰"
                    elif ai_score >= 0.65:
                        investment_amount = 600_000    # 중신뢰: 60만원
                        confidence_level = "중신뢰"
                    elif ai_score >= 0.55:
                        investment_amount = 400_000    # 저신뢰: 40만원
                        confidence_level = "저신뢰"
                    else:
                        investment_amount = 300_000      # 매우저신뢰: 30만원 (하이브리드 등)
                        confidence_level = "매우저신뢰"

                    # 투자 가능 금액 계산 (200만원 안전자금 제외)
                    available_balance = current_balance - total_invested - 2_000_000

                    # 투자 가능 금액이 0 이하면 바로 건너뛰기
                    if available_balance <= 0:
                        print(f"⚠️ {ticker}: 투자 가능 금액 부족 (남은 금액: {available_balance:,}원)")
                        continue
                    
                    # 투자 가능 금액이 계획된 금액보다 작으면 조정
                    if available_balance < investment_amount:
                        # 최소 투자금액(30만원) 확인
                        if available_balance < 300_000:
                            print(f"⚠️ {ticker}: 최소 투자금액 부족 (가능: {available_balance:,}원, 최소: 100,000원)")
                            continue
                        investment_amount = available_balance

                    # 현재가 조회
                    try:
                        current_data = ht.get_past_data(ticker, n=1)
                        current_price = current_data['close']
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

                        try:
                            ht.post_message(buy_message, HANLYANG_CHANNEL_ID)
                            print(f"✅ {ticker} 매수 완료 및 슬랙 알림 전송")
                        except Exception as e:
                            print(f"❌ {ticker} 슬랙 알림 실패: {e}")
                    else:
                        print(f"❌ {ticker} 매수 주문 실패")

                except Exception as e:
                    print(f"❌ {ticker} 매수 처리 오류: {e}")

        print(f"\n💼 AI 신뢰도 기반 매수 완료:")
        print(f"   매수 종목 수: {len(bought_tickers)}개")
        print(f"   총 투자금액: {total_invested:,}원")
        if balance_check_success:
            print(f"   남은 현금: {current_balance - total_invested:,}원")

        # === 슬랙 알림: 오후 매수 완료 요약 ===
        evening_summary_message = f"🚀 **오후 매수 완료!**\n"
        evening_summary_message += f"📥 매수: {len(bought_tickers)}개"
        if total_invested > 0:
            evening_summary_message += f" (투자: {total_invested:,}원)"
        evening_summary_message += f"\n📊 현재 보유: {len(holdings) + len(bought_tickers)}개\n"

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

        evening_summary_message += f"\n⏰ 실행 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        evening_summary_message += f"\n🔔 내일 오전 8시 30분에 매도 검토 예정"

        try:
            ht.post_message(evening_summary_message, HANLYANG_CHANNEL_ID)
            print("✅ 슬랙 오후 매수 완료 요약 알림 전송")
        except Exception as e:
            print(f"❌ 슬랙 요약 알림 실패: {e}")

        # 성과 로깅 (매수 전용)
        strategy_data['performance_log'].append({
            'timestamp': datetime.now().isoformat(),
            'strategy_type': 'buy_only',
            'technical_candidates': len(entry_tickers),
            'ai_selected': len(final_entry_tickers),
            'bought_count': len(bought_tickers),
            'total_invested': total_invested,
            'current_holdings': len(holdings) + len(bought_tickers),
            'enhanced_analysis_enabled': strategy_data['enhanced_analysis_enabled'],
            'ai_confidence_strategy': True
        })

        # 전략 데이터 저장
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

        with open('technical_strategy_data.json', 'w') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

        print("💾 매수 전략 데이터 저장 완료")
        print("✅ 오후 매수 전략 실행 완료!")
        executed_date = current_date  # 실행 완료 표시
        break

    # 루프 돌때마다 1초씩 쉬어줌
    time.sleep(1)
