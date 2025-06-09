import pandas as pd
import time
import requests
import json
from datetime import datetime

import FinanceDataReader as fdr
from pykrx import stock as pystock

from dateutil.relativedelta import relativedelta
import yaml
import ta  # 기술적 분석 라이브러리 추가
import numpy as np


from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os

        
class Slack:
    def activate_slack(self, slack_key):
        self.client = WebClient(token=slack_key)
        
    def post_message(self, message, channel_id=None):
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=message,
                mrkdwn=False
            )
            return response
        except SlackApiError as e:
            print(f"슬랙 메시지 전송 실패: {e.response['error']}")
            return None


class HantuStock(Slack): # HantuStock 클래스로 패키지명 설정
    ######################## init 함수로 HantuStock 기본 기능 개발 ########################
    def __init__(self,api_key,secret_key,account_id):
        self._api_key = api_key
        self._secret_key = secret_key
        self._account_id = account_id
        ### 실전 Domain : https://openapi.koreainvestment.com:9443 || 모의 Domain : https://openapivts.koreainvestment.com:29443
        self._base_url = 'https://openapivts.koreainvestment.com:29443'
        self._account_suffix = '01'

        self._access_token = self.get_access_token() # 접근토큰 발급, 헤더 생성 등 자주쓰는 기능 함수화
        
        # AI 기능 초기화
        self.ai_cache = {}  # AI 분석 결과 캐시
        self.last_ai_update = None

    ######################## 접근토큰 발급, 헤더 생성 등 자주쓰는 기능 함수화 ########################
    def get_access_token(self):
        while True:
            try:
                headers = {"content-type":"application/json"}
                body = {
                        "grant_type":"client_credentials",
                        "appkey":self._api_key, 
                        "appsecret":self._secret_key,
                        }
                url = self._base_url + '/oauth2/tokenP'
                res = requests.post(url, headers=headers, data=json.dumps(body)).json()
                return res['access_token']
            except Exception as e:
                print('ERROR: get_access_token error. Retrying in 10 seconds...: {}'.format(e))
                time.sleep(10)
                
    def get_header(self,tr_id): # 접근토큰 발급, 헤더 생성 등 자주쓰는 기능 함수화
        headers = {"content-type":"application/json",
                "appkey":self._api_key, 
                "appsecret":self._secret_key,
                "authorization":f"Bearer {self._access_token}",
                "tr_id":tr_id,
                }
        return headers

    def _requests(self,url,headers,params,request_type = 'get'):
        while True:
            try:
                if request_type == 'get':
                    response = requests.get(url, headers=headers, params=params)
                else:
                    response = requests.post(url, headers=headers, data=json.dumps(params))
                returning_headers = response.headers
                contents = response.json()
                if contents['rt_cd'] != '0':
                    if contents['msg_cd'] == 'EGW00201': # {'rt_cd': '1', 'msg_cd': 'EGW00201', 'msg1': '초당 거래건수를 초과하였습니다.'}
                        time.sleep(0.1)
                        continue
                    else:
                        print('ERROR at _requests: {}, headers: {}, params: {}'.format(contents,headers,params))
                break
            except requests.exceptions.SSLError as e:
                print('SSLERROR: {}'.format(e))
                time.sleep(0.1)
            except Exception as e:
                print('other _requests error: {}'.format(e))
                time.sleep(0.1)
        return returning_headers, contents

    ######################## 시장 데이터 가져오기 기능 함수화 ########################
    def get_past_data(self,ticker,n=100): 
        temp = fdr.DataReader(ticker)
        temp.columns = list(map(lambda x: str.lower(x),temp.columns))
        temp.index.name = 'timestamp'
        temp = temp.reset_index()
        if n == 1:
            temp = temp.iloc[-1]
        else:
            temp = temp.tail(n)

        return temp
    
    def get_past_data_total(self,n=10): # 시장 데이터 가져오기 기능 함수화
        """
            전체 시장 past_data를 더 빨리 불러올 수 있는 기능
        """
        total_data = None
        days_passed = 0
        days_collected = 0
        today_timestamp = datetime.now()
        while (days_collected < n) and days_passed < max(10,n*2): # 하루씩 돌아가면서 데이터 받아오기
            iter_date = str(today_timestamp - relativedelta(days=days_passed)).split(' ')[0]
            data1 = pystock.get_market_ohlcv(iter_date,market='KOSPI')
            data2 = pystock.get_market_ohlcv(iter_date,market='KOSDAQ')
            data = pd.concat([data1,data2])

            days_passed += 1
            if data['거래대금'].sum() == 0: continue # 주말일 경우 패스
            else: days_collected += 1
            # 안전한 컬럼명 매핑
            column_mapping = {
                '시가': 'open',
                '고가': 'high',
                '저가': 'low',
                '종가': 'close',
                '거래량': 'volume',
                '거래대금': 'trade_amount',
                '등락률': 'diff',
                '시가총액': 'market_cap'
            }

            data = data.rename(columns=column_mapping)
            data.index.name = 'ticker'

            data['timestamp'] = iter_date
            
            if total_data is None:
                total_data = data.copy()
            else:
                total_data = pd.concat([total_data,data])

        total_data = total_data.sort_values('timestamp').reset_index()

        # 거래가 없었던 종목은(거래정지) open/high/low가 0으로 표시됨. 이런 경우, open/high/low를 close값으로 바꿔줌
        total_data['open'] = total_data['open'].where(total_data['open'] > 0,other=total_data['close'])
        total_data['high'] = total_data['high'].where(total_data['high'] > 0,other=total_data['close'])
        total_data['low'] = total_data['low'].where(total_data['low'] > 0,other=total_data['close'])

        return total_data

    ######################## 계좌 데이터 가져오기 ########################
    def get_holding_stock(self,ticker = None,remove_stock_warrant = True):
        order_result = self._get_order_result(get_account_info = False)

        if ticker is not None:
            for order in order_result:
                if order['pdno'] == ticker:
                    return int(order['hldg_qty'])
            return 0
        else:
            returning_result = {}
            for order in order_result:
                order_tkr = order['pdno']
                if remove_stock_warrant and order_tkr[0] == 'J': continue # 신주인수권 제외
                returning_result[order_tkr] = int(order['hldg_qty'])
            return returning_result

    def _get_order_result(self,get_account_info = False):
        headers = self.get_header('VTTC8434R')  # 실전 계좌 : TTTC8434R | 모의 계좌 : VTTC8434R
        output1_result = []
        cont = True
        ctx_area_fk100 = ''
        ctx_area_nk100 = ''
        while cont:
            params = {
                "CANO":self._account_id,
                "ACNT_PRDT_CD": self._account_suffix,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "N",
                "INQR_DVSN": "01",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": ctx_area_fk100,
                "CTX_AREA_NK100": ctx_area_nk100
            }

            url = self._base_url + '/uapi/domestic-stock/v1/trading/inquire-balance'
            hd,order_result = self._requests(url, headers, params)
            if get_account_info:
                return order_result['output2'][0]
            else:
                cont = hd['tr_cont'] in ['F','M']
                headers['tr_cont'] = 'N'
                ctx_area_fk100 = order_result['ctx_area_fk100']
                ctx_area_nk100 = order_result['ctx_area_nk100']
                output1_result = output1_result + order_result['output1']

        return output1_result

    def get_holding_cash(self):
        order_result = self._get_order_result(get_account_info = True)
        return float(order_result['prvs_rcdl_excc_amt'])

    ######################## 주문 기능 ########################
    def bid(self,ticker,price,quantity,quantity_scale):
        """ 
            price가 numeric이면 지정가주문, price = 'market'이면 시장가주문\n
            quantity_scale: CASH 혹은 STOCK
        """     
        if price in ['market','',0]:
            # 시장가주문
            price = '0'
            ord_dvsn = '01'
            if quantity_scale == 'CASH':
                price_for_quantity_calculation = self.get_past_data(ticker).iloc[-1]['close']
        else:
            # 지정가주문
            price_for_quantity_calculation = price
            price = str(price)
            ord_dvsn = '00'
            
        if quantity_scale == 'CASH':
            quantity = int(quantity/price_for_quantity_calculation)
        elif quantity_scale == 'STOCK':
            quantity = int(quantity)
        else:
            print('ERROR: quantity_scale should be one of CASH, STOCK')
            return None, 0

        headers = self.get_header('VTTC0011U')  # 실전 TR ID : (매도) TTTC0011U (매수) TTTC0012U | 모의 TR ID : (매도) VTTC0011U (매수) VTTC0012U
        params = {
                "CANO":self._account_id,
                "ACNT_PRDT_CD": self._account_suffix,
                'PDNO':ticker,
                'ORD_DVSN':ord_dvsn,
                'ORD_QTY':str(quantity),
                'ORD_UNPR':str(price)
                }

        url = self._base_url + '/uapi/domestic-stock/v1/trading/order-cash'
        hd,order_result = self._requests(url, headers=headers, params=params, request_type='post')
        if order_result['rt_cd'] == '0':
            return order_result['output']['ODNO'], quantity
        else:
            print(order_result['msg1'])
            return None, 0

    def ask(self,ticker,price,quantity,quantity_scale):
        """ 
            price가 numeric이면 지정가주문, price = 'market'이면 시장가주문\n
            quantity_scale: CASH 혹은 STOCK
        """
        if price in ['market','',0]:
            # 시장가주문
            price = '0'
            ord_dvsn = '01'
            if quantity_scale == 'CASH':
                price_for_quantity_calculation = self.get_past_data(ticker).iloc[-1]['close']
        else:
            # 지정가주문
            price_for_quantity_calculation = price
            price = str(price)
            ord_dvsn = '00'
            
        if quantity_scale == 'CASH':
            quantity = int(quantity/price_for_quantity_calculation)
        elif quantity_scale == 'STOCK':
            quantity = int(quantity)
        else:
            print('ERROR: quantity_scale should be one of CASH, STOCK')
            return None, 0

        headers = self.get_header('VTTC0012U')  # 실전 TR ID : (매도) TTTC0011U (매수) TTTC0012U | 모의 TR ID : (매도) VTTC0011U (매수) VTTC0012U
        params = {
                "CANO":self._account_id,
                "ACNT_PRDT_CD": self._account_suffix,
                'PDNO':ticker,
                'ORD_DVSN':ord_dvsn,
                'ORD_QTY':str(quantity),
                'ORD_UNPR':str(price)
                }
        url = self._base_url + '/uapi/domestic-stock/v1/trading/order-cash'
        hd,order_result = self._requests(url, headers, params, 'post')

        if order_result['rt_cd'] == '0':
            if order_result['output']['ODNO'] is None:
                print('ask error',order_result['msg1'])
                return None, 0
            return order_result['output']['ODNO'], quantity
        else:
            print(order_result['msg1'])
            return None, 0
        
    ######################## AI 분석 기능 추가 ########################
    def get_technical_indicators(self, ticker, n=100):
        """종목의 기술적 지표 계산"""
        try:
            data = self.get_past_data(ticker, n=n)
            if len(data) < 50:
                return None
            
            # 기본 이동평균
            data['ma_5'] = data['close'].rolling(5).mean()
            data['ma_10'] = data['close'].rolling(10).mean()
            data['ma_20'] = data['close'].rolling(20).mean()
            data['ma_60'] = data['close'].rolling(60).mean()
            
            # RSI
            data['rsi_14'] = ta.momentum.rsi(data['close'], window=14)
            
            # MACD
            data['macd'] = ta.trend.macd(data['close'])
            data['macd_signal'] = ta.trend.macd_signal(data['close'])
            
            # 볼린저 밴드
            data['bb_upper'] = ta.volatility.bollinger_hband(data['close'])
            data['bb_lower'] = ta.volatility.bollinger_lband(data['close'])
            data['bb_middle'] = ta.volatility.bollinger_mavg(data['close'])
            
            # 스토캐스틱
            data['stoch_k'] = ta.momentum.stoch(data['high'], data['low'], data['close'])
            data['stoch_d'] = ta.momentum.stoch_signal(data['high'], data['low'], data['close'])
            
            # 거래량 지표
            data['volume_sma'] = data['volume'].rolling(20).mean()
            data['volume_ratio'] = data['volume'] / data['volume_sma']
            
            return data
            
        except Exception as e:
            print(f'기술적 지표 계산 오류 ({ticker}): {e}')
            return None
    
    def get_ai_market_signal(self, ticker):
        """AI 기반 시장 신호 분석"""
        try:
            # 캐시 확인 (5분간 유효)
            cache_key = f"ai_signal_{ticker}"
            current_time = datetime.now()
            
            if (cache_key in self.ai_cache and 
                self.ai_cache[cache_key]['timestamp'] and
                (current_time - datetime.fromisoformat(self.ai_cache[cache_key]['timestamp'])).seconds < 300):
                return self.ai_cache[cache_key]['signal']
            
            # 기술적 지표 데이터 가져오기
            data = self.get_technical_indicators(ticker, n=100)
            if data is None or len(data) < 50:
                return {'signal': 'NEUTRAL', 'confidence': 0.5, 'reasons': ['데이터 부족']}
            
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            signal_score = 0
            reasons = []
            
            # 1. 이동평균 분석
            ma_signals = 0
            if latest['close'] > latest['ma_5']:
                ma_signals += 1
            if latest['close'] > latest['ma_10']:
                ma_signals += 1
            if latest['close'] > latest['ma_20']:
                ma_signals += 1
                
            if ma_signals >= 2:
                signal_score += 0.2
                reasons.append('이동평균 상승세')
            elif ma_signals == 0:
                signal_score -= 0.2
                reasons.append('이동평균 하락세')
            
            # 2. RSI 분석
            rsi = latest['rsi_14']
            if not pd.isna(rsi):
                if rsi < 30:
                    signal_score += 0.3
                    reasons.append('RSI 과매도')
                elif rsi > 70:
                    signal_score -= 0.3
                    reasons.append('RSI 과매수')
                elif 40 <= rsi <= 60:
                    signal_score += 0.1
                    reasons.append('RSI 중립권')
            
            # 3. MACD 분석
            if not pd.isna(latest['macd']) and not pd.isna(latest['macd_signal']):
                if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                    signal_score += 0.25
                    reasons.append('MACD 골든크로스')
                elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                    signal_score -= 0.25
                    reasons.append('MACD 데드크로스')
            
            # 4. 볼린저 밴드 분석
            if not pd.isna(latest['bb_lower']) and not pd.isna(latest['bb_upper']):
                bb_position = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])
                if bb_position < 0.2:
                    signal_score += 0.2
                    reasons.append('볼린저밴드 하단')
                elif bb_position > 0.8:
                    signal_score -= 0.2
                    reasons.append('볼린저밴드 상단')
            
            # 5. 거래량 분석
            if not pd.isna(latest['volume_ratio']):
                if latest['volume_ratio'] > 1.5:
                    signal_score += 0.15
                    reasons.append('거래량 급증')
                elif latest['volume_ratio'] < 0.5:
                    signal_score -= 0.1
                    reasons.append('거래량 위축')
            
            # 6. 가격 모멘텀
            price_change_1d = (latest['close'] - prev['close']) / prev['close']
            if len(data) >= 6:
                price_change_5d = (latest['close'] - data.iloc[-6]['close']) / data.iloc[-6]['close']
            else:
                price_change_5d = 0
            
            if price_change_1d > 0.03:
                signal_score += 0.1
                reasons.append('단기 강세')
            elif price_change_1d < -0.03:
                signal_score -= 0.1
                reasons.append('단기 약세')
            
            # 신호 결정
            confidence = min(abs(signal_score), 1.0)
            
            if signal_score > 0.3:
                signal = 'STRONG_BUY'
            elif signal_score > 0.15:
                signal = 'BUY'
            elif signal_score > -0.15:
                signal = 'NEUTRAL'
            elif signal_score > -0.3:
                signal = 'SELL'
            else:
                signal = 'STRONG_SELL'
            
            result = {
                'signal': signal,
                'confidence': confidence,
                'score': signal_score,
                'reasons': reasons,
                'rsi': rsi if not pd.isna(rsi) else None,
                'volume_ratio': latest['volume_ratio'] if not pd.isna(latest['volume_ratio']) else None
            }
            
            # 캐시에 저장
            self.ai_cache[cache_key] = {
                'signal': result,
                'timestamp': current_time.isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f'AI 시장 신호 분석 오류 ({ticker}): {e}')
            return {'signal': 'NEUTRAL', 'confidence': 0.5, 'reasons': ['분석 오류']}
    
    def get_ai_risk_assessment(self, ticker):
        """AI 기반 리스크 평가"""
        try:
            data = self.get_past_data(ticker, n=60)
            if len(data) < 30:
                return {'risk_level': 'UNKNOWN', 'risk_score': 0.5}
            
            # 변동성 계산
            returns = data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 연환산 변동성
            
            # 최대 낙폭 계산
            rolling_max = data['close'].expanding().max()
            drawdown = (data['close'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # 거래량 변동성
            volume_cv = data['volume'].std() / data['volume'].mean()
            
            # 리스크 점수 계산 (0: 낮음, 1: 높음)
            risk_score = 0
            
            # 변동성 기준
            if volatility > 0.4:
                risk_score += 0.4
            elif volatility > 0.25:
                risk_score += 0.2
            
            # 최대 낙폭 기준
            if max_drawdown < -0.3:
                risk_score += 0.3
            elif max_drawdown < -0.2:
                risk_score += 0.2
            
            # 거래량 변동성
            if volume_cv > 2.0:
                risk_score += 0.2
            elif volume_cv > 1.5:
                risk_score += 0.1
            
            # 최근 급등/급락 체크
            if len(data) >= 6:
                recent_change = (data['close'].iloc[-1] - data['close'].iloc[-6]) / data['close'].iloc[-6]
                if abs(recent_change) > 0.15:
                    risk_score += 0.1
            
            # 리스크 레벨 결정
            if risk_score > 0.7:
                risk_level = 'VERY_HIGH'
            elif risk_score > 0.5:
                risk_level = 'HIGH'
            elif risk_score > 0.3:
                risk_level = 'MEDIUM'
            elif risk_score > 0.15:
                risk_level = 'LOW'
            else:
                risk_level = 'VERY_LOW'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'volatility': volatility,
                'max_drawdown': max_drawdown,
                'volume_cv': volume_cv
            }
            
        except Exception as e:
            print(f'리스크 평가 오류 ({ticker}): {e}')
            return {'risk_level': 'UNKNOWN', 'risk_score': 0.5}
    
    def get_ai_enhanced_analysis(self, ticker):
        """종합 AI 분석 결과"""
        try:
            market_signal = self.get_ai_market_signal(ticker)
            risk_assessment = self.get_ai_risk_assessment(ticker)
            
            # 종합 점수 계산
            signal_weight = 0.7
            risk_weight = 0.3
            
            signal_score = market_signal.get('score', 0)
            risk_penalty = risk_assessment.get('risk_score', 0.5) * risk_weight
            
            final_score = (signal_score * signal_weight) - risk_penalty
            
            # 최종 추천
            if final_score > 0.25 and market_signal['signal'] in ['BUY', 'STRONG_BUY']:
                recommendation = 'BUY'
            elif final_score < -0.25 and market_signal['signal'] in ['SELL', 'STRONG_SELL']:
                recommendation = 'SELL'
            else:
                recommendation = 'HOLD'
            
            return {
                'ticker': ticker,
                'recommendation': recommendation,
                'final_score': final_score,
                'confidence': market_signal.get('confidence', 0.5),
                'market_signal': market_signal,
                'risk_assessment': risk_assessment,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f'종합 AI 분석 오류 ({ticker}): {e}')
            return {
                'ticker': ticker,
                'recommendation': 'HOLD',
                'final_score': 0,
                'confidence': 0.5,
                'error': str(e)
            }
    
    def bulk_ai_analysis(self, tickers):
        """여러 종목 일괄 AI 분석"""
        results = []
        
        print(f"🤖 {len(tickers)}개 종목 AI 분석 시작...")
        
        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"  {i}/{len(tickers)} {ticker} 분석 중...")
                analysis = self.get_ai_enhanced_analysis(ticker)
                results.append(analysis)
                
                # API 호출 제한 고려하여 잠시 대기
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ {ticker} 분석 실패: {e}")
                continue
        
        # 추천도 순으로 정렬
        results.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        print(f"✅ AI 분석 완료: {len(results)}개 결과")
        return results
