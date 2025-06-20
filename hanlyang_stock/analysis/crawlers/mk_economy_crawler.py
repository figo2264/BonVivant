"""
매일경제 뉴스 크롤러
Maeil Kyungjae news crawler implementation
"""

from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random

from .news_crawler_base import NewsCrawlerBase, NewsItem
from pykrx import stock


class MKEconomyCrawler(NewsCrawlerBase):
    """매일경제 뉴스 크롤러"""
    
    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.company_name_cache = {}
    
    def _get_quality_sources(self) -> List[str]:
        """매일경제는 자체 필터링 불필요"""
        return []
    
    def fetch_news(self, ticker: str, company_name: str, date: str,
                   max_items: int = 10) -> List[NewsItem]:
        """매일경제에서 뉴스 크롤링"""
        print(f"📡 매일경제에서 {ticker} ({company_name}) 뉴스 수집 시작...")
        
        # 회사명 확인
        if company_name == ticker or not company_name:
            company_name = self._get_company_name(ticker)
        
        news_list = []
        driver = None
        
        try:
            driver = self._setup_driver()
            
            # 매일경제 AI 검색 URL
            url = f'https://www.mk.co.kr/aisearch?word={company_name}'
            print(f"  📡 매일경제 AI 검색 URL: {url}")
            
            driver.get(url)
            
            # 페이지 로드 대기
            time.sleep(3)
            
            # 검색 결과 파싱
            news_list = self._parse_search_results(driver, date, max_items)
            
            # 스크롤 및 더보기 시도
            if len(news_list) < max_items:
                news_list.extend(self._load_more_news(driver, date, max_items - len(news_list)))
            
            # 중복 제거
            unique_news = self._remove_duplicates(news_list)
            
            print(f"  ✅ 최종 {len(unique_news)}개 뉴스 수집")
            return unique_news[:max_items]
            
        except Exception as e:
            print(f"❌ 매일경제 크롤링 오류: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return []
            
        finally:
            if driver:
                driver.quit()
    
    def _get_company_name(self, ticker: str) -> str:
        """종목 코드로 회사명 조회"""
        if ticker in self.company_name_cache:
            return self.company_name_cache[ticker]
        
        try:
            actual_company_name = stock.get_market_ticker_name(ticker)
            if actual_company_name:
                self.company_name_cache[ticker] = actual_company_name
                print(f"  🏢 종목 코드 {ticker} → 회사명: {actual_company_name}")
                return actual_company_name
        except Exception as e:
            print(f"  ⚠️ 회사명 조회 실패 ({ticker}): {e}")
        
        return ticker
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Selenium 드라이버 설정"""
        chrome_options = webdriver.ChromeOptions()
        if not self.debug:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        serv = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=serv, options=chrome_options)
    
    def _parse_search_results(self, driver, date: str, max_items: int) -> List[NewsItem]:
        """검색 결과 파싱"""
        news_list = []
        
        try:
            # 페이지가 로드될 때까지 대기
            WebDriverWait(driver, 10).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, 'h3.news_ttl, [class*="result"], div[class*="news"]')
            )
            
            # 추가 대기 (동적 컨텐츠 로딩)
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 뉴스 제목 찾기 - 다양한 선택자 시도
            news_titles = soup.select('h3.news_ttl')
            print(f"  📊 h3.news_ttl로 {len(news_titles)}개 뉴스 제목 발견")
            
            # 다른 선택자로 추가 검색
            if len(news_titles) < max_items:
                for selector in ['div[class*="news"] h3', 'div[class*="news"] h2', 'a[href*="/news/"]']:
                    additional_titles = soup.select(selector)
                    for title in additional_titles:
                        if title not in news_titles and title.text.strip():
                            news_titles.append(title)
            
            # 뉴스 정보 추출
            for idx, title_elem in enumerate(news_titles[:max_items * 2]):
                try:
                    title = title_elem.text.strip()
                    
                    # 필터링
                    if not title or len(title) < 10:
                        continue
                    
                    exclude_keywords = ['AI 답변', '참고자료', '관련 질문', 'Powered by', 'perplexity']
                    if any(keyword in title for keyword in exclude_keywords):
                        continue
                    
                    # URL 추출
                    news_url = self._extract_url(title_elem)
                    
                    news_list.append(NewsItem(
                        title=title,
                        date=date,
                        url=news_url,
                        source='매일경제'
                    ))
                    
                    if self.debug:
                        print(f"  ✅ 뉴스 {idx+1}: {title[:50]}...")
                        
                except Exception as e:
                    if self.debug:
                        print(f"  ⚠️ 뉴스 항목 파싱 오류: {e}")
                    continue
                    
        except Exception as e:
            print(f"  ⚠️ 검색 결과 파싱 중 오류: {e}")
            
        return news_list
    
    def _extract_url(self, title_elem) -> str:
        """제목 요소에서 URL 추출"""
        news_url = ''
        
        # 제목 요소 자체가 링크인 경우
        if title_elem.name == 'a' and title_elem.get('href'):
            news_url = title_elem['href']
        else:
            # 부모나 형제 요소에서 링크 찾기
            parent = title_elem.parent
            while parent and parent.name != 'body':
                link = parent.find('a', href=True)
                if link and link.get('href'):
                    news_url = link['href']
                    break
                parent = parent.parent
        
        # 상대 경로를 절대 경로로 변환
        if news_url and not news_url.startswith('http'):
            if news_url.startswith('//'):
                news_url = 'https:' + news_url
            else:
                news_url = 'https://www.mk.co.kr' + news_url
        
        return news_url
    
    def _load_more_news(self, driver, date: str, needed: int) -> List[NewsItem]:
        """더 많은 뉴스 로드"""
        additional_news = []
        
        print(f"  📌 추가 뉴스 로드 시도...")
        
        # 1. 스크롤을 내려서 더 많은 뉴스 로드
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        
        # 2. 더보기 버튼 찾기
        try:
            more_button_clicked = False
            
            # JavaScript로 더보기 버튼 찾기
            buttons = driver.find_elements(By.TAG_NAME, 'button') + driver.find_elements(By.TAG_NAME, 'a')
            for button in buttons:
                if '더보기' in button.text and button.is_displayed():
                    button.click()
                    print(f"  ✅ 더보기 버튼 클릭 성공")
                    more_button_clicked = True
                    time.sleep(2)
                    break
            
            # 3. 페이지 재파싱
            if more_button_clicked:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                additional_news = self._parse_search_results(driver, date, needed)
                
        except Exception as e:
            if self.debug:
                print(f"  ⚠️ 더보기 처리 중 오류: {e}")
        
        return additional_news
    
    def _remove_duplicates(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """중복 뉴스 제거"""
        seen_titles = set()
        unique_items = []
        
        for item in news_items:
            title_key = item.title[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_items.append(item)
        
        return unique_items
