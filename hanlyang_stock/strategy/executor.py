"""
Strategy execution modules for buy and sell operations
Enhanced with complete data validation and stop-loss logic from backtest_engine
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from ..data.fetcher import get_data_fetcher
from ..analysis.technical import get_technical_hold_signal, validate_ticker_data
from ..strategy.selector import get_stock_selector
from ..utils.storage import get_data_manager
from ..utils.notification import get_notifier
from ..config.settings import get_hantustock


class SellExecutor:
    """매도 전략 실행 클래스 - 백테스트 엔진의 모든 기능 완전 적용"""
    
    def __init__(self, stop_loss_rate=-0.05):
        self.data_fetcher = get_data_fetcher()
        self.data_manager = get_data_manager()
        self.notifier = get_notifier()
        self.ht = get_hantustock()
        self.stop_loss_rate = stop_loss_rate  # 손실 제한 비율 (기본 -5%)
    
    def execute(self) -> Dict[str, Any]:
        """
        아침 매도 전략 실행
        
        Returns:
            dict: 실행 결과 요약
        """
        print("🌅 아침 매도 전략 실행 시작!")
        
        # 현재 보유중인 종목 조회
        holdings = self.data_fetcher.get_holding_stock()
        print(f"📊 현재 보유: {len(holdings)}개")
        
        # holding_period를 하루씩 높여줌
        self._update_holding_periods(holdings)
        
        # 매도 대상 종목 결정
        tickers_to_sell = self._determine_sell_candidates(holdings)
        print(f"📤 매도 예정: {len(tickers_to_sell)}개")
        
        # 매도 실행
        sell_results = self._execute_sells(tickers_to_sell, holdings)
        
        # 요약 알림 전송
        self._send_sell_summary(sell_results, len(holdings))
        
        # 성과 로깅
        self._log_sell_performance(sell_results)
        
        # 데이터 저장
        self.data_manager.save()
        
        print("✅ 아침 매도 전략 실행 완료!")
        return sell_results
    
    def _update_holding_periods(self, holdings: Dict[str, int]) -> None:
        """보유 기간 업데이트"""
        for ticker in holdings:
            current_days = self.data_manager.increment_holding_period(ticker)
            print(f"📅 {ticker}: {current_days}일차")
    
    def check_stop_loss(self, ticker: str, quantity: int) -> tuple[bool, float, float]:
        """
        손실 제한 체크 (백테스트 엔진에서 완전 이식)
        
        Args:
            ticker: 종목 코드
            quantity: 보유 수량
            
        Returns:
            tuple: (should_sell, current_price, loss_rate)
        """
        try:
            # 매수 정보 조회
            purchase_info = self.data_manager.get_purchase_info(ticker)
            if not purchase_info:
                print(f"⚠️ {ticker}: 매수 정보 없음")
                return False, 0, 0
            
            buy_price = purchase_info.get('buy_price', 0)
            if buy_price <= 0:
                print(f"⚠️ {ticker}: 매수가 정보 오류")
                return False, 0, 0
            
            # 현재가 조회 (데이터 검증 강화)
            current_price = self.data_fetcher.get_current_price(ticker)
            if not current_price or current_price <= 0:
                print(f"⚠️ {ticker}: 현재가 조회 실패")
                return False, 0, 0
            
            # 손실률 계산
            loss_rate = (current_price - buy_price) / buy_price
            should_sell = loss_rate <= self.stop_loss_rate
            
            if should_sell:
                print(f"🛑 {ticker}: 손실 제한 매도 신호 - 손실률 {loss_rate*100:.1f}% (기준: {self.stop_loss_rate*100:.1f}%)")
            
            return should_sell, current_price, loss_rate
            
        except Exception as e:
            print(f"❌ {ticker} 손실 제한 체크 실패: {e}")
            return False, 0, 0
    
    def _determine_sell_candidates(self, holdings: Dict[str, int]) -> List[str]:
        """매도 후보 종목 결정 - 백테스트 엔진 로직 완전 적용
        
        매도 우선순위:
        1순위: 손실제한 (-5%)
        2순위: 전략별 목표 기간
          - 뉴스 전략: news_signal의 holding_days
          - 기본 전략: 3일
        3순위: 최대 보유기간
          - 뉴스 전략: 10일
          - 기본 전략: 5일
        """
        tickers_to_sell = []
        strategy_data = self.data_manager.get_data()
        enhanced_analysis_enabled = strategy_data.get('enhanced_analysis_enabled', True)
        hybrid_strategy_enabled = strategy_data.get('hybrid_strategy_enabled', False)
        
        print("🔍 매도 후보 검토 시작...")
        
        for ticker in holdings:
            holding_days = self.data_manager.get_holding_period(ticker)
            should_sell = False
            sell_reason = ""
            
            print(f"   {ticker}: {holding_days}일 보유 중")
            
            # 🔧 1. 데이터 검증 강화 (백테스트 엔진 기능)
            if not validate_ticker_data(ticker):
                print(f"   ❌ {ticker}: 데이터 검증 실패 - 매도 스킵")
                continue
            
            # 🔧 2. 손실 제한 체크 (최우선)
            stop_loss_sell, current_price, loss_rate = self.check_stop_loss(ticker, holdings[ticker])
            if stop_loss_sell:
                should_sell = True
                sell_reason = f"손실제한 (손실률: {loss_rate*100:.1f}%)"
                print(f"   🛑 {ticker}: 손실 제한 매도 - 손실률 {loss_rate*100:.1f}%")
            
            # 🔧 3. 전략별 목표 기간 체크 (손실제한이 아닌 경우만)
            elif hybrid_strategy_enabled:
                # 하이브리드 전략인 경우
                purchase_info = self.data_manager.get_purchase_info(ticker)
                if purchase_info and purchase_info.get('is_hybrid'):
                    # 뉴스 기반 매도 체크
                    if self._check_news_sell_signal(ticker, holding_days):
                        should_sell = True
                        sell_reason = "뉴스 하락 예측"
                        print(f"   📉 {ticker}: 뉴스 기반 매도 신호")
                    else:
                        # 리셋 횟수 확인
                        reset_count = purchase_info.get('reset_count', 0)
                        max_resets = strategy_data.get('pyramiding_max_resets', 2)  # 설정에서 가져오기
                        
                        # news_signal에서 holding_days 가져오기 (백테스트 엔진과 동일)
                        news_signal = purchase_info.get('news_signal', {})
                        planned_holding_days = news_signal.get('holding_days', 5)  # 기본값 5일
                        
                        if holding_days >= planned_holding_days:
                            if reset_count >= max_resets:
                                should_sell = True
                                sell_reason = f"최대 리셋 횟수({max_resets}회) 도달"
                                print(f"   → {ticker}: 최대 리셋 횟수 도달로 매도")
                            else:
                                should_sell = True
                                sell_reason = f"뉴스 전략 목표 기간({planned_holding_days}일) 달성"
                                print(f"   → {ticker}: 뉴스 전략 목표 기간 달성으로 매도")
                else:
                    # 하이브리드 전략이지만 뉴스 정보 없는 경우 기본 3일 룰
                    if holding_days >= 3:
                        should_sell = True
                        sell_reason = f"기본 보유기간(3일) 달성"
                        print(f"   → {ticker}: 3일 이상 보유로 매도 검토")
                        
                        # 종합적인 홀드 판단 (3일차에만)
                        if holding_days == 3 and enhanced_analysis_enabled and loss_rate > -0.02:
                            hold_score = self._calculate_hold_score(ticker, loss_rate)
                            
                            if hold_score >= 0.75:
                                should_sell = False
                                sell_reason = ""
                                print(f"   → {ticker}: 종합 홀드 신호로 1일 연장 (점수: {hold_score:.3f})")
            else:
                # 기본 전략인 경우 (3일 룰)
                if holding_days >= 3:
                    should_sell = True
                    sell_reason = f"기본 보유기간(3일) 달성"
                    print(f"   → {ticker}: 3일 이상 보유로 매도 검토")
                    
                    # 종합적인 홀드 판단 (3일차에만)
                    if holding_days == 3 and enhanced_analysis_enabled and loss_rate > -0.02:
                        hold_score = self._calculate_hold_score(ticker, loss_rate)
                        
                        if hold_score >= 0.75:
                            should_sell = False
                            sell_reason = ""
                            print(f"   → {ticker}: 종합 홀드 신호로 1일 연장 (점수: {hold_score:.3f})")
            
            # 4. 최대 보유기간 체크 (전략별 차별화)
            if not should_sell:  # 아직 매도 결정이 안 된 경우만
                # 하이브리드 전략이고 뉴스 정보가 있는 경우 10일, 아니면 5일
                purchase_info = self.data_manager.get_purchase_info(ticker)
                is_news_based = (hybrid_strategy_enabled and purchase_info and 
                               purchase_info.get('is_hybrid'))
                
                max_holding_days = 10 if is_news_based else 5
                
                if holding_days >= max_holding_days:
                    should_sell = True
                    sell_reason = f"최대 보유기간({max_holding_days}일) 도달"
                    print(f"   → {ticker}: 최대 보유기간 도달로 매도")
            
            if should_sell:
                tickers_to_sell.append({
                    'ticker': ticker,
                    'reason': sell_reason,
                    'holding_days': holding_days,
                    'is_stop_loss': stop_loss_sell
                })
        
        print(f"📤 매도 대상: {len(tickers_to_sell)}개 종목")
        for item in tickers_to_sell:
            print(f"   - {item['ticker']}: {item['reason']}")
        
        return [item['ticker'] for item in tickers_to_sell]
    
    def _check_news_sell_signal(self, ticker: str, holding_days: int) -> bool:
        """뉴스 예측값 기반 매도 신호 체크"""
        purchase_info = self.data_manager.get_purchase_info(ticker)
        
        # 하이브리드 전략으로 매수한 경우만
        if not purchase_info or not purchase_info.get('is_hybrid'):
            return False
        
        # 보유 기간에 따른 적절한 예측값 확인
        if holding_days <= 1:
            # 1일 보유: 1일 후 예측 확인
            current_prob = purchase_info.get('news_prob_1', 0.5)
            next_prob = purchase_info.get('news_prob_5', 0.5)
        elif holding_days <= 3:
            # 2-3일 보유: 5일 예측 확인
            current_prob = purchase_info.get('news_prob_5', 0.5)
            next_prob = purchase_info.get('news_prob_10', 0.5)
        else:
            # 4일 이상: 10일 예측 확인
            current_prob = purchase_info.get('news_prob_10', 0.5)
            next_prob = 0.5
        
        # 매도 신호 판단
        # 1) 현재 시점 예측이 하락 예상 (45% 미만)
        if current_prob < 0.45:
            print(f"      📉 뉴스 하락 예측: {current_prob*100:.1f}% < 45%")
            return True
        
        # 2) 예측 추세가 급격한 하락세
        if next_prob < current_prob - 0.1:  # 10%p 이상 하락
            print(f"      📉 뉴스 하락 추세: {current_prob*100:.1f}% → {next_prob*100:.1f}%")
            return True
        
        return False
    
    def _calculate_hold_score(self, ticker: str, loss_rate: float) -> float:
        """종합적인 홀드 점수 계산 (기술적 분석 + 뉴스)"""
        hold_score = 0.5  # 기본 점수
        
        # 1. 기술적 홀드 시그널
        try:
            technical_hold = get_technical_hold_signal(ticker)
            hold_score = technical_hold * 0.7  # 기술적 분석 70% 가중치
            print(f"      📊 기술적 홀드 신호: {technical_hold:.3f}")
        except Exception as e:
            print(f"      ⚠️ 기술적 분석 오류: {e}")
            hold_score = 0.5 * 0.7
        
        # 2. 뉴스 예측값 반영 (하이브리드 전략인 경우)
        purchase_info = self.data_manager.get_purchase_info(ticker)
        if purchase_info and purchase_info.get('is_hybrid'):
            # 5일 예측값 확인 (3일 보유 중이므로)
            news_prob = purchase_info.get('news_prob_5', 0.5)
            news_hold_score = news_prob  # 상승 확률이 높으면 홀드
            hold_score += news_hold_score * 0.3  # 뉴스 30% 가중치
            print(f"      📰 뉴스 홀드 신호: {news_hold_score:.3f} (5일 예측)")
        else:
            hold_score += 0.5 * 0.3  # 뉴스 정보 없으면 중립
        
        # 3. 수익률 보정
        if loss_rate > 0.03:  # 3% 이상 수익 중
            hold_score -= 0.1  # 수익 실현 유도
        elif loss_rate < -0.02:  # 2% 이상 손실
            hold_score -= 0.1  # 손실 확대 방지
        
        return hold_score
    
    def _execute_sells(self, tickers_to_sell: List[str], holdings: Dict[str, int]) -> Dict[str, Any]:
        """매도 실행"""
        sold_tickers = []
        total_sell_profit = 0
        
        for ticker in tickers_to_sell:
            holding_days = self.data_manager.get_holding_period(ticker)
            
            try:
                # 매도 전 수익률 계산
                profit_info = self._calculate_profit(ticker, holdings[ticker])
                
                print(f"📤 {ticker} 매도 (보유기간: {holding_days}일{profit_info['display']})")
                
                # 매도 주문 실행
                order_id, quantity = self.ht.ask(ticker, 'market', holdings[ticker], 'STOCK')
                
                if order_id:
                    sold_tickers.append(ticker)
                    total_sell_profit += profit_info['profit']
                    
                    # 슬랙 알림: 매도 체결
                    purchase_info = self.data_manager.get_purchase_info(ticker)
                    confidence_level = purchase_info.get('confidence_level') if purchase_info else None
                    
                    self.notifier.notify_sell_execution(
                        ticker=ticker,
                        quantity=quantity,
                        holding_days=holding_days,
                        profit_rate=profit_info['profit_rate'],
                        profit=profit_info['profit'],
                        confidence_level=confidence_level
                    )
                    
                    # 매도 완료 후 구매 정보 정리
                    self.data_manager.remove_purchase_info(ticker)
                
                # 보유 기간 초기화
                self.data_manager.reset_holding_period(ticker)
                print(f"   📅 {ticker} 보유 기간 초기화 완료")
                
            except Exception as e:
                print(f"❌ {ticker} 매도 처리 오류: {e}")
        
        return {
            'sold_tickers': sold_tickers,
            'sold_count': len(sold_tickers),
            'total_profit': total_sell_profit
        }
    
    def _calculate_profit(self, ticker: str, quantity: int) -> Dict[str, Any]:
        """수익률 계산"""
        purchase_info = self.data_manager.get_purchase_info(ticker)
        current_price = self.data_fetcher.get_current_price(ticker)
        
        profit_info = {
            'profit': 0,
            'profit_rate': 0.0,
            'display': ""
        }
        
        if purchase_info and current_price:
            buy_price = purchase_info.get('buy_price', 0)
            
            if buy_price > 0:
                sell_value = quantity * current_price
                buy_value = quantity * buy_price
                profit = sell_value - buy_value
                profit_rate = (profit / buy_value) * 100
                
                profit_info = {
                    'profit': profit,
                    'profit_rate': profit_rate,
                    'display': f" | 수익률: {profit_rate:+.2f}% ({profit:+,}원)"
                }
        
        return profit_info
    
    def _send_sell_summary(self, sell_results: Dict[str, Any], initial_holdings: int) -> None:
        """매도 완료 요약 알림"""
        current_holdings = initial_holdings - sell_results['sold_count']
        
        self.notifier.notify_morning_sell_summary(
            sold_count=sell_results['sold_count'],
            total_profit=sell_results['total_profit'],
            current_holdings=current_holdings
        )
        
        if sell_results['total_profit'] != 0:
            print(f"💰 총 매도 손익: {sell_results['total_profit']:+,}원")
    
    def _log_sell_performance(self, sell_results: Dict[str, Any]) -> None:
        """성과 로깅"""
        strategy_data = self.data_manager.get_data()
        current_holdings = self.data_fetcher.get_holding_stock()
        
        self.data_manager.add_performance_log({
            'strategy_type': 'sell_only',
            'sold_count': sell_results['sold_count'],
            'sell_profit': sell_results['total_profit'],
            'current_holdings': len(current_holdings),
            'enhanced_analysis_enabled': strategy_data.get('enhanced_analysis_enabled', True),
            'stop_loss_enabled': strategy_data.get('stop_loss_enabled', True)
        })


class BuyExecutor:
    """매수 전략 실행 클래스 - 하이브리드 전략 지원 (기술적 분석 + 뉴스 감정 분석)"""
    
    def __init__(self, 
                 hybrid_strategy_enabled: bool = False,
                 news_weight: float = 0.3,
                 technical_weight: float = 0.7,
                 min_combined_score: float = 0.7,
                 debug_news: bool = True,
                 **kwargs):
        self.data_fetcher = get_data_fetcher()
        self.data_manager = get_data_manager()
        self.notifier = get_notifier()
        self.stock_selector = get_stock_selector()
        self.ht = get_hantustock()
        
        # 하이브리드 전략 설정
        self.hybrid_strategy_enabled = hybrid_strategy_enabled
        self.news_weight = news_weight
        self.technical_weight = technical_weight
        self.min_combined_score = min_combined_score
        self.debug_news = debug_news
        
        # 뉴스 분석기 (하이브리드 전략 사용 시)
        if self.hybrid_strategy_enabled:
            from ..analysis.news_sentiment import get_news_analyzer
            self.news_analyzer = get_news_analyzer(debug=debug_news)
    
    def execute(self) -> Dict[str, Any]:
        """
        오후 매수 전략 실행
        
        Returns:
            dict: 실행 결과 요약
        """
        print("🚀 오후 매수 전략 실행 시작!")
        
        # 현재 보유중인 종목 조회 (매수 전)
        holdings = self.data_fetcher.get_holding_stock()
        print(f"📊 현재 보유: {len(holdings)}개")
        
        # 종목 선정 (데이터 검증 강화)
        buy_candidates = self._select_buy_candidates(holdings)
        
        if not buy_candidates:
            print("📊 매수 대상 종목이 없습니다.")
            # 매수 대상이 없어도 슬랙 알림 전송
            buy_results = {'bought_count': 0, 'total_invested': 0}
            self._send_buy_summary(buy_results, len(holdings))
            return buy_results
        
        # 잔고 확인
        balance_info = self._check_balance()
        if not balance_info['success']:
            print("❌ 잔고 확인 실패로 매수를 진행할 수 없습니다.")
            # 잔고 확인 실패 시에도 슬랙 알림 전송
            buy_results = {'bought_count': 0, 'total_invested': 0, 'error': 'balance_check_failed'}
            self._send_buy_summary(buy_results, len(holdings))
            return buy_results
        
        # 매수 실행 (데이터 검증 강화)
        buy_results = self._execute_buys(buy_candidates, balance_info['balance'])
        
        # 요약 알림 전송
        self._send_buy_summary(buy_results, len(holdings))
        
        # 성과 로깅
        self._log_buy_performance(buy_results)
        
        # 데이터 저장
        self.data_manager.save()
        
        print("✅ 오후 매수 전략 실행 완료!")
        return buy_results
    
    def _select_buy_candidates(self, current_holdings: Dict[str, int]) -> List[Dict[str, Any]]:
        """매수 후보 종목 선정 (하이브리드 전략 + 피라미딩 지원)"""
        # 종목 선정 (백테스트 엔진 로직 적용)
        final_tickers = self.stock_selector.select_stocks_for_buy()
        
        if not final_tickers:
            print("📊 기술적 분석에서 선정된 종목이 없습니다.")
            return []
        
        print(f"📊 기술적 분석 선정: {len(final_tickers)}개 종목")
        
        # 피라미딩 전략: 보유 종목도 재평가 대상에 포함
        strategy_data = self.data_manager.get_data()
        pyramiding_enabled = strategy_data.get('pyramiding_enabled', False)
        
        if pyramiding_enabled:
            print("🔄 피라미딩 전략 활성화 - 보유 종목도 평가")
            technical_candidates = final_tickers  # 모든 종목 포함
            
            # 보유 종목 표시
            for ticker in technical_candidates:
                if ticker in current_holdings:
                    print(f"   → {ticker}: 보유 중 (피라미딩 후보)")
        else:
            # 현재 보유중인 종목은 매수 후보에서 제외
            current_holdings_set = set(current_holdings.keys())
            technical_candidates = [t for t in final_tickers if t not in current_holdings_set]
            
            if not technical_candidates:
                print("📊 이미 보유 중인 종목을 제외하면 매수 대상이 없습니다.")
                return []
        
        # 하이브리드 전략 적용
        if self.hybrid_strategy_enabled:
            print("\n📰 하이브리드 전략: 뉴스 감정 분석 추가...")
            enhanced_candidates = self._apply_hybrid_strategy(technical_candidates, current_holdings)
            
            # 슬랙 알림: 하이브리드 전략 선정 완료
            if enhanced_candidates:
                summary = self.stock_selector.get_selection_summary()
                self.notifier.notify_stock_selection(
                    analyzed_count=summary['technical_analysis_count'],
                    ai_selected_count=len(enhanced_candidates),
                    final_count=len(enhanced_candidates),
                    selected_tickers=[c['ticker'] for c in enhanced_candidates]
                )
            
            return enhanced_candidates
        else:
            # 기존 방식: 기술적 분석만
            # 슬랙 알림: 종목 선정 완료
            summary = self.stock_selector.get_selection_summary()
            self.notifier.notify_stock_selection(
                analyzed_count=summary['technical_analysis_count'],
                ai_selected_count=summary['ai_predictions_count'],
                final_count=len(technical_candidates),
                selected_tickers=technical_candidates
            )
            
            # 딕셔너리 형태로 변환 (보유 여부 포함)
            candidates = []
            for ticker in technical_candidates:
                candidates.append({
                    'ticker': ticker,
                    'is_holding': ticker in current_holdings
                })
            
            return candidates
    
    def _apply_hybrid_strategy(self, technical_candidates: List[str], current_holdings: Dict[str, int]) -> List[Dict[str, Any]]:
        """하이브리드 전략 적용: 기술적 분석 + 뉴스 감정 분석"""
        from datetime import datetime
        from pykrx import stock
        
        enhanced_candidates = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        strategy_data = self.data_manager.get_data()
        pyramiding_enabled = strategy_data.get('pyramiding_enabled', False)
        
        for ticker in technical_candidates:
            try:
                # 보유 여부 확인
                is_holding = ticker in current_holdings
                
                # 회사명 조회
                company_name = stock.get_market_ticker_name(ticker)
                if not company_name:
                    company_name = ticker
                
                print(f"\n🔍 {ticker} ({company_name}) 뉴스 분석 중..." + 
                      (" [보유중]" if is_holding else ""))
                
                # 뉴스 수집 및 분석
                news_list = self.news_analyzer.fetch_ticker_news(ticker, company_name, current_date)
                
                # 기술적 분석 점수 가져오기 (보유 기간과 진입 가격 고려)
                from ..analysis.technical import get_technical_score, get_technical_analyzer
                
                # 보유 종목인 경우 보유 기간과 진입 가격 정보를 활용
                if is_holding:
                    purchase_info = self.data_manager.get_purchase_info(ticker)
                    holding_days = self.data_manager.get_holding_period(ticker)
                    entry_price = purchase_info.get('buy_price', None) if purchase_info else None
                    
                    # 보유 기간과 진입 가격을 고려한 점수 계산
                    analyzer = get_technical_analyzer()
                    technical_score = analyzer.get_technical_score(ticker, holding_days, entry_price)
                    print(f"   📊 기술적 점수 계산 (보유 {holding_days}일): {technical_score:.3f}")
                else:
                    # 신규 매수인 경우 일반 점수 계산
                    technical_score = get_technical_score(ticker)
                    print(f"   📊 기술적 점수 실시간 계산: {technical_score:.3f}")
                
                if news_list:
                    print(f"   📰 {len(news_list)}개 뉴스 수집")
                    
                    # 감정 분석
                    news_analysis = self.news_analyzer.analyze_news_sentiment(
                        news_list, ticker, company_name
                    )
                    
                    # 보유 예정 기간(3-5일)에 맞는 예측값 사용
                    # 기존: avg_confidence만 사용 → 개선: 5일 후 예측값 우선 사용
                    news_score = news_analysis.get('prob_5', news_analysis.get('avg_confidence', 0.5))
                    news_sentiment = news_analysis.get('sentiment', '중립')
                    
                    # 디버깅: 시간별 예측값 출력
                    if self.debug_news:
                        print(f"   📈 시간별 예측: 1일 {news_analysis.get('prob_1', 0.5)*100:.1f}%, "
                              f"5일 {news_analysis.get('prob_5', 0.5)*100:.1f}%, "
                              f"10일 {news_analysis.get('prob_10', 0.5)*100:.1f}%")
                    
                    # 종합 점수 계산
                    combined_score = (
                        technical_score * self.technical_weight + 
                        news_score * self.news_weight
                    )
                    normalized_score = combined_score  # 정규화된 점수 (0~1 사이)
                    
                    print(f"   ✅ 뉴스 감정: {news_sentiment}, 5일 예측: {news_score*100:.1f}%")
                    print(f"   📊 종합 점수: {combined_score*100:.1f}% "
                          f"(기술적: {technical_score*100:.1f}%, 뉴스 5일: {news_score*100:.1f}%)")
                    
                    # 피라미딩 최소 점수 적용 (보유 종목은 더 높은 기준)
                    if is_holding and pyramiding_enabled:
                        min_score = max(self.min_combined_score, 0.75)  # 보유 종목은 75% 이상
                        print(f"   🔄 피라미딩 기준: {min_score*100:.1f}%")
                    else:
                        min_score = self.min_combined_score
                    
                    # 뉴스 감정이 부정적인 경우 매수 차단
                    if news_sentiment == '부정':
                        print(f"   ❌ 뉴스 감정이 부정적이므로 매수하지 않음 (감정: {news_sentiment}, 5일 예측: {news_score*100:.1f}%)")
                    # 최소 점수 기준 충족 확인
                    elif combined_score >= min_score:
                        enhanced_candidates.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'technical_score': technical_score,
                            'news_score': news_score,
                            'news_sentiment': news_sentiment,
                            'combined_score': combined_score,
                            'normalized_score': normalized_score,  # 정규화된 점수 추가
                            'news_analysis': news_analysis,
                            'is_holding': is_holding
                        })
                    else:
                        print(f"   ❌ 종합 점수 {combined_score*100:.1f}% < {min_score*100:.1f}% (기준 미달)")
                else:
                    print(f"   ⚠️ 뉴스 없음 - 기술적 점수만 사용")
                    # 뉴스가 없는 경우 기술적 점수만으로 평가
                    combined_score = technical_score
                    normalized_score = technical_score  # 정규화된 점수
                    
                    # 피라미딩 시 더 높은 기준 적용
                    min_score = 0.75 if (is_holding and pyramiding_enabled) else self.min_combined_score
                    
                    if combined_score >= min_score:
                        enhanced_candidates.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'technical_score': technical_score,
                            'news_score': 0.5,  # 중립값
                            'news_sentiment': '중립',
                            'combined_score': combined_score,
                            'normalized_score': normalized_score,  # 정규화된 점수 추가
                            'news_analysis': None,
                            'is_holding': is_holding
                        })
                        
            except Exception as e:
                print(f"   ❌ 뉴스 분석 오류: {e}")
                # 오류 시 기술적 점수만 사용
                combined_score = technical_score
                normalized_score = technical_score  # 정규화된 점수
                
                min_score = 0.75 if (is_holding and pyramiding_enabled) else self.min_combined_score
                
                if combined_score >= min_score:
                    enhanced_candidates.append({
                        'ticker': ticker,
                        'technical_score': technical_score,
                        'news_score': 0.5,
                        'news_sentiment': '중립',
                        'combined_score': combined_score,
                        'normalized_score': normalized_score,  # 정규화된 점수 추가
                        'news_analysis': None,
                        'is_holding': is_holding
                    })
        
        # 종합 점수 기준으로 정렬
        enhanced_candidates.sort(key=lambda x: x.get('normalized_score', x.get('combined_score', 0)), reverse=True)
        
        print(f"\n📊 하이브리드 전략 최종 선정: {len(enhanced_candidates)}개 종목")
        for i, cand in enumerate(enhanced_candidates[:5]):
            holding_status = " [보유중]" if cand.get('is_holding') else ""
            # 정규화된 점수 사용
            display_score = cand.get('normalized_score', cand.get('combined_score', 0))
            if display_score > 1.0:  # combined_score가 거래대금 기반인 경우
                display_score = cand.get('technical_score', 0)
            print(f"   {i+1}. {cand['ticker']}{holding_status}: 종합 {display_score*100:.1f}% "
                  f"(기술적 {cand['technical_score']*100:.1f}%, "
                  f"뉴스 {cand.get('news_score', 0.5)*100:.1f}%)")
        
        return enhanced_candidates
    
    def _check_balance(self) -> Dict[str, Any]:
        """계좌 잔고 확인"""
        try:
            current_balance = self.data_fetcher.get_holding_cash()
            print(f"💰 현재 계좌 잔고: {current_balance:,}원")
            return {'success': True, 'balance': current_balance}
        except Exception as e:
            print(f"❌ 계좌 잔고 조회 실패: {e}")
            self.notifier.notify_balance_check_failure(str(e))
            return {'success': False, 'balance': 0}
    
    def _execute_buys(self, buy_candidates: List[Any], current_balance: float) -> Dict[str, Any]:
        """매수 실행 - 백테스트 엔진 로직 완전 적용 (하이브리드 전략 지원)"""
        bought_tickers = []
        total_invested = 0
        confidence_stats = {}
        max_positions = 10  # 최대 보유 종목 수
        
        strategy_data = self.data_manager.get_data()
        
        print(f"📊 매수 실행 시작 - 후보: {len(buy_candidates)}개")
        
        # 현재 보유 종목 수 확인
        current_holdings = self.data_fetcher.get_holding_stock()
        current_positions = len(current_holdings)
        available_slots = max_positions - current_positions
        
        print(f"   현재 보유: {current_positions}개")
        print(f"   매수 가능: {available_slots}개")
        
        if available_slots <= 0:
            print(f"📊 포트폴리오 한계 도달 (현재 {current_positions}개 보유)")
            return {'bought_count': 0, 'total_invested': 0}
        
        # 🔧 데이터 검증된 후보만 필터링 (백테스트 엔진 기능)
        validated_candidates = []
        for candidate in buy_candidates:
            # 하이브리드 전략인 경우 딕셔너리, 아닌 경우 문자열
            ticker = candidate['ticker'] if isinstance(candidate, dict) else candidate
            
            if validate_ticker_data(ticker):
                validated_candidates.append(candidate)
            else:
                print(f"   ❌ {ticker}: 데이터 검증 실패 - 매수 후보에서 제외")
        
        print(f"   ✅ 검증 통과: {len(validated_candidates)}개 종목")
        
        # 종목당 투자 금액 계산 (현금의 80%를 사용 가능한 슬롯으로 나누기)
        available_cash = current_balance * 0.8
        investment_per_stock = available_cash / available_slots if available_slots > 0 else 0
        
        print(f"   사용 가능 현금: {available_cash:,.0f}원")
        print(f"   종목당 기본 투자: {investment_per_stock:,.0f}원")
        
        for candidate in validated_candidates[:available_slots]:
            try:
                # 티커 추출 및 보유 여부 확인
                ticker = candidate['ticker'] if isinstance(candidate, dict) else candidate
                is_holding = candidate.get('is_holding', False) if isinstance(candidate, dict) else False
                
                # 피라미딩 체크
                strategy_data = self.data_manager.get_data()
                pyramiding_enabled = strategy_data.get('pyramiding_enabled', False)
                
                if is_holding and pyramiding_enabled:
                    # 보유 종목의 현재 포지션 확인
                    current_quantity = current_holdings.get(ticker, 0)
                    purchase_info = self.data_manager.get_purchase_info(ticker)
                    if purchase_info:
                        current_avg_price = purchase_info.get('buy_price', 0)
                        current_position_value = current_quantity * current_avg_price
                        
                        # 최대 포지션 크기 체크 (전체 자산의 30%)
                        max_position_ratio = strategy_data.get('pyramiding_max_position', 0.3)
                        max_position_value = (current_balance + total_invested) * max_position_ratio
                        
                        if current_position_value >= max_position_value:
                            print(f"   ⚠️ {ticker}: 최대 포지션 도달 ({current_position_value:,.0f}원 / {max_position_value:,.0f}원)")
                            continue
                        
                        print(f"   🔄 {ticker} 피라미딩 매수 검토:")
                        print(f"      현재 보유: {current_quantity:,}주 @ {current_avg_price:,.0f}원")
                        print(f"      현재 포지션: {current_position_value:,.0f}원")
                        print(f"      최대 포지션: {max_position_value:,.0f}원 (전체 자산의 {max_position_ratio*100:.0f}%)")
                        
                        # 리셋 횟수 확인
                        reset_count = purchase_info.get('reset_count', 0)
                        max_resets = strategy_data.get('pyramiding_max_resets', 2)
                        print(f"      리셋 횟수: {reset_count}/{max_resets}회")
                
                # AI 점수 및 투자 금액 결정
                investment_info = self._determine_investment_amount(ticker, strategy_data, candidate)
                
                # 피라미딩인 경우 투자 금액 조정 (설정에서 비율 가져오기)
                if is_holding and pyramiding_enabled:
                    pyramiding_ratio = strategy_data.get('pyramiding_investment_ratio', 0.5)
                    investment_info['amount'] = int(investment_info['amount'] * pyramiding_ratio)
                    print(f"   🔄 피라미딩 투자금액: {investment_info['amount']:,}원 ({pyramiding_ratio*100:.0f}% 적용)")
                
                # 투자 가능 금액 확인
                remaining_balance = current_balance - total_invested - 2_000_000  # 200만원 안전자금
                
                print(f"💹 {ticker} 투자 계산:")
                print(f"   💰 계좌 잔고: {current_balance:,}원")
                print(f"   📊 기투자액: {total_invested:,}원") 
                print(f"   🛡️ 안전자금: 2,000,000원")
                print(f"   💵 투자가능: {remaining_balance:,}원")
                print(f"   🎯 계획투자: {investment_info['amount']:,}원")
                
                if investment_info.get('is_hybrid'):
                    print(f"   🤝 하이브리드 점수: {investment_info['ai_score']:.3f} ({investment_info['confidence_level']})")
                    print(f"      - 기술적: {investment_info['technical_score']:.3f}")
                    print(f"      - 뉴스: {investment_info['news_score']:.3f} ({investment_info['news_sentiment']})")
                else:
                    print(f"   🤖 AI점수: {investment_info['ai_score']:.3f} ({investment_info['confidence_level']})")
                
                if remaining_balance <= 0:
                    print(f"⚠️ {ticker}: 투자 가능 금액 부족 (잔액: {remaining_balance:,}원)")
                    continue
                
                if remaining_balance < investment_info['amount']:
                    if remaining_balance < 300_000:  # 최소 투자금액
                        print(f"⚠️ {ticker}: 최소 투자금액 부족 (가능: {remaining_balance:,}원 < 최소: 300,000원)")
                        continue
                    print(f"   📉 투자금액 조정: {investment_info['amount']:,}원 → {remaining_balance:,}원")
                    investment_info['amount'] = remaining_balance
                
                # 🔧 현재가 재검증 (매수 직전) - 백테스트 엔진 기능
                current_price = self.data_fetcher.get_current_price(ticker)
                if not current_price or current_price <= 0:
                    print(f"❌ {ticker}: 매수 직전 현재가 조회 실패")
                    continue
                
                print(f"   📈 현재가: {current_price:,}원")
                
                # 투자금액이 현재가보다 작으면 현재가의 1.2배로 조정
                if investment_info['amount'] < current_price:
                    adjusted_amount = int(current_price * 1.2)
                    if remaining_balance >= adjusted_amount:
                        print(f"   🔧 투자금액 자동 조정: {investment_info['amount']:,}원 → {adjusted_amount:,}원 (현재가 × 1.2)")
                        investment_info['amount'] = adjusted_amount
                    else:
                        print(f"⚠️ {ticker}: 현재가({current_price:,}원)보다 투자금액({investment_info['amount']:,}원)이 작아 매수 불가")
                        continue
                
                quantity_to_buy = int(investment_info['amount'] // current_price)
                print(f"   📦 매수수량: {quantity_to_buy:,}주")
                
                if quantity_to_buy <= 0:
                    print(f"⚠️ {ticker}: 매수 수량 0주 (투자금액: {investment_info['amount']:,}원, 현재가: {current_price:,}원)")
                    continue
                
                actual_investment = quantity_to_buy * current_price
                print(f"   💸 실제투자: {actual_investment:,}원")
                
                if self.hybrid_strategy_enabled:
                    print(f"📥 {ticker} 하이브리드 전략 기반 매수 실행:")
                else:
                    print(f"📥 {ticker} AI 신뢰도 기반 매수 실행:")
                print(f"   수량: {quantity_to_buy:,}주")
                print(f"   단가: {current_price:,}원")
                print(f"   투자금액: {actual_investment:,}원")
                
                # 매수 주문 실행
                order_id, actual_quantity = self.ht.bid(ticker, 'market', quantity_to_buy, 'STOCK')
                
                if order_id:
                    bought_tickers.append({
                        'ticker': ticker,
                        'quantity': actual_quantity,
                        'investment': actual_investment,
                        'ai_score': investment_info['ai_score'],
                        'confidence_level': investment_info['confidence_level']
                    })
                    total_invested += actual_investment
                    
                    # 신뢰도별 통계 업데이트
                    level = investment_info['confidence_level']
                    if level not in confidence_stats:
                        confidence_stats[level] = {'count': 0, 'amount': 0}
                    confidence_stats[level]['count'] += 1
                    confidence_stats[level]['amount'] += actual_investment
                    
                    # 매수 정보 저장 (피라미딩 고려)
                    if is_holding and pyramiding_enabled:
                        # 기존 매수 정보 업데이트
                        existing_info = self.data_manager.get_purchase_info(ticker)
                        if existing_info:
                            # 평균 단가 계산
                            existing_quantity = existing_info.get('quantity', 0)
                            existing_price = existing_info.get('buy_price', 0)

                            # 새로운 매수 수량과 현재 가격
                            total_quantity = existing_quantity + actual_quantity  # 총 수량
                            new_avg_price = ((existing_quantity * existing_price) + (
                                        actual_quantity * current_price)) / total_quantity  # 새로운 평균 단가 계산

                            print(f"   📥 {ticker} 피라미딩 매수: {actual_quantity:,}주 @ {current_price:,}원")
                            print(f"      총 보유: {existing_quantity + actual_quantity:,}주, 평균단가: {new_avg_price:,.0f}원")
                            
                            purchase_info = {
                                'buy_price': new_avg_price,
                                'quantity': existing_quantity + actual_quantity,
                                'investment': existing_info.get('investment', 0) + actual_investment,
                                'buy_date': existing_info.get('buy_date'),  # 최초 매수일 유지
                                'last_buy_date': datetime.now().isoformat(),  # 최근 매수일
                                'ai_score': investment_info['ai_score'],
                                'confidence_level': investment_info['confidence_level'],
                                'is_pyramiding': True,
                                'pyramiding_count': existing_info.get('pyramiding_count', 0) + 1,
                                'reset_count': existing_info.get('reset_count', 0)  # 리셋 횟수 유지
                            }
                            
                            # 보유 기간 리셋 여부 (점수가 80% 이상일 때)
                            reset_threshold = strategy_data.get('pyramiding_reset_threshold', 0.80)
                            reset_holding = investment_info['ai_score'] >= reset_threshold
                            
                            if reset_holding:
                                # 현재 보유 기간 확인
                                old_holding_days = self.data_manager.get_holding_period(ticker)
                                print(f"   🔄 높은 점수({investment_info['ai_score']*100:.1f}%)로 보유기간 리셋")
                                print(f"      🔄 {ticker} 보유기간 리셋 (현재 보유일: {old_holding_days}일 → 1일)")
                                
                                # 리셋 정보 업데이트
                                purchase_info['reset_count'] = purchase_info.get('reset_count', 0) + 1
                                purchase_info['reset_date'] = datetime.now().isoformat()
                                
                                # 보유 기간 리셋 (1일로 설정)
                                self.data_manager.reset_holding_period(ticker)
                                self.data_manager.set_holding_period(ticker, 1)
                            else:
                                print(f"   📊 점수({investment_info['ai_score']*100:.1f}%)가 리셋 기준({reset_threshold*100:.0f}%) 미달")
                    else:
                        # 신규 매수
                        purchase_info = {
                            'buy_price': current_price,
                            'quantity': actual_quantity,
                            'investment': actual_investment,
                            'buy_date': datetime.now().isoformat(),
                            'ai_score': investment_info['ai_score'],
                            'confidence_level': investment_info['confidence_level'],
                            'reset_count': 0  # 리셋 횟수 초기화
                        }
                    
                    # 하이브리드 전략 정보 추가
                    if investment_info.get('is_hybrid'):
                        purchase_info.update({
                            'is_hybrid': True,
                            'technical_score': investment_info.get('technical_score'),
                            'news_score': investment_info.get('news_score'),
                            'news_sentiment': investment_info.get('news_sentiment'),
                            # 시간별 예측값 추가 저장
                            'news_prob_1': candidate.get('news_analysis', {}).get('prob_1') if isinstance(candidate, dict) else None,
                            'news_prob_5': candidate.get('news_analysis', {}).get('prob_5') if isinstance(candidate, dict) else None,
                            'news_prob_10': candidate.get('news_analysis', {}).get('prob_10') if isinstance(candidate, dict) else None,
                            # news_signal 정보 저장 (백테스트 엔진과 동일)
                            'news_signal': {
                                'holding_days': candidate.get('news_analysis', {}).get('optimal_holding_days', 5) if isinstance(candidate, dict) else 5,  # 최적화된 값 사용
                                'predictions': {
                                    '1d': candidate.get('news_analysis', {}).get('prob_1', 0.5),
                                    '5d': candidate.get('news_analysis', {}).get('prob_5', 0.5),
                                    '10d': candidate.get('news_analysis', {}).get('prob_10', 0.5),
                                    '20d': candidate.get('news_analysis', {}).get('prob_20', 0.5)
                                } if isinstance(candidate, dict) else {}
                            }
                        })
                    
                    self.data_manager.set_purchase_info(ticker, purchase_info)
                    
                    # 슬랙 알림: 매수 체결
                    self.notifier.notify_buy_execution(
                        ticker=ticker,
                        quantity=actual_quantity,
                        investment=actual_investment,
                        current_price=current_price,
                        ai_score=investment_info['ai_score'],
                        confidence_level=investment_info['confidence_level']
                    )
                    
                    print(f"✅ {ticker} 매수 완료")
                    if self.hybrid_strategy_enabled:
                        print(f"   🤝 하이브리드: 기술적({investment_info.get('technical_score', 0)*100:.1f}%) + 뉴스({investment_info.get('news_score', 0)*100:.1f}%)")
                else:
                    print(f"❌ {ticker} 매수 주문 실패")
                    
            except Exception as e:
                print(f"❌ {ticker} 매수 처리 오류: {e}")
        
        return {
            'bought_tickers': bought_tickers,
            'bought_count': len(bought_tickers),
            'total_invested': total_invested,
            'confidence_stats': confidence_stats
        }
    
    def _determine_investment_amount(self, ticker: str, strategy_data: Dict[str, Any], 
                                    candidate: Any = None) -> Dict[str, Any]:
        """투자 금액 결정 (하이브리드 전략 지원)"""
        # 하이브리드 전략인 경우
        if self.hybrid_strategy_enabled and isinstance(candidate, dict) and 'combined_score' in candidate:
            # normalized_score가 있으면 사용, 없으면 combined_score 사용
            score = candidate.get('normalized_score', candidate.get('combined_score', 0))
            
            # combined_score가 거래대금 기반인 경우 (매우 큰 값) technical_score 사용
            if score > 1.0:
                score = candidate.get('technical_score', 0.7)
            
            # 종합 점수 기반 투자 금액 계산
            if score >= 0.80:           # 최고신뢰: 80만원
                investment_amount = 800_000    
                confidence_level = "최고신뢰"
            elif score >= 0.70:         # 고신뢰: 60만원
                investment_amount = 600_000    
                confidence_level = "고신뢰"
            elif score >= 0.65:         # 중신뢰: 40만원
                investment_amount = 400_000    
                confidence_level = "중신뢰"
            else:                       # 저신뢰: 30만원
                investment_amount = 300_000      
                confidence_level = "저신뢰"
            
            return {
                'amount': investment_amount,
                'ai_score': score,
                'confidence_level': confidence_level,
                'is_hybrid': True,
                'technical_score': candidate.get('technical_score', 0.7),
                'news_score': candidate.get('news_score', 0.5),
                'news_sentiment': candidate.get('news_sentiment', '중립')
            }
        else:
            # 기존 방식: 기술적 분석 점수 사용 (보유 기간 고려)
            from ..analysis.technical import get_technical_score, get_technical_analyzer
            
            # 보유 종목인지 확인
            current_holdings = self.data_fetcher.get_holding_stock()
            is_holding = ticker in current_holdings
            
            if is_holding:
                # 보유 종목인 경우 보유 기간과 진입 가격 고려
                purchase_info = self.data_manager.get_purchase_info(ticker)
                holding_days = self.data_manager.get_holding_period(ticker)
                entry_price = purchase_info.get('buy_price', None) if purchase_info else None
                
                analyzer = get_technical_analyzer()
                ai_score = analyzer.get_technical_score(ticker, holding_days, entry_price)
                print(f"      📊 보유 종목 기술점수 (보유 {holding_days}일): {ai_score:.3f}")
            else:
                # 신규 매수인 경우
                ai_score = get_technical_score(ticker)
            
            # 강화된 AI 신뢰도 기반 투자 금액 계산 (백테스트 엔진과 일관성 맞춤)
            if ai_score >= 0.80:           # 최고신뢰: 80만원
                investment_amount = 800_000    
                confidence_level = "최고신뢰"
            elif ai_score >= 0.70:         # 고신뢰: 60만원
                investment_amount = 600_000    
                confidence_level = "고신뢰"
            elif ai_score >= 0.65:         # 중신뢰: 40만원
                investment_amount = 400_000    
                confidence_level = "중신뢰"
            else:                          # 저신뢰: 30만원
                investment_amount = 300_000      
                confidence_level = "저신뢰"
            
            return {
                'amount': investment_amount,
                'ai_score': ai_score,
                'confidence_level': confidence_level,
                'is_hybrid': False
            }
    
    def _send_buy_summary(self, buy_results: Dict[str, Any], initial_holdings: int) -> None:
        """매수 완료 요약 알림"""
        current_holdings = initial_holdings + buy_results['bought_count']
        
        self.notifier.notify_evening_buy_summary(
            bought_count=buy_results['bought_count'],
            total_invested=buy_results['total_invested'],
            current_holdings=current_holdings,
            confidence_stats=buy_results.get('confidence_stats')
        )
        
        if self.hybrid_strategy_enabled:
            print(f"\n💼 하이브리드 전략 기반 매수 완료:")
        else:
            print(f"\n💼 AI 신뢰도 기반 매수 완료:")
        print(f"   매수 종목 수: {buy_results['bought_count']}개")
        print(f"   총 투자금액: {buy_results['total_invested']:,}원")
    
    def _log_buy_performance(self, buy_results: Dict[str, Any]) -> None:
        """성과 로깅"""
        strategy_data = self.data_manager.get_data()
        current_holdings = self.data_fetcher.get_holding_stock()
        
        self.data_manager.add_performance_log({
            'strategy_type': 'buy_only',
            'bought_count': buy_results['bought_count'],
            'total_invested': buy_results['total_invested'],
            'current_holdings': len(current_holdings),
            'enhanced_analysis_enabled': strategy_data.get('enhanced_analysis_enabled', True),
            'ai_confidence_strategy': True,
            'data_validation_enhanced': True,
            'hybrid_strategy_enabled': self.hybrid_strategy_enabled
        })


# 편의 함수들
def execute_sell_strategy() -> Dict[str, Any]:
    """매도 전략 실행"""
    executor = SellExecutor()
    return executor.execute()

def execute_buy_strategy() -> Dict[str, Any]:
    """매수 전략 실행"""
    executor = BuyExecutor()
    return executor.execute()
