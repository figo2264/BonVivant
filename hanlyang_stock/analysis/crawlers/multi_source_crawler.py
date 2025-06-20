"""
멀티 소스 뉴스 크롤러
Crawler that aggregates news from multiple sources
"""

from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .news_crawler_base import NewsItem, NewsSource
from .news_crawler_factory import NewsCrawlerFactory


class MultiSourceCrawler:
    """여러 소스에서 뉴스를 수집하는 통합 크롤러"""
    
    def __init__(self, sources: Optional[List[str]] = None, debug: bool = False,
                 parallel: bool = True, max_workers: int = 3):
        """
        Initialize multi-source crawler
        
        Args:
            sources: 사용할 뉴스 소스 리스트 (None이면 기본값 사용)
            debug: 디버그 모드
            parallel: 병렬 처리 여부
            max_workers: 최대 워커 수 (병렬 처리 시)
        """
        self.debug = debug
        self.parallel = parallel
        self.max_workers = max_workers
        
        # 기본 소스 설정
        if sources is None:
            sources = [NewsSource.NAVER_FINANCE]
        
        self.sources = sources
        self._validate_sources()
        
        # 크롤러 인스턴스 생성
        self.crawlers = {
            source: NewsCrawlerFactory.create_crawler(source, debug)
            for source in self.sources
        }
        
        print(f"📡 멀티 소스 크롤러 초기화: {len(self.crawlers)}개 소스")
        if debug:
            print(f"   - 소스: {', '.join(self.sources)}")
            print(f"   - 병렬 처리: {'활성화' if parallel else '비활성화'}")
    
    def _validate_sources(self):
        """소스 유효성 검증"""
        available_sources = NewsCrawlerFactory.get_available_sources()
        invalid_sources = [s for s in self.sources if s not in available_sources]
        
        if invalid_sources:
            raise ValueError(
                f"Invalid sources: {', '.join(invalid_sources)}. "
                f"Available sources: {', '.join(available_sources)}"
            )
    
    def fetch_news(self, ticker: str, company_name: str, date: str,
                   max_items: int = 10) -> List[NewsItem]:
        """
        모든 소스에서 뉴스 수집 및 통합
        
        Args:
            ticker: 종목 코드
            company_name: 회사명
            date: 기준 날짜 (YYYY-MM-DD)
            max_items: 최대 수집 개수
            
        Returns:
            List[NewsItem]: 통합된 뉴스 리스트
        """
        print(f"\n🔍 {ticker} ({company_name}) 뉴스 통합 수집 시작...")
        start_time = time.time()
        
        if self.parallel and len(self.crawlers) > 1:
            all_news = self._fetch_parallel(ticker, company_name, date, max_items)
        else:
            all_news = self._fetch_sequential(ticker, company_name, date, max_items)
        
        # 중복 제거
        unique_news = self._remove_duplicates(all_news)
        
        # 날짜순 정렬 (최신순)
        unique_news.sort(key=lambda x: x.date, reverse=True)
        
        # 최대 개수 제한
        final_news = unique_news[:max_items]
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 통합 수집 완료: {len(final_news)}개 뉴스 "
              f"(전체 {len(all_news)}개, 중복 {len(all_news) - len(unique_news)}개 제거)")
        print(f"⏱️ 소요 시간: {elapsed_time:.2f}초")
        
        # 소스별 통계
        if final_news:
            self._print_source_distribution(final_news)
        
        return final_news
    
    def _fetch_sequential(self, ticker: str, company_name: str, date: str,
                          max_items: int) -> List[NewsItem]:
        """순차적으로 뉴스 수집"""
        all_news = []
        
        for source, crawler in self.crawlers.items():
            try:
                news_items = crawler.fetch_news(ticker, company_name, date, max_items)
                all_news.extend(news_items)
                print(f"  ✅ {source}: {len(news_items)}개 수집")
            except Exception as e:
                print(f"  ⚠️ {source} 오류: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        return all_news
    
    def _fetch_parallel(self, ticker: str, company_name: str, date: str,
                        max_items: int) -> List[NewsItem]:
        """병렬로 뉴스 수집"""
        all_news = []
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(self.crawlers))) as executor:
            # 크롤링 작업 제출
            future_to_source = {
                executor.submit(
                    crawler.fetch_news, ticker, company_name, date, max_items
                ): source
                for source, crawler in self.crawlers.items()
            }
            
            # 결과 수집
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    news_items = future.result()
                    all_news.extend(news_items)
                    print(f"  ✅ {source}: {len(news_items)}개 수집")
                except Exception as e:
                    print(f"  ⚠️ {source} 오류: {e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
        
        return all_news
    
    def _remove_duplicates(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """중복 뉴스 제거 (제목 기반)"""
        seen_titles = set()
        unique_items = []
        duplicate_count = 0
        
        for item in news_items:
            # 제목의 앞 50자를 키로 사용
            title_key = item.title[:50].lower().strip()
            
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
            else:
                duplicate_count += 1
                if self.debug:
                    print(f"  🔁 중복 제거: {item.title[:40]}...")
        
        if duplicate_count > 0:
            print(f"  🔄 {duplicate_count}개 중복 뉴스 제거")
        
        return unique_items
    
    def _print_source_distribution(self, news_items: List[NewsItem]):
        """소스별 뉴스 분포 출력"""
        source_stats = {}
        
        for item in news_items:
            # 크롤러별로 소스 그룹화
            crawler_source = None
            for source in self.sources:
                if source == NewsSource.NAVER_FINANCE:
                    # 네이버 증권 크롤러의 뉴스들
                    if item.source != '매일경제':  # 매일경제가 아닌 것들
                        crawler_source = source
                        break
                elif source == NewsSource.MK_ECONOMY:
                    # 매일경제 크롤러의 뉴스들
                    if item.source == '매일경제':
                        crawler_source = source
                        break
            
            if crawler_source:
                if crawler_source not in source_stats:
                    source_stats[crawler_source] = {}
                
                # 언론사별 카운트
                news_source = item.source
                source_stats[crawler_source][news_source] = \
                    source_stats[crawler_source].get(news_source, 0) + 1
        
        print(f"\n  📊 소스별 뉴스 분포:")
        for crawler, sources in source_stats.items():
            total = sum(sources.values())
            print(f"     [{crawler}] 총 {total}개")
            for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                print(f"       - {src}: {count}개")
    
    def add_source(self, source: str):
        """새로운 소스 추가"""
        if source not in self.sources:
            self.sources.append(source)
            self.crawlers[source] = NewsCrawlerFactory.create_crawler(source, self.debug)
            print(f"✅ 소스 추가: {source}")
        else:
            print(f"⚠️ 이미 존재하는 소스: {source}")
    
    def remove_source(self, source: str):
        """소스 제거"""
        if source in self.sources:
            self.sources.remove(source)
            del self.crawlers[source]
            print(f"✅ 소스 제거: {source}")
        else:
            print(f"⚠️ 존재하지 않는 소스: {source}")
