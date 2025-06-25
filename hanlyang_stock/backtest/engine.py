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
from ..analysis.technical import get_technical_analyzer
from ..strategy.selector import get_stock_selector
from ..strategy.news_based_selector import get_news_based_selector


class BacktestEngine:
    """모듈화된 백테스트 엔진 - hanlyang_stock 모듈 활용"""

    def __init__(self, initial_capital: float = 10_000_000, transaction_cost: float = 0.003, debug: bool = False):
        """
        백테스트 엔진 초기화
        
        Args:
            initial_capital: 초기 자본금 (기본 1000만원)
            transaction_cost: 거래 비용 (기본 0.3%)
            debug: 디버그 모드
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.debug = debug

        # 모듈 인스턴스들
        self.portfolio = Portfolio(initial_capital, transaction_cost)
        self.data_fetcher = get_data_fetcher()
        self.technical_analyzer = get_technical_analyzer()
        self.stock_selector = get_stock_selector()
        self.news_selector = get_news_based_selector(debug=debug)  # 뉴스 기반 선택기 추가
        self.data_validator = get_data_validator()
        self.performance_analyzer = get_performance_analyzer()

        # 백테스트 모드 활성화
        self.stock_selector.set_backtest_mode(True)

        # 백테스트 설정
        self.news_analysis_enabled = False  # 뉴스 분석 기능 비활성화 (기본값)
        self.use_news_strategy = False  # 뉴스 전략 사용 여부

        print(f"🚀 모듈화된 백테스트 엔진 초기화 완료")
        print(f"   초기 자본: {initial_capital:,}원")
        print(f"   거래 비용: {transaction_cost * 100:.1f}%")
        if debug:
            print(f"   디버그 모드: 활성화")

    def run_backtest(self, start_date: str, end_date: str, news_analysis_enabled: bool = False,
                     use_news_strategy: bool = False) -> Dict[str, Any]:
        """
        백테스팅 실행 (모듈화된 버전)
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            news_analysis_enabled: 뉴스 분석 기능 활성화 여부 (하이브리드 전략을 위해 필요)
            use_news_strategy: 뉴스 전략 사용 여부
            
        Returns:
            Dict: 백테스트 결과
        """
        print(f"🚀 백테스팅 시작: {start_date} ~ {end_date}")

        # 전략 설정
        self.use_news_strategy = use_news_strategy

        if use_news_strategy:
            print(f"📰 하이브리드 전략 사용 (기술적 분석 + 뉴스 감정 분석)")
        else:
            print(f"📊 기술적 분석 전략만 사용")

        print("=" * 60)

        # 뉴스 분석 기능 설정
        self.news_analysis_enabled = news_analysis_enabled

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

            # 1. 매도 전략 실행
            sell_results = self._execute_sell_strategy(date_str)

            # 3. 매수 전략 실행
            buy_results = self._execute_buy_strategy(date_str)

            # 4. 포트폴리오 가치 계산 및 기록
            self._record_daily_portfolio(date_str, sell_results, buy_results)

        # 최종 성과 계산
        return self._finalize_backtest()

    def _execute_sell_strategy(self, current_date: str) -> Dict[str, Any]:
        """매도 전략 실행"""
        current_holdings = self.portfolio.get_current_holdings()

        if not current_holdings:
            return {'sold_count': 0, 'total_profit': 0}

        print(f"🔍 매도 후보 검토: {len(current_holdings)}개 보유 중")

        sold_count = 0
        total_profit = 0

        for ticker, holding in current_holdings.items():
            # 실제 보유 기간 계산 (날짜 차이)
            buy_date_str = holding.get('buy_date', current_date)
            buy_date = pd.to_datetime(buy_date_str)
            current_date_pd = pd.to_datetime(current_date)
            holding_days = (current_date_pd - buy_date).days
            
            should_sell = False
            sell_reason = ""

            # 데이터 검증
            if not self.data_validator.validate_ticker_data(ticker, current_date):
                print(f"   ❌ {ticker}: 데이터 검증 실패 - 매도 스킵")
                continue

            # 1. 손실 제한 체크 (최우선) - 3%로 변경
            buy_price = holding.get('buy_price', 0)
            stop_loss_sell, current_price, loss_rate = self.data_validator.check_stop_loss(
                ticker, buy_price, current_date, stop_loss_rate=-0.03
            )

            if stop_loss_sell:
                should_sell = True
                sell_reason = f"손실 제한 매도 - 손실률 {loss_rate * 100:.1f}%"
                print(f"   🛑 {ticker}: 손실 제한 매도 - 손실률 {loss_rate * 100:.1f}%")

            # 2. 전략별 목표 기간 체크 (손실제한이 아닌 경우만)
            elif self.use_news_strategy:
                # 뉴스 전략인 경우
                news_signal = holding.get('additional_info', {}).get('news_signal', {})
                planned_holding_days = news_signal.get('holding_days', 5)

                # 리셋 횟수 확인
                reset_count = holding.get('additional_info', {}).get('reset_count', 0)
                max_resets = 2  # 최대 2번까지만 리셋 허용

                if holding_days >= planned_holding_days:
                    if reset_count >= max_resets:
                        should_sell = True
                        sell_reason = f"최대 리셋 횟수({max_resets}회) 도달"
                        print(f"   → {ticker}: 최대 리셋 횟수 도달로 매도 ({holding_days}일 보유)")
                    else:
                        should_sell = True
                        sell_reason = f"뉴스 전략 목표 기간({planned_holding_days}일) 달성"
                        print(f"   → {ticker}: 뉴스 전략 목표 기간 달성으로 매도 ({holding_days}일 보유)")
            else:
                # 기본 전략인 경우 (3일 룰)
                if holding_days >= 3:
                    should_sell = True
                    sell_reason = f"기본 보유기간(3일) 달성"
                    print(f"   → {ticker}: 3일 이상 보유로 매도 ({holding_days}일 보유)")

            # 3. 최대 보유기간 체크 (전략별 차별화)
            if not should_sell:  # 아직 매도 결정이 안 된 경우만
                max_holding_days = 10 if self.use_news_strategy else 5
                if holding_days >= max_holding_days:
                    should_sell = True
                    sell_reason = f"최대 보유기간({max_holding_days}일) 도달"
                    print(f"   → {ticker}: 최대 보유기간 도달로 매도 ({holding_days}일 보유)")

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
        """매수 전략 실행 (피라미딩 지원)"""
        # 현재 보유 종목 수 확인
        current_holdings = self.portfolio.get_current_holdings()

        # 설정에서 max_positions 가져오기
        from ..utils.storage import get_data_manager
        data_manager = get_data_manager()
        strategy_data = data_manager.get_data()
        backtest_params = strategy_data.get('backtest_params', {})
        max_positions = backtest_params.get('max_positions', 7)  # 설정값 사용, 기본값 7

        available_slots = max_positions - len(current_holdings)

        # 피라미딩을 고려한 매수 가능 여부 체크
        # 보유 종목이 7개여도 피라미딩은 가능
        if available_slots <= 0 and not current_holdings:
            print(f"📊 포트폴리오 한계 도달 (현재 {len(current_holdings)}개 보유)")
            return {'bought_count': 0, 'total_invested': 0}

        print(f"📊 매수 전략 실행 - 보유: {len(current_holdings)}개, 신규 가능: {available_slots}개")

        # 종목 선정 (신규 후보)
        candidates = self._select_buy_candidates(current_date)

        # 보유 종목도 재평가해서 피라미딩 후보로 추가
        if current_holdings and self.use_news_strategy:
            print("🔄 보유 종목 피라미딩 평가...")

            for ticker, holding in current_holdings.items():
                try:
                    # 회사명 조회
                    company_name = self.news_selector._get_company_name(ticker)

                    # 보유 기간 계산
                    buy_date_str = holding.get('buy_date', current_date)
                    buy_date = pd.to_datetime(buy_date_str)
                    current_date_pd = pd.to_datetime(current_date)
                    holding_days = (current_date_pd - buy_date).days
                    
                    entry_price = holding.get('buy_price', None)

                    # 기술적 점수 재계산 (보유 기간과 진입 가격 고려)
                    from ..analysis.technical import get_technical_analyzer
                    analyzer = get_technical_analyzer()
                    technical_score = analyzer.get_technical_score(ticker, holding_days, entry_price)

                    print(f"   → {ticker}: 기술점수 재계산 {technical_score * 100:.1f}% (보유 {holding_days}일)")

                    # 뉴스 분석
                    from ..analysis.news_sentiment import get_news_analyzer
                    news_analyzer = get_news_analyzer(debug=self.debug)

                    news_list = news_analyzer.fetch_ticker_news(ticker, company_name, current_date)
                    if news_list:
                        news_analysis = news_analyzer.analyze_news_sentiment(
                            news_list, ticker, company_name
                        )

                        news_score = news_analysis.get('avg_confidence', 0.5)
                        news_sentiment = news_analysis.get('sentiment', '중립')

                        # 부정적 감정이면 스킵
                        if news_sentiment == '부정':
                            continue

                        # 종합 점수 계산 (기술적 점수 70% + 뉴스 점수 30%)
                        technical_weight = 0.7
                        news_weight = 0.3
                        combined_score = (
                                technical_score * technical_weight +
                                news_score * news_weight
                        )

                        # 피라미딩 후보로 추가
                        if combined_score >= 0.75:  # 피라미딩 최소 점수
                            print(f"   → {ticker}: 피라미딩 후보 추가 (하이브리드 점수: {combined_score * 100:.1f}%)")
                            candidates.append({
                                'ticker': ticker,
                                'technical_score': technical_score,
                                'news_score': news_score,
                                'news_sentiment': news_sentiment,
                                'combined_score': combined_score,
                                'normalized_score': combined_score,  # 정규화된 점수 추가
                                'hybrid_score': combined_score,  # 명확한 명칭 추가
                                'is_holding': True,
                                'holding_days': holding_days,
                                'news_signal': {
                                    'ticker': ticker,
                                    'company_name': company_name,
                                    'sentiment': news_sentiment,
                                    'confidence': news_score,
                                    'holding_days': self.news_selector.optimal_holding_days,
                                    'predictions': {
                                        f'{d}d': news_analysis.get(f'prob_{d}', 0.5)
                                        for d in [1, 5, 10, 20]
                                    }
                                }
                            })

                except Exception as e:
                    print(f"   ❌ {ticker} 재평가 오류: {e}")
                    continue

        if not candidates:
            print("📊 매수 대상 종목이 없습니다.")
            return {'bought_count': 0, 'total_invested': 0}

        # 점수 기준으로 정렬
        candidates.sort(key=lambda x: x.get('normalized_score', x.get('combined_score', x.get('technical_score', 0))),
                        reverse=True)

        # 매수 실행
        return self._execute_buy_orders(candidates, available_slots, current_date, max_positions)

    def _select_buy_candidates(self, current_date: str) -> List[Dict[str, Any]]:
        """매수 후보 종목 선정 - 기술적 분석 + 뉴스 감정 평가 결합"""
        try:
            # 1단계: 항상 기술적 분석으로 기본 선정
            print("📊 기술적 분석 기반 종목 선정...")

            # 백테스트 모드에서 현재 날짜 설정
            self.stock_selector.set_backtest_mode(True, current_date)

            # 기술적 분석 기반 선정
            entry_candidates = self.stock_selector.enhanced_stock_selection(current_date)

            if not entry_candidates:
                print("📊 기술적 분석에서 선정된 종목이 없습니다.")
                return []

            # 보유 종목 정보 가져오기 (기술점수 재계산용)
            current_holdings = self.portfolio.get_current_holdings()

            # 데이터 검증 및 기술점수 재계산
            validated_candidates = []
            for candidate in entry_candidates:
                ticker = candidate['ticker']
                if self.data_validator.validate_ticker_data(ticker, current_date):
                    # 보유 종목인 경우 기술점수 재계산
                    if ticker in current_holdings:
                        holding_info = current_holdings[ticker]
                        holding_days = self.portfolio.holding_period.get(ticker, 0)
                        entry_price = holding_info.get('buy_price', None)

                        # 보유 기간과 진입 가격을 고려한 점수 계산
                        from ..analysis.technical import get_technical_analyzer
                        analyzer = get_technical_analyzer()
                        technical_score = analyzer.get_technical_score(ticker, holding_days, entry_price)

                        # candidate 정보 업데이트
                        candidate['technical_score'] = technical_score
                        candidate['is_holding'] = True
                        candidate['holding_days'] = holding_days

                        print(f"   📊 {ticker}: 보유 중 - 기술점수 재계산 {technical_score * 100:.1f}% (보유 {holding_days}일)")

                    validated_candidates.append(candidate)
                else:
                    print(f"   ❌ {ticker}: 데이터 검증 실패 - 매수 후보에서 제외")

            print(f"   ✅ 검증 통과: {len(validated_candidates)}개 종목")

            # 2단계: 뉴스 전략 사용 시 뉴스 감정 평가 추가
            if self.use_news_strategy:
                print("\n📰 선정된 종목에 대한 뉴스 감정 평가 실행...")

                # NewsAnalyzer 인스턴스 가져오기
                from ..analysis.news_sentiment import get_news_analyzer
                news_analyzer = get_news_analyzer(debug=self.debug)

                # 각 종목에 대해 뉴스 감정 평가 수행
                enhanced_candidates = []
                for candidate in validated_candidates:
                    ticker = candidate['ticker']

                    try:
                        # 회사명 조회
                        company_name = self.news_selector._get_company_name(ticker)
                        print(f"\n   🔍 {ticker} ({company_name}) 뉴스 분석 중...")

                        # 뉴스 수집 및 분석
                        news_list = news_analyzer.fetch_ticker_news(ticker, company_name, current_date)

                        if news_list:
                            print(f"      📰 {len(news_list)}개 뉴스 수집")

                            # 감정 분석
                            news_analysis = news_analyzer.analyze_news_sentiment(
                                news_list, ticker, company_name
                            )

                            # 뉴스 분석 결과를 candidate에 추가
                            candidate['news_analysis'] = news_analysis
                            candidate['news_score'] = news_analysis.get('avg_confidence', 0.5)
                            candidate['news_sentiment'] = news_analysis.get('sentiment', '중립')

                            # ⭐ 부정적 감정인 경우 즉시 제외
                            if candidate['news_sentiment'] == '부정':
                                print(f"      ❌ 뉴스 감정이 부정적이어서 매수 후보에서 제외")
                                continue

                            # 종합 점수 계산 (기술적 점수 70% + 뉴스 점수 30%)
                            technical_weight = 0.7
                            news_weight = 0.3
                            candidate['combined_score'] = (
                                    candidate['technical_score'] * technical_weight +
                                    candidate['news_score'] * news_weight
                            )
                            # 정규화된 점수 추가
                            candidate['normalized_score'] = candidate['combined_score']
                            # 명확한 명칭 추가
                            candidate['hybrid_score'] = candidate['combined_score']

                            print(f"      ✅ 뉴스 감정: {candidate['news_sentiment']}, "
                                  f"신뢰도: {candidate['news_score'] * 100:.1f}%")
                            print(f"      📊 종합 점수: {candidate['combined_score'] * 100:.1f}% "
                                  f"(기술적: {candidate['technical_score'] * 100:.1f}%, "
                                  f"뉴스: {candidate['news_score'] * 100:.1f}%)")

                            # 뉴스 신호 정보 추가 (보유 기간 등)
                            candidate['news_signal'] = {
                                'ticker': ticker,
                                'company_name': company_name,
                                'sentiment': candidate['news_sentiment'],
                                'confidence': candidate['news_score'],
                                'holding_days': self.news_selector.optimal_holding_days,
                                'predictions': {
                                    f'{d}d': news_analysis.get(f'prob_{d}', 0.5)
                                    for d in [1, 5, 10, 20]
                                }
                            }
                        else:
                            print(f"      ⚠️ 뉴스 없음 - 기술적 점수만 사용")
                            candidate['news_score'] = 0.5  # 중립값
                            candidate['news_sentiment'] = '중립'
                            candidate['combined_score'] = candidate['technical_score']
                            candidate['normalized_score'] = candidate['technical_score']  # 정규화된 점수
                            candidate['hybrid_score'] = candidate['technical_score']  # 기술적 점수만 사용

                        enhanced_candidates.append(candidate)

                    except Exception as e:
                        print(f"      ❌ 뉴스 분석 오류: {e}")
                        # 오류 시 기술적 점수만 사용
                        candidate['news_score'] = 0.5
                        candidate['news_sentiment'] = '중립'
                        candidate['combined_score'] = candidate['technical_score']
                        candidate['normalized_score'] = candidate['technical_score']  # 정규화된 점수
                        candidate['hybrid_score'] = candidate['technical_score']  # 기술적 점수만 사용
                        enhanced_candidates.append(candidate)

                # 종합 점수 기준으로 정렬
                enhanced_candidates.sort(key=lambda x: x.get('normalized_score', x.get('combined_score', 0)),
                                         reverse=True)

                # 최소 기준 필터링 (종합 점수 0.7 이상만)
                final_candidates = [c for c in enhanced_candidates
                                    if c.get('normalized_score', c.get('combined_score', 0)) >= 0.7]

                if not final_candidates and enhanced_candidates:
                    # 기준에 맞는 종목이 없으면 상위 1개만 선택
                    final_candidates = enhanced_candidates[:1]

                print(f"\n📊 최종 선정: {len(final_candidates)}개 종목 (종합 점수 0.7 이상)")
                for i, cand in enumerate(final_candidates[:5]):
                    # 정규화된 점수 사용
                    display_score = cand.get('normalized_score', cand.get('combined_score', 0))
                    if display_score > 1.0:  # combined_score가 거래대금 기반인 경우
                        display_score = cand.get('technical_score', 0)

                    print(f"   {i + 1}. {cand['ticker']}: 종합 {display_score * 100:.1f}% "
                          f"(기술적 {cand['technical_score'] * 100:.1f}%, "
                          f"뉴스 {cand.get('news_score', 0.5) * 100:.1f}%)")

                return final_candidates[:5]  # 최대 5개

            else:
                # 뉴스 전략 미사용 시 기술적 점수 기준으로 상위 5개만
                final_candidates = validated_candidates[:5]
                print(f"📊 기술적 분석 상위 {len(final_candidates)}개 선정")
                return final_candidates

        except Exception as e:
            print(f"❌ 종목 선정 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _execute_buy_orders(self, candidates: List[Dict[str, Any]], available_slots: int,
                            current_date: str, max_positions: int = 7) -> Dict[str, Any]:
        """매수 주문 실행 (피라미딩 지원)"""
        bought_count = 0
        total_invested = 0

        # 현재 보유 종목 정보
        current_holdings = self.portfolio.get_current_holdings()

        # 포트폴리오 가치 계산 (포지션 크기 제한용)
        current_prices = {}
        for ticker in current_holdings:
            price = self.data_validator.get_valid_price(ticker, current_date)
            if price:
                current_prices[ticker] = price

        portfolio_value = self.portfolio.calculate_portfolio_value(current_prices)
        max_position_value = portfolio_value * 0.3  # 종목당 최대 30%

        # 종목당 투자 금액 계산
        available_cash = self.portfolio.cash * 0.8  # 현금의 80% 사용
        # 피라미딩 고려해서 더 많은 슬롯으로 나눔
        investment_per_stock = available_cash / max(available_slots + len(current_holdings), 1)

        print(f"   사용 가능 현금: {available_cash:,.0f}원")
        print(f"   종목당 기본 투자: {investment_per_stock:,.0f}원")
        print(f"   종목당 최대 포지션: {max_position_value:,.0f}원")

        for candidate in candidates:
            ticker = candidate['ticker']

            # 현재가 조회
            current_price = self.data_validator.get_valid_price(ticker, current_date)
            if not current_price or current_price <= 0:
                print(f"   ❌ {ticker}: 현재가 조회 실패")
                continue

            # 보유 중인 종목인지 확인
            is_holding = ticker in current_holdings

            if is_holding:
                # 피라미딩 처리
                holding = current_holdings[ticker]
                current_position_value = holding['quantity'] * current_price

                # 최대 포지션 크기 체크
                if current_position_value >= max_position_value:
                    print(f"   ⚠️ {ticker}: 최대 포지션 도달 ({current_position_value:,.0f}원 / {max_position_value:,.0f}원)")
                    continue

                # 피라미딩 최소 점수 체크 (80% 이상으로 상향)
                min_pyramiding_score = 0.80  # 기존 0.75에서 0.80으로 상향
                
                # 하이브리드 전략인 경우
                if self.use_news_strategy:
                    # hybrid_score가 있으면 사용, 없으면 combined_score 사용
                    score = candidate.get('hybrid_score', 
                                         candidate.get('normalized_score',
                                                      candidate.get('combined_score', 0)))
                else:
                    # 기술적 전략인 경우
                    score = candidate.get('technical_score', 0)
                
                # combined_score가 거래대금 기반인 경우 (매우 큰 값) technical_score 사용
                if score > 1.0:
                    score = candidate.get('technical_score', 0)

                if score < min_pyramiding_score:
                    score_type = "하이브리드" if self.use_news_strategy else "기술적"
                    print(f"   {ticker}: 보유 중 - 피라미딩 {score_type} 점수 미달 ({score * 100:.1f}% < {min_pyramiding_score * 100}%)")
                    continue

                # 피라미딩 횟수 제한 확인
                pyramiding_count = holding.get('additional_info', {}).get('pyramiding_count', 0)
                if pyramiding_count >= 1:
                    print(f"   ⚠️ {ticker}: 피라미딩 횟수 초과 (최대 1회)")
                    continue

                # 손실 중 피라미딩 금지
                buy_price = holding.get('buy_price', 0)
                if buy_price > 0:
                    profit_rate = (current_price - buy_price) / buy_price
                    if profit_rate < -0.02:  # 2% 이상 손실
                        print(f"   ⚠️ {ticker}: 손실 중으로 피라미딩 취소 (손실률: {profit_rate * 100:.1f}%)")
                        continue

                print(f"   🔄 {ticker}: 피라미딩 매수 검토 (점수: {score * 100:.1f}%)")

                # 추가 투자 금액 결정 (남은 허용 금액의 50% 또는 기본 투자금의 50%)
                remaining_allowed = max_position_value - current_position_value
                investment_amount = min(investment_per_stock * 0.5, remaining_allowed)

                # 보유 기간 리셋 여부 (80% 이상일 때)
                if self.use_news_strategy:
                    # 하이브리드 점수 사용
                    reset_score = candidate.get('hybrid_score',
                                               candidate.get('normalized_score',
                                                            candidate.get('combined_score', 0)))
                else:
                    # 기술적 점수 사용
                    reset_score = candidate.get('technical_score', 0)
                    
                reset_holding = reset_score >= 0.80
                if reset_holding:
                    score_type = "하이브리드" if self.use_news_strategy else "기술적"
                    print(f"   → 높은 {score_type} 점수({reset_score * 100:.1f}%)로 보유기간 리셋 예정")

            else:
                # 신규 매수
                if len(current_holdings) >= max_positions:
                    print(f"   ⚠️ {ticker}: 포트폴리오 한계 도달 ({max_positions}개)")
                    continue

                # 기본 투자 금액 결정
                investment_amount = self._determine_investment_amount(
                    candidate, investment_per_stock
                )
                reset_holding = False  # 신규 매수는 리셋 불필요

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
                'momentum_score': candidate.get('momentum_score', 0.5),
                'volume_signal': candidate.get('volume_signal', '정상')
            }

            # 피라미딩인 경우 횟수 추적
            if is_holding:
                holding = current_holdings[ticker]
                current_pyramiding_count = holding.get('additional_info', {}).get('pyramiding_count', 0)
                additional_info['pyramiding_count'] = current_pyramiding_count + 1
            else:
                additional_info['pyramiding_count'] = 0

            # 뉴스 전략인 경우 뉴스 정보 추가
            if self.use_news_strategy:
                additional_info['news_score'] = candidate.get('news_score', 0.5)
                additional_info['news_sentiment'] = candidate.get('news_sentiment', '중립')
                additional_info['combined_score'] = candidate.get('combined_score',
                                                                  candidate.get('technical_score', 0.5))
                additional_info['normalized_score'] = candidate.get('normalized_score',
                                                                    candidate.get('technical_score', 0.5))
                additional_info['hybrid_score'] = candidate.get('hybrid_score',
                                                               candidate.get('combined_score', 
                                                                           candidate.get('technical_score', 0.5)))

                # 뉴스 신호 정보 추가
                if 'news_signal' in candidate:
                    additional_info['news_signal'] = candidate['news_signal']

            success = self.portfolio.buy_stock(
                ticker, current_price, investment_amount, current_date,
                additional_info, reset_holding_period=reset_holding
            )

            if success:
                bought_count += 1
                total_invested += investment_amount

                # 상세 매수 정보 출력
                action = "피라미딩" if is_holding else "신규"
                if self.use_news_strategy:
                    # hybrid_score가 있으면 사용
                    display_score = candidate.get('hybrid_score',
                                                 candidate.get('normalized_score', 
                                                              candidate.get('combined_score', 0)))
                    if display_score > 1.0:  # combined_score가 거래대금 기반인 경우
                        display_score = candidate.get('technical_score', 0)

                    print(f"✅ {ticker} {action} 매수 완료 - 하이브리드점수: {display_score * 100:.1f}% "
                          f"(기술적: {candidate.get('technical_score', 0) * 100:.1f}%, "
                          f"뉴스: {candidate.get('news_score', 0) * 100:.1f}%)")
                else:
                    print(f"✅ {ticker} {action} 매수 완료 - 기술적 점수: {candidate.get('technical_score', 0) * 100:.1f}%")

        print(f"📊 매수 완료: {bought_count}개 종목, 총 투자 {total_invested:,.0f}원")
        return {'bought_count': bought_count, 'total_invested': total_invested}

    def _determine_investment_amount(self, candidate: Dict[str, Any],
                                     base_amount: float) -> float:
        """종합 점수 기반 투자 금액 결정"""
        # 뉴스 전략 사용 시 하이브리드 점수 사용, 아니면 기술적 점수만 사용
        if self.use_news_strategy:
            # hybrid_score가 있으면 사용, 없으면 combined_score나 normalized_score 사용
            score = candidate.get('hybrid_score',
                                 candidate.get('normalized_score', 
                                              candidate.get('combined_score', 0.5)))
        else:
            score = candidate.get('technical_score', 0.5)

        # combined_score가 거래대금 기반인 경우 (매우 큰 값) technical_score 사용
        if score > 1.0:
            score = candidate.get('technical_score', 0.5)

        # 점수 기반 투자 금액 조정
        if score >= 0.80:  # 매우 강한 신호: 1.3배
            multiplier = 1.3
        elif score >= 0.70:  # 강한 신호: 1.1배
            multiplier = 1.1
        elif score >= 0.60:  # 보통 신호: 1.0배
            multiplier = 1.0
        else:  # 약한 신호: 0.8배
            multiplier = 0.8

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
            'strategy': 'news_based' if self.use_news_strategy else 'technical_only'
        }

        self.portfolio.record_daily_portfolio(date_str, portfolio_value, additional_data)

        daily_return = (portfolio_value - self.initial_capital) / self.initial_capital
        current_positions = len(current_holdings)

        print(f"💼 포트폴리오: {portfolio_value:,.0f}원 (수익률: {daily_return * 100:+.2f}%, 보유: {current_positions}개)")

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
            'final_cash': self.portfolio.cash,
            'strategy': 'news_based' if self.use_news_strategy else 'technical_only'
        })

        # 성과 요약 출력
        self.performance_analyzer.print_performance_summary()

        return results

    def save_results(self, filename: str = None) -> str:
        """결과 저장"""
        return self.performance_analyzer.save_results_to_json(filename)


# 편의 함수
def run_backtest(start_date: str, end_date: str, initial_capital: float = 10_000_000,
                 transaction_cost: float = 0.003) -> Dict[str, Any]:
    """
    백테스트 실행 편의 함수 - 기술적 분석만 사용
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        initial_capital: 초기 자본
        transaction_cost: 거래 비용
        
    Returns:
        Dict: 백테스트 결과
    """
    engine = BacktestEngine(initial_capital, transaction_cost)
    return engine.run_backtest(start_date, end_date, news_analysis_enabled=False)


# 사용 예시
if __name__ == "__main__":
    # 모듈화된 백테스트 실행 - 기술적 분석만
    start_date = "2025-06-01"
    end_date = "2025-06-10"

    try:
        results = run_backtest(start_date, end_date)

        # 결과 저장
        engine = BacktestEngine()
        engine.performance_analyzer.results = results
        engine.save_results("technical_only_backtest_result.json")

    except Exception as e:
        print(f"❌ 백테스팅 실행 오류: {e}")
        import traceback

        traceback.print_exc()
