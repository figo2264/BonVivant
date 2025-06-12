"""
Data preprocessing and technical indicator generation
Enhanced with features from backtest_engine and train_ai_model
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, Any


class TechnicalIndicatorGenerator:
    """기술적 지표 생성 클래스 - 백테스트 엔진 기능 완전 적용"""
    
    @staticmethod
    def create_technical_features(data: pd.DataFrame) -> pd.DataFrame:
        """
        강화된 기술적 분석 지표 생성 (backtest_engine.py와 완전 동일)
        
        Args:
            data: 주가 데이터 (OHLCV)
            
        Returns:
            DataFrame: 기술적 지표가 추가된 데이터
        """
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
            
            # 기본 수익률 계산
            for period in [1, 3, 5, 10, 20]:
                data[f'return_{period}d'] = data['close'].pct_change(period)

            # 이동평균 및 비율 (더 다양한 기간)
            for ma_period in [5, 10, 20, 60]:
                data[f'ma_{ma_period}'] = data['close'].rolling(ma_period).mean()
                data[f'price_ma_ratio_{ma_period}'] = data['close'] / data[f'ma_{ma_period}']

            # 기본 기술적 지표
            data['rsi_14'] = ta.momentum.rsi(data['close'], window=14)
            data['rsi_30'] = ta.momentum.rsi(data['close'], window=30)
            data['volume_ratio_5d'] = data['volume'] / data['volume'].rolling(5).mean()
            data['volume_ratio_20d'] = data['volume'] / data['volume'].rolling(20).mean()
            data['volatility_10d'] = data['close'].pct_change().rolling(10).std()
            data['volatility_20d'] = data['close'].pct_change().rolling(20).std()

            # 볼린저 밴드 관련 지표
            bb_middle = data['close'].rolling(20).mean()
            bb_std = data['close'].rolling(20).std()
            data['bb_upper'] = bb_middle + (2 * bb_std)
            data['bb_lower'] = bb_middle - (2 * bb_std)
            data['bb_position'] = (data['close'] - bb_middle) / (2 * bb_std)
            data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / bb_middle

            # MACD 지표
            try:
                macd_line = ta.trend.macd(data['close'])
                macd_signal = ta.trend.macd_signal(data['close'])
                data['macd'] = macd_line
                data['macd_signal'] = macd_signal
                data['macd_histogram'] = macd_line - macd_signal
            except:
                data['macd'] = 0
                data['macd_signal'] = 0
                data['macd_histogram'] = 0

            # 스토캐스틱 지표
            try:
                data['stoch_k'] = ta.momentum.stoch(data['high'], data['low'], data['close'])
                data['stoch_d'] = data['stoch_k'].rolling(3).mean()
            except:
                data['stoch_k'] = 50
                data['stoch_d'] = 50

            # 가격 모멘텀 지표
            data['price_momentum_5'] = data['close'] / data['close'].shift(5) - 1
            data['price_momentum_10'] = data['close'] / data['close'].shift(10) - 1
            data['price_momentum_20'] = data['close'] / data['close'].shift(20) - 1

            # 거래량 가중 평균 가격 (VWAP)
            try:
                data['vwap'] = (data['close'] * data['volume']).rolling(20).sum() / data['volume'].rolling(20).sum()
                data['price_vwap_ratio'] = data['close'] / data['vwap']
            except:
                data['vwap'] = data['close']
                data['price_vwap_ratio'] = 1.0

            # 변동성 기반 지표
            data['high_low_ratio'] = (data['high'] - data['low']) / data['close']
            data['close_open_ratio'] = data['close'] / data['open'] - 1

            # 지지/저항 레벨 근접도
            data['recent_high_20'] = data['high'].rolling(20).max()
            data['recent_low_20'] = data['low'].rolling(20).min()
            data['high_proximity'] = (data['recent_high_20'] - data['close']) / data['recent_high_20']
            data['low_proximity'] = (data['close'] - data['recent_low_20']) / data['recent_low_20']

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


# 편의 함수
def create_technical_features(data: pd.DataFrame) -> pd.DataFrame:
    """기술적 지표 생성 (편의 함수)"""
    generator = TechnicalIndicatorGenerator()
    return generator.create_technical_features(data)
