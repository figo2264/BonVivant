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
        """매도 후보 종목 결정 - 백테스트 엔진 로직 완전 적용"""
        tickers_to_sell = []
        strategy_data = self.data_manager.get_data()
        enhanced_analysis_enabled = strategy_data.get('enhanced_analysis_enabled', True)
        
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
            
            # 🔧 2. 손실 제한 체크 (우선순위 최고)
            stop_loss_sell, current_price, loss_rate = self.check_stop_loss(ticker, holdings[ticker])
            if stop_loss_sell:
                should_sell = True
                sell_reason = f"손실제한 (손실률: {loss_rate*100:.1f}%)"
                print(f"   🛑 {ticker}: 손실 제한 매도 - 손실률 {loss_rate*100:.1f}%")
            
            # 3. 기본 3일 룰 (손실 제한이 아닌 경우만)
            elif holding_days >= 3:
                should_sell = True
                sell_reason = f"보유기간 ({holding_days}일)"
                print(f"   → {ticker}: 3일 이상 보유로 매도 검토")
                
                # 기술적 홀드 시그널 체크 (3일차에만, 손실이 없는 경우만)
                if holding_days == 3 and enhanced_analysis_enabled and loss_rate > -0.02:  # 2% 이상 손실이 아닌 경우만
                    try:
                        hold_signal = get_technical_hold_signal(ticker)
                        
                        if hold_signal >= 0.75:
                            should_sell = False
                            sell_reason = ""
                            print(f"   → {ticker}: 기술적 분석 강홀드 신호로 1일 연장 (신호강도: {hold_signal:.3f})")
                        elif hold_signal <= 0.25:
                            print(f"   ⚠️ {ticker}: 기술적 분석 매도 신호 (신호강도: {hold_signal:.3f})")
                    except Exception as e:
                        print(f"   → {ticker}: 홀드 시그널 계산 오류: {e}")
            
            # 4. 안전장치: 5일 이상은 무조건 매도
            if holding_days >= 5:
                should_sell = True
                sell_reason = f"5일 안전룰"
                print(f"   → {ticker}: 5일 안전룰 적용")
            
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
                 min_combined_score: float = 0.6,
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
            return {'bought_count': 0, 'total_invested': 0}
        
        # 잔고 확인
        balance_info = self._check_balance()
        if not balance_info['success']:
            return {'bought_count': 0, 'total_invested': 0, 'error': 'balance_check_failed'}
        
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
        """매수 후보 종목 선정 (하이브리드 전략 지원)"""
        # 종목 선정 (백테스트 엔진 로직 적용)
        final_tickers = self.stock_selector.select_stocks_for_buy()
        
        if not final_tickers:
            print("📊 기술적 분석에서 선정된 종목이 없습니다.")
            return []
        
        print(f"📊 기술적 분석 선정: {len(final_tickers)}개 종목")
        
        # 현재 보유중인 종목은 매수 후보에서 제외
        current_holdings_set = set(current_holdings.keys())
        technical_candidates = [t for t in final_tickers if t not in current_holdings_set]
        
        if not technical_candidates:
            print("📊 이미 보유 중인 종목을 제외하면 매수 대상이 없습니다.")
            return []
        
        # 하이브리드 전략 적용
        if self.hybrid_strategy_enabled:
            print("\n📰 하이브리드 전략: 뉴스 감정 분석 추가...")
            enhanced_candidates = self._apply_hybrid_strategy(technical_candidates)
            
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
            
            # 딕셔너리 형태로 변환
            return [{'ticker': t} for t in technical_candidates]
    
    def _apply_hybrid_strategy(self, technical_candidates: List[str]) -> List[Dict[str, Any]]:
        """하이브리드 전략 적용: 기술적 분석 + 뉴스 감정 분석"""
        from datetime import datetime
        from pykrx import stock
        
        enhanced_candidates = []
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        for ticker in technical_candidates:
            try:
                # 회사명 조회
                company_name = stock.get_market_ticker_name(ticker)
                if not company_name:
                    company_name = ticker
                
                print(f"\n🔍 {ticker} ({company_name}) 뉴스 분석 중...")
                
                # 뉴스 수집 및 분석
                news_list = self.news_analyzer.fetch_ticker_news(ticker, company_name, current_date)
                
                # AI 점수 가져오기 (기술적 분석에서의 점수)
                strategy_data = self.data_manager.get_data()
                ai_predictions = strategy_data.get('ai_predictions', {})
                technical_score = ai_predictions.get(ticker, {}).get('score', 0.7)
                
                if news_list:
                    print(f"   📰 {len(news_list)}개 뉴스 수집")
                    
                    # 감정 분석
                    news_analysis = self.news_analyzer.analyze_news_sentiment(
                        news_list, ticker, company_name
                    )
                    
                    news_score = news_analysis.get('avg_confidence', 0.5)
                    news_sentiment = news_analysis.get('sentiment', '중립')
                    
                    # 종합 점수 계산
                    combined_score = (
                        technical_score * self.technical_weight + 
                        news_score * self.news_weight
                    )
                    
                    print(f"   ✅ 뉴스 감정: {news_sentiment}, 신뢰도: {news_score*100:.1f}%")
                    print(f"   📊 종합 점수: {combined_score*100:.1f}% "
                          f"(기술적: {technical_score*100:.1f}%, 뉴스: {news_score*100:.1f}%)")
                    
                    # 최소 점수 기준 충족 확인
                    if combined_score >= self.min_combined_score:
                        enhanced_candidates.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'technical_score': technical_score,
                            'news_score': news_score,
                            'news_sentiment': news_sentiment,
                            'combined_score': combined_score,
                            'news_analysis': news_analysis
                        })
                    else:
                        print(f"   ❌ 종합 점수 {combined_score*100:.1f}% < {self.min_combined_score*100:.1f}% (기준 미달)")
                else:
                    print(f"   ⚠️ 뉴스 없음 - 기술적 점수만 사용")
                    # 뉴스가 없는 경우 기술적 점수만으로 평가
                    combined_score = technical_score
                    
                    if combined_score >= self.min_combined_score:
                        enhanced_candidates.append({
                            'ticker': ticker,
                            'company_name': company_name,
                            'technical_score': technical_score,
                            'news_score': 0.5,  # 중립값
                            'news_sentiment': '중립',
                            'combined_score': combined_score,
                            'news_analysis': None
                        })
                        
            except Exception as e:
                print(f"   ❌ 뉴스 분석 오류: {e}")
                # 오류 시 기술적 점수만 사용
                combined_score = technical_score
                
                if combined_score >= self.min_combined_score:
                    enhanced_candidates.append({
                        'ticker': ticker,
                        'technical_score': technical_score,
                        'news_score': 0.5,
                        'news_sentiment': '중립',
                        'combined_score': combined_score,
                        'news_analysis': None
                    })
        
        # 종합 점수 기준으로 정렬
        enhanced_candidates.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        
        print(f"\n📊 하이브리드 전략 최종 선정: {len(enhanced_candidates)}개 종목")
        for i, cand in enumerate(enhanced_candidates[:5]):
            print(f"   {i+1}. {cand['ticker']}: 종합 {cand.get('combined_score', 0)*100:.1f}% "
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
                # 티커 추출
                ticker = candidate['ticker'] if isinstance(candidate, dict) else candidate
                
                # AI 점수 및 투자 금액 결정
                investment_info = self._determine_investment_amount(ticker, strategy_data, candidate)
                
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
                    
                    # 매수 정보 저장
                    purchase_info = {
                        'buy_price': current_price,
                        'quantity': actual_quantity,
                        'investment': actual_investment,
                        'buy_date': datetime.now().isoformat(),
                        'ai_score': investment_info['ai_score'],
                        'confidence_level': investment_info['confidence_level']
                    }
                    
                    # 하이브리드 전략 정보 추가
                    if investment_info.get('is_hybrid'):
                        purchase_info.update({
                            'is_hybrid': True,
                            'technical_score': investment_info.get('technical_score'),
                            'news_score': investment_info.get('news_score'),
                            'news_sentiment': investment_info.get('news_sentiment')
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
            score = candidate['combined_score']
            
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
            
            # 뉴스 감정이 부정적인 경우 추가 감소
            if candidate.get('news_sentiment') == '부정':
                investment_amount = int(investment_amount * 0.7)
                confidence_level += " (뉴스 부정)"
            
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
            # 기존 방식: AI 점수만 사용
            ai_score = strategy_data.get('ai_predictions', {}).get(ticker, {}).get('score', 0.5)
            
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
