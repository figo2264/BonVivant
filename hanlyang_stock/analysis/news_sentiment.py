"""
뉴스 감정 분석 기반 주가 예측 모듈
News sentiment analysis based stock price prediction module
"""

import os
from typing import List, Dict, Tuple, Optional
import pandas as pd
from anthropic import Anthropic
from pathlib import Path

# 새로운 크롤러 모듈 임포트
from .crawlers import (
    NewsItem,
    NewsSource,
    NewsCrawlerFactory,
    MultiSourceCrawler
)


# .env 파일 수동 로드
def load_env():
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value


class NewsAnalyzer:
    """뉴스 감정 분석 클래스 - Claude API 사용"""
    
    def __init__(self, api_key: Optional[str] = None, debug: bool = False,
                 news_sources: Optional[List[str]] = None):
        """
        Initialize NewsAnalyzer with Claude API
        
        Args:
            api_key: Anthropic API key
            debug: 디버그 모드
            news_sources: 사용할 뉴스 소스 리스트
        """
        # .env 파일 로드
        load_env()
        
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.debug = debug
        
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None
            print("⚠️ Claude API 키가 설정되지 않았습니다. 뉴스 분석 기능이 제한됩니다.")
        
        # 크롤러 초기화
        self.news_sources = news_sources or [NewsSource.NAVER_FINANCE]
        self.crawler = MultiSourceCrawler(sources=self.news_sources, debug=debug)
        
        # 종목별 회사명 캐시
        self.company_name_cache = {}
    
    def fetch_ticker_news(self, ticker: str, company_name: str, date: str) -> List[Dict[str, str]]:
        """
        특정 종목의 뉴스 수집 (새로운 크롤러 모듈 사용)
        
        Args:
            ticker: 종목 코드 (예: '005930')
            company_name: 회사명 (예: '삼성전자')
            date: 날짜 (YYYY-MM-DD)
            
        Returns:
            List[Dict]: 뉴스 리스트 [{title, date, url, source}, ...]
        """
        # 회사명 확인
        if company_name == ticker or not company_name:
            company_name = self._get_company_name(ticker)
        
        # 크롤러를 통해 뉴스 수집
        news_items = self.crawler.fetch_news(ticker, company_name, date, max_items=10)
        
        # NewsItem을 Dict로 변환
        news_list = [item.to_dict() for item in news_items]
        
        return news_list
    
    def _get_company_name(self, ticker: str) -> str:
        """종목 코드로 회사명 조회"""
        if ticker in self.company_name_cache:
            return self.company_name_cache[ticker]
        
        try:
            from pykrx import stock
            company_name = stock.get_market_ticker_name(ticker)
            if company_name:
                self.company_name_cache[ticker] = company_name
                print(f"  🏢 종목 코드 {ticker} → 회사명: {company_name}")
                return company_name
        except Exception as e:
            print(f"  ⚠️ 회사명 조회 실패 ({ticker}): {e}")
        
        return ticker
    
    def add_news_source(self, source: str):
        """새로운 뉴스 소스 추가"""
        if source not in self.news_sources:
            self.news_sources.append(source)
            # 크롤러 재초기화
            self.crawler = MultiSourceCrawler(sources=self.news_sources, debug=self.debug)
            print(f"✅ 뉴스 소스 추가: {source}")
    
    def remove_news_source(self, source: str):
        """뉴스 소스 제거"""
        if source in self.news_sources:
            self.news_sources.remove(source)
            # 크롤러 재초기화
            self.crawler = MultiSourceCrawler(sources=self.news_sources, debug=self.debug)
            print(f"✅ 뉴스 소스 제거: {source}")
    
    def analyze_news_sentiment(self, news_list: List[Dict], ticker: str, company_name: str, 
                               days: List[int] = [1, 5, 10, 20]) -> Dict[str, any]:
        """
        Claude API를 사용한 뉴스 감정 분석 및 주가 예측
        
        Args:
            news_list: 뉴스 리스트
            ticker: 종목 코드
            company_name: 회사명
            days: 예측할 일수 리스트
            
        Returns:
            Dict: 예측 결과
        """
        # 디버깅: 뉴스 리스트 상태 확인
        if self.debug:
            print(f"  [DEBUG] 뉴스 개수: {len(news_list) if news_list else 0}")
            print(f"  [DEBUG] Claude 클라이언트: {'있음' if self.client else '없음'}")
        
        if not self.client or not news_list:
            if self.debug:
                print(f"  [DEBUG] 기본값 반환 - 클라이언트: {bool(self.client)}, 뉴스: {bool(news_list)}")
            return self._get_default_predictions(days)
        
        # 프롬프트 생성 - 소스 정보 포함
        news_info = []
        for i, news in enumerate(news_list[:10]):
            source = news.get('source', '알 수 없음')
            title = news['title']
            news_info.append(f"{i+1}. [{source}] {title}")
        
        news_titles = "\n".join(news_info)
        
        prompt = f"""다음은 {company_name}({ticker}) 관련 최근 뉴스입니다:

{news_titles}

위 뉴스들을 바탕으로 주가 영향을 분석해주세요.

분석 시 고려사항:
1. 뉴스 출처의 신뢰도: 한국경제, 연합인포맥스 등 경제 전문지는 높은 가중치
2. 뉴스 내용의 구체성: 실적, 계약, 투자 등 구체적 수치가 있는 뉴스는 중요
3. 시장 반응 예측: 기관투자자와 개인투자자의 반응 차이 고려

단계별 분석:
1. 뉴스 분류: 각 뉴스를 긍정적/부정적/중립적으로 분류하고 중요도 평가
2. 시간별 영향: 즉각적 반응(1일), 단기 모멘텀(5일), 중기 트렌드(10-20일) 구분
3. 신뢰도 평가: 뉴스의 출처와 구체성을 고려한 예측 신뢰도

주가 상승 가능성 평가 기준:
- 50% 미만: 하락 가능성이 더 높음
- 50-60%: 보합 또는 소폭 상승
- 60-70%: 상승 가능성 있음
- 70% 이상: 강한 상승 기대

다음 형식으로만 답변해주세요:
- {days[0]}일 후 상승 확률: XX%
- {days[1]}일 후 상승 확률: XX%
- {days[2]}일 후 상승 확률: XX%
- {days[3]}일 후 상승 확률: XX%
- 종합 감정: 긍정/중립/부정
- 주요 이유: (가장 영향력 있는 뉴스 요인을 50자 이내로)"""
        
        try:
            # Claude API 호출
            if self.debug:
                print(f"  [DEBUG] Claude API 호출 시작...")
            
            response = self.client.messages.create(
                model=os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929'),
                max_tokens=500,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 디버깅: 응답 내용 확인
            response_text = response.content[0].text
            if self.debug:
                print(f"  [DEBUG] Claude 응답 길이: {len(response_text)}자")
                print(f"  [DEBUG] Claude 응답 첫 100자: {response_text[:100]}...")
            
            # 응답 파싱
            return self._parse_claude_response(response_text, days)
        
        except Exception as e:
            print(f"❌ Claude API 오류: {e}")
            return self._get_default_predictions(days)
    
    def _parse_claude_response(self, response_text: str, days: List[int]) -> Dict[str, any]:
        """Claude 응답 파싱"""
        predictions = {}
        
        # 디버깅: 파싱 시작
        if self.debug:
            print(f"  [DEBUG] 응답 파싱 시작...")
        
        try:
            lines = response_text.strip().split('\n')
            if self.debug:
                print(f"  [DEBUG] 응답 라인 수: {len(lines)}")
            
            # 각 일수별 확률 추출
            for i, day in enumerate(days):
                for line in lines:
                    if f"{day}일 후" in line:
                        prob = float(line.split(':')[1].strip().replace('%', ''))
                        predictions[f'prob_{day}'] = prob / 100.0
                        if self.debug:
                            print(f"  [DEBUG] {day}일 확률 파싱: {prob}%")
                        break
            
            # 종합 감정 추출
            for line in lines:
                if '종합 감정:' in line:
                    sentiment = line.split(':')[1].strip()
                    predictions['sentiment'] = sentiment
                    if self.debug:
                        print(f"  [DEBUG] 감정 파싱: {sentiment}")
                elif '주요 이유:' in line:
                    reason = line.split(':')[1].strip()
                    predictions['reason'] = reason
            
            # 평균 확률 계산
            prob_values = [v for k, v in predictions.items() if k.startswith('prob_')]
            predictions['avg_confidence'] = sum(prob_values) / len(prob_values) if prob_values else 0.5
            if self.debug:
                print(f"  [DEBUG] 파싱된 확률 개수: {len(prob_values)}")
                print(f"  [DEBUG] 평균 신뢰도: {predictions['avg_confidence'] * 100:.1f}%")
            
        except Exception as e:
            print(f"⚠️ 응답 파싱 오류: {e}")
            return self._get_default_predictions(days)
        
        return predictions
    
    def _get_default_predictions(self, days: List[int]) -> Dict[str, any]:
        """기본 예측값 반환"""
        predictions = {
            'avg_confidence': 0.5,
            'sentiment': '중립',
            'reason': '뉴스 분석 불가'
        }
        
        for day in days:
            predictions[f'prob_{day}'] = 0.5
        
        return predictions
    
    def find_optimal_parameters(self, historical_data: pd.DataFrame, 
                                days_list: List[int] = [1, 5, 10, 20],
                                threshold_list: List[float] = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]) -> Tuple[int, float]:
        """
        과거 데이터를 사용하여 최적의 보유 기간(n)과 매수 기준 확률(threshold) 찾기
        
        Args:
            historical_data: 과거 뉴스 및 주가 데이터
            days_list: 테스트할 보유 기간 리스트
            threshold_list: 테스트할 매수 기준 확률 리스트
            
        Returns:
            Tuple[int, float]: (최적 보유 기간, 최적 매수 기준 확률)
        """
        best_return = -float('inf')
        best_n = days_list[0]
        best_threshold = threshold_list[0]
        
        for n in days_list:
            for threshold in threshold_list:
                # 백테스트 수행
                total_return = self._backtest_strategy(historical_data, n, threshold)
                
                if total_return > best_return:
                    best_return = total_return
                    best_n = n
                    best_threshold = threshold
        
        print(f"🎯 최적 파라미터: 보유기간={best_n}일, 매수기준={best_threshold:.2f}, 수익률={best_return:.2%}")
        
        return best_n, best_threshold
    
    def _backtest_strategy(self, data: pd.DataFrame, n: int, threshold: float) -> float:
        """간단한 백테스트 구현"""
        initial_capital = 10_000_000
        capital = initial_capital
        position = 0
        
        # 실제 백테스트 로직은 더 복잡하게 구현 필요
        # 여기서는 간단한 예시만 제공
        
        return (capital - initial_capital) / initial_capital
    
    def analyze_ticker_news(self, ticker: str, company_name: str, date: str) -> Dict[str, any]:
        """
        특정 종목의 뉴스를 수집하고 분석
        
        Args:
            ticker: 종목 코드
            company_name: 회사명
            date: 날짜 (YYYY-MM-DD)
            
        Returns:
            Dict: 분석 결과
        """
        # 뉴스 수집
        news_list = self.fetch_ticker_news(ticker, company_name, date)
        
        # 감정 분석 및 예측
        return self.analyze_news_sentiment(news_list, ticker, company_name)


# 편의 함수들
_analyzer_instance = None

def get_news_analyzer(debug: bool = False) -> NewsAnalyzer:
    """뉴스 분석기 인스턴스 반환 (싱글톤)"""
    global _analyzer_instance
    if _analyzer_instance is None or _analyzer_instance.debug != debug:
        _analyzer_instance = NewsAnalyzer(debug=debug)
    return _analyzer_instance


def analyze_ticker_news(ticker: str, company_name: str, date: str, debug: bool = False) -> Dict[str, any]:
    """특정 종목의 뉴스 분석"""
    analyzer = get_news_analyzer(debug)
    news_list = analyzer.fetch_ticker_news(ticker, company_name, date)
    return analyzer.analyze_news_sentiment(news_list, ticker, company_name)


# 사용 예시
if __name__ == "__main__":
    # 1. 기본 사용법 (네이버 증권만 사용)
    analyzer = NewsAnalyzer(debug=True)
    results = analyzer.analyze_ticker_news("005930", "삼성전자", "2024-01-15")
    
    # 2. 여러 소스 사용
    analyzer = NewsAnalyzer(
        debug=True,
        news_sources=[NewsSource.NAVER_FINANCE, NewsSource.MK_ECONOMY]
    )
    results = analyzer.analyze_ticker_news("005930", "삼성전자", "2024-01-15")
    
    # 3. 동적으로 소스 추가/제거
    analyzer.add_news_source(NewsSource.MK_ECONOMY)
    analyzer.remove_news_source(NewsSource.NAVER_FINANCE)
