"""
뉴스 크롤러 베이스 클래스 및 데이터 구조
Base classes and data structures for news crawlers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class NewsItem:
    """뉴스 아이템 데이터 클래스"""
    title: str
    date: str
    url: str
    source: str
    content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """딕셔너리로 변환"""
        result = {
            'title': self.title,
            'date': self.date,
            'url': self.url,
            'source': self.source
        }
        if self.content:
            result['content'] = self.content
        return result


class NewsSource:
    """뉴스 소스 상수"""
    NAVER_FINANCE = "naver_finance"
    DAUM_FINANCE = "daum_finance"
    MK_ECONOMY = "mk_economy"
    HANKYUNG = "hankyung"


class NewsCrawlerBase(ABC):
    """뉴스 크롤러 추상 베이스 클래스"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.quality_sources = self._get_quality_sources()
    
    @abstractmethod
    def fetch_news(self, ticker: str, company_name: str, date: str, 
                   max_items: int = 10) -> List[NewsItem]:
        """
        뉴스 수집 추상 메서드
        
        Args:
            ticker: 종목 코드
            company_name: 회사명
            date: 기준 날짜 (YYYY-MM-DD)
            max_items: 최대 수집 개수
            
        Returns:
            List[NewsItem]: 뉴스 아이템 리스트
        """
        pass
    
    @abstractmethod
    def _get_quality_sources(self) -> List[str]:
        """
        신뢰할 수 있는 뉴스 소스 리스트
        
        Returns:
            List[str]: 품질 소스 리스트
        """
        pass
    
    def filter_by_quality(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        품질 기준으로 뉴스 필터링
        
        Args:
            news_items: 필터링할 뉴스 아이템
            
        Returns:
            List[NewsItem]: 필터링된 뉴스 아이템
        """
        if not self.quality_sources:
            return news_items
        
        filtered = []
        for item in news_items:
            # 소스가 품질 소스 목록에 포함되는지 확인
            if any(src in item.source for src in self.quality_sources):
                filtered.append(item)
                if self.debug:
                    print(f"  ✅ 포함: [{item.source}] {item.title[:40]}...")
            elif self.debug:
                print(f"  ❌ 제외: [{item.source}] {item.title[:40]}...")
        
        return filtered
