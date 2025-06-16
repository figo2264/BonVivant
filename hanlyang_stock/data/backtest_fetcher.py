"""
Backtest-specific data fetching utilities
백테스트 전용 데이터 조회 기능
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from .fetcher import DataFetcher, PYKRX_AVAILABLE, FDR_AVAILABLE

if PYKRX_AVAILABLE:
    from pykrx import stock as pystock

if FDR_AVAILABLE:
    import FinanceDataReader as fdr


class BacktestDataFetcher(DataFetcher):
    """백테스트 전용 데이터 페처 - 날짜 범위 지정 가능"""
    
    def get_past_data_for_date(self, ticker: str, target_date: str, n: int = 100) -> pd.DataFrame:
        """
        특정 날짜 기준으로 과거 데이터 조회 (백테스트 전용)
        
        Args:
            ticker: 종목 코드
            target_date: 기준 날짜 (YYYY-MM-DD)
            n: 조회할 일수
            
        Returns:
            DataFrame: target_date 이전 n일간의 데이터
        """
        try:
            target_date_obj = pd.to_datetime(target_date)
            
            # 1차 시도: pykrx 사용 (날짜 범위 지정 가능)
            if PYKRX_AVAILABLE:
                try:
                    # 날짜 범위 계산 (주말 고려하여 여유있게)
                    end_date = target_date_obj
                    start_date = end_date - timedelta(days=n * 2)  # 주말 고려하여 2배
                    
                    # pykrx 형식으로 변환
                    start_str = start_date.strftime('%Y%m%d')
                    end_str = end_date.strftime('%Y%m%d')
                    
                    # KOSPI 시도
                    try:
                        data = pystock.get_market_ohlcv(start_str, end_str, ticker, market='KOSPI')
                        if not data.empty:
                            data = self._standardize_pykrx_columns(data)
                            data.index.name = 'timestamp'
                            data = data.reset_index()
                            data['timestamp'] = pd.to_datetime(data['timestamp'])
                            
                            # target_date 이전 데이터만 필터링
                            data = data[data['timestamp'] <= target_date_obj]
                            
                            # 최근 n개만 반환
                            return data.tail(n).copy()
                    except:
                        pass
                    
                    # KOSDAQ 시도
                    try:
                        data = pystock.get_market_ohlcv(start_str, end_str, ticker, market='KOSDAQ')
                        if not data.empty:
                            data = self._standardize_pykrx_columns(data)
                            data.index.name = 'timestamp'
                            data = data.reset_index()
                            data['timestamp'] = pd.to_datetime(data['timestamp'])
                            
                            # target_date 이전 데이터만 필터링
                            data = data[data['timestamp'] <= target_date_obj]
                            
                            # 최근 n개만 반환
                            return data.tail(n).copy()
                    except:
                        pass
                        
                except Exception as e:
                    print(f"⚠️ {ticker}: pykrx 백테스트 조회 실패 ({e})")
            
            # 2차 시도: FinanceDataReader (전체 데이터 조회 후 필터링)
            if FDR_AVAILABLE:
                try:
                    # 충분한 과거 데이터 조회
                    data = fdr.DataReader(ticker)
                    if not data.empty:
                        data.columns = [col.lower() for col in data.columns]
                        data.index.name = 'timestamp'
                        data = data.reset_index()
                        data['timestamp'] = pd.to_datetime(data['timestamp'])
                        
                        # target_date 이전 데이터만 필터링
                        data = data[data['timestamp'] <= target_date_obj]
                        
                        # 최근 n개만 반환
                        return data.tail(n).copy()
                except Exception as e:
                    print(f"⚠️ {ticker}: FinanceDataReader 백테스트 조회 실패 ({e})")
            
            # 3차 시도: 부모 클래스 메서드 사용 (전체 데이터 조회 후 필터링)
            print(f"⚠️ {ticker}: 백테스트 전용 조회 실패, 일반 조회 시도")
            data = super().get_past_data_enhanced(ticker, n=n*5)  # 여유있게 조회
            
            if not data.empty:
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                # target_date 이전 데이터만 필터링
                filtered_data = data[data['timestamp'] <= target_date_obj]
                
                if not filtered_data.empty:
                    return filtered_data.tail(n).copy()
                else:
                    print(f"❌ {ticker}: target_date({target_date}) 이전 데이터 없음")
                    return pd.DataFrame()
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ {ticker} 백테스트 데이터 조회 오류: {e}")
            return pd.DataFrame()
    
    def get_valid_price_for_date(self, ticker: str, target_date: str) -> Optional[float]:
        """
        특정 날짜의 종가 조회 (백테스트 전용)
        
        Args:
            ticker: 종목 코드
            target_date: 조회할 날짜
            
        Returns:
            float: 해당 날짜의 종가 (없으면 가장 가까운 과거 날짜의 종가)
        """
        try:
            # 5일치 데이터 조회
            data = self.get_past_data_for_date(ticker, target_date, n=5)
            
            if data.empty:
                return None
            
            # 정확히 해당 날짜의 데이터가 있는지 확인
            target_date_obj = pd.to_datetime(target_date)
            exact_match = data[data['timestamp'] == target_date_obj]
            
            if not exact_match.empty:
                # 정확한 날짜의 종가 반환
                price = exact_match.iloc[0]['close']
            else:
                # 가장 최근 날짜의 종가 반환
                price = data.iloc[-1]['close']
            
            # 가격 유효성 검증
            if price > 0 and price < 1_000_000:
                return float(price)
            else:
                return None
                
        except Exception as e:
            print(f"❌ {ticker} 날짜별 가격 조회 오류: {e}")
            return None


# 전역 백테스트 데이터 페처 (싱글톤)
_backtest_fetcher_instance = None

def get_backtest_data_fetcher() -> BacktestDataFetcher:
    """백테스트 데이터 페처 인스턴스 반환 (싱글톤)"""
    global _backtest_fetcher_instance
    if _backtest_fetcher_instance is None:
        _backtest_fetcher_instance = BacktestDataFetcher()
    return _backtest_fetcher_instance
