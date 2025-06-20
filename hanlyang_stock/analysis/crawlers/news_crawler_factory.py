"""
뉴스 크롤러 팩토리
Factory pattern for creating news crawler instances
"""

from typing import Dict, Type, List
from .news_crawler_base import NewsCrawlerBase, NewsSource
from .naver_finance_crawler import NaverFinanceCrawler
from .mk_economy_crawler import MKEconomyCrawler


class NewsCrawlerFactory:
    """뉴스 크롤러 팩토리"""
    
    # 기본 크롤러 매핑
    _crawlers: Dict[str, Type[NewsCrawlerBase]] = {
        NewsSource.NAVER_FINANCE: NaverFinanceCrawler,
        NewsSource.MK_ECONOMY: MKEconomyCrawler,
    }
    
    @classmethod
    def create_crawler(cls, source: str, debug: bool = False) -> NewsCrawlerBase:
        """
        크롤러 인스턴스 생성
        
        Args:
            source: 뉴스 소스 (NewsSource 상수 사용)
            debug: 디버그 모드
            
        Returns:
            NewsCrawlerBase: 생성된 크롤러 인스턴스
            
        Raises:
            ValueError: 알 수 없는 소스인 경우
        """
        crawler_class = cls._crawlers.get(source)
        if not crawler_class:
            available_sources = ', '.join(cls._crawlers.keys())
            raise ValueError(
                f"Unknown news source: {source}. "
                f"Available sources: {available_sources}"
            )
        
        return crawler_class(debug=debug)
    
    @classmethod
    def register_crawler(cls, source: str, crawler_class: Type[NewsCrawlerBase]):
        """
        새로운 크롤러 등록
        
        Args:
            source: 뉴스 소스 식별자
            crawler_class: 크롤러 클래스 (NewsCrawlerBase 상속)
            
        Raises:
            TypeError: NewsCrawlerBase를 상속하지 않은 경우
        """
        if not issubclass(crawler_class, NewsCrawlerBase):
            raise TypeError(
                f"{crawler_class.__name__} must inherit from NewsCrawlerBase"
            )
        
        cls._crawlers[source] = crawler_class
        print(f"✅ 크롤러 등록 완료: {source} → {crawler_class.__name__}")
    
    @classmethod
    def unregister_crawler(cls, source: str):
        """
        크롤러 등록 해제
        
        Args:
            source: 제거할 뉴스 소스
        """
        if source in cls._crawlers:
            crawler_name = cls._crawlers[source].__name__
            del cls._crawlers[source]
            print(f"✅ 크롤러 등록 해제: {source} ({crawler_name})")
        else:
            print(f"⚠️ 등록되지 않은 소스: {source}")
    
    @classmethod
    def get_available_sources(cls) -> List[str]:
        """
        사용 가능한 뉴스 소스 목록 반환
        
        Returns:
            List[str]: 등록된 뉴스 소스 리스트
        """
        return list(cls._crawlers.keys())
    
    @classmethod
    def get_crawler_info(cls) -> Dict[str, str]:
        """
        등록된 크롤러 정보 반환
        
        Returns:
            Dict[str, str]: {소스: 크롤러 클래스명} 매핑
        """
        return {
            source: crawler_class.__name__
            for source, crawler_class in cls._crawlers.items()
        }
