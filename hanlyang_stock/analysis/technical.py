"""
Technical analysis utilities
Enhanced with complete features from backtest_engine
"""

import pandas as pd
import numpy as np
from typing import Optional, Any
from ..data.fetcher import get_data_fetcher
from ..data.preprocessor import create_technical_features
from ..utils.data_validator import validate_ticker_data as validate_data


class TechnicalAnalyzer:
    """기술적 분석 클래스 - 백테스트 엔진의 모든 기능 적용"""
    
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        
        # 기본 가중치 설정 (설정에서 오버라이드 가능)
        self.default_weights = {
            'trend': 0.25,           # 추세 (25%)
            'momentum': 0.20,        # 모멘텀 (20%)
            'oversold': 0.20,        # 과매도 (20%)
            'parabolic_sar': 0.20,   # 파라볼릭 SAR (20%)
            'volume': 0.10,          # 거래량 (10%)
            'volatility': 0.05       # 변동성 (5%)
        }
    
    def get_technical_score(self, ticker: str, holding_days: int = 0, 
                          entry_price: Optional[float] = None, config: Any = None) -> float:
        """
        개선된 기술적 분석 점수 계산 - 다각도 평가 및 동적 조정 (파라볼릭 SAR 포함)
        
        Args:
            ticker: 종목 코드
            holding_days: 현재 보유 일수 (0이면 미보유)
            entry_price: 매수 가격 (보유 중인 경우)
            config: 백테스트/전략 설정 (가중치 포함)
            
        Returns:
            float: 기술적 분석 점수 (0.0 ~ 1.0)
        """
        try:
            # 데이터 조회
            data = self.data_fetcher.get_past_data_enhanced(ticker, n=50)
            if data.empty or len(data) < 30:
                return 0.5
            
            # 기술적 지표 생성
            data = create_technical_features(data)
            
            # 파라볼릭 SAR 계산 추가
            data = self._calculate_parabolic_sar(data)
            latest = data.iloc[-1]
            
            # NaN 체크
            if pd.isna(latest.get('rsi_14', np.nan)):
                return 0.5
            
            # 가중치 설정 (설정이 있으면 사용, 없으면 기본값)
            weights = self.default_weights.copy()
            
            if config:
                # BacktestConfig 또는 StrategyConfig에서 가중치 추출
                if hasattr(config, 'technical_score_weights'):
                    weights.update(config.technical_score_weights)
                elif hasattr(config, 'to_dict'):
                    config_dict = config.to_dict()
                    if 'technical_score_weights' in config_dict:
                        weights.update(config_dict['technical_score_weights'])
            
            # 각 구성요소 점수 계산
            components = {
                'trend': self._calculate_trend_score(data, latest),
                'momentum': self._calculate_momentum_score(data, latest),
                'oversold': self._calculate_oversold_score(data, latest),
                'parabolic_sar': self._calculate_parabolic_sar_score(data, latest),
                'volume': self._calculate_volume_score(latest),
                'volatility': self._calculate_volatility_score(latest)
            }
            
            # 가중 평균 계산
            base_score = sum(components[key] * weights[key] for key in components)
            
            # 보유 중인 종목에 대한 조정
            if holding_days > 0:
                adjustment = self._apply_holding_adjustment(
                    base_score, holding_days, latest['close'], entry_price
                )
                final_score = base_score * adjustment
            else:
                final_score = base_score
            
            # 디버그 출력 (중요한 경우만)
            if holding_days > 0 or final_score > 0.85 or final_score < 0.3:
                print(f"   📊 {ticker} 기술적 점수 상세:")
                print(f"      추세: {components['trend']:.2f}, "
                      f"모멘텀: {components['momentum']:.2f}, "
                      f"과매도: {components['oversold']:.2f}, "
                      f"SAR: {components['parabolic_sar']:.2f}")
                if holding_days > 0:
                    print(f"      보유일수: {holding_days}일, 조정계수: {adjustment:.2f}")
                print(f"      최종점수: {final_score:.3f}")
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            print(f"기술적 점수 계산 오류 ({ticker}): {e}")
            return 0.5
    
    def _calculate_trend_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """추세 점수 계산 (0-1)"""
        # 이평선 가격 대비 위치
        ma5_ratio = latest.get('price_ma_ratio_5', 1.0)
        ma20_ratio = latest.get('price_ma_ratio_20', 1.0)
        
        # 이평선 배열 점수
        if ma5_ratio > 1.02 and ma20_ratio > 1.01:
            arrangement_score = 0.9
        elif ma5_ratio > 1.0 and ma20_ratio > 1.0:
            arrangement_score = 0.7
        elif ma5_ratio > 1.0:
            arrangement_score = 0.5
        elif ma5_ratio < 0.95 and ma20_ratio < 0.95:
            arrangement_score = 0.2
        else:
            arrangement_score = 0.4
        
        # 추세 강도 (최근 20일 수익률)
        return_20d = latest.get('return_20d', 0)
        if return_20d > 0.1:
            strength_score = 0.9
        elif return_20d > 0.05:
            strength_score = 0.7
        elif return_20d > 0:
            strength_score = 0.5
        elif return_20d > -0.05:
            strength_score = 0.3
        else:
            strength_score = 0.1
        
        return arrangement_score * 0.7 + strength_score * 0.3
    
    def _calculate_momentum_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """모멘텀 점수 계산 (0-1)"""
        # 단기 수익률 모멘텀
        return_1d = latest.get('return_1d', 0)
        return_3d = latest.get('return_3d', 0)
        
        if return_1d > 0.03 and return_3d > 0.05:
            momentum_score = 0.9
        elif return_1d > 0.01 and return_3d > 0:
            momentum_score = 0.7
        elif return_1d > 0 and return_3d < -0.03:
            momentum_score = 0.8  # 반등 시작
        elif return_1d < -0.02:
            momentum_score = 0.3
        else:
            momentum_score = 0.5
        
        # RSI 모멘텀
        rsi = latest.get('rsi_14', 50)
        rsi_change = 0
        
        if len(data) >= 2:
            prev_rsi = data.iloc[-2].get('rsi_14', 50)
            rsi_change = rsi - prev_rsi
        
        if rsi < 30 and rsi_change > 0:
            rsi_score = 0.9
        elif rsi > 70 and rsi_change < 0:
            rsi_score = 0.2
        else:
            rsi_score = 0.5 + min(0.3, max(-0.3, rsi_change / 100))
        
        return momentum_score * 0.6 + rsi_score * 0.4
    
    def _calculate_oversold_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """과매도 점수 계산 - 지속 기간 고려"""
        rsi = latest.get('rsi_14', 50)
        
        # 과매도 지속 일수 계산
        oversold_days = 0
        for i in range(min(10, len(data))):
            if data.iloc[-(i+1)].get('rsi_14', 50) < 30:
                oversold_days += 1
            else:
                break
        
        # RSI 기반 점수
        if oversold_days > 5:
            rsi_score = 0.2  # 장기 과매도 위험
        elif rsi < 25 and oversold_days <= 2:
            rsi_score = 0.8  # 단기 급락 기회
        elif rsi < 30 and oversold_days <= 3:
            rsi_score = 0.6
        elif rsi < 40:
            rsi_score = 0.5
        elif rsi > 70:
            rsi_score = 0.3
        else:
            rsi_score = 0.5
        
        # 볼린저 밴드 위치
        bb_position = latest.get('bb_position', 0)
        
        if bb_position < -1.0 and oversold_days <= 2:
            bb_score = 0.7
        elif bb_position < -0.5:
            bb_score = 0.6
        elif bb_position > 1.0:
            bb_score = 0.3
        else:
            bb_score = 0.5
        
        return rsi_score * 0.7 + bb_score * 0.3
    
    def _calculate_volume_score(self, latest: pd.Series) -> float:
        """거래량 점수 계산"""
        volume_ratio = latest.get('volume_ratio_5d', 1.0)
        price_change = latest.get('return_1d', 0)
        
        if volume_ratio > 2.0 and price_change < -0.02:
            return 0.8  # 하락 중 대량 거래
        elif volume_ratio > 1.5 and price_change > 0.01:
            return 0.8  # 상승 중 거래량 증가
        elif volume_ratio > 1.5:
            return 0.7
        elif volume_ratio < 0.5:
            return 0.3
        else:
            return 0.5
    
    def _calculate_volatility_score(self, latest: pd.Series) -> float:
        """변동성 점수 계산"""
        volatility = latest.get('volatility_10d', 0.03)
        
        if volatility < 0.02:
            return 0.9
        elif volatility < 0.03:
            return 0.7
        elif volatility < 0.05:
            return 0.5
        elif volatility < 0.08:
            return 0.3
        else:
            return 0.1
    
    def _calculate_parabolic_sar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        파라볼릭 SAR 계산
        
        Args:
            data: OHLC 데이터
            
        Returns:
            pd.DataFrame: SAR 컬럼이 추가된 데이터
        """
        try:
            data = data.copy()
            n = len(data)
            
            if n < 2:
                data['sar'] = data['close']
                data['sar_trend'] = 1  # 1: 상승, -1: 하락
                return data
            
            # 파라볼릭 SAR 파라미터
            initial_af = 0.02
            step_af = 0.02
            max_af = 0.20
            
            # 초기값 설정
            sar = np.zeros(n)
            trend = np.zeros(n, dtype=int)
            af = np.zeros(n)
            ep = np.zeros(n)  # Extreme Point
            
            # 첫 번째 값들 초기화
            sar[0] = data['low'].iloc[0]
            trend[0] = 1  # 상승 추세로 시작
            af[0] = initial_af
            ep[0] = data['high'].iloc[0]
            
            for i in range(1, n):
                high = data['high'].iloc[i]
                low = data['low'].iloc[i]
                
                # 이전 값들
                prev_sar = sar[i-1]
                prev_trend = trend[i-1]
                prev_af = af[i-1]
                prev_ep = ep[i-1]
                
                # SAR 계산
                sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)
                
                # 추세 판정
                if prev_trend == 1:  # 상승 추세였던 경우
                    # SAR이 현재 저가보다 높으면 추세 전환
                    if sar[i] > low:
                        trend[i] = -1  # 하락 추세로 전환
                        sar[i] = prev_ep  # SAR을 이전 EP로 설정
                        af[i] = initial_af
                        ep[i] = low
                    else:
                        trend[i] = 1  # 상승 추세 유지
                        # EP 업데이트 (새로운 고점)
                        if high > prev_ep:
                            ep[i] = high
                            af[i] = min(prev_af + step_af, max_af)
                        else:
                            ep[i] = prev_ep
                            af[i] = prev_af
                        
                        # SAR이 이전 이틀의 저가보다 높으면 조정
                        if i >= 2:
                            prev_low = min(data['low'].iloc[i-1], data['low'].iloc[i-2])
                            sar[i] = min(sar[i], prev_low)
                
                else:  # 하락 추세였던 경우
                    # SAR이 현재 고가보다 낮으면 추세 전환
                    if sar[i] < high:
                        trend[i] = 1  # 상승 추세로 전환
                        sar[i] = prev_ep  # SAR을 이전 EP로 설정
                        af[i] = initial_af
                        ep[i] = high
                    else:
                        trend[i] = -1  # 하락 추세 유지
                        # EP 업데이트 (새로운 저점)
                        if low < prev_ep:
                            ep[i] = low
                            af[i] = min(prev_af + step_af, max_af)
                        else:
                            ep[i] = prev_ep
                            af[i] = prev_af
                        
                        # SAR이 이전 이틀의 고가보다 낮으면 조정
                        if i >= 2:
                            prev_high = max(data['high'].iloc[i-1], data['high'].iloc[i-2])
                            sar[i] = max(sar[i], prev_high)
            
            # 결과를 데이터프레임에 추가
            data['sar'] = sar
            data['sar_trend'] = trend
            data['sar_signal'] = 0  # 신호 초기화
            
            # 신호 계산 (추세 전환점)
            for i in range(1, n):
                if trend[i] != trend[i-1]:
                    if trend[i] == 1:
                        data.loc[data.index[i], 'sar_signal'] = 1  # 매수 신호
                    else:
                        data.loc[data.index[i], 'sar_signal'] = -1  # 매도 신호
            
            return data
            
        except Exception as e:
            print(f"⚠️ 파라볼릭 SAR 계산 오류: {e}")
            # 오류 시 기본값으로 설정
            data['sar'] = data['close']
            data['sar_trend'] = 1
            data['sar_signal'] = 0
            return data
    
    def _calculate_parabolic_sar_score(self, data: pd.DataFrame, latest: pd.Series) -> float:
        """
        파라볼릭 SAR 점수 계산
        
        Args:
            data: SAR이 계산된 데이터
            latest: 최신 데이터
            
        Returns:
            float: SAR 점수 (0.0~1.0)
        """
        try:
            if len(data) < 3:
                return 0.5
            
            current_price = latest['close']
            current_sar = latest.get('sar', current_price)
            current_trend = latest.get('sar_trend', 1)
            current_signal = latest.get('sar_signal', 0)
            
            # 기본 점수
            base_score = 0.5
            
            # 1. 현재 추세에 따른 점수 (50% 가중치)
            if current_trend == 1:  # 상승 추세
                if current_price > current_sar:
                    trend_score = 0.8  # 매수 포지션 유리
                else:
                    trend_score = 0.3  # 추세 전환 신호
            else:  # 하락 추세
                if current_price < current_sar:
                    trend_score = 0.2  # 매도 포지션
                else:
                    trend_score = 0.7  # 매수 기회 포착
            
            # 2. 신호 강도 (30% 가중치)
            signal_score = 0.5
            if current_signal == 1:  # 매수 신호
                signal_score = 0.9
                print(f"      🔵 파라볼릭 SAR 매수 신호 발생!")
            elif current_signal == -1:  # 매도 신호
                signal_score = 0.1
                print(f"      🔴 파라볼릭 SAR 매도 신호 발생!")
            
            # 3. 추세 지속성 확인 (20% 가중치)
            # 최근 3일간 추세 일관성
            recent_trends = data['sar_trend'].tail(3).values
            if len(recent_trends) >= 3:
                trend_consistency = len(set(recent_trends)) == 1  # 모두 같은 추세
                consistency_score = 0.7 if trend_consistency else 0.4
            else:
                consistency_score = 0.5
            
            # 가중 평균 계산
            final_score = (trend_score * 0.5 + 
                          signal_score * 0.3 + 
                          consistency_score * 0.2)
            
            # SAR과 가격의 거리 고려 (보정)
            if current_sar > 0:
                price_sar_ratio = abs(current_price - current_sar) / current_sar
                
                # SAR과 가격이 너무 가까우면 신호 약화
                if price_sar_ratio < 0.01:  # 1% 이내
                    final_score *= 0.8
                # SAR과 가격이 적당히 떨어져 있으면 신호 강화
                elif 0.02 <= price_sar_ratio <= 0.05:  # 2-5% 구간
                    final_score *= 1.1
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            print(f"⚠️ 파라볼릭 SAR 점수 계산 오류: {e}")
            return 0.5
    
    def _apply_holding_adjustment(self, base_score: float, holding_days: int,
                                 current_price: float, entry_price: Optional[float]) -> float:
        """보유 중인 종목에 대한 점수 조정"""
        # 기본 시간 감쇠
        time_decay = max(0.7, 1.0 - holding_days * 0.05)
        
        # 손익 상황 반영
        if entry_price and entry_price > 0:
            profit_rate = (current_price - entry_price) / entry_price
            
            if profit_rate > 0.05:
                profit_adjustment = 1.0
            elif profit_rate > 0:
                profit_adjustment = 0.9
            elif profit_rate > -0.03:
                profit_adjustment = 0.8
            else:
                profit_adjustment = 0.6
        else:
            profit_adjustment = 0.9
        
        return time_decay * profit_adjustment

    def get_technical_hold_signal(self, ticker: str, current_date=None) -> float:
        """
        기술적 분석 기반 홀드 시그널 (백테스트 엔진에서 완전 이식)
        
        Args:
            ticker: 종목 코드
            current_date: 현재 날짜 (백테스트 시)
            
        Returns:
            float: 홀드 시그널 (0.0~1.0, 0.75 이상이면 강홀드)
        """
        try:
            # 데이터 검증부터 수행
            if not validate_data(ticker):
                print(f"⚠️ {ticker}: 홀드 시그널 계산용 데이터 검증 실패")
                return 0.5
            
            # 과거 데이터 조회
            data = self.data_fetcher.get_past_data_enhanced(ticker, n=30)
            if data.empty or len(data) < 20:
                print(f"⚠️ {ticker}: 홀드 시그널용 데이터 부족")
                return 0.5
            
            # 현재 날짜 이후 데이터 제거 (백테스트 시)
            if current_date:
                current_date_pd = pd.to_datetime(current_date)
                data = data[pd.to_datetime(data['timestamp']) <= current_date_pd].copy()
                if len(data) < 20:
                    print(f"⚠️ {ticker}: 홀드 시그널용 유효 데이터 부족")
                    return 0.5
            
            # 기술적 지표 생성
            data = create_technical_features(data)
            
            # 파라볼릭 SAR 계산 추가
            data = self._calculate_parabolic_sar(data)
            latest = data.iloc[-1]
            
            # 홀드 점수 계산 시작
            hold_score = 0.5  # 기본 중립점수
            
            print(f"🔍 {ticker} 홀드 시그널 분석:")
            
            # 1. 단기 모멘텀 (30% 가중치)
            return_1d = latest.get('return_1d', 0)
            if return_1d > 0.03:  # 3% 이상 상승
                momentum_boost = 0.25
                hold_score += momentum_boost
                print(f"   📈 강한 상승 모멘텀: +{momentum_boost:.2f} (1일 수익률: {return_1d*100:+.1f}%)")
            elif return_1d > 0.01:  # 1% 이상 상승
                momentum_boost = 0.15
                hold_score += momentum_boost
                print(f"   📈 상승 모멘텀: +{momentum_boost:.2f} (1일 수익률: {return_1d*100:+.1f}%)")
            elif return_1d < -0.02:  # 2% 이상 하락
                momentum_penalty = -0.2
                hold_score += momentum_penalty
                print(f"   📉 하락 모멘텀: {momentum_penalty:.2f} (1일 수익률: {return_1d*100:+.1f}%)")
            
            # 2. RSI 과매수/과매도 체크 (25% 가중치)
            rsi_14 = latest.get('rsi_14', 50)
            if rsi_14 > 75:  # 과매수
                rsi_penalty = -0.25
                hold_score += rsi_penalty
                print(f"   ⚠️ RSI 과매수: {rsi_penalty:.2f} (RSI: {rsi_14:.1f})")
            elif rsi_14 < 30:  # 과매도 (홀드 유리)
                rsi_boost = 0.15
                hold_score += rsi_boost
                print(f"   💪 RSI 과매도 반등 기대: +{rsi_boost:.2f} (RSI: {rsi_14:.1f})")
            else:
                print(f"   📊 RSI 정상 범위: {rsi_14:.1f}")
            
            # 3. 볼린저 밴드 위치 (20% 가중치)
            bb_position = latest.get('bb_position', 0)
            if bb_position > 0.8:  # 상단 근처 (매도 압력)
                bb_penalty = -0.2
                hold_score += bb_penalty
                print(f"   📊 볼린저 밴드 상단: {bb_penalty:.2f} (위치: {bb_position:.2f})")
            elif bb_position < -0.5:  # 하단 근처 (반등 기대)
                bb_boost = 0.1
                hold_score += bb_boost
                print(f"   📊 볼린저 밴드 하단: +{bb_boost:.2f} (위치: {bb_position:.2f})")
            
            # 4. 거래량 급증 체크 (15% 가중치)
            volume_ratio = latest.get('volume_ratio_5d', 1.0)
            if volume_ratio > 2.0:  # 거래량 2배 이상 급증
                volume_boost = 0.15
                hold_score += volume_boost
                print(f"   📊 거래량 급증: +{volume_boost:.2f} (비율: {volume_ratio:.1f}배)")
            
            # 5. 파라볼릭 SAR 확인 (15% 가중치)
            sar_trend = latest.get('sar_trend', 1)
            sar_signal = latest.get('sar_signal', 0)
            current_sar = latest.get('sar', latest['close'])
            
            if sar_signal == 1:  # 매수 신호 발생
                sar_boost = 0.2
                hold_score += sar_boost
                print(f"   🔵 파라볼릭 SAR 매수 신호: +{sar_boost:.2f}")
            elif sar_signal == -1:  # 매도 신호 발생
                sar_penalty = -0.25
                hold_score += sar_penalty
                print(f"   🔴 파라볼릭 SAR 매도 신호: {sar_penalty:.2f}")
            elif sar_trend == 1 and latest['close'] > current_sar:  # 상승 추세 유지
                sar_boost = 0.1
                hold_score += sar_boost
                print(f"   📈 파라볼릭 SAR 상승 추세: +{sar_boost:.2f}")
            elif sar_trend == -1:  # 하락 추세
                sar_penalty = -0.1
                hold_score += sar_penalty
                print(f"   📉 파라볼릭 SAR 하락 추세: {sar_penalty:.2f}")
            
            # 6. 중기 추세 확인 (10% 가중치)
            price_ma_ratio_20 = latest.get('price_ma_ratio_20', 1.0)
            if price_ma_ratio_20 > 1.05:  # 20일 이평선 위 5% 이상
                trend_boost = 0.1
                hold_score += trend_boost
                print(f"   📈 중기 상승 추세: +{trend_boost:.2f} (20일선 대비: {(price_ma_ratio_20-1)*100:+.1f}%)")
            elif price_ma_ratio_20 < 0.95:  # 20일 이평선 아래 5% 이상
                trend_penalty = -0.1
                hold_score += trend_penalty
                print(f"   📉 중기 하락 추세: {trend_penalty:.2f} (20일선 대비: {(price_ma_ratio_20-1)*100:+.1f}%)")
            
            # 최종 점수 조정
            final_score = max(0.0, min(1.0, hold_score))
            
            # 시그널 강도 분류
            if final_score >= 0.75:
                signal_strength = "강홀드"
                signal_color = "🟢"
            elif final_score >= 0.6:
                signal_strength = "홀드"
                signal_color = "🟡"
            elif final_score >= 0.4:
                signal_strength = "중립"
                signal_color = "⚪"
            else:
                signal_strength = "매도신호"
                signal_color = "🔴"
            
            print(f"   {signal_color} 최종 홀드 시그널: {final_score:.3f} ({signal_strength})")
            
            return final_score
            
        except Exception as e:
            print(f"❌ {ticker} 홀드 시그널 계산 오류: {e}")
            import traceback
            print(f"   오류 상세: {traceback.format_exc()}")
            return 0.5

    def analyze_multiple_tickers(self, tickers: list) -> dict:
        """
        여러 종목에 대한 기술적 분석 일괄 수행
        
        Args:
            tickers: 종목 코드 리스트
            
        Returns:
            dict: {ticker: {'score': float, 'hold_signal': float}}
        """
        results = {}
        
        for ticker in tickers:
            try:
                # 데이터 검증부터 수행
                if not validate_data(ticker):
                    print(f"❌ {ticker} 데이터 검증 실패 - 분석 스킵")
                    results[ticker] = {
                        'score': 0.3,
                        'hold_signal': 0.3,
                        'recommendation': 'SKIP_DATA_INVALID'
                    }
                    continue
                
                score = self.get_technical_score(ticker)
                hold_signal = self.get_technical_hold_signal(ticker)
                
                results[ticker] = {
                    'score': score,
                    'hold_signal': hold_signal,
                    'recommendation': self._get_recommendation(score, hold_signal)
                }
                
            except Exception as e:
                print(f"❌ {ticker} 분석 실패: {e}")
                results[ticker] = {
                    'score': 0.5,
                    'hold_signal': 0.5,
                    'recommendation': 'NEUTRAL'
                }
        
        return results
    
    def _get_recommendation(self, score: float, hold_signal: Optional[float] = None) -> str:
        """점수를 기반으로 추천 등급 반환"""
        if score >= 0.75:
            return 'STRONG_BUY'
        elif score >= 0.65:
            return 'BUY'
        elif score >= 0.55:
            return 'WEAK_BUY'
        elif score >= 0.45:
            return 'NEUTRAL'
        elif score >= 0.35:
            return 'WEAK_SELL'
        else:
            return 'SELL'


# 전역 기술적 분석기 (싱글톤 패턴)
_technical_analyzer_instance = None

def get_technical_analyzer() -> TechnicalAnalyzer:
    """기술적 분석기 인스턴스 반환 (싱글톤)"""
    global _technical_analyzer_instance
    if _technical_analyzer_instance is None:
        _technical_analyzer_instance = TechnicalAnalyzer()
    return _technical_analyzer_instance

# 편의 함수들
def get_technical_score(ticker: str, holding_days: int = 0, 
                      entry_price: Optional[float] = None, config: Any = None) -> float:
    """기술적 분석 점수 계산"""
    analyzer = get_technical_analyzer()
    return analyzer.get_technical_score(ticker, holding_days, entry_price, config)

def get_technical_hold_signal(ticker: str, current_date=None) -> float:
    """기술적 홀드 시그널 계산"""
    analyzer = get_technical_analyzer()
    return analyzer.get_technical_hold_signal(ticker, current_date)

# validate_ticker_data는 공용 data_validator에서 직접 import
from ..utils.data_validator import validate_ticker_data

def analyze_multiple_tickers(tickers: list) -> dict:
    """여러 종목 기술적 분석"""
    analyzer = get_technical_analyzer()
    return analyzer.analyze_multiple_tickers(tickers)
