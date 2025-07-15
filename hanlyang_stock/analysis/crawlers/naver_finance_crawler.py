"""
네이버 증권 뉴스 크롤러
Naver Finance news crawler implementation
"""

from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import tempfile
import os
import shutil
from datetime import datetime

from .news_crawler_base import NewsCrawlerBase, NewsItem


class NaverFinanceCrawler(NewsCrawlerBase):
    """네이버 증권 뉴스 크롤러"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._temp_dir = None
    
    def _get_quality_sources(self) -> List[str]:
        """경제 전문 매체 리스트"""
        return [
            '한국경제', '한경', '연합인포맥스', '인포맥스',
            '매일경제', '매경', '서울경제', '이데일리',
            '머니투데이', '파이낸셜뉴스', '아시아경제',
            '헤럴드경제', '조선비즈', '뉴스1', '뉴시스'
        ]
    
    def fetch_news(self, ticker: str, company_name: str, date: str, 
                   max_items: int = 10) -> List[NewsItem]:
        """네이버 증권에서 뉴스 크롤링"""
        print(f"📡 네이버 증권에서 {ticker} ({company_name}) 뉴스 수집 시작...")
        
        news_list = []
        driver = None
        
        try:
            driver = self._setup_driver()
            url = f"https://finance.naver.com/item/news.naver?code={ticker}"
            
            print(f"  📄 페이지 접속: {url}")
            driver.get(url)
            
            # iframe 처리
            self._switch_to_news_frame(driver)
            
            # 뉴스 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            news_list = self._parse_news_items(soup, date)
            
            # 품질 필터링
            filtered_news = self.filter_by_quality(news_list)
            
            # 날짜순 정렬
            filtered_news.sort(key=lambda x: self._parse_news_date(x.date), reverse=True)
            
            # 최대 개수 제한
            final_news = filtered_news[:max_items]
            
            print(f"  📰 최종 {len(final_news)}개 뉴스 수집 (전체 {len(news_list)}개 중)")
            
            # 소스별 통계
            if final_news and self.debug:
                self._print_source_stats(final_news)
            
            return final_news
            
        except Exception as e:
            print(f"❌ 네이버 증권 크롤링 오류: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return []
            
        finally:
            if driver:
                try:
                    # Chrome 종료
                    driver.quit()
                    
                    # Chrome user-data-dir 임시 디렉토리 정리
                    # chrome_options에서 user-data-dir 찾기
                    if hasattr(self, '_temp_dir') and os.path.exists(self._temp_dir):
                        shutil.rmtree(self._temp_dir, ignore_errors=True)
                except Exception as e:
                    print(f"⚠️ 드라이버 종료 중 오류: {e}")
    
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
        
        # 고유한 user-data-dir 설정으로 세션 충돌 방지
        self._temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f'--user-data-dir={self._temp_dir}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # 이미지 로딩 비활성화 (속도 향상)
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        serv = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=serv, options=chrome_options)
    
    def _switch_to_news_frame(self, driver):
        """뉴스 iframe으로 전환"""
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "news_frame"))
            )
            news_iframe = driver.find_element(By.ID, "news_frame")
            driver.switch_to.frame(news_iframe)
            print("  ✅ 뉴스 프레임 진입 성공")
            
            # 뉴스 테이블 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.type5"))
            )
        except Exception as e:
            print(f"  ⚠️ iframe 전환 실패: {e}")
    
    def _parse_news_items(self, soup: BeautifulSoup, date: str) -> List[NewsItem]:
        """뉴스 아이템 파싱"""
        news_items = []
        news_table = soup.find('table', class_='type5')
        
        if not news_table:
            print("  ⚠️ 뉴스 테이블을 찾을 수 없습니다.")
            return news_items
        
        rows = news_table.find_all('tr')
        print(f"  📊 {len(rows)}개 행 발견")
        
        for row in rows:
            if row.find('th'):  # 헤더 행 스킵
                continue
            
            title_cell = row.find('td', class_='title')
            if not title_cell:
                continue
            
            link_elem = title_cell.find('a')
            if not link_elem:
                continue
            
            # 정보 추출
            title = link_elem.text.strip()
            news_url = link_elem.get('href', '')
            
            # URL 정규화
            if news_url and not news_url.startswith('http'):
                if news_url.startswith('//'):
                    news_url = 'https:' + news_url
                else:
                    news_url = 'https://finance.naver.com' + news_url
            
            # 언론사
            info_cell = row.find('td', class_='info')
            source = info_cell.text.strip() if info_cell else '알 수 없음'
            
            # 날짜
            date_cell = row.find('td', class_='date')
            news_date = date_cell.text.strip() if date_cell else date
            
            news_items.append(NewsItem(
                title=title,
                date=news_date,
                url=news_url,
                source=source
            ))
        
        return news_items
    
    def _parse_news_date(self, date_str: str) -> datetime:
        """날짜 문자열을 datetime 객체로 변환"""
        try:
            # 다양한 날짜 형식 처리
            if '시간' in date_str or '분' in date_str:
                return datetime.now()
            elif '.' in date_str:
                date_parts = date_str.split()[0].split('.')
                if len(date_parts[0]) == 2:
                    date_str = '20' + date_str
                return datetime.strptime(date_str.split()[0], '%Y.%m.%d')
            else:
                return datetime.now()
        except:
            return datetime.now()
    
    def _print_source_stats(self, news_items: List[NewsItem]):
        """소스별 통계 출력"""
        source_stats = {}
        for news in news_items:
            src = news.source
            source_stats[src] = source_stats.get(src, 0) + 1
        
        print(f"  📊 소스별 분포:")
        for src, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"     - {src}: {count}개")
