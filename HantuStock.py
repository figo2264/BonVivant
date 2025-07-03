import pandas as pd
import time
import requests
import json
from datetime import datetime

import FinanceDataReader as fdr
from pykrx import stock as pystock

from dateutil.relativedelta import relativedelta


from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

        
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
    def __init__(self,api_key,secret_key,account_id,mode='simulation'):
        self._api_key = api_key
        self._secret_key = secret_key
        self._account_id = account_id
        self._mode = mode
        
        # 모드에 따른 URL 및 TR ID 접두사 설정
        if mode == 'real':
            self._base_url = 'https://openapi.koreainvestment.com:9443'
            self._tr_prefix = 'T'  # 실거래 TR ID 접두사
            print("🔴 실거래 모드로 초기화됩니다!")
        else:
            self._base_url = 'https://openapivts.koreainvestment.com:29443'
            self._tr_prefix = 'V'  # 모의투자 TR ID 접두사
            print("🟢 모의투자 모드로 초기화됩니다.")
            
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
                
    def get_header(self,tr_id_suffix): # 접근토큰 발급, 헤더 생성 등 자주쓰는 기능 함수화
        # TR ID를 모드에 따라 동적으로 생성 (V/T + suffix)
        tr_id = f"{self._tr_prefix}{tr_id_suffix}"
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
        headers = self.get_header('TTC8434R')  # suffix만 전달 (실전/모의는 자동 처리)
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

        headers = self.get_header('TTC0012U')  # suffix만 전달 (실전/모의는 자동 처리)
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

        headers = self.get_header('TTC0011U')  # suffix만 전달 (실전/모의는 자동 처리)
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
