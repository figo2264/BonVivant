"""
Stock selection strategies
Enhanced with technical analysis features
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from ..data.fetcher import get_data_fetcher
from ..analysis.technical import get_technical_score, validate_ticker_data
from ..utils.storage import get_data_manager
import pandas as pd
try:
    from pykrx import stock
except ImportError:
    print("⚠️ pykrx 패키지가 설치되지 않았습니다. 일부 기능이 제한될 수 있습니다.")
    stock = None


class StockSelector:
    """종목 선정 클래스 - 기술적 분석 기반"""
    
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        self.data_manager = get_data_manager()
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
                               min_market_cap: int = 2_000_000_000_000) -> List[str]:
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
            # 기본값: 10억원 (적절한 유동성 확보)
            min_trade_amount = strategy_data.get('enhanced_min_trade_amount', 1_000_000_000)
        
        print(f"💰 강화된 유동성 필터 적용 (최소 거래대금: {min_trade_amount/1_000_000_000:.1f}억원)")
        
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
        strategy_data = self.data_manager.get_data()
        min_market_cap = strategy_data.get('min_market_cap', 2_000_000_000_000)  # 기본 2천억
        tickers = self.apply_market_cap_filter(tickers, current_date, min_market_cap)
        
        print(f"\n✅ [1단계] 기본 품질 필터 완료: {len(tickers)}개 종목 통과")
        print("-" * 60)
        
        return tickers
    
    def enhanced_stock_selection(self, current_date=None) -> List[Dict[str, Any]]:
        """
        기술적 분석 강화 종목 선정 - 백테스트 모드 지원
        
        Args:
            current_date: 현재 날짜 (백테스트 시 사용)
            
        Returns:
            List[Dict]: 선정된 종목 정보 리스트
        """
        try:
            # 백테스트 최적화 파라미터 로드
            strategy_data = self.data_manager.get_data()
            backtest_params = strategy_data.get('backtest_params', {})
            technical_params = strategy_data.get('technical_params', {})
            
            # 파라미터 설정 (technical_params 우선, 그 다음 백테스트 파라미터, 없으면 기본값)
            min_close_days = technical_params.get('min_close_days', backtest_params.get('min_close_days', 7))  # 최적화: 7일
            ma_period = technical_params.get('ma_period', backtest_params.get('ma_period', 20))
            min_trade_amount = strategy_data.get('enhanced_min_trade_amount', backtest_params.get('min_trade_amount', 300_000_000))  # 최적화: 3억
            min_technical_score = technical_params.get('min_technical_score', backtest_params.get('min_technical_score', 0.7))  # 최적화: 0.7
            
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
                print(f"      - 최소 거래대금: {min_trade_amount/1_000_000_000:.1f}억")
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
            
            # 파라미터화된 조건에 맞는 종목 찾기
            traditional_candidates = today_data[
                (today_data[f'{min_close_days}d_min_close'] == today_data['close']) &
                (today_data[f'{ma_period}d_ma'] > today_data['close'])
            ].copy()
            
            print(f"📊 기술적 조건 후보: {len(traditional_candidates)}개")
            
            if traditional_candidates.empty:
                return []
            
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
                technical_multiplier = 0.5 + technical_score  # 0.5 ~ 1.5 배수
                combined_score = row['trade_amount'] * technical_multiplier
                
                enhanced_candidates.append({
                    'ticker': ticker,
                    'trade_amount': row['trade_amount'],
                    'technical_score': technical_score,
                    'combined_score': combined_score,
                    'current_price': row['close']
                })
            
            # 기술적 분석 강화 점수로 정렬
            enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
            
            # 기술적 점수가 기준 이상인 종목만 선정
            selected_candidates = []
            for candidate in enhanced_candidates[:10]:  # 상위 10개 확인
                if candidate['technical_score'] >= min_technical_score and len(selected_candidates) < 5:  # 파라미터화된 기준
                    selected_candidates.append(candidate)
            
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
        
        # 설정 로드
        strategy_data = self.data_manager.get_data()
        backtest_params = strategy_data.get('backtest_params', {})
        technical_params = strategy_data.get('technical_params', {})
        
        # 파라미터 설정 (technical_params 우선, 그 다음 백테스트 파라미터, 없으면 기본값)
        max_selections = backtest_params.get('max_positions', strategy_data.get('max_selections', 3))
        min_technical_score = technical_params.get('min_technical_score', backtest_params.get('min_technical_score', strategy_data.get('min_technical_score', 0.7)))  # 최적화: 0.7
        
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

        # 기술적 분석 정보 저장
        if 'technical_analysis' not in strategy_data:
            strategy_data['technical_analysis'] = {}
        
        for item in entry_tickers:
            strategy_data['technical_analysis'][item['ticker']] = {
                'score': item['technical_score'],
                'timestamp': datetime.now().isoformat(),
                'trade_amount': int(item['trade_amount']),
                'selected': item in final_selection
            }

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
        strategy_data = self.data_manager.get_data()
        
        technical_analysis = strategy_data.get('technical_analysis', {})
        
        summary = {
            'technical_analysis_count': len(technical_analysis),
            'selected_count': 0,
            'avg_technical_score': 0,
            'max_technical_score': 0,
            'min_technical_score': 1.0
        }
        
        # 기술적 분석 통계
        scores = []
        for analysis in technical_analysis.values():
            score = analysis.get('score', 0)
            scores.append(score)
            
            if analysis.get('selected', False):
                summary['selected_count'] += 1
            
            if score > summary['max_technical_score']:
                summary['max_technical_score'] = score
            if score < summary['min_technical_score']:
                summary['min_technical_score'] = score
        
        if scores:
            summary['avg_technical_score'] = sum(scores) / len(scores)
        
        return summary


# 전역 스톡 셀렉터 (싱글톤 패턴)
_selector_instance = None

def get_stock_selector() -> StockSelector:
    """스톡 셀렉터 인스턴스 반환 (싱글톤)"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = StockSelector()
    return _selector_instance

# 편의 함수들
def enhanced_stock_selection(current_date=None) -> List[Dict[str, Any]]:
    """기술적 분석 기반 종목 선정"""
    selector = get_stock_selector()
    return selector.enhanced_stock_selection(current_date)

def select_stocks_for_buy(current_date=None) -> List[str]:
    """매수용 종목 선정 (전체 워크플로우)"""
    selector = get_stock_selector()
    return selector.select_stocks_for_buy(current_date)
