"""
Portfolio management for backtesting
백테스트용 포트폴리오 관리 클래스
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional


class Portfolio:
    """백테스트용 포트폴리오 관리 클래스"""
    
    def __init__(self, initial_capital: float = 10_000_000, transaction_cost: float = 0.003):
        """
        포트폴리오 초기화
        
        Args:
            initial_capital: 초기 자본금
            transaction_cost: 거래 비용 (비율)
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        
        # 포트폴리오 상태
        self.cash = initial_capital
        self.holdings = {}  # {ticker: {'quantity': int, 'buy_price': float, 'buy_date': str}}
        self.holding_period = {}  # {ticker: days}
        
        # 거래 기록
        self.trade_history = []
        self.portfolio_history = []
        
        print(f"💼 포트폴리오 초기화 완료")
        print(f"   초기 자본: {initial_capital:,}원")
        print(f"   거래 비용: {transaction_cost*100:.1f}%")
    
    def buy_stock(self, ticker: str, price: float, investment_amount: float, 
                  current_date: str, additional_info: Dict[str, Any] = None,
                  reset_holding_period: bool = False) -> bool:
        """
        주식 매수 (피라미딩 지원)
        
        Args:
            ticker: 종목 코드
            price: 매수 가격
            investment_amount: 투자 금액
            current_date: 매수 날짜
            additional_info: 추가 정보 (AI 점수, 기술적 점수 등)
            reset_holding_period: 보유 기간 리셋 여부
            
        Returns:
            bool: 매수 성공 여부
        """
        try:
            # 매수 수량 계산
            quantity = int(investment_amount // price)
            if quantity <= 0:
                print(f"⚠️ {ticker}: 매수 수량 부족 (투자금액: {investment_amount:,}원, 가격: {price:,}원)")
                return False
            
            actual_investment = quantity * price
            transaction_fee = actual_investment * self.transaction_cost
            total_cost = actual_investment + transaction_fee
            
            # 현금 부족 체크
            if total_cost > self.cash:
                print(f"⚠️ {ticker}: 현금 부족 (필요: {total_cost:,.0f}원, 보유: {self.cash:,.0f}원)")
                return False
            
            # 매수 실행
            self.cash -= total_cost
            
            # 이미 보유 중인 종목인지 확인 (피라미딩)
            is_pyramiding = False
            if ticker in self.holdings and self.holdings[ticker].get('quantity', 0) > 0:
                # 기존 보유 정보
                existing_quantity = self.holdings[ticker]['quantity']
                existing_avg_price = self.holdings[ticker]['buy_price']
                existing_investment = existing_quantity * existing_avg_price
                
                # 새로운 평균 단가 계산
                new_quantity = existing_quantity + quantity
                new_avg_price = (existing_investment + actual_investment) / new_quantity
                
                # holdings 업데이트
                self.holdings[ticker]['quantity'] = new_quantity
                self.holdings[ticker]['buy_price'] = new_avg_price
                self.holdings[ticker]['last_buy_date'] = current_date
                
                # 보유 기간 리셋 여부
                if reset_holding_period:
                    # 리셋 전의 보유기간 저장
                    old_holding_days = self.holding_period.get(ticker, 0)
                    self.holding_period[ticker] = 1
                    print(f"🔄 {ticker} 보유기간 리셋 (현재 보유일: {old_holding_days}일 → 1일)")
                    
                    # 리셋 정보 저장
                    if 'additional_info' not in self.holdings[ticker]:
                        self.holdings[ticker]['additional_info'] = {}
                    self.holdings[ticker]['additional_info']['reset_date'] = current_date
                    self.holdings[ticker]['additional_info']['reset_count'] = \
                        self.holdings[ticker]['additional_info'].get('reset_count', 0) + 1
                
                is_pyramiding = True
                print(f"📥 {ticker} 피라미딩 매수: {quantity:,}주 @ {price:,}원")
                print(f"   총 보유: {new_quantity:,}주, 평균단가: {new_avg_price:,.0f}원")
                
            else:
                # 신규 매수
                self.holdings[ticker] = {
                    'quantity': quantity,
                    'buy_price': price,
                    'buy_date': current_date,
                    'last_buy_date': current_date,
                    'additional_info': {
                        'reset_count': 0  # 초기화
                    }
                }
                self.holding_period[ticker] = 1
                
                print(f"📥 {ticker} 신규 매수: {quantity:,}주 @ {price:,}원 (투자: {actual_investment:,}원)")
            
            # 추가 정보 저장
            if additional_info:
                if 'additional_info' not in self.holdings[ticker]:
                    self.holdings[ticker]['additional_info'] = {}
                
                # 기존 정보와 병합 (리셋 정보는 유지)
                existing_info = self.holdings[ticker]['additional_info'].copy()
                existing_info.update(additional_info)
                self.holdings[ticker]['additional_info'] = existing_info
            
            # 거래 기록
            trade_record = {
                'date': current_date,
                'action': 'BUY',
                'ticker': ticker,
                'quantity': quantity,
                'price': price,
                'amount': actual_investment,
                'fee': transaction_fee,
                'is_pyramiding': is_pyramiding
            }
            
            if additional_info:
                trade_record.update(additional_info)
                
            self.trade_history.append(trade_record)
            
            return True
            
        except Exception as e:
            print(f"❌ {ticker} 매수 오류: {e}")
            return False
    
    def sell_stock(self, ticker: str, price: float, current_date: str, 
                   sell_reason: str = "") -> bool:
        """
        주식 매도 (부분 매도 지원)
        
        Args:
            ticker: 종목 코드
            price: 매도 가격
            current_date: 매도 날짜
            sell_reason: 매도 사유
            
        Returns:
            bool: 매도 성공 여부
        """
        try:
            holding = self.holdings.get(ticker, {})
            quantity = holding.get('quantity', 0)
            
            if quantity <= 0:
                print(f"⚠️ {ticker}: 보유 수량 없음")
                return False
            
            buy_price = holding.get('buy_price', 0)
            
            # 매도 금액 계산
            sell_amount = quantity * price
            transaction_fee = sell_amount * self.transaction_cost
            net_amount = sell_amount - transaction_fee
            
            # 손익 계산 (평균 단가 기준)
            buy_amount = quantity * buy_price
            buy_fee = buy_amount * self.transaction_cost  # 매수 시 수수료 고려
            total_buy_cost = buy_amount + buy_fee
            
            profit = net_amount - total_buy_cost
            profit_rate = (profit / total_buy_cost) * 100 if total_buy_cost > 0 else 0
            
            # 매도 실행
            self.cash += net_amount
            self.holdings[ticker]['quantity'] = 0  # 수량만 0으로 설정
            
            # 거래 기록
            self.trade_history.append({
                'date': current_date,
                'action': 'SELL',
                'ticker': ticker,
                'quantity': quantity,
                'price': price,
                'amount': sell_amount,
                'fee': transaction_fee,
                'profit': profit,
                'profit_rate': profit_rate,
                'holding_days': self.holding_period.get(ticker, 0),
                'sell_reason': sell_reason,
                'avg_buy_price': buy_price  # 평균 매수 단가 기록
            })
            
            # 보유기간 초기화
            if ticker in self.holding_period:
                self.holding_period[ticker] = 0
            
            print(f"📤 {ticker} 매도 완료: 수익률 {profit_rate:+.2f}% ({self.holding_period.get(ticker, 0)}일 보유)")
            return True
            
        except Exception as e:
            print(f"❌ {ticker} 매도 오류: {e}")
            return False
    
    def update_holding_periods(self):
        """보유 기간 업데이트"""
        for ticker in self.holdings:
            quantity = self.holdings[ticker].get('quantity', 0)
            if quantity > 0:
                current_days = self.holding_period.get(ticker, 0)
                self.holding_period[ticker] = current_days + 1
            else:
                # 매도된 종목은 보유 기간 초기화
                if ticker in self.holding_period:
                    self.holding_period[ticker] = 0
    
    def get_current_holdings(self) -> Dict[str, Dict[str, Any]]:
        """현재 보유 종목 반환"""
        current_holdings = {}
        for ticker, holding in self.holdings.items():
            if holding.get('quantity', 0) > 0:
                current_holdings[ticker] = holding.copy()
        return current_holdings
    
    def calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """
        현재 포트폴리오 가치 계산
        
        Args:
            current_prices: {ticker: current_price} 딕셔너리
            
        Returns:
            float: 총 포트폴리오 가치
        """
        total_value = self.cash
        stock_value = 0
        
        for ticker, holding in self.holdings.items():
            quantity = holding.get('quantity', 0)
            if quantity <= 0:
                continue
                
            # 현재가 확인
            current_price = current_prices.get(ticker)
            if current_price is None:
                # 현재가를 찾을 수 없으면 매수가로 대체
                current_price = holding.get('buy_price', 0)
                
            position_value = quantity * current_price
            stock_value += position_value
            total_value += position_value
        
        return total_value
    
    def record_daily_portfolio(self, date: str, portfolio_value: float, 
                             additional_data: Dict[str, Any] = None):
        """일별 포트폴리오 기록 저장"""
        daily_return = (portfolio_value - self.initial_capital) / self.initial_capital
        current_positions = len([t for t, h in self.holdings.items() if h.get('quantity', 0) > 0])
        
        record = {
            'date': date,
            'portfolio_value': portfolio_value,
            'cash': self.cash,
            'daily_return': daily_return,
            'positions': current_positions
        }
        
        if additional_data:
            record.update(additional_data)
            
        self.portfolio_history.append(record)
    
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """거래 내역 반환"""
        return self.trade_history.copy()
    
    def get_portfolio_history(self) -> List[Dict[str, Any]]:
        """포트폴리오 히스토리 반환"""
        return self.portfolio_history.copy()
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """포트폴리오 요약 통계"""
        if not self.portfolio_history:
            return {}
        
        portfolio_values = [record['portfolio_value'] for record in self.portfolio_history]
        final_value = portfolio_values[-1]
        
        # 거래 통계
        buy_trades = [t for t in self.trade_history if t['action'] == 'BUY']
        sell_trades = [t for t in self.trade_history if t['action'] == 'SELL']
        
        profitable_trades = [t for t in sell_trades if t['profit'] > 0]
        win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
        
        avg_profit = np.mean([t['profit'] for t in sell_trades]) if sell_trades else 0
        avg_holding_days = np.mean([t['holding_days'] for t in sell_trades]) if sell_trades else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': (final_value - self.initial_capital) / self.initial_capital,
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit,
            'avg_holding_days': avg_holding_days,
            'final_cash': self.cash
        }
