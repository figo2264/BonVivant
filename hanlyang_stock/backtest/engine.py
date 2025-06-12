"""
Main backtest engine - modularized version
모듈화된 백테스트 엔진
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .portfolio import Portfolio
from .performance import PerformanceAnalyzer, get_performance_analyzer
from .data_validator import DataValidator, get_data_validator
from ..data.fetcher import get_data_fetcher
from ..analysis.ai_model import get_ai_manager
from ..analysis.technical import get_technical_analyzer
from ..strategy.selector import get_stock_selector


class BacktestEngine:
    """모듈화된 백테스트 엔진 - hanlyang_stock 모듈 활용"""
    
    def __init__(self, initial_capital: float = 10_000_000, transaction_cost: float = 0.003):
        """
        백테스트 엔진 초기화
        
        Args:
            initial_capital: 초기 자본금 (기본 1000만원)
            transaction_cost: 거래 비용 (기본 0.3%)
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        
        # 모듈 인스턴스들
        self.portfolio = Portfolio(initial_capital, transaction_cost)
        self.data_fetcher = get_data_fetcher()
        self.ai_manager = get_ai_manager()
        self.technical_analyzer = get_technical_analyzer()
        self.stock_selector = get_stock_selector()
        self.data_validator = get_data_validator()
        self.performance_analyzer = get_performance_analyzer()
        
        # 백테스트 모드 활성화
        self.stock_selector.set_backtest_mode(True)
        
        # 백테스트 설정
        self.ai_enabled = True
        self.current_model = None
        self.model_trained_date = None
        
        print(f"🚀 모듈화된 백테스트 엔진 초기화 완료")
        print(f"   초기 자본: {initial_capital:,}원")
        print(f"   거래 비용: {transaction_cost*100:.1f}%")
    
    def run_backtest(self, start_date: str, end_date: str, ai_enabled: bool = True) -> Dict[str, Any]:
        """
        백테스팅 실행 (모듈화된 버전)
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            ai_enabled: AI 기능 활성화 여부
            
        Returns:
            Dict: 백테스트 결과
        """
        print(f"🚀 백테스팅 시작: {start_date} ~ {end_date}")
        print(f"🤖 AI 기능: {'활성화' if ai_enabled else '비활성화'}")
        print("=" * 60)
        
        # AI 기능 설정
        self.ai_enabled = ai_enabled
        
        # 날짜 범위 생성
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start, end=end, freq='D')
        
        for current_date in date_range:
            # 주말은 스킵
            if current_date.weekday() >= 5:
                continue
            
            date_str = current_date.strftime('%Y-%m-%d')
            weekday = current_date.weekday()  # 0=월요일
            
            print(f"\n📅 {date_str} 처리 중... ({'월화수목금'[weekday]}요일)")
            
            # 매주 월요일마다 AI 모델 재훈련 (AI 활성화된 경우)
            if self.ai_enabled and (weekday == 0 or self.current_model is None):
                self._retrain_ai_model(date_str)
            
            # AI 모델 사용 현황 출력
            self._print_ai_status()
            
            # 1. 보유 기간 업데이트
            self.portfolio.update_holding_periods()
            
            # 2. 매도 전략 실행
            sell_results = self._execute_sell_strategy(date_str)
            
            # 3. 매수 전략 실행
            buy_results = self._execute_buy_strategy(date_str)
            
            # 4. 포트폴리오 가치 계산 및 기록
            self._record_daily_portfolio(date_str, sell_results, buy_results)
        
        # 최종 성과 계산
        return self._finalize_backtest()
    
    def _retrain_ai_model(self, date_str: str):
        """AI 모델 재훈련"""
        print(f"🤖 {date_str} AI 모델 재훈련 시작...")
        try:
            temp_model = self.ai_manager.train_ai_model_at_date(date_str)
            if temp_model is not None:
                self.current_model = temp_model
                self.model_trained_date = date_str
                print(f"✅ AI 모델 훈련 완료 ({date_str})")
            else:
                print(f"❌ AI 모델 훈련 실패 - 이번 주는 이전 모델 사용 또는 기술적 분석만 사용")
        except Exception as e:
            print(f"❌ AI 모델 훈련 오류: {e}")
    
    def _print_ai_status(self):
        """AI 모델 사용 현황 출력"""
        if self.ai_enabled and self.current_model is not None:
            model_accuracy = getattr(self.current_model, 'test_accuracy', 0)
            model_quality = getattr(self.current_model, 'model_quality_score', 0)
            print(f"🤖 AI 모델 사용 중 (훈련일: {self.model_trained_date})")
            print(f"   📊 모델 정확도: {model_accuracy:.1%}, 품질점수: {model_quality:.1f}/100")
        else:
            print(f"📊 기술적 분석만 사용")
    
    def _execute_sell_strategy(self, current_date: str) -> Dict[str, Any]:
        """매도 전략 실행"""
        current_holdings = self.portfolio.get_current_holdings()
        
        if not current_holdings:
            return {'sold_count': 0, 'total_profit': 0}
        
        print(f"🔍 매도 후보 검토: {len(current_holdings)}개 보유 중")
        
        sold_count = 0
        total_profit = 0
        
        for ticker, holding in current_holdings.items():
            holding_days = self.portfolio.holding_period.get(ticker, 0)
            should_sell = False
            sell_reason = ""
            
            # 데이터 검증
            if not self.data_validator.validate_ticker_data(ticker, current_date):
                print(f"   ❌ {ticker}: 데이터 검증 실패 - 매도 스킵")
                continue
            
            # 손실 제한 체크 (우선순위 최고)
            buy_price = holding.get('buy_price', 0)
            stop_loss_sell, current_price, loss_rate = self.data_validator.check_stop_loss(
                ticker, buy_price, current_date, stop_loss_rate=-0.05
            )
            
            if stop_loss_sell:
                should_sell = True
                sell_reason = f"손실제한 (손실률: {loss_rate*100:.1f}%)"
                print(f"   🛑 {ticker}: 손실 제한 매도 - 손실률 {loss_rate*100:.1f}%")
            
            # 기본 3일 룰 (손실 제한이 아닌 경우만)
            elif holding_days >= 3:
                should_sell = True
                sell_reason = f"보유기간 ({holding_days}일)"
                print(f"   → {ticker}: 3일 이상 보유로 매도 검토")
                
                # 기술적 홀드 시그널 체크 (3일차에만, 손실이 없는 경우만)
                if holding_days == 3 and self.ai_enabled and loss_rate > -0.02:
                    try:
                        hold_signal = self.technical_analyzer.get_technical_hold_signal(ticker, current_date)
                        
                        if hold_signal >= 0.75:
                            should_sell = False
                            sell_reason = ""
                            print(f"   → {ticker}: 기술적 분석 강홀드 신호로 1일 연장 (신호: {hold_signal:.3f})")
                    except Exception as e:
                        print(f"   → {ticker}: 홀드 시그널 계산 오류: {e}")
            
            # 안전장치: 5일 이상은 무조건 매도
            if holding_days >= 5:
                should_sell = True
                sell_reason = f"5일 안전룰"
                print(f"   → {ticker}: 5일 안전룰 적용")
            
            # 매도 실행
            if should_sell:
                # 현재가 확인
                if current_price == 0:  # stop_loss에서 구하지 못한 경우
                    current_price = self.data_validator.get_valid_price(ticker, current_date)
                
                if current_price and current_price > 0:
                    success = self.portfolio.sell_stock(ticker, current_price, current_date, sell_reason)
                    if success:
                        sold_count += 1
                        # 수익 계산은 포트폴리오에서 처리됨
                else:
                    print(f"   ❌ {ticker}: 현재가 조회 실패로 매도 스킵")
        
        return {'sold_count': sold_count, 'total_profit': 0}  # 실제 수익은 거래내역에서 계산
    
    def _execute_buy_strategy(self, current_date: str) -> Dict[str, Any]:
        """매수 전략 실행"""
        # 현재 보유 종목 수 확인
        current_holdings = self.portfolio.get_current_holdings()
        max_positions = 5
        available_slots = max_positions - len(current_holdings)
        
        if available_slots <= 0:
            print(f"📊 포트폴리오 한계 도달 (현재 {len(current_holdings)}개 보유)")
            return {'bought_count': 0, 'total_invested': 0}
        
        print(f"📊 매수 전략 실행 - 사용 가능 슬롯: {available_slots}개")
        
        # 종목 선정 (AI 향상 기능 포함)
        candidates = self._select_buy_candidates(current_date)
        
        if not candidates:
            print("📊 매수 대상 종목이 없습니다.")
            return {'bought_count': 0, 'total_invested': 0}
        
        # 매수 실행
        return self._execute_buy_orders(candidates, available_slots, current_date)
    
    def _select_buy_candidates(self, current_date: str) -> List[Dict[str, Any]]:
        """매수 후보 종목 선정"""
        try:
            # 백테스트 모드에서 현재 날짜 설정
            self.stock_selector.set_backtest_mode(True, current_date)
            
            # 1단계: 기술적 분석 기반 1차 선정
            entry_candidates = self.stock_selector.enhanced_stock_selection(current_date)
            
            if not entry_candidates:
                print("📊 기술적 분석에서 선정된 종목이 없습니다.")
                return []
            
            # 데이터 검증 강화
            validated_candidates = []
            for candidate in entry_candidates:
                ticker = candidate['ticker']
                if self.data_validator.validate_ticker_data(ticker, current_date):
                    validated_candidates.append(candidate)
                else:
                    print(f"   ❌ {ticker}: 데이터 검증 실패 - 매수 후보에서 제외")
            
            print(f"   ✅ 검증 통과: {len(validated_candidates)}개 종목")
            
            # 2단계: AI 기반 최종 선정 (AI 활성화된 경우)
            if self.ai_enabled and self.current_model is not None:
                final_tickers = self.stock_selector.ai_enhanced_final_selection(
                    validated_candidates, current_date
                )
                print(f"🤖 AI 선정 결과: {len(final_tickers)}개")
                return final_tickers
            else:
                # AI 없으면 상위 5개
                final_candidates = validated_candidates[:5]
                print(f"📊 AI 모델 없음 - 기술적 분석 상위 {len(final_candidates)}개 선정")
                return final_candidates
                
        except Exception as e:
            print(f"❌ 종목 선정 오류: {e}")
            return []
    
    def _execute_buy_orders(self, candidates: List[Dict[str, Any]], available_slots: int, 
                          current_date: str) -> Dict[str, Any]:
        """매수 주문 실행"""
        bought_count = 0
        total_invested = 0
        
        # 종목당 투자 금액 계산
        available_cash = self.portfolio.cash * 0.8  # 현금의 80% 사용
        investment_per_stock = available_cash / available_slots if available_slots > 0 else 0
        
        print(f"   사용 가능 현금: {available_cash:,.0f}원")
        print(f"   종목당 기본 투자: {investment_per_stock:,.0f}원")
        
        for candidate in candidates[:available_slots]:
            ticker = candidate['ticker']
            
            # 현재 보유 중인 종목은 스킵
            current_holdings = self.portfolio.get_current_holdings()
            if ticker in current_holdings:
                print(f"   {ticker}: 이미 보유 중 - 스킵")
                continue
            
            # 현재가 조회
            current_price = self.data_validator.get_valid_price(ticker, current_date)
            if not current_price or current_price <= 0:
                print(f"   ❌ {ticker}: 현재가 조회 실패")
                continue
            
            # AI 점수 기반 투자 금액 조정
            investment_amount = self._determine_investment_amount(
                candidate, investment_per_stock
            )
            
            # 현금 부족 체크
            remaining_balance = self.portfolio.cash - total_invested - 2_000_000  # 200만원 안전자금
            if remaining_balance < investment_amount:
                if remaining_balance < 300_000:  # 최소 투자금액
                    print(f"   ⚠️ {ticker}: 최소 투자금액 부족")
                    continue
                investment_amount = remaining_balance
            
            # 매수 실행
            additional_info = {
                'technical_score': candidate.get('technical_score', 0.5),
                'ai_score': candidate.get('ai_score', 0.5),
                'confidence_level': candidate.get('confidence_level', '중립')
            }
            
            success = self.portfolio.buy_stock(
                ticker, current_price, investment_amount, current_date, additional_info
            )
            
            if success:
                bought_count += 1
                total_invested += investment_amount
                print(f"✅ {ticker} 매수 완료")
        
        print(f"📊 매수 완료: {bought_count}개 종목, 총 투자 {total_invested:,.0f}원")
        return {'bought_count': bought_count, 'total_invested': total_invested}
    
    def _determine_investment_amount(self, candidate: Dict[str, Any], 
                                   base_amount: float) -> float:
        """AI 점수 기반 투자 금액 결정"""
        ai_score = candidate.get('ai_score', 0.5)
        
        # AI 신뢰도 기반 투자 금액 조정 (백테스트 엔진과 동일)
        if ai_score >= 0.80:           # 최고신뢰: 1.5배
            multiplier = 1.5
        elif ai_score >= 0.70:         # 고신뢰: 1.2배
            multiplier = 1.2
        elif ai_score >= 0.65:         # 중신뢰: 1.0배
            multiplier = 1.0
        else:                          # 저신뢰: 0.7배
            multiplier = 0.7
        
        return base_amount * multiplier
    
    def _record_daily_portfolio(self, date_str: str, sell_results: Dict[str, Any], 
                              buy_results: Dict[str, Any]):
        """일별 포트폴리오 기록"""
        # 현재 포트폴리오 가치 계산
        current_holdings = self.portfolio.get_current_holdings()
        current_prices = {}
        
        # 보유 종목들의 현재가 수집
        for ticker in current_holdings.keys():
            price = self.data_validator.get_valid_price(ticker, date_str)
            if price:
                current_prices[ticker] = price
        
        portfolio_value = self.portfolio.calculate_portfolio_value(current_prices)
        
        # 추가 정보
        additional_data = {
            'sold_count': sell_results['sold_count'],
            'bought_count': buy_results['bought_count'],
            'ai_enabled': self.ai_enabled,
            'model_trained_date': self.model_trained_date
        }
        
        # AI 모델 정보 추가
        if self.ai_enabled and self.current_model is not None:
            additional_data.update({
                'model_accuracy': getattr(self.current_model, 'test_accuracy', 0),
                'model_quality': getattr(self.current_model, 'model_quality_score', 0)
            })
        
        self.portfolio.record_daily_portfolio(date_str, portfolio_value, additional_data)
        
        daily_return = (portfolio_value - self.initial_capital) / self.initial_capital
        current_positions = len(current_holdings)
        
        print(f"💼 포트폴리오: {portfolio_value:,.0f}원 (수익률: {daily_return*100:+.2f}%, 보유: {current_positions}개)")
    
    def _finalize_backtest(self) -> Dict[str, Any]:
        """백테스트 종료 및 결과 반환"""
        print("\n" + "=" * 60)
        print("✅ 백테스팅 완료!")
        
        # 성과 분석
        portfolio_history = self.portfolio.get_portfolio_history()
        trade_history = self.portfolio.get_trade_history()
        
        results = self.performance_analyzer.calculate_performance_metrics(
            portfolio_history, trade_history, self.initial_capital
        )
        
        # 추가 데이터
        results.update({
            'trade_history': trade_history,
            'portfolio_history': portfolio_history,
            'final_cash': self.portfolio.cash
        })
        
        # 성과 요약 출력
        self.performance_analyzer.print_performance_summary()
        
        # AI 성과 분석 (AI 활성화된 경우)
        if self.ai_enabled:
            ai_performance = self.performance_analyzer.analyze_ai_performance(trade_history)
            if ai_performance:
                self.performance_analyzer.print_ai_performance_summary(ai_performance)
                results['ai_performance'] = ai_performance
        
        return results
    
    def save_results(self, filename: str = None) -> str:
        """결과 저장"""
        return self.performance_analyzer.save_results_to_json(filename)


# 편의 함수
def run_backtest(start_date: str, end_date: str, initial_capital: float = 10_000_000,
                transaction_cost: float = 0.003, ai_enabled: bool = True) -> Dict[str, Any]:
    """
    백테스트 실행 편의 함수
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        initial_capital: 초기 자본
        transaction_cost: 거래 비용
        ai_enabled: AI 기능 활성화
        
    Returns:
        Dict: 백테스트 결과
    """
    engine = BacktestEngine(initial_capital, transaction_cost)
    return engine.run_backtest(start_date, end_date, ai_enabled)


# 사용 예시
if __name__ == "__main__":
    # 모듈화된 백테스트 실행
    start_date = "2025-06-01"
    end_date = "2025-06-10"
    
    try:
        results = run_backtest(start_date, end_date, ai_enabled=True)
        
        # 결과 저장
        engine = BacktestEngine()
        engine.performance_analyzer.results = results
        engine.save_results("modular_backtest_result.json")
        
    except Exception as e:
        print(f"❌ 모듈화된 백테스팅 실행 오류: {e}")
        import traceback
        traceback.print_exc()
