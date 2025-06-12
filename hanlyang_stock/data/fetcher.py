"""
Data fetching utilities for stock market data
Enhanced with features from backtest_engine
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..config.settings import get_hantustock

# pykrx import 시도 (백테스트 엔진과 동일)
try:
    from pykrx import stock as pystock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("⚠️ pykrx 라이브러리가 없어 일부 데이터 기능이 제한됩니다.")

# FinanceDataReader import 시도
try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False
    print("⚠️ FinanceDataReader 라이브러리가 없어 일부 데이터 기능이 제한됩니다.")


class DataFetcher:
    """주식 데이터 조회 클래스 - 백테스트 엔진의 모든 데이터 기능 포함"""
    
    def __init__(self):
        self.ht = get_hantustock()
    
    def get_past_data_enhanced(self, ticker: str, n: int = 100) -> pd.DataFrame:
        """
        개별 종목 과거 원시 데이터 조회 (백테스트 엔진 안정성 강화 버전)
        
        Args:
            ticker: 종목 코드
            n: 조회할 일수
            
        Returns:
            DataFrame: 과거 데이터 (실패시 빈 DataFrame 반환)
        """
        try:
            # 1차 시도: HantuStock 사용
            try:
                data = self.ht.get_past_data(ticker, n=n)
                
                # pandas Series인 경우 DataFrame으로 변환
                if isinstance(data, pd.Series):
                    if len(data) > 0:
                        data_df = data.to_frame().T  # 행으로 변환
                        # timestamp 컬럼이 없으면 추가
                        if 'timestamp' not in data_df.columns:
                            data_df['timestamp'] = datetime.now().strftime('%Y-%m-%d')
                        return data_df
                    else:
                        return pd.DataFrame()
                
                # DataFrame인 경우
                elif isinstance(data, pd.DataFrame):
                    if len(data) == 0:
                        return pd.DataFrame()
                    
                    # 컬럼 표준화
                    data = self._standardize_columns(data)
                    
                    # timestamp 컬럼이 없으면 추가
                    if 'timestamp' not in data.columns:
                        if data.index.name == 'date' or 'date' in str(data.index.dtype):
                            data['timestamp'] = data.index.astype(str)
                        else:
                            # 최근 n일로 추정하여 날짜 생성
                            end_date = datetime.now()
                            dates = [end_date - timedelta(days=i) for i in range(n-1, -1)]
                            dates = dates[-len(data):]  # 실제 데이터 길이에 맞춤
                            data['timestamp'] = [d.strftime('%Y-%m-%d') for d in dates]
                    
                    return data
                
                else:
                    print(f"⚠️ {ticker}: 예상하지 못한 데이터 타입 {type(data)} 반환")
                    
            except Exception as e:
                print(f"⚠️ {ticker}: HantuStock 조회 실패 ({e})")
            
            # 2차 시도: FinanceDataReader 사용 (백테스트 엔진과 동일)
            if FDR_AVAILABLE:
                try:
                    data = fdr.DataReader(ticker, start=None, end=None)
                    if not data.empty:
                        data.columns = [col.lower() for col in data.columns]
                        data.index.name = 'timestamp'
                        data = data.reset_index()
                        
                        if n == 1:
                            return data.iloc[-1:].copy()
                        else:
                            return data.tail(n).copy()
                except Exception as e:
                    print(f"⚠️ {ticker}: FinanceDataReader 조회 실패 ({e})")
            
            # 3차 시도: pykrx 사용 (백테스트 엔진과 동일)
            if PYKRX_AVAILABLE:
                try:
                    end_date = datetime.now().strftime('%Y%m%d')
                    start_date = (datetime.now() - timedelta(days=n*2)).strftime('%Y%m%d')
                    
                    # KOSPI 시도
                    try:
                        kospi_data = pystock.get_market_ohlcv(start_date, end_date, ticker, market='KOSPI')
                        if not kospi_data.empty:
                            kospi_data = self._standardize_pykrx_columns(kospi_data)
                            kospi_data.index.name = 'timestamp'
                            kospi_data = kospi_data.reset_index()
                            print(f"✅ {ticker}: pykrx KOSPI 데이터 조회 성공")
                            return kospi_data.tail(n).copy() if n > 1 else kospi_data.iloc[-1:].copy()
                    except:
                        pass
                    
                    # KOSDAQ 시도
                    try:
                        kosdaq_data = pystock.get_market_ohlcv(start_date, end_date, ticker, market='KOSDAQ')
                        if not kosdaq_data.empty:
                            kosdaq_data = self._standardize_pykrx_columns(kosdaq_data)
                            kosdaq_data.index.name = 'timestamp'
                            kosdaq_data = kosdaq_data.reset_index()
                            print(f"✅ {ticker}: pykrx KOSDAQ 데이터 조회 성공")
                            return kosdaq_data.tail(n).copy() if n > 1 else kosdaq_data.iloc[-1:].copy()
                    except:
                        pass
                        
                except Exception as e:
                    print(f"⚠️ {ticker}: pykrx 조회 실패 ({e})")
            
            print(f"❌ {ticker}: 모든 데이터 소스 조회 실패")
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ {ticker} 데이터 조회 치명적 오류: {e}")
            return pd.DataFrame()
    
    def get_past_data_total(self, n: int = 20) -> pd.DataFrame:
        """
        전체 종목 과거 데이터 조회 (백테스트 엔진 기능 강화)
        
        Args:
            n: 조회할 일수
            
        Returns:
            DataFrame: 전체 종목 과거 데이터
        """
        try:
            # 1차 시도: HantuStock 사용
            try:
                data = self.ht.get_past_data_total(n=n)
                if isinstance(data, pd.DataFrame) and not data.empty:
                    # 컬럼 표준화
                    data = self._standardize_columns(data)
                    return data
            except Exception as e:
                print(f"⚠️ HantuStock 전체 데이터 조회 실패: {e}")
            
            # 2차 시도: pykrx를 사용한 수집 (백테스트 엔진과 동일)
            if PYKRX_AVAILABLE:
                return self._get_total_market_data_pykrx(n)
            
            print("❌ 전체 시장 데이터 조회 실패")
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 전체 데이터 조회 치명적 오류: {e}")
            return pd.DataFrame()
    
    def get_market_data_by_date(self, date_str: str) -> pd.DataFrame:
        """
        특정 날짜의 시장 데이터 조회 (백테스트 엔진 기능)
        
        Args:
            date_str: 날짜 문자열 (YYYY-MM-DD)
            
        Returns:
            DataFrame: 해당 날짜의 시장 데이터
        """
        try:
            if not PYKRX_AVAILABLE:
                print("❌ pykrx가 없어 날짜별 시장 데이터 조회 불가")
                return pd.DataFrame()
            
            # 날짜 형식 변환
            date_obj = pd.to_datetime(date_str)
            pykrx_date = date_obj.strftime('%Y%m%d')
            
            try:
                # KOSPI + KOSDAQ 데이터
                kospi = pystock.get_market_ohlcv(pykrx_date, market='KOSPI')
                kosdaq = pystock.get_market_ohlcv(pykrx_date, market='KOSDAQ')
                daily_data = pd.concat([kospi, kosdaq])
                
                if daily_data.empty or daily_data['거래대금'].sum() == 0:
                    return pd.DataFrame()  # 휴장일
                
                # 컬럼명 표준화
                daily_data = self._standardize_pykrx_columns(daily_data)
                
                daily_data['timestamp'] = date_str
                daily_data.index.name = 'ticker'
                daily_data = daily_data.reset_index()
                
                return daily_data
                
            except Exception as e:
                print(f"❌ {date_str} 시장 데이터 조회 실패: {e}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 날짜별 시장 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    def get_market_data_by_date_range(self, end_date: str, n_days_before: int = 20) -> pd.DataFrame:
        """
        날짜 범위의 시장 데이터 조회 (백테스트 엔진 기능) - 성능 최적화
        
        Args:
            end_date: 종료 날짜 (YYYY-MM-DD)
            n_days_before: 이전 일수
            
        Returns:
            DataFrame: 날짜 범위의 시장 데이터
        """
        # 캐시 키 생성
        cache_key = f"market_data_{end_date}_{n_days_before}"
        
        # 간단한 메모리 캐시 (실제로는 Redis 등을 사용할 수 있음)
        if not hasattr(self, '_cache'):
            self._cache = {}
        
        if cache_key in self._cache:
            print(f"💾 캐시에서 데이터 로드: {cache_key}")
            return self._cache[cache_key]
        
        try:
            if not PYKRX_AVAILABLE:
                # pykrx가 없으면 HantuStock 시도
                result = self.get_past_data_total(n=n_days_before)
                self._cache[cache_key] = result
                return result
            
            # 날짜 범위 생성
            end_date_obj = pd.to_datetime(end_date)
            start_date_obj = end_date_obj - timedelta(days=n_days_before)
            
            all_data = []
            current_date = start_date_obj
            collected_days = 0
            
            print(f"📊 시장 데이터 수집 중: {start_date_obj.strftime('%Y-%m-%d')} ~ {end_date}")
            
            while current_date <= end_date_obj and collected_days < n_days_before:
                if current_date.weekday() < 5:  # 평일만
                    date_str = current_date.strftime('%Y-%m-%d')
                    daily_data = self.get_market_data_by_date(date_str)
                    
                    if not daily_data.empty:
                        all_data.append(daily_data)
                        collected_days += 1
                        
                current_date += timedelta(days=1)
            
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                result['timestamp'] = pd.to_datetime(result['timestamp'])
                result = result.sort_values(['timestamp', 'ticker']).reset_index(drop=True)
                
                # 캐시에 저장 (최대 100개 캐시)
                if len(self._cache) > 100:
                    # 가장 오래된 캐시 삭제
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                
                self._cache[cache_key] = result
                print(f"✅ 시장 데이터 수집 완료: {len(result)}건 ({collected_days}일)")
                return result
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ 날짜 범위 시장 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    def clear_cache(self):
        """캐시 초기화"""
        if hasattr(self, '_cache'):
            self._cache.clear()
            print("💾 데이터 캐시 초기화 완료")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보"""
        if not hasattr(self, '_cache'):
            return {'cache_size': 0, 'cache_keys': []}
        
        return {
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys()),
            'memory_usage_mb': sum(data.memory_usage(deep=True).sum() for data in self._cache.values()) / 1024 / 1024
        }
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """
        현재가 조회 (안정성 강화)
        
        Args:
            ticker: 종목 코드
            
        Returns:
            float: 현재가 (실패시 None)
        """
        def is_valid_price(price):
            """현재가가 유효한지 검증"""
            try:
                price_float = float(price)
                # 주식 가격은 양수이고 합리적인 범위(100원 ~ 1억원)여야 함
                return 100 <= price_float <= 100_000_000
            except:
                return False
        
        # 방법 1: get_past_data_enhanced 사용
        try:
            current_data = self.get_past_data_enhanced(ticker, n=1)
            
            if isinstance(current_data, pd.DataFrame) and len(current_data) > 0:
                # close 컬럼이 있는 경우
                if 'close' in current_data.columns:
                    price = float(current_data['close'].iloc[-1])
                    if is_valid_price(price):
                        return price
                
                # close 컬럼이 없으면 다른 가격 관련 컬럼 시도
                price_columns = ['Close', 'price', 'Price', 'current_price']
                for col in price_columns:
                    if col in current_data.columns:
                        price = float(current_data[col].iloc[-1])
                        if is_valid_price(price):
                            return price
        except Exception as e:
            pass
        
        # 방법 2: HantuStock 직접 호출 (Series 처리 포함)
        try:
            raw_data = self.ht.get_past_data(ticker, n=1)
            
            # pandas Series 처리
            if isinstance(raw_data, pd.Series):
                # Series에서 가격 관련 인덱스 찾기
                price_indices = ['close', 'Close', 'price', 'Price', 'current_price']
                for idx in price_indices:
                    if idx in raw_data.index:
                        price = float(raw_data[idx])
                        if is_valid_price(price):
                            return price
                
                # 인덱스 이름으로 찾을 수 없으면 값들을 확인
                for value in raw_data.values:
                    if is_valid_price(value):
                        return float(value)
            
            # DataFrame 처리
            elif isinstance(raw_data, pd.DataFrame):
                if len(raw_data) > 0:
                    price_columns = ['close', 'Close', 'price', 'Price', 'current_price']
                    for col in price_columns:
                        if col in raw_data.columns:
                            price = float(raw_data[col].iloc[-1])
                            if is_valid_price(price):
                                return price
            
            # 단일 숫자값 처리
            elif isinstance(raw_data, (int, float)):
                if is_valid_price(raw_data):
                    return float(raw_data)
            
            # 리스트/배열 처리
            elif hasattr(raw_data, '__iter__') and not isinstance(raw_data, str):
                for value in raw_data:
                    if is_valid_price(value):
                        return float(value)
            
        except Exception as e:
            pass
        
        # 방법 3: HantuStock에 다른 메서드가 있는지 확인
        try:
            if hasattr(self.ht, 'get_current_price'):
                price = self.ht.get_current_price(ticker)
                if price and is_valid_price(price):
                    return float(price)
            
            # 다른 가능한 메서드들 시도
            possible_methods = ['get_price', 'current_price', 'get_quote']
            for method_name in possible_methods:
                if hasattr(self.ht, method_name):
                    try:
                        method = getattr(self.ht, method_name)
                        price = method(ticker)
                        if price and is_valid_price(price):
                            return float(price)
                    except:
                        continue
                        
        except Exception as e:
            pass
        
        print(f"❌ {ticker}: 현재가 조회 실패")
        return None
    
    def get_holding_stock(self) -> dict:
        """
        현재 보유 종목 조회
        
        Returns:
            dict: 보유 종목 정보 {ticker: quantity}
        """
        try:
            holdings = self.ht.get_holding_stock()
            return holdings
        except Exception as e:
            print(f"❌ 보유 종목 조회 실패: {e}")
            return {}
    
    def get_holding_cash(self) -> float:
        """
        현재 계좌 잔고 조회
        
        Returns:
            float: 계좌 잔고
        """
        try:
            cash = self.ht.get_holding_cash()
            return float(cash)
        except Exception as e:
            print(f"❌ 계좌 잔고 조회 실패: {e}")
            raise e
    
    # ============ 내부 헬퍼 메서드들 ============
    
    def _standardize_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """컬럼명 표준화"""
        try:
            # 기본적인 컬럼명 소문자 변환
            data.columns = [col.lower() for col in data.columns]
            
            # 한글 컬럼명 변환
            column_mapping = {
                '시가': 'open',
                '고가': 'high', 
                '저가': 'low',
                '종가': 'close',
                '거래량': 'volume',
                '거래대금': 'trade_amount'
            }
            
            data = data.rename(columns=column_mapping)
            return data
        except:
            return data
    
    def _standardize_pykrx_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """pykrx 데이터 컬럼명 표준화"""
        try:
            data = data.rename(columns={
                '시가': 'open', 
                '고가': 'high', 
                '저가': 'low', 
                '종가': 'close',
                '거래량': 'volume', 
                '거래대금': 'trade_amount'
            })
            return data
        except:
            return data
    
    def _get_total_market_data_pykrx(self, n: int) -> pd.DataFrame:
        """pykrx를 사용한 전체 시장 데이터 수집 (백테스트 엔진과 동일)"""
        try:
            all_data = []
            end_date = datetime.now()
            current_date = end_date - timedelta(days=n)
            
            collected_days = 0
            max_collect_days = min(n, 30)  # 최대 30일
            
            while current_date <= end_date and collected_days < max_collect_days:
                if current_date.weekday() < 5:  # 평일만
                    try:
                        date_str = current_date.strftime('%Y%m%d')
                        
                        # 데이터 수집 시도
                        try:
                            kospi = pystock.get_market_ohlcv(date_str, market='KOSPI')
                        except:
                            kospi = pd.DataFrame()
                        
                        try:
                            kosdaq = pystock.get_market_ohlcv(date_str, market='KOSDAQ')
                        except:
                            kosdaq = pd.DataFrame()
                        
                        if kospi.empty and kosdaq.empty:
                            current_date += timedelta(days=1)
                            continue
                            
                        daily_data = pd.concat([kospi, kosdaq])
                        
                        if not daily_data.empty and daily_data['거래대금'].sum() > 0:
                            # 컬럼명 변환
                            daily_data = self._standardize_pykrx_columns(daily_data)
                            
                            daily_data['timestamp'] = current_date.strftime('%Y-%m-%d')
                            daily_data.index.name = 'ticker'
                            daily_data = daily_data.reset_index()
                            all_data.append(daily_data)
                            collected_days += 1
                            
                    except Exception as e:
                        pass  # 데이터 없는 날짜는 스킵
                        
                current_date += timedelta(days=1)
            
            if not all_data:
                print("❌ pykrx 전체 데이터 수집 실패")
                return pd.DataFrame()
            
            result = pd.concat(all_data, ignore_index=True)
            result['timestamp'] = pd.to_datetime(result['timestamp'])
            
            print(f"✅ pykrx 데이터 수집 완료: {len(result)}개 레코드, {result['ticker'].nunique()}개 종목")
            return result.sort_values(['timestamp', 'ticker']).reset_index(drop=True)
            
        except Exception as e:
            print(f"❌ pykrx 전체 데이터 수집 오류: {e}")
            return pd.DataFrame()


# 전역 데이터 페처 (싱글톤 패턴)
_fetcher_instance = None

def get_data_fetcher() -> DataFetcher:
    """데이터 페처 인스턴스 반환 (싱글톤)"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = DataFetcher()
    return _fetcher_instance

# 편의 함수들
def get_past_data_enhanced(ticker: str, n: int = 100) -> pd.DataFrame:
    """개별 종목 과거 데이터 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_past_data_enhanced(ticker, n)

def get_past_data_total(n: int = 20) -> pd.DataFrame:
    """전체 종목 과거 데이터 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_past_data_total(n)

def get_market_data_by_date(date_str: str) -> pd.DataFrame:
    """특정 날짜의 시장 데이터 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_market_data_by_date(date_str)

def get_market_data_by_date_range(end_date: str, n_days_before: int = 20) -> pd.DataFrame:
    """날짜 범위의 시장 데이터 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_market_data_by_date_range(end_date, n_days_before)

def get_current_price(ticker: str) -> Optional[float]:
    """현재가 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_current_price(ticker)

def get_holding_stock() -> dict:
    """보유 종목 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_holding_stock()

def get_holding_cash() -> float:
    """계좌 잔고 조회"""
    fetcher = get_data_fetcher()
    return fetcher.get_holding_cash()
