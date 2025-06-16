"""
Data validation utilities for backtesting
백테스트용 데이터 검증 클래스
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..data.fetcher import get_data_fetcher
from ..data.backtest_fetcher import get_backtest_data_fetcher


class DataValidator:
    """백테스트용 데이터 검증 클래스"""
    
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        self.backtest_fetcher = get_backtest_data_fetcher()  # 백테스트 전용 페처
    
    def validate_ticker_data(self, ticker: str, current_date: str = None, min_days: int = 5) -> bool:
        """
        종목 데이터 존재 여부 사전 확인 (백테스트 엔진에서 완전 이식)
        
        Args:
            ticker: 종목 코드
            current_date: 현재 날짜 (백테스트용)
            min_days: 최소 필요 데이터 일수
            
        Returns:
            bool: 데이터 유효성 여부
        """
        try:
            # 1. 기본 데이터 조회 (백테스트 모드 구분)
            if current_date:
                # 백테스트 모드: 특정 날짜 기준 데이터 조회
                data = self.backtest_fetcher.get_past_data_for_date(ticker, current_date, n=min_days * 3)
            else:
                # 실시간 모드: 현재 기준 데이터 조회
                data = self.data_fetcher.get_past_data_enhanced(ticker, n=min_days * 3)
                
            if data.empty:
                print(f"⚠️ {ticker}: 기본 데이터 조회 실패")
                return False
            
            # 2. 백테스트 모드에서는 이미 필터링된 데이터이므로 추가 필터링 불필요
            valid_data = data
            
            # 3. 최소 데이터 개수 확인
            if len(valid_data) < min_days:
                print(f"⚠️ {ticker}: 데이터 부족 ({len(valid_data)}개 < {min_days}개)")
                return False
            
            # 4. 최근 데이터 확인 (완화된 기준: 7일 이내)
            if current_date:
                latest_date = pd.to_datetime(valid_data['timestamp'].max())
                current_date_pd = pd.to_datetime(current_date)
                days_diff = (current_date_pd - latest_date).days
                if days_diff > 7:  # 3일에서 7일로 완화
                    print(f"⚠️ {ticker}: 데이터가 너무 오래됨 ({days_diff}일 전)")
                    return False
            
            # 5. 가격 데이터 유효성 확인
            latest_row = valid_data.iloc[-1]
            current_price = latest_row.get('close', 0)
            
            if current_price <= 0:
                print(f"⚠️ {ticker}: 유효하지 않은 가격 ({current_price})")
                return False
            
            # 6. 거래량 확인 (0이면 거래 정지 종목일 가능성)
            volume = latest_row.get('volume', 0)
            if volume <= 0:
                print(f"⚠️ {ticker}: 거래량 없음 (거래정지 가능성)")
                return False
            
            # 7. 가격 범위 확인 (리스크 관리)
            if current_price < 1000:  # 1천원 미만 저가주
                print(f"⚠️ {ticker}: 저가주 제외 ({current_price:,}원)")
                return False
            
            if current_price > 500_000:  # 50만원 초과 고가주
                print(f"⚠️ {ticker}: 고가주 제외 ({current_price:,}원)")
                return False
            
            # print(f"✅ {ticker}: 데이터 검증 통과 (가격: {current_price:,}원, 거래량: {volume:,})")
            return True
            
        except Exception as e:
            print(f"❌ {ticker} 데이터 검증 오류: {e}")
            return False
    
    def check_stop_loss(self, ticker: str, buy_price: float, current_date: str, 
                       stop_loss_rate: float = -0.05) -> tuple[bool, float, float]:
        """
        손실 제한 체크 (백테스트 엔진에서 완전 이식)
        
        Args:
            ticker: 종목 코드
            buy_price: 매수 가격
            current_date: 현재 날짜
            stop_loss_rate: 손실 제한 비율 (기본 -5%)
            
        Returns:
            tuple: (should_sell, current_price, loss_rate)
        """
        try:
            if buy_price <= 0:
                return False, 0, 0
            
            # 백테스트 모드에서는 특정 날짜의 가격 조회
            current_price = self.backtest_fetcher.get_valid_price_for_date(ticker, current_date)
            
            if not current_price:
                return False, 0, 0
            
            loss_rate = (current_price - buy_price) / buy_price
            should_sell = loss_rate <= stop_loss_rate
            
            return should_sell, current_price, loss_rate
            
        except Exception as e:
            print(f"⚠️ {ticker} 손실 제한 체크 실패: {e}")
            return False, 0, 0
    
    def validate_market_data(self, market_data: pd.DataFrame, date: str) -> bool:
        """
        시장 데이터 유효성 검증
        
        Args:
            market_data: 시장 데이터
            date: 검증할 날짜
            
        Returns:
            bool: 데이터 유효 여부
        """
        if market_data.empty:
            print(f"❌ {date}: 시장 데이터 없음")
            return False
        
        # 필수 컬럼 확인
        required_columns = ['ticker', 'close', 'volume', 'trade_amount', 'timestamp']
        missing_columns = [col for col in required_columns if col not in market_data.columns]
        
        if missing_columns:
            print(f"❌ {date}: 필수 컬럼 누락 - {missing_columns}")
            return False
        
        # 거래대금 확인
        total_trade_amount = market_data['trade_amount'].sum()
        if total_trade_amount == 0:
            print(f"❌ {date}: 거래대금 0 (휴장일 가능성)")
            return False
        
        # 종목 수 확인
        unique_tickers = market_data['ticker'].nunique()
        if unique_tickers < 100:  # 최소 100개 종목
            print(f"⚠️ {date}: 종목 수 부족 ({unique_tickers}개)")
            return False
        
        print(f"✅ {date}: 시장 데이터 검증 통과 ({unique_tickers}개 종목, 거래대금: {total_trade_amount:,.0f})")
        return True
    
    def get_valid_price(self, ticker: str, current_date: str) -> Optional[float]:
        """
        유효한 현재가 조회
        
        Args:
            ticker: 종목 코드
            current_date: 현재 날짜
            
        Returns:
            float: 유효한 가격 또는 None
        """
        try:
            # 백테스트 모드에서는 백테스트 전용 메서드 사용
            if current_date:
                price = self.backtest_fetcher.get_valid_price_for_date(ticker, current_date)
                return price
            else:
                # 실시간 모드
                data = self.data_fetcher.get_past_data_enhanced(ticker, n=1)
                if data.empty:
                    return None
                
                price = data.iloc[-1]['close']
                
                # 가격 유효성 검증
                if price <= 0 or not np.isfinite(price):
                    return None
                
                # 가격 범위 검증
                if price < 100 or price > 1_000_000:  # 100원 ~ 100만원
                    return None
                
                return float(price)
            
        except Exception as e:
            print(f"❌ {ticker} 가격 조회 오류: {e}")
            return None
    
    def validate_multiple_tickers(self, tickers: List[str], current_date: str = None) -> List[str]:
        """
        여러 종목의 데이터 검증
        
        Args:
            tickers: 종목 코드 리스트
            current_date: 현재 날짜
            
        Returns:
            List[str]: 검증 통과한 종목 리스트
        """
        valid_tickers = []
        
        print(f"🔍 {len(tickers)}개 종목 데이터 검증 시작...")
        
        for ticker in tickers:
            if self.validate_ticker_data(ticker, current_date):
                valid_tickers.append(ticker)
        
        print(f"✅ 데이터 검증 완료: {len(valid_tickers)}/{len(tickers)}개 종목 통과")
        
        return valid_tickers
    
    def validate_ai_features(self, ticker: str, current_date: str = None) -> bool:
        """
        AI 모델 피처 생성용 데이터 검증
        
        Args:
            ticker: 종목 코드
            current_date: 현재 날짜
            
        Returns:
            bool: AI 피처 생성 가능 여부
        """
        try:
            # 기본 데이터 검증
            if not self.validate_ticker_data(ticker, current_date, min_days=30):
                return False
            
            # AI 피처 생성에 필요한 충분한 데이터 확인
            data = self.data_fetcher.get_past_data_enhanced(ticker, n=50)
            if data.empty or len(data) < 30:
                print(f"❌ {ticker}: AI 피처 생성용 데이터 부족 ({len(data)}개 < 30개)")
                return False
            
            # 현재 날짜 필터링 (백테스트용)
            if current_date:
                current_date_pd = pd.to_datetime(current_date)
                data = data[pd.to_datetime(data['timestamp']) <= current_date_pd]
                if len(data) < 30:
                    print(f"❌ {ticker}: 날짜 필터링 후 데이터 부족 ({len(data)}개)")
                    return False
            
            # OHLCV 데이터 완전성 확인
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in data.columns:
                    print(f"❌ {ticker}: 필수 컬럼 누락 - {col}")
                    return False
                
                # NaN 값 비율 확인
                nan_ratio = data[col].isnull().sum() / len(data)
                if nan_ratio > 0.1:  # 10% 이상 NaN이면 제외
                    print(f"❌ {ticker}: {col} 컬럼 NaN 비율 높음 ({nan_ratio:.1%})")
                    return False
            
            print(f"✅ {ticker}: AI 피처 생성 가능 ({len(data)}개 데이터)")
            return True
            
        except Exception as e:
            print(f"❌ {ticker} AI 피처 검증 오류: {e}")
            return False


# 전역 데이터 검증기 (싱글톤 패턴)
_validator_instance = None

def get_data_validator() -> DataValidator:
    """데이터 검증기 인스턴스 반환 (싱글톤)"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DataValidator()
    return _validator_instance

# 편의 함수들
def validate_ticker_data(ticker: str, current_date: str = None, min_days: int = 5) -> bool:
    """종목 데이터 검증"""
    validator = get_data_validator()
    return validator.validate_ticker_data(ticker, current_date, min_days)

def check_stop_loss(ticker: str, buy_price: float, current_date: str, 
                   stop_loss_rate: float = -0.05) -> tuple[bool, float, float]:
    """손실 제한 체크"""
    validator = get_data_validator()
    return validator.check_stop_loss(ticker, buy_price, current_date, stop_loss_rate)

def validate_multiple_tickers(tickers: List[str], current_date: str = None) -> List[str]:
    """여러 종목 데이터 검증"""
    validator = get_data_validator()
    return validator.validate_multiple_tickers(tickers, current_date)
