"""
뉴스 기반 종목 선정 전략
News-based stock selection strategy
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from ..strategy.selector import get_stock_selector
from ..analysis.news_sentiment import get_news_analyzer
from ..data.fetcher import get_data_fetcher
from ..utils.storage import get_data_manager
import pandas as pd


class NewsBasedSelector:
    """뉴스 감정 분석 기반 종목 선정 클래스"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.technical_selector = get_stock_selector()
        self.news_analyzer = get_news_analyzer(debug=debug)
        self.data_fetcher = get_data_fetcher()
        self.data_manager = get_data_manager()
        
        # 최적 파라미터 (기본값)
        self.optimal_holding_days = 5
        self.optimal_threshold = 0.65
        
        # 종목별 한글 이름 매핑 (예시)
        self.ticker_names = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '035420': 'NAVER',
            '035720': '카카오',
            '051910': 'LG화학',
            # 더 많은 종목 추가 필요
        }
    
    def set_optimal_parameters(self, holding_days: int, threshold: float):
        """최적 파라미터 설정"""
        self.optimal_holding_days = holding_days
        self.optimal_threshold = threshold
        print(f"📊 최적 파라미터 설정: 보유기간={holding_days}일, 매수기준={threshold:.2f}")
    
    def select_stocks_by_news(self, current_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        뉴스 감정 분석을 통한 종목 선정
        
        Args:
            current_date: 현재 날짜 (백테스트용)
            
        Returns:
            List[Dict]: 매수 신호 리스트
        """
        if current_date:
            date_obj = datetime.strptime(current_date, '%Y-%m-%d')
        else:
            date_obj = datetime.now()
        
        print(f"📰 뉴스 기반 종목 선정 시작 ({date_obj.strftime('%Y-%m-%d')})")
        
        # 1단계: 기술적 지표로 1차 선정
        technical_stocks = self.technical_selector.select_stocks_for_buy(current_date)
        
        if not technical_stocks:
            print("📊 기술적 분석에서 선정된 종목이 없습니다.")
            return []
        
        print(f"📊 기술적 분석 선정 종목: {len(technical_stocks)}개")
        
        # 2단계: 각 종목의 뉴스 수집 및 분석
        buy_signals = []
        
        for ticker in technical_stocks:
            try:
                # 종목명 가져오기
                company_name = self._get_company_name(ticker)
                
                # 뉴스 수집 및 분석
                print(f"\n🔍 {ticker} ({company_name}) 뉴스 분석 중...")
                news_analysis = self.news_analyzer.analyze_ticker_news(
                    ticker, company_name, date_obj.strftime('%Y-%m-%d')
                )
                
                # 3단계: 매수 결정
                if self._should_buy(news_analysis):
                    buy_signal = {
                        'ticker': ticker,
                        'company_name': company_name,
                        'buy_date': (date_obj + timedelta(days=1)).strftime('%Y-%m-%d'),
                        'sell_date': (date_obj + timedelta(days=1+self.optimal_holding_days)).strftime('%Y-%m-%d'),
                        'holding_days': self.optimal_holding_days,
                        'confidence': news_analysis['avg_confidence'],
                        'sentiment': news_analysis.get('sentiment', '중립'),
                        'reason': news_analysis.get('reason', ''),
                        'predictions': {
                            f'{d}d': news_analysis.get(f'prob_{d}', 0.5) 
                            for d in [1, 5, 10, 20]
                        }
                    }
                    
                    buy_signals.append(buy_signal)
                    print(f"✅ 매수 신호: 신뢰도={buy_signal['confidence']:.2%}, 감정={buy_signal['sentiment']}")
                else:
                    print(f"❌ 매수 기준 미달: 평균 신뢰도={news_analysis['avg_confidence']:.2%}")
            
            except Exception as e:
                print(f"⚠️ {ticker} 분석 오류: {e}")
                continue
        
        # 4단계: 신뢰도 순으로 정렬
        buy_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 5단계: 최대 보유 종목 수 제한
        max_positions = self.data_manager.get_data().get('max_selections', 3)
        final_signals = buy_signals[:max_positions]
        
        print(f"\n🎯 최종 매수 신호: {len(final_signals)}개 종목")
        for signal in final_signals:
            print(f"  - {signal['ticker']} ({signal['company_name']}): "
                  f"신뢰도={signal['confidence']:.2%}, {signal['holding_days']}일 보유")
        
        return final_signals
    
    def _should_buy(self, news_analysis: Dict[str, Any]) -> bool:
        """매수 여부 결정"""
        # 평균 신뢰도가 임계값 이상인지 확인
        avg_confidence = news_analysis.get('avg_confidence', 0.5)
        
        # 감정이 부정적이면 매수하지 않음
        sentiment = news_analysis.get('sentiment', '중립')
        if sentiment == '부정':
            return False
        
        # 특정 기간의 예측 확률 확인
        target_prob = news_analysis.get(f'prob_{self.optimal_holding_days}', 0.5)
        
        return avg_confidence >= self.optimal_threshold or target_prob >= self.optimal_threshold
    
    def _get_company_name(self, ticker: str) -> str:
        """종목 코드로 회사명 조회"""
        # pykrx를 사용한 실시간 조회
        try:
            from pykrx import stock
            name = stock.get_market_ticker_name(ticker)
            if name:
                return name
        except Exception as e:
            print(f"  ⚠️ 회사명 조회 실패 ({ticker}): {e}")
        
        # 캐시된 매핑에서 조회
        return self.ticker_names.get(ticker, ticker)
    
    def train_optimal_parameters(self, start_date: str, end_date: str) -> Tuple[int, float]:
        """
        과거 데이터로 최적 파라미터 학습
        
        Args:
            start_date: 학습 시작일 (YYYY-MM-DD)
            end_date: 학습 종료일 (YYYY-MM-DD)
            
        Returns:
            Tuple[int, float]: (최적 보유 기간, 최적 매수 기준 확률)
        """
        print(f"📚 최적 파라미터 학습 시작: {start_date} ~ {end_date}")
        
        # 테스트할 파라미터 범위
        days_list = [1, 3, 5, 7, 10, 20]
        threshold_list = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
        
        best_return = -float('inf')
        best_days = days_list[0]
        best_threshold = threshold_list[0]
        
        # 각 파라미터 조합에 대해 백테스트
        results = []
        
        for days in days_list:
            for threshold in threshold_list:
                # 백테스트 수행
                total_return, num_trades = self._backtest_with_params(
                    start_date, end_date, days, threshold
                )
                
                results.append({
                    'days': days,
                    'threshold': threshold,
                    'return': total_return,
                    'trades': num_trades
                })
                
                if total_return > best_return:
                    best_return = total_return
                    best_days = days
                    best_threshold = threshold
                
                print(f"  테스트: n={days}일, threshold={threshold:.2f} "
                      f"→ 수익률={total_return:.2%}, 거래횟수={num_trades}")
        
        # 결과 저장
        self.optimal_holding_days = best_days
        self.optimal_threshold = best_threshold
        
        print(f"\n🏆 최적 파라미터 발견!")
        print(f"  - 보유 기간: {best_days}일")
        print(f"  - 매수 기준: {best_threshold:.2f}")
        print(f"  - 기대 수익률: {best_return:.2%}")
        
        return best_days, best_threshold
    
    def _backtest_with_params(self, start_date: str, end_date: str, 
                              holding_days: int, threshold: float) -> Tuple[float, int]:
        """특정 파라미터로 백테스트 수행"""
        # 간단한 백테스트 구현 (실제로는 더 정교하게 구현 필요)
        initial_capital = 10_000_000
        capital = initial_capital
        num_trades = 0
        
        # 여기서는 예시값 반환
        # 실제로는 과거 데이터로 시뮬레이션 수행 필요
        import random
        return_rate = random.uniform(-0.1, 0.3)
        trades = random.randint(5, 50)
        
        return return_rate, trades


# 전역 인스턴스
_news_selector_instance = None

def get_news_based_selector(debug: bool = False) -> NewsBasedSelector:
    """뉴스 기반 선택기 인스턴스 반환 (싱글톤)"""
    global _news_selector_instance
    if _news_selector_instance is None or _news_selector_instance.debug != debug:
        _news_selector_instance = NewsBasedSelector(debug=debug)
    return _news_selector_instance


# 편의 함수들
def select_stocks_by_news(current_date: Optional[str] = None, debug: bool = False) -> List[Dict[str, Any]]:
    """뉴스 기반 종목 선정"""
    selector = get_news_based_selector(debug)
    return selector.select_stocks_by_news(current_date)


def train_news_parameters(start_date: str, end_date: str, debug: bool = False) -> Tuple[int, float]:
    """뉴스 전략 파라미터 학습"""
    selector = get_news_based_selector(debug)
    return selector.train_optimal_parameters(start_date, end_date)
