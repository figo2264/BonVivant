"""
Stock selection strategies
Enhanced with technical analysis features
"""

from datetime import datetime
from typing import List, Dict, Any
from ..data.fetcher import get_data_fetcher
from ..analysis.technical import get_technical_score, validate_ticker_data
from ..utils.storage import get_data_manager


class StockSelector:
    """종목 선정 클래스 - 기술적 분석 기반"""
    
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        self.data_manager = get_data_manager()
        self.backtest_mode = False  # 백테스트 모드 플래그
        self.current_backtest_date = None  # 백테스트 현재 날짜
    
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
    
    def enhanced_stock_selection(self, current_date=None) -> List[Dict[str, Any]]:
        """
        기술적 분석 강화 종목 선정 - 백테스트 모드 지원
        
        Args:
            current_date: 현재 날짜 (백테스트 시 사용)
            
        Returns:
            List[Dict]: 선정된 종목 정보 리스트
        """
        try:
            # 백테스트 모드일 때 날짜 설정
            if self.backtest_mode and current_date:
                self.current_backtest_date = current_date
                effective_date = current_date
            elif self.backtest_mode and self.current_backtest_date:
                effective_date = self.current_backtest_date
            else:
                effective_date = current_date
            
            print(f"📊 {'백테스트' if self.backtest_mode else '실시간'} 종목 분석 시작... ({effective_date or '현재'})")
            
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
            
            # 5일 종가 최저값, 20일 이동평균 계산
            market_data = market_data.sort_values(['ticker', 'timestamp'])
            market_data['5d_min_close'] = market_data.groupby('ticker')['close'].rolling(5, min_periods=1).min().reset_index(0, drop=True)
            market_data['20d_ma'] = market_data.groupby('ticker')['close'].rolling(20, min_periods=1).mean().reset_index(0, drop=True)
            
            # 현재 날짜 데이터만 추출
            if effective_date:
                today_data = market_data[market_data['timestamp'] == effective_date].copy()
            else:
                today_data = market_data[market_data['timestamp'] == market_data['timestamp'].max()].copy()
                
            if today_data.empty:
                print(f"⚠️ 당일 데이터 없음")
                return []
            
            # 기존 조건에 맞는 종목 찾기
            traditional_candidates = today_data[
                (today_data['5d_min_close'] == today_data['close']) &
                (today_data['20d_ma'] > today_data['close']) &
                (today_data['trade_amount'] > 1_000_000_000)  # 최소 거래대금 10억
            ].copy()
            
            print(f"📊 전통적 조건 후보: {len(traditional_candidates)}개")
            
            if traditional_candidates.empty:
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
            
            # 기술적 점수가 0.6 이상인 종목만 선정
            selected_candidates = []
            for candidate in enhanced_candidates[:15]:  # 상위 15개 확인
                if candidate['technical_score'] >= 0.6 and len(selected_candidates) < 10:
                    selected_candidates.append(candidate)
            
            print(f"🎯 기술적 분석 최종 선정: {len(selected_candidates)}개 종목")
            
            return selected_candidates
            
        except Exception as e:
            print(f"❌ 종목 선정 오류: {e}")
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
        max_selections = strategy_data.get('max_selections', 5)
        min_technical_score = strategy_data.get('min_technical_score', 0.65)
        
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
