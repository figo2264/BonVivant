"""
뉴스 감정 분석 기반 주가 예측 모듈
News sentiment analysis based stock price prediction module
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
import json
from bs4 import BeautifulSoup
import os
from anthropic import Anthropic
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from pykrx import stock

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
    
    def __init__(self, api_key: Optional[str] = None, debug: bool = False):
        """
        Initialize NewsAnalyzer with Claude API
        
        Args:
            api_key: Anthropic API key
            debug: 디버그 모드
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
        
        # 종목별 회사명 캐시
        self.company_name_cache = {}
    
    def fetch_ticker_news_old(self, ticker: str, company_name: str, date: str) -> List[Dict[str, str]]:
        """
        특정 종목의 뉴스 수집 (매일경제)
        
        Args:
            ticker: 종목 코드 (예: '005930')
            company_name: 회사명 (예: '삼성전자')
            date: 날짜 (YYYY-MM-DD)
            
        Returns:
            List[Dict]: 뉴스 리스트 [{title, date, url}, ...]
        """
        news_list = []
        
        # 회사명이 종목코드와 같거나 비어있으면 실제 회사명 조회
        if company_name == ticker or not company_name:
            # 캐시 확인
            if ticker in self.company_name_cache:
                company_name = self.company_name_cache[ticker]
                if self.debug:
                    print(f"  🏢 캐시에서 회사명 조회: {ticker} → {company_name}")
            else:
                try:
                    actual_company_name = stock.get_market_ticker_name(ticker)
                    if actual_company_name:
                        company_name = actual_company_name
                        self.company_name_cache[ticker] = company_name
                        print(f"  🏢 종목 코드 {ticker} → 회사명: {company_name}")
                except Exception as e:
                    print(f"  ⚠️ 회사명 조회 실패 ({ticker}): {e}")
                    # 회사명을 모르면 종목 코드로라도 검색 시도
        
        # Selenium 드라이버 설정
        serv = Service(ChromeDriverManager().install())
        chrome_options = webdriver.ChromeOptions()
        
        # 디버그 모드가 아닌 경우만 headless
        if not self.debug:
            chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        # User-Agent 설정 (봇으로 인식되는 것 방지)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(service=serv, options=chrome_options)
        
        try:
            # 매일경제 AI 검색 URL (더 간단한 구조)
            url = f'https://www.mk.co.kr/aisearch?word={company_name}'
            
            print(f"  📡 매일경제 AI 검색 URL: {url}")
            driver.get(url)
            
            # 페이지 로드 대기
            time.sleep(3)
            
            # 검색 결과 대기 및 파싱
            try:
                # 페이지가 로드될 때까지 대기 - h3 태그나 result 클래스가 나타날 때까지
                WebDriverWait(driver, 10).until(
                    lambda driver: driver.find_elements(By.CSS_SELECTOR, 'h3.news_ttl, [class*="result"], div[class*="news"]')
                )
                
                # 추가 대기 (동적 컨텐츠 로딩)
                time.sleep(2)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # 매일경제 AI 검색 페이지에서 뉴스 찾기
                news_items = []
                
                # 방법 1: h3.news_ttl 선택자로 뉴스 제목 직접 찾기
                news_titles = soup.select('h3.news_ttl')
                print(f"  📊 h3.news_ttl로 {len(news_titles)}개 뉴스 제목 발견")
                
                # 방법 2: 뉴스 컨테이너 찾기
                if not news_titles:
                    news_containers = soup.select('div[class*="news"]')
                    print(f"  📊 div[class*='news']로 {len(news_containers)}개 컨테이너 발견")
                    
                    # 각 컨테이너에서 뉴스 제목 추출
                    for container in news_containers:
                        title_elem = container.find('h3') or container.find('h2') or container.find('h4')
                        if title_elem:
                            news_titles.append(title_elem)
                
                # 방법 3: 기사 링크가 있는 모든 항목 찾기
                if not news_titles:
                    article_links = soup.select('a[href*="/news/"], a[href*="/article/"]')
                    print(f"  📊 기사 링크로 {len(article_links)}개 발견")
                    
                    # 링크에서 제목이 있는 것만 추출
                    for link in article_links:
                        if link.text.strip() and len(link.text.strip()) > 10:
                            news_titles.append(link)
                
                print(f"  📊 총 {len(news_titles)}개 뉴스 제목 수집")
                
                # 뉴스 정보 추출
                for idx, title_elem in enumerate(news_titles[:20]):  # 최근 20개만 추출
                    try:
                        # 제목 추출
                        title = title_elem.text.strip()
                        
                        # 제목이 너무 짧거나 AI 답변 등 불필요한 내용 필터링
                        if not title or len(title) < 10:
                            continue
                        
                        # AI 관련 컨텐츠 필터링
                        exclude_keywords = ['AI 답변', '참고자료', '관련 질문', 'Powered by', 'perplexity']
                        if any(keyword in title for keyword in exclude_keywords):
                            continue
                        
                        # 실제 뉴스 제목 패턴 확인 (보통 회사명이나 관련 키워드 포함)
                        if company_name not in title and ticker not in title:
                            # 제목에 회사명이나 종목코드가 없으면 관련성 낮음
                            # 하지만 완전히 제외하지는 않음 (관련 업계 뉴스일 수 있음)
                            pass
                        
                        # URL 추출 - 제목 요소나 부모 요소에서 링크 찾기
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
                        
                        # 날짜 추출 - 현재 날짜를 기본값으로 사용
                        news_date = date
                        
                        # 부모 요소에서 날짜 정보 찾기
                        parent = title_elem.parent
                        while parent and parent.name != 'body':
                            date_text = parent.find(string=lambda x: x and any(year in str(x) for year in ['2023', '2024', '2025']))
                            if date_text:
                                date_str = str(date_text).strip()
                                # 날짜 형식일 가능성이 높은 텍스트만 사용
                                if len(date_str) < 20 and ('.' in date_str or '-' in date_str or '년' in date_str):
                                    news_date = date_str
                                    break
                            parent = parent.parent
                        
                        news_list.append({
                            'title': title,
                            'date': news_date,
                            'url': news_url
                        })
                        
                        print(f"  ✅ 뉴스 {idx+1}: {title[:50]}...")
                        
                    except Exception as e:
                        print(f"  ⚠️ 뉴스 항목 파싱 오류: {e}")
                        continue
                
                # 더 많은 뉴스 로드 시도 (무한 스크롤이나 더보기 버튼)
                if len(news_list) < 10:
                    print(f"  📌 뉴스가 {len(news_list)}개뿐이므로 추가 로드 시도...")
                    
                    # 1. 스크롤을 내려서 더 많은 뉴스 로드 시도
                    for _ in range(3):  # 3번 스크롤
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1.5)
                    
                    # 2. 더보기 버튼 찾기 - 다양한 선택자 시도
                    try:
                        more_button_selectors = [
                            'button:contains("더보기")',
                            'a:contains("더보기")',
                            'button[class*="more"]',
                            'a[class*="more"]',
                            'button.btn_more',
                            'a.btn_more',
                            'div[class*="more"] button',
                            'div[class*="more"] a'
                        ]
                        
                        for selector in more_button_selectors:
                            try:
                                # JavaScript로 요소 찾기 (contains 선택자 지원)
                                if ':contains(' in selector:
                                    text = selector.split('"')[1]
                                    element_type = selector.split(':')[0]
                                    buttons = driver.find_elements(By.TAG_NAME, element_type)
                                    for button in buttons:
                                        if text in button.text and button.is_displayed():
                                            button.click()
                                            print(f"  ✅ 더보기 버튼 클릭 성공: {button.text}")
                                            time.sleep(2)
                                            break
                                else:
                                    # CSS 선택자로 찾기
                                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                                    for button in buttons:
                                        if button.is_displayed():
                                            button.click()
                                            print(f"  ✅ 더보기 버튼 클릭 성공")
                                            time.sleep(2)
                                            break
                            except:
                                continue
                    except Exception as e:
                        print(f"  ⚠️ 더보기 버튼 처리 중 오류: {e}")
                    
                    # 3. 페이지 재파싱하여 추가 뉴스 수집
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # 추가 뉴스 제목 찾기
                    additional_titles = soup.select('h3.news_ttl')
                    for title_elem in additional_titles[len(news_list):]:  # 이미 수집한 것 이후부터
                        try:
                            title = title_elem.text.strip()
                            if not title or len(title) < 10:
                                continue
                            
                            # URL과 날짜 추출 (위와 동일한 로직)
                            news_url = ''
                            if title_elem.name == 'a' and title_elem.get('href'):
                                news_url = title_elem['href']
                            else:
                                parent = title_elem.parent
                                while parent and parent.name != 'body':
                                    link = parent.find('a', href=True)
                                    if link and link.get('href'):
                                        news_url = link['href']
                                        break
                                    parent = parent.parent
                            
                            if news_url and not news_url.startswith('http'):
                                if news_url.startswith('//'):
                                    news_url = 'https:' + news_url
                                else:
                                    news_url = 'https://www.mk.co.kr' + news_url
                            
                            news_list.append({
                                'title': title,
                                'date': date,
                                'url': news_url
                            })
                        except Exception as e:
                            continue
                
            except Exception as e:
                print(f"  ⚠️ 검색 결과 파싱 중 오류: {e}")
                # 디버깅을 위해 페이지 소스 일부 출력
                print(f"  📄 페이지 제목: {driver.title}")
                print(f"  📄 URL: {driver.current_url}")
                
                # 페이지 구조 디버깅
                try:
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # AI 관련 요소 확인
                    ai_elements = soup.select('[class*="ai"], [id*="ai"]')
                    print(f"  📄 AI 관련 요소: {len(ai_elements)}개")
                    
                    # 뉴스 관련 요소 확인
                    news_elements = soup.select('h3.news_ttl, div[class*="news"], [class*="result"]')
                    print(f"  📄 뉴스 관련 요소: {len(news_elements)}개")
                    
                    # 첫 번째 h3 요소들 출력
                    h3_elements = soup.find_all('h3')[:5]
                    print(f"  📄 첫 5개 h3 요소:")
                    for i, h3 in enumerate(h3_elements):
                        print(f"    {i+1}. {h3.text.strip()[:50]}...")
                except:
                    pass
                
        except Exception as e:
            print(f"❌ 뉴스 수집 오류 ({ticker}): {e}")
            
        finally:
            driver.quit()
        
        print(f"  ✅ 수집 완료: {len(news_list)}개 뉴스")
        return news_list
    
    def fetch_ticker_news(self, ticker: str, company_name: str, date: str) -> List[Dict[str, str]]:
        """
        네이버 증권에서 종목 뉴스를 Selenium으로 크롤링
        
        Args:
            ticker: 종목 코드 (예: '005930')
            company_name: 회사명 (예: '삼성전자')
            date: 기준 날짜 (YYYY-MM-DD)
            
        Returns:
            List[Dict]: 뉴스 리스트 [{title, date, url, source}, ...]
        """
        print(f"📡 네이버 증권에서 {ticker} ({company_name}) 뉴스 수집 시작...")
        
        # 경제 전문 매체 리스트
        QUALITY_SOURCES = [
            '한국경제', '한경', '연합인포맥스', '인포맥스',
            '매일경제', '매경', '서울경제', '이데일리',
            '머니투데이', '파이낸셜뉴스', '아시아경제',
            '헤럴드경제', '조선비즈', '뉴스1', '뉴시스'
        ]
        
        news_list = []
        driver = None
        
        try:
            # Selenium 드라이버 설정
            chrome_options = webdriver.ChromeOptions()
            if not self.debug:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # 이미지 로딩 비활성화 (속도 향상)
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)
            
            serv = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=serv, options=chrome_options)
            
            # 네이버 증권 뉴스 페이지
            url = f"https://finance.naver.com/item/news.naver?code={ticker}"
            print(f"  📄 페이지 접속: {url}")
            
            driver.get(url)
            
            # iframe 대기 및 전환
            try:
                # iframe이 로드될 때까지 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "news_frame"))
                )
                
                # iframe으로 전환
                news_iframe = driver.find_element(By.ID, "news_frame")
                driver.switch_to.frame(news_iframe)
                print("  ✅ 뉴스 프레임 진입 성공")
                
                # 뉴스 테이블 대기
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.type5"))
                )
                
            except Exception as e:
                print(f"  ⚠️ iframe 전환 실패: {e}")
                # iframe 없이 시도
                pass
            
            # 페이지 소스 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 뉴스 테이블 찾기
            news_table = soup.find('table', class_='type5')
            if not news_table:
                print("  ⚠️ 뉴스 테이블을 찾을 수 없습니다.")
                return []
            
            # 뉴스 행 찾기
            rows = news_table.find_all('tr')
            print(f"  📊 {len(rows)}개 행 발견")
            
            news_count = 0
            
            for row in rows:
                # 헤더 행 스킵
                if row.find('th'):
                    continue
                
                # 제목 셀 찾기
                title_cell = row.find('td', class_='title')
                if not title_cell:
                    continue
                
                # 제목과 링크
                link_elem = title_cell.find('a')
                if not link_elem:
                    continue
                
                title = link_elem.text.strip()
                news_url = link_elem.get('href', '')
                
                # 절대 URL로 변환
                if news_url and not news_url.startswith('http'):
                    if news_url.startswith('//'):
                        news_url = 'https:' + news_url
                    else:
                        news_url = 'https://finance.naver.com' + news_url
                
                # 정보 제공자 (언론사)
                info_cell = row.find('td', class_='info')
                source = info_cell.text.strip() if info_cell else '알 수 없음'
                
                # 날짜
                date_cell = row.find('td', class_='date')
                news_date = date_cell.text.strip() if date_cell else date
                
                # 경제 전문지 필터링
                is_quality = any(s in source for s in QUALITY_SOURCES)
                
                if not is_quality and not self.debug:
                    continue
                
                news_item = {
                    'title': title,
                    'date': news_date,
                    'url': news_url,
                    'source': source
                }
                
                news_list.append(news_item)
                news_count += 1
                
                if self.debug:
                    print(f"  ✅ [{source}] {title[:50]}...")
                
                # 최대 20개만 수집
                if news_count >= 20:
                    break
            
            print(f"  📰 {len(news_list)}개 뉴스 수집")
            
            # 날짜순 정렬
            news_list.sort(key=lambda x: x['date'], reverse=True)
            
            # 최대 10개만 반환
            final_news = news_list[:10]
            
            # 소스별 통계
            if final_news:
                source_stats = {}
                for news in final_news:
                    src = news['source']
                    source_stats[src] = source_stats.get(src, 0) + 1
                
                print(f"  📊 소스별 분포:")
                for src, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
                    print(f"     - {src}: {count}개")
            
            return final_news
            
        except Exception as e:
            print(f"❌ 뉴스 수집 오류 ({ticker}): {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            
            # Selenium 실패 시 기존 방식으로 fallback
            print(f"  ⚠️ 기존 방식으로 재시도...")
            return self.fetch_ticker_news_old(ticker, company_name, date)
            
        finally:
            if driver:
                driver.quit()
    
    def fetch_ticker_news_requests(self, ticker: str, company_name: str, date: str) -> List[Dict[str, str]]:
        """
        네이버 증권에서 종목 뉴스를 크롤링하고 경제 전문 매체만 필터링
        
        Args:
            ticker: 종목 코드 (예: '005930')
            company_name: 회사명 (예: '삼성전자')
            date: 기준 날짜 (YYYY-MM-DD)
            
        Returns:
            List[Dict]: 뉴스 리스트 [{title, date, url, source}, ...]
        """
        print(f"📡 네이버 증권에서 {ticker} ({company_name}) 뉴스 수집 시작...")
        
        # 경제 전문 매체 리스트 (한경, 연합인포맥스 중심)
        QUALITY_SOURCES = [
            '한국경제', '한경', '한국경제신문', 'hankyung',
            '연합인포맥스', '인포맥스', 'einfomax',
            '매일경제', '매경', 'mk',
            '서울경제', '서경', 'sedaily',
            '머니투데이', 'moneytoday',
            '이데일리', 'edaily',
            '파이낸셜뉴스', 'fnnews',
            '아시아경제', 'asiae'
        ]
        
        news_list = []
        
        # 날짜 범위 설정 (기본 7일)
        days_back = 7
        end_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = end_date - timedelta(days=days_back)
        
        # 최적화된 헤더
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # 네이버 증권 뉴스 URL
        base_url = "https://finance.naver.com/item/news_news.naver"
        
        try:
            # 페이지별로 크롤링 (최대 5페이지)
            for page in range(1, 6):
                # 요청 간격 조절 (로봇 차단 회피)
                if page > 1:
                    time.sleep(random.uniform(1.0, 2.5))
                
                # URL 파라미터
                params = {
                    'code': ticker,
                    'page': page,
                    'sm': 'entity_id.basic',
                    'clusterId': ''
                }
                
                # 요청 전송
                response = requests.get(base_url, params=params, headers=headers)
                
                if response.status_code != 200:
                    print(f"  ⚠️ 페이지 {page} 요청 실패 (상태 코드: {response.status_code})")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 뉴스 테이블 찾기
                news_table = soup.find('table', class_='type5')
                if not news_table:
                    print(f"  ⚠️ 페이지 {page}에 뉴스 테이블이 없습니다.")
                    break
                
                # 뉴스 항목 추출
                rows = news_table.find_all('tr')
                page_news_count = 0
                
                for row in rows:
                    # 제목과 링크가 있는 행만 처리
                    title_cell = row.find('td', class_='title')
                    if not title_cell:
                        continue
                    
                    link_elem = title_cell.find('a')
                    if not link_elem:
                        continue
                    
                    # 뉴스 정보 추출
                    title = link_elem.text.strip()
                    news_url = 'https://finance.naver.com' + link_elem.get('href', '')
                    
                    # 정보 제공자 추출
                    info_cell = row.find('td', class_='info')
                    source = info_cell.text.strip() if info_cell else '알 수 없음'
                    
                    # 날짜 추출
                    date_cell = row.find('td', class_='date')
                    news_date_str = date_cell.text.strip() if date_cell else ''
                    
                    # 날짜 파싱 및 필터링
                    try:
                        # 다양한 날짜 형식 처리
                        if '시간' in news_date_str or '분' in news_date_str:
                            # 오늘 날짜
                            news_date = end_date
                        elif '.' in news_date_str:
                            # 2024.01.15 형식
                            if len(news_date_str.split('.')[0]) == 2:
                                # 24.01.15 형식
                                news_date_str = '20' + news_date_str
                            news_date = datetime.strptime(news_date_str.split()[0], '%Y.%m.%d')
                        else:
                            # 다른 형식은 오늘로 가정
                            news_date = end_date
                        
                        # 날짜 범위 체크
                        if news_date < start_date:
                            if self.debug:
                                print(f"  ⏭️ 날짜 범위 벗어남: {news_date_str}")
                            continue
                            
                    except Exception as e:
                        if self.debug:
                            print(f"  ⚠️ 날짜 파싱 오류: {news_date_str} - {e}")
                        news_date = end_date
                    
                    # 경제 전문 매체 필터링
                    is_quality_source = any(
                        src.lower() in source.lower() 
                        for src in QUALITY_SOURCES
                    )
                    
                    if not is_quality_source:
                        if self.debug:
                            print(f"  ⏭️ 필터링됨: {source} - {title[:30]}...")
                        continue
                    
                    # 뉴스 추가
                    news_item = {
                        'title': title,
                        'date': news_date.strftime('%Y-%m-%d'),
                        'url': news_url,
                        'source': source
                    }
                    
                    news_list.append(news_item)
                    page_news_count += 1
                    
                    if self.debug:
                        print(f"  ✅ [{source}] {title[:50]}...")
                
                print(f"  📄 페이지 {page}: {page_news_count}개 수집")
                
                # 뉴스가 없거나 날짜 범위를 벗어난 경우 중단
                if page_news_count == 0:
                    break
            
            # 중복 제거 (제목 기준)
            unique_news = []
            seen_titles = set()
            
            for news in news_list:
                title_key = news['title'][:50]  # 앞 50자로 중복 체크
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    unique_news.append(news)
            
            # 날짜순 정렬 (최신순)
            unique_news.sort(key=lambda x: x['date'], reverse=True)
            
            # 최대 10개만 반환 (Claude API 비용 절감)
            final_news = unique_news[:10]
            
            print(f"  ✅ 최종 수집: {len(final_news)}개 (전체 {len(unique_news)}개 중)")
            
            # 소스별 통계
            if final_news:
                source_stats = {}
                for news in final_news:
                    src = news['source']
                    source_stats[src] = source_stats.get(src, 0) + 1
                
                print(f"  📊 소스별 분포:")
                for src, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
                    print(f"     - {src}: {count}개")
            
            return final_news
            
        except Exception as e:
            print(f"❌ 뉴스 수집 오류 ({ticker}): {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            
            # 오류 발생 시 기존 방식으로 fallback
            print(f"  ⚠️ 네이버 증권 크롤링 실패, 기존 방식으로 재시도...")
            return self.fetch_ticker_news_old(ticker, company_name, date)
    
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
                model="claude-3-5-sonnet-20241022",
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
