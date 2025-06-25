"""
Stock selection strategies
Enhanced with technical analysis features
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from ..data.fetcher import get_data_fetcher
from ..analysis.technical import get_technical_score, validate_ticker_data
from ..utils.storage import get_data_manager
import pandas as pd
import numpy as np
try:
    from pykrx import stock
except ImportError:
    print("⚠️ pykrx 패키지가 설치되지 않았습니다. 일부 기능이 제한될 수 있습니다.")
    stock = None


class StockSelector:
    """종목 선정 클래스 - 기술적 분석 기반"""
    
    def __init__(self, preset: str = None):
        self.data_fetcher = get_data_fetcher()
        # 프리셋이 지정되지 않으면 환경변수 확인
        if preset is None:
            preset = os.environ.get('STRATEGY_PRESET')
        
        # 프리셋에 따른 data_manager 생성
        self.data_manager = get_data_manager(preset=preset)
        self.backtest_mode = False  # 백테스트 모드 플래그
        self.current_backtest_date = None  # 백테스트 현재 날짜
        
        # 거래정지/관리종목 리스트 캐시
        self._suspended_stocks_cache = set()
        self._cache_date = None
    
    def set_backtest_mode(self, enabled: bool, current_date: str = None):
        """
        백테스트 모드 설정
        
        Args:
            enabled: 백테스트 모드 활성화 여부
            current_date: 백테스트 현재 날짜
        """
        self.backtest_mode = enabled
        self.current_backtest_date = current_date
        if enabled:
            print(f"🔄 백테스트 모드 활성화: {current_date}")
        else:
            print("🔄 실시간 모드 활성화")
    
    def apply_market_cap_filter(self, tickers: List[str], current_date: str = None, 
                               min_market_cap: int = 200_000_000_000) -> List[str]:
        """
        시가총액 필터 적용
        
        Args:
            tickers: 종목 코드 리스트
            current_date: 기준 날짜
            min_market_cap: 최소 시가총액 (기본: 2천억원)
            
        Returns:
            필터링된 종목 리스트
        """
        if not stock:
            print("⚠️ pykrx가 설치되지 않아 시가총액 필터를 건너뜁니다.")
            return tickers
        
        try:
            # 날짜 설정
            if current_date:
                date_str = current_date.replace('-', '')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
            
            # 시가총액 데이터를 한 번만 가져오기 (효율성)
            print(f"🔍 시가총액 필터 적용 중... (최소: {min_market_cap/1_000_000_000:.0f}억원)")
            market_cap_df = stock.get_market_cap_by_ticker(date_str)
            
            if market_cap_df is None or market_cap_df.empty:
                print("⚠️ 시가총액 데이터를 가져올 수 없습니다.")
                return tickers
            
            filtered_tickers = []
            
            for ticker in tickers:
                try:
                    # DataFrame에서 시가총액 조회
                    if ticker in market_cap_df.index:
                        market_cap = market_cap_df.loc[ticker, '시가총액']
                        
                        if market_cap >= min_market_cap:
                            filtered_tickers.append(ticker)
                        else:
                            # print(f"   ❌ {ticker}: 시가총액 {market_cap/1_000_000_000:.0f}억원 - 제외")
                            pass
                    else:
                        print(f"   ⚠️ {ticker}: 시가총액 데이터 없음 - 제외")
                        
                except Exception as e:
                    # 조회 실패 시 보수적으로 제외
                    print(f"   ⚠️ {ticker}: 시가총액 조회 실패 ({e}) - 제외")
                    continue
            
            print(f"   ✅ 시가총액 필터 통과: {len(filtered_tickers)}/{len(tickers)}개")
            return filtered_tickers
            
        except Exception as e:
            print(f"⚠️ 시가총액 필터 오류: {e}")
            return tickers  # 오류 시 원본 반환
    
    def exclude_suspended_stocks(self, tickers: List[str], current_date: str = None) -> List[str]:
        """
        거래정지/관리종목 제외
        
        Args:
            tickers: 종목 코드 리스트
            current_date: 기준 날짜
            
        Returns:
            필터링된 종목 리스트
        """
        try:
            # 캐시 날짜 확인 (하루 단위로 갱신)
            today = current_date or datetime.now().strftime('%Y-%m-%d')
            
            if self._cache_date != today:
                self._update_suspended_stocks_cache(today)
            
            # 필터링
            filtered_tickers = []
            excluded_count = 0
            excluded_list = []
            
            print("🚫 거래정지/관리종목 필터 적용 중...")
            
            for ticker in tickers:
                if ticker in self._suspended_stocks_cache:
                    excluded_list.append(ticker)
                    excluded_count += 1
                else:
                    filtered_tickers.append(ticker)
            
            if excluded_count > 0:
                print(f"   ✅ 거래정지/관리종목 {excluded_count}개 제외")
                # 제외된 종목 일부 표시 (디버깅용)
                if excluded_list[:3]:  # 처음 3개만
                    for ticker in excluded_list[:3]:
                        try:
                            name = stock.get_market_ticker_name(ticker) if stock else ticker
                            print(f"      - {ticker} ({name})")
                        except:
                            print(f"      - {ticker}")
                    if len(excluded_list) > 3:
                        print(f"      ... 외 {len(excluded_list) - 3}개")
            else:
                print(f"   ✅ 거래정지/관리종목 없음")
            
            return filtered_tickers
            
        except Exception as e:
            print(f"⚠️ 거래정지/관리종목 필터 오류: {e}")
            return tickers  # 오류 시 원본 반환
    
    def _update_suspended_stocks_cache(self, date: str):
        """거래정지/관리종목 캐시 업데이트"""
        self._suspended_stocks_cache.clear()
        
        if not stock:
            print("⚠️ pykrx가 설치되지 않아 거래정지 종목 필터를 건너뜁니다.")
            return
        
        try:
            date_str = date.replace('-', '')
            
            # 백테스트 모드에서는 간소화된 필터링만 적용
            if self.backtest_mode:
                print("   🔍 백테스트 모드: 간소화된 거래정지 종목 탐색...")
                try:
                    market_data = stock.get_market_ohlcv_by_ticker(date_str)
                    if not market_data.empty:
                        # 거래량이 0인 종목만 필터링
                        zero_volume = market_data[
                            (market_data['거래량'] == 0) & 
                            (market_data['종가'] > 0)
                        ]
                        zero_volume_tickers = zero_volume.index.tolist()
                        if zero_volume_tickers:
                            self._suspended_stocks_cache.update(zero_volume_tickers)
                            print(f"      - 거래량 0인 종목: {len(zero_volume_tickers)}개")
                except Exception as e:
                    print(f"      ⚠️ 거래량 확인 실패: {e}")
            else:
                # 실시간 모드에서는 전체 필터링 적용
                # 1. 거래량이 0인 종목 (거래정지 가능성 높음)
                print("   🔍 거래량 기반 거래정지 종목 탐색 중...")
                try:
                    market_data = stock.get_market_ohlcv_by_ticker(date_str)
                    if not market_data.empty:
                        # 거래량이 0이고 종가가 있는 종목 (상장폐지가 아닌 거래정지)
                        zero_volume = market_data[
                            (market_data['거래량'] == 0) & 
                            (market_data['종가'] > 0)
                        ]
                        zero_volume_tickers = zero_volume.index.tolist()
                        if zero_volume_tickers:
                            self._suspended_stocks_cache.update(zero_volume_tickers)
                            print(f"      - 거래량 0인 종목: {len(zero_volume_tickers)}개")
                except Exception as e:
                    print(f"      ⚠️ 거래량 확인 실패: {e}")
                
                # 2. 연속 하한가 종목 (관리종목 가능성)
                try:
                    # 5일간 등락률 확인
                    consecutive_limit_down = set()
                    for i in range(5):
                        check_date = (datetime.strptime(date_str, '%Y%m%d') - timedelta(days=i)).strftime('%Y%m%d')
                        try:
                            price_data = stock.get_market_ohlcv_by_ticker(check_date)
                            if not price_data.empty:
                                # 등락률이 -29% 이하인 종목 (거의 하한가)
                                limit_down = price_data[price_data['등락률'] <= -29.0]
                                if i == 0:
                                    consecutive_limit_down = set(limit_down.index)
                                else:
                                    consecutive_limit_down &= set(limit_down.index)
                        except:
                            break
                    
                    if consecutive_limit_down:
                        self._suspended_stocks_cache.update(consecutive_limit_down)
                        print(f"      - 연속 하한가 종목: {len(consecutive_limit_down)}개")
                        
                except Exception as e:
                    print(f"      ⚠️ 하한가 종목 확인 실패: {e}")
                
                # 3. 시가총액이 극도로 낮은 종목 (100억 미만)
                try:
                    market_cap_data = stock.get_market_cap_by_ticker(date_str)
                    if isinstance(market_cap_data, pd.DataFrame) and not market_cap_data.empty:
                        # 시가총액 100억 미만인 종목
                        tiny_cap = market_cap_data[market_cap_data['시가총액'] < 10_000_000_000]
                        tiny_cap_tickers = tiny_cap.index.tolist()
                        if tiny_cap_tickers:
                            # 이 종목들은 관리종목일 가능성이 높음
                            self._suspended_stocks_cache.update(tiny_cap_tickers)
                            print(f"      - 초소형주(시총 100억 미만): {len(tiny_cap_tickers)}개")
                except Exception as e:
                    print(f"      ⚠️ 시가총액 확인 실패: {e}")
                
                # 4. 알려진 특수 종목 패턴 필터링
                # 900000번대: 우선주, CB, BW 등 특수증권
                # 이런 종목들은 일반 주식과 다른 특성을 가지므로 제외
                try:
                    all_tickers = stock.get_market_ticker_list(date_str)
                    special_tickers = [t for t in all_tickers if t.startswith('9')]
                    if special_tickers:
                        self._suspended_stocks_cache.update(special_tickers)
                        print(f"      - 특수 종목(9XXXXX): {len(special_tickers)}개")
                except:
                    pass
            
            print(f"   📊 총 제외 대상: {len(self._suspended_stocks_cache)}개 종목")
            
        except Exception as e:
            print(f"   ⚠️ 거래정지/관리종목 캐시 업데이트 실패: {e}")
            # 실패 시 최소한의 안전장치로 알려진 거래정지 종목만 추가
            # 이 리스트는 주기적으로 수동 업데이트 필요
            self._suspended_stocks_cache.update({
                '155660',  # DSR제강 (실제 거래정지 종목 예시)
                '900090',  # CMG제약 (실제 관리종목 예시)
                # 새로운 거래정지/관리종목 발생 시 여기에 추가
            })
        
        self._cache_date = date
    
    def apply_enhanced_liquidity_filter(self, market_data, min_trade_amount: int = None) -> Any:
        """
        강화된 유동성 필터 (거래대금 상향)
        
        Args:
            market_data: 시장 데이터
            min_trade_amount: 최소 거래대금 (None이면 설정값 사용)
            
        Returns:
            필터링된 데이터
        """
        # 설정에서 최소 거래대금 로드
        strategy_data = self.data_manager.get_data()
        
        if min_trade_amount is None:
            # 기본값: 1억원으로 수정 (기존 3억에서 하향)
            min_trade_amount = strategy_data.get('enhanced_min_trade_amount', 100_000_000)
        
        print(f"💰 강화된 유동성 필터 적용 (최소 거래대금: {min_trade_amount/100_000_000:.0f}억원)")
        
        # 거래대금 필터 적용
        before_count = len(market_data['ticker'].unique())
        filtered_data = market_data[market_data['trade_amount'] >= min_trade_amount].copy()
        after_count = len(filtered_data['ticker'].unique())
        
        print(f"   ✅ 유동성 필터 통과: {after_count}/{before_count}개")
        
        return filtered_data
    
    def apply_basic_quality_filters(self, tickers: List[str], current_date: str = None) -> List[str]:
        """
        1단계 기본 품질 필터 통합 적용
        
        Args:
            tickers: 종목 코드 리스트
            current_date: 기준 날짜
            
        Returns:
            필터링된 종목 리스트
        """
        print("\n🔍 [1단계] 기본 품질 필터 적용 시작...")
        print(f"   초기 종목 수: {len(tickers)}개")
        
        # 1. 거래정지/관리종목 제외
        tickers = self.exclude_suspended_stocks(tickers, current_date)
        
        # 2. 시가총액 필터
        if self.backtest_mode and hasattr(self.data_manager, '_temp_config'):
            # 백테스트 설정 사용
            min_market_cap = self.data_manager._temp_config.get('min_market_cap', 200_000_000_000)
        else:
            # 기존 방식
            strategy_data = self.data_manager.get_data()
            min_market_cap = strategy_data.get('min_market_cap', 200_000_000_000)  # 기본 2천억
        
        tickers = self.apply_market_cap_filter(tickers, current_date, min_market_cap)
        
        print(f"\n✅ [1단계] 기본 품질 필터 완료: {len(tickers)}개 종목 통과")
        print("-" * 60)
        
        return tickers
    
    def validate_bullish_candle(self, row) -> bool:
        """
        품질 높은 양봉 확인
        
        Args:
            row: 당일 종목 데이터
            
        Returns:
            bool: 품질 높은 양봉 여부
        """
        try:
            # 1. 양봉 크기: 최소 0.5% 이상 상승 (기존 1.0%에서 추가 완화)
            candle_size = (row['close'] - row['open']) / row['open']
            if candle_size < 0.005:  # 0.5%로 완화
                return False
            
            # 2. 긴 아래꼬리 확인 (망치형 캔들)
            if row['high'] > row['low']:  # 0으로 나누기 방지
                lower_wick = (row['open'] - row['low']) / row['open']
                upper_wick = (row['high'] - row['close']) / row['close']
                
                if lower_wick > upper_wick * 2:  # 아래꼬리가 위꼬리의 2배 이상
                    return True
            
            # 3. 실체가 전체 캔들의 60% 이상
            if row['high'] != row['low']:  # 0으로 나누기 방지
                body_ratio = abs(row['close'] - row['open']) / (row['high'] - row['low'])
                return body_ratio >= 0.6
            
            return True  # 기본적으로 통과
            
        except Exception as e:
            print(f"⚠️ 양봉 검증 오류: {e}")
            return False
    
    def check_volume_surge(self, market_data: pd.DataFrame, ticker: str) -> bool:
        """
        거래량 급증 여부 확인
        
        Args:
            market_data: 전체 시장 데이터
            ticker: 종목 코드
            
        Returns:
            bool: 거래량 급증 여부
        """
        try:
            ticker_data = market_data[market_data['ticker'] == ticker].sort_values('timestamp')
            
            if len(ticker_data) < 6:  # 5일 평균을 계산하기 위한 최소 데이터
                return True  # 데이터 부족시 통과
            
            # 5일 평균 거래량
            avg_volume_5d = ticker_data['volume'].tail(6).iloc[:-1].mean()
            current_volume = ticker_data['volume'].iloc[-1]
            
            # 평균이 0이면 체크 불가
            if avg_volume_5d == 0:
                return True
            
            # 조건:
            # 1. 당일 거래량이 5일 평균의 1.2배 이상 (기존 1.5배에서 완화)
            # 2. 거래대금도 함께 증가 (허수 거래 방지)
            volume_ratio = current_volume / avg_volume_5d
            
            avg_trade_amount_5d = ticker_data['trade_amount'].tail(6).iloc[:-1].mean()
            current_trade_amount = ticker_data['trade_amount'].iloc[-1]
            
            if avg_trade_amount_5d > 0:
                trade_amount_ratio = current_trade_amount / avg_trade_amount_5d
                return volume_ratio >= 1.2 and trade_amount_ratio >= 1.1  # 1.2배, 1.1배로 완화
            else:
                return volume_ratio >= 1.2  # 1.2배로 완화
                
        except Exception as e:
            print(f"⚠️ 거래량 급증 확인 오류: {e}")
            return True  # 오류시 통과
    
    def check_rsi_reversal(self, market_data: pd.DataFrame, ticker: str) -> bool:
        """
        RSI 반등 신호 확인
        
        Args:
            market_data: 전체 시장 데이터
            ticker: 종목 코드
            
        Returns:
            bool: RSI 반등 신호 여부
        """
        try:
            # RSI 계산을 위해 기술적 지표 추가
            from ..data.preprocessor import create_technical_features
            
            ticker_data = market_data[market_data['ticker'] == ticker].sort_values('timestamp').copy()
            
            if len(ticker_data) < 14:  # RSI 계산에 필요한 최소 데이터
                return True  # 데이터 부족시 통과
            
            # RSI 계산
            ticker_data = create_technical_features(ticker_data)

            # 최근 3일간 RSI 추세
            if 'rsi_14' not in ticker_data.columns:
                # print(f"⚠️ RSI 지표가 계산되지 않음: {ticker}")
                return True  # RSI 계산 불가시 통과
            
            recent_rsi = ticker_data['rsi_14'].tail(3).values
            
            if len(recent_rsi) < 3 or pd.isna(recent_rsi).any():
                return True  # RSI 계산 불가시 통과
            
            # 조건:
            # 1. RSI가 30 근처에서 반등 (과매도 → 상승)
            # 2. RSI가 상승 추세
            
            # RSI 30~50 구간에서 상승 중 (기존 30~40에서 확대)
            if 30 <= recent_rsi[-1] <= 50:
                return recent_rsi[-1] > recent_rsi[-2]  # 단순 상승 추세만 확인
            
            # RSI가 30 미만에서 반등
            if recent_rsi[-2] < 30 and recent_rsi[-1] > recent_rsi[-2]:
                return True
            
            # RSI가 너무 높으면 제외 (과매수)
            if recent_rsi[-1] > 70:
                return False
            
            return True  # 기본적으로 통과
            
        except Exception as e:
            print(f"⚠️ RSI 반등 확인 오류: {e}")
            return True  # 오류시 통과
    
    def check_near_support(self, row, market_data: pd.DataFrame, ticker: str) -> bool:
        """
        지지선 근처 여부 확인
        
        Args:
            row: 당일 종목 데이터
            market_data: 전체 시장 데이터
            ticker: 종목 코드
            
        Returns:
            bool: 지지선 근처 여부
        """
        try:
            ticker_data = market_data[market_data['ticker'] == ticker].sort_values('timestamp')
            
            if len(ticker_data) < 20:
                return True  # 데이터 부족시 통과
            
            # 최근 20일 저점들 추출
            recent_lows = ticker_data['low'].tail(20).values
            current_price = row['close']
            
            # 지지선 후보: 2번 이상 터치한 가격대 (1% 오차 허용)
            support_levels = []
            for i in range(len(recent_lows)):
                count = sum(1 for low in recent_lows if abs(low - recent_lows[i])/recent_lows[i] < 0.01)
                if count >= 2:
                    support_levels.append(recent_lows[i])
            
            if not support_levels:
                return True  # 지지선이 없으면 통과
            
            # 중복 제거
            support_levels = list(set(support_levels))
            
            # 현재가가 가장 가까운 지지선의 5% 이내 (기존 3%에서 완화)
            nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
            distance_ratio = abs(current_price - nearest_support) / nearest_support
            
            return distance_ratio <= 0.05  # 5%로 완화
            
        except Exception as e:
            print(f"⚠️ 지지선 확인 오류: {e}")
            return True  # 오류시 통과
    
    def enhanced_stock_selection(self, current_date=None) -> List[Dict[str, Any]]:
        """
        기술적 분석 강화 종목 선정 - 백테스트 모드 지원
        
        Args:
            current_date: 현재 날짜 (백테스트 시 사용)
            
        Returns:
            List[Dict]: 선정된 종목 정보 리스트
        """
        try:
            # 백테스트 모드에서 임시 파라미터 확인
            if self.backtest_mode and hasattr(self.data_manager, '_temp_backtest_params'):
                # 백테스트 엔진에서 주입한 파라미터 사용
                backtest_params = self.data_manager._temp_backtest_params
                temp_config = getattr(self.data_manager, '_temp_config', {})
                
                # 백테스트 설정에서 파라미터 가져오기
                min_close_days = backtest_params.get('min_close_days', 7)
                ma_period = backtest_params.get('ma_period', 20)
                min_trade_amount = backtest_params.get('min_trade_amount', 100_000_000)
                min_technical_score = backtest_params.get('min_technical_score', 0.6)
                
                # temp_config에서 추가 설정 가져오기
                min_market_cap = temp_config.get('min_market_cap', 200_000_000_000)
                trend_strength_filter_enabled = temp_config.get('trend_strength_filter_enabled', True)
            else:
                # 기존 방식: strategy_data에서 파라미터 로드
                strategy_data = self.data_manager.get_data()
                backtest_params = strategy_data.get('backtest_params', {})
                technical_params = strategy_data.get('technical_params', {})
                
                # 파라미터 설정 (technical_params 우선, 그 다음 백테스트 파라미터, 없으면 기본값)
                min_close_days = technical_params.get('min_close_days', backtest_params.get('min_close_days', 7))
                ma_period = technical_params.get('ma_period', backtest_params.get('ma_period', 20))
                min_trade_amount = strategy_data.get('enhanced_min_trade_amount', backtest_params.get('min_trade_amount', 100_000_000))
                min_technical_score = technical_params.get('min_technical_score', backtest_params.get('min_technical_score', 0.65))
                
                # 추가 설정
                min_market_cap = strategy_data.get('min_market_cap', 200_000_000_000)
                trend_strength_filter_enabled = strategy_data.get('trend_strength_filter_enabled', True)
            
            # 백테스트 모드일 때 날짜 설정
            if self.backtest_mode and current_date:
                self.current_backtest_date = current_date
                effective_date = current_date
            elif self.backtest_mode and self.current_backtest_date:
                effective_date = self.current_backtest_date
            else:
                effective_date = current_date
            
            print(f"📊 {'백테스트' if self.backtest_mode else '실시간'} 종목 분석 시작... ({effective_date or '현재'})")
            
            # 사용 중인 파라미터 출력
            if backtest_params:
                print(f"   🔧 백테스트 파라미터 적용:")
                print(f"      - 최저점 기간: {min_close_days}일")
                print(f"      - 이평선 기간: {ma_period}일")
                print(f"      - 최소 거래대금: {min_trade_amount/100_000_000:.0f}억")
                print(f"      - 최소 기술점수: {min_technical_score}")
            
            # 현재 날짜의 시장 데이터 조회 (백테스트 모드 고려)
            if effective_date:
                if self.backtest_mode:
                    # 백테스트 모드: 특정 날짜 기준으로 과거 데이터만 사용
                    market_data = self.data_fetcher.get_market_data_by_date_range(effective_date, n_days_before=25)
                else:
                    # 실시간 모드: 지정된 날짜 기준
                    market_data = self.data_fetcher.get_market_data_by_date_range(effective_date, n_days_before=25)
            else:
                # 날짜 지정 없음: 최신 데이터 사용
                market_data = self.data_fetcher.get_past_data_total(n=25)
            
            if market_data.empty:
                print(f"⚠️ 시장 데이터 없음")
                return []
            
            # 🎯 1단계: 강화된 유동성 필터 적용
            market_data = self.apply_enhanced_liquidity_filter(market_data, min_trade_amount)
            
            if market_data.empty:
                print(f"⚠️ 유동성 필터 통과 종목 없음")
                return []
            
            # 파라미터화된 이동평균 계산
            market_data = market_data.sort_values(['ticker', 'timestamp'])
            market_data[f'{min_close_days}d_min_close'] = market_data.groupby('ticker')['close'].rolling(min_close_days, min_periods=1).min().reset_index(0, drop=True)
            market_data[f'{ma_period}d_ma'] = market_data.groupby('ticker')['close'].rolling(ma_period, min_periods=1).mean().reset_index(0, drop=True)
            
            # 현재 날짜 데이터만 추출
            if effective_date:
                today_data = market_data[market_data['timestamp'] == effective_date].copy()
            else:
                today_data = market_data[market_data['timestamp'] == market_data['timestamp'].max()].copy()
                
            if today_data.empty:
                print(f"⚠️ 당일 데이터 없음")
                return []
            
            # 파라미터화된 조건에 맞는 종목 찾기 + 양봉 조건 추가
            traditional_candidates = today_data[
                (today_data[f'{min_close_days}d_min_close'] == today_data['close']) &
                (today_data[f'{ma_period}d_ma'] > today_data['close']) &
                (today_data['close'] > today_data['open'])  # 양봉 조건 추가 (반전 신호)
            ].copy()
            
            # 추가 필터 적용 (v3 버전)
            if 'min_candle_size' in backtest_params or 'max_rsi' in backtest_params:
                print("   🔧 추가 필터 적용 (양봉 크기/RSI)")
                
                # 양봉 크기 필터
                min_candle_size = backtest_params.get('min_candle_size', 0)
                if min_candle_size > 0:
                    # 양봉 크기 계산 (종가 - 시가) / 시가
                    traditional_candidates['candle_size'] = (
                        (traditional_candidates['close'] - traditional_candidates['open']) / 
                        traditional_candidates['open']
                    )
                    before_count = len(traditional_candidates)
                    traditional_candidates = traditional_candidates[
                        traditional_candidates['candle_size'] >= min_candle_size
                    ].copy()
                    print(f"      - 양봉 크기 {min_candle_size*100:.0f}% 이상: {before_count} → {len(traditional_candidates)}개")
                
                # RSI 필터
                max_rsi = backtest_params.get('max_rsi', 100)
                if max_rsi < 100:
                    # RSI 계산이 필요한 경우
                    # 기술적 지표가 이미 계산되어 있다고 가정
                    # create_technical_features를 통해 RSI 추가
                    from ..data.preprocessor import create_technical_features
                    
                    # 각 종목별로 RSI 계산
                    filtered_candidates = []
                    for ticker in traditional_candidates['ticker'].unique():
                        ticker_data = market_data[market_data['ticker'] == ticker].copy()
                        if len(ticker_data) >= 14:  # RSI 계산에 필요한 최소 데이터
                            ticker_data = create_technical_features(ticker_data)
                            latest_rsi = ticker_data.iloc[-1].get('rsi_14', 50)
                            
                            if latest_rsi <= max_rsi:
                                candidate_row = traditional_candidates[
                                    traditional_candidates['ticker'] == ticker
                                ]
                                if not candidate_row.empty:
                                    filtered_candidates.append(candidate_row.iloc[0])
                                    print(f"      - {ticker}: RSI {latest_rsi:.1f} ✓")
                    
                    if filtered_candidates:
                        traditional_candidates = pd.DataFrame(filtered_candidates)
                        print(f"      - RSI {max_rsi} 이하: {len(traditional_candidates)}개 통과")
                    else:
                        traditional_candidates = pd.DataFrame()  # 빈 DataFrame
            
            print(f"📊 기술적 조건 후보 (양봉 필터 포함): {len(traditional_candidates)}개")
            
            if traditional_candidates.empty:
                return []
            
            # 🔍 추세 강도 필터 적용 (설정에서 활성화된 경우)
            # 백테스트 모드에서는 위에서 설정한 trend_strength_filter_enabled 사용
            # 실시간 모드에서는 strategy_data에서 다시 가져오기
            if not self.backtest_mode or not hasattr(self.data_manager, '_temp_config'):
                strategy_data = self.data_manager.get_data()
                trend_strength_filter_enabled = strategy_data.get('trend_strength_filter_enabled', True)
            
            if trend_strength_filter_enabled:
                print("\n🔍 [추세 강도 필터] 적용 시작...")
                print("   📋 필터 조건 (4개 중 3개 이상 충족시 통과):")
                print("      - 양봉 크기 0.5% 이상")
                print("      - 거래량 5일 평균 대비 1.2배 이상")
                print("      - RSI 반등 신호 (30-50 구간에서 상승)")
                print("      - 지지선 근처 (5% 이내)")
                
                strong_candidates = []
                
                for _, row in traditional_candidates.iterrows():
                    ticker = row['ticker']
                    
                    # 각 조건 체크 및 점수 계산
                    score = 0
                    passed_conditions = []
                    
                    # 1. 양봉 품질 검증
                    if self.validate_bullish_candle(row):
                        score += 1
                        passed_conditions.append("양봉")
                    
                    # 2. 거래량 급증 확인
                    if self.check_volume_surge(market_data, ticker):
                        score += 1
                        passed_conditions.append("거래량")
                    
                    # 3. RSI 반등 신호
                    if self.check_rsi_reversal(market_data, ticker):
                        score += 1
                        passed_conditions.append("RSI")
                    
                    # 4. 지지선 근처 확인
                    if self.check_near_support(row, market_data, ticker):
                        score += 1
                        passed_conditions.append("지지선")
                    
                    # 4개 중 3개 이상 통과시 선정
                    if score >= 3:
                        print(f"   ✅ {ticker}: 추세 강도 필터 통과 ({score}/4) - {', '.join(passed_conditions)}")
                        strong_candidates.append(row)
                    elif score == 2:
                        pass
                        # print(f"   ⚠️ {ticker}: \부분 통과 ({score}/4) - {', '.join(passed_conditions)}")
                    # else:
                    #     print(f"   ❌ {ticker}: 필터 미달 ({score}/4)")
                
                if strong_candidates:
                    traditional_candidates = pd.DataFrame(strong_candidates)
                    print(f"\n📊 추세 강도 필터 통과: {len(traditional_candidates)}개 종목")
                else:
                    print(f"\n❌ 추세 강도 필터 통과 종목 없음")
                    return []
            else:
                print("\n⚠️ 추세 강도 필터 비활성화됨 (설정에서 활성화 가능)")
            
            # 🎯 2단계: 기본 품질 필터 적용 (시가총액, 거래정지 등)
            candidate_tickers = traditional_candidates['ticker'].unique().tolist()
            filtered_tickers = self.apply_basic_quality_filters(candidate_tickers, effective_date)
            
            # 필터 통과한 종목만 유지
            traditional_candidates = traditional_candidates[
                traditional_candidates['ticker'].isin(filtered_tickers)
            ].copy()
            
            if traditional_candidates.empty:
                print("⚠️ 품질 필터 통과 종목 없음")
                return []
            
            # 기술적 분석 점수 추가 분석 (백테스트 모드 고려)
            enhanced_candidates = []
            
            for _, row in traditional_candidates.iterrows():
                ticker = row['ticker']
                
                # 🔧 데이터 검증 강화 (백테스트 엔진 기능 적용)
                if self.backtest_mode:
                    # 백테스트 모드에서는 data_validator 직접 사용
                    from ..backtest.data_validator import get_data_validator
                    validator = get_data_validator()
                    if not validator.validate_ticker_data(ticker, effective_date):
                        print(f"   ❌ {ticker}: 데이터 검증 실패 - 스킵")
                        continue
                else:
                    # 실시간 모드에서는 기존 검증 방식 사용
                    if not validate_ticker_data(ticker):
                        print(f"   ❌ {ticker}: 데이터 검증 실패 - 스킵")
                        continue
                
                # 기술적 분석 점수 계산
                technical_score = get_technical_score(ticker)
                
                # 결합 점수: 기존 거래량 가중치 + 기술적 분석 보정
                # 거래량 순위를 위한 값 (정렬용)
                technical_multiplier = 0.5 + technical_score  # 0.5 ~ 1.5 배수
                combined_score_raw = row['trade_amount'] * technical_multiplier
                
                # 정규화된 점수 (0~1 사이, 표시용)
                # 기술적 점수를 주로 사용하되, 거래량이 매우 높으면 약간의 보너스
                volume_bonus = min(0.1, row['trade_amount'] / 10_000_000_000)  # 100억 거래대금당 0.01, 최대 0.1
                normalized_score = min(1.0, technical_score + volume_bonus)
                
                enhanced_candidates.append({
                    'ticker': ticker,
                    'trade_amount': row['trade_amount'],
                    'technical_score': technical_score,
                    'combined_score': combined_score_raw,  # 정렬용 (거래량 가중치 포함)
                    'normalized_score': normalized_score,  # 표시용 (0~1 사이)
                    'current_price': row['close']
                })
            
            # 기술적 분석 강화 점수로 정렬
            enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
            
            # 기술적 점수가 기준 이상인 종목만 선정
            selected_candidates = []
            print(f"\n🔍 기술적 점수 필터링 (최소 점수: {min_technical_score})")
            for candidate in enhanced_candidates[:10]:  # 상위 10개 확인
                print(f"   - {candidate['ticker']}: 기술점수 {candidate['technical_score']:.3f}")
                if candidate['technical_score'] >= min_technical_score and len(selected_candidates) < 5:  # 파라미터화된 기준
                    selected_candidates.append(candidate)
                    print(f"     ✅ 선정됨")
                else:
                    if len(selected_candidates) >= 5:
                        print(f"     ❌ 최대 선정 수 초과")
                    else:
                        print(f"     ❌ 점수 미달")
            
            print(f"🎯 기술적 분석 최종 선정: {len(selected_candidates)}개 종목")
            
            return selected_candidates
            
        except Exception as e:
            print(f"❌ 종목 선정 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

    def technical_final_selection(self, entry_tickers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        기술적 분석 기반 최종 종목 선정
        
        Args:
            entry_tickers: 기술적 분석으로 선정된 종목들
            
        Returns:
            List[Dict]: 최종 선정된 종목 정보
        """
        print("📊 기술적 분석 최종 종목 선정 시작...")

        # 기술적 점수로 정렬 (이미 정렬되어 있지만 확실히 함)
        entry_tickers.sort(key=lambda x: x['combined_score'], reverse=True)
        
        # 백테스트 모드에서 임시 파라미터 확인
        if self.backtest_mode and hasattr(self.data_manager, '_temp_backtest_params'):
            # 백테스트 파라미터 사용
            backtest_params = self.data_manager._temp_backtest_params
            temp_config = getattr(self.data_manager, '_temp_config', {})
            
            max_selections = backtest_params.get('max_positions', 5)
            min_technical_score = backtest_params.get('min_technical_score', 0.6)
        else:
            # 기존 방식: 설정 로드
            strategy_data = self.data_manager.get_data()
            backtest_params = strategy_data.get('backtest_params', {})
            technical_params = strategy_data.get('technical_params', {})
            
            # 파라미터 설정 (technical_params 우선, 그 다음 백테스트 파라미터, 없으면 기본값)
            max_selections = backtest_params.get('max_positions', strategy_data.get('max_selections', 3))
            min_technical_score = technical_params.get('min_technical_score', backtest_params.get('min_technical_score', strategy_data.get('min_technical_score', 0.7)))
        
        # 기준을 만족하는 종목만 선정
        final_selection = []
        for item in entry_tickers:
            if len(final_selection) >= max_selections:
                break
                
            # 기술적 점수가 기준 이상인 경우만 선정
            if item['technical_score'] >= min_technical_score:
                final_selection.append(item)
                print(f"✅ {item['ticker']}: 기술 점수 {item['technical_score']:.3f} (거래대금: {item['trade_amount']:,.0f})")

        # 선정 결과 출력
        if len(final_selection) == 0:
            print("❌ 기술적 분석 기준을 만족하는 종목이 없습니다.")
            print("⚠️ 오늘은 매수를 건너뛰겠습니다.")
            
            # 가장 높은 점수라도 출력
            if entry_tickers:
                best_score = entry_tickers[0]['technical_score']
                print(f"📊 최고 점수: {best_score:.3f} (기준: {min_technical_score:.2f})")
        else:
            print(f"🏆 기술적 분석 최종 선정: {len(final_selection)}개 종목")

        # 실시간 계산으로 전환 - 저장하지 않음
        print("   🔄 기술적 점수는 실시간으로 계산됩니다")
        
        # 데이터 저장 (technical_analysis 제외)
        self.data_manager.save()
        
        return final_selection

    def select_stocks_for_buy(self, current_date=None) -> List[str]:
        """
        매수용 종목 선정 (전체 워크플로우) - 기술적 분석 기반
        
        Args:
            current_date: 현재 날짜 (백테스트 시)
            
        Returns:
            List[str]: 최종 선정된 종목 코드 리스트
        """
        try:
            # 1단계: 기술적 분석 기반 1차 선정 (데이터 검증 포함)
            entry_candidates = self.enhanced_stock_selection(current_date)
            
            if not entry_candidates:
                print("📊 기술적 분석에서 선정된 종목이 없습니다.")
                return []
            
            # 2단계: 기술적 분석 기반 최종 선정
            final_selections = self.technical_final_selection(entry_candidates)
            final_tickers = [item['ticker'] for item in final_selections]
            
            print(f"📊 최종 선정 결과: {len(final_tickers)}개")
            
            return final_tickers
            
        except Exception as e:
            print(f"❌ 종목 선정 전체 워크플로우 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_selection_summary(self) -> Dict[str, Any]:
        """
        선정 과정 요약 정보 반환
        
        Returns:
            dict: 선정 과정 요약
        """
        # 실시간 계산이므로 기본값만 반환
        summary = {
            'technical_analysis_count': 0,
            'selected_count': 0,
            'avg_technical_score': 0,
            'max_technical_score': 0,
            'min_technical_score': 1.0,
            'ai_predictions_count': 0  # 호환성을 위해 추가
        }
        
        print("   🔄 기술적 분석 요약은 실시간 계산 기반으로 제공됩니다")
        
        return summary


# 전역 스톡 셀렉터 (프리셋별 싱글톤 패턴)
_selector_instances = {}

def get_stock_selector(preset: str = None) -> StockSelector:
    """스톡 셀렉터 인스턴스 반환 (프리셋별 싱글톤)"""
    global _selector_instances
    
    # 프리셋이 없으면 기본 인스턴스
    key = preset or 'default'
    
    if key not in _selector_instances:
        _selector_instances[key] = StockSelector(preset=preset)
    
    return _selector_instances[key]

# 편의 함수들
def enhanced_stock_selection(current_date=None, preset: str = None) -> List[Dict[str, Any]]:
    """기술적 분석 기반 종목 선정"""
    selector = get_stock_selector(preset=preset)
    return selector.enhanced_stock_selection(current_date)

def select_stocks_for_buy(current_date=None, preset: str = None) -> List[str]:
    """매수용 종목 선정 (전체 워크플로우)"""
    selector = get_stock_selector(preset=preset)
    return selector.select_stocks_for_buy(current_date)
