# AI 강화된 6-7 전략 (기존 이동평균 + AI 예측)

import pandas as pd
import time
import requests
import json
from datetime import datetime
import numpy as np

import FinanceDataReader as fdr
from pykrx import stock as pystock
from dateutil.relativedelta import relativedelta
import yaml
import ta

# AI 모델
from sklearn.tree import DecisionTreeClassifier
import pickle
import warnings
warnings.filterwarnings('ignore')

with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

api_key = config['hantu']['api_key']
secret_key = config['hantu']['secret_key']
account_id = config['hantu']['account_id']

# HantuStock 패키지 불러오기
from HantuStock import HantuStock

ht = HantuStock(api_key=api_key, secret_key=secret_key, account_id=account_id)

# AI 강화 전략 데이터 로드
try:
    with open('ai_strategy_data.json', 'r') as f:
        strategy_data = json.load(f)
except:
    # 기존 strategy_data.json과 호환성 유지
    try:
        with open('strategy_data.json', 'r') as f:
            old_data = json.load(f)
            strategy_data = {
                'holding_period': old_data.get('holding_period', {}),
                'ai_predictions': {},
                'ai_enabled': True,
                'performance_log': []
            }
    except:
        strategy_data = {
            'holding_period': {},
            'ai_predictions': {},
            'ai_enabled': True,
            'performance_log': []
        }

def create_ai_features_simple(data):
    """AI를 위한 간단한 기술적 지표 생성"""
    try:
        # 수익률 계산
        for period in [1, 3, 5, 10, 20]:
            data[f'return_{period}d'] = data['close'].pct_change(period)
        
        # 이동평균 및 비율
        for ma_period in [5, 10, 20]:
            data[f'ma_{ma_period}'] = data['close'].rolling(ma_period).mean()
            data[f'price_ma_ratio_{ma_period}'] = data['close'] / data[f'ma_{ma_period}']
        
        # 기술적 지표
        data['rsi_14'] = ta.momentum.rsi(data['close'], window=14)
        data['volume_ratio_5d'] = data['volume'] / data['volume'].rolling(5).mean()
        data['volatility_10d'] = data['close'].pct_change().rolling(10).std()
        
        # 볼린저 밴드 위치
        bb_middle = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        data['bb_position'] = (data['close'] - bb_middle) / (2 * bb_std)
        
        return data
    except Exception as e:
        print(f"AI 피처 생성 오류: {e}")
        return data

def get_ai_score(ticker):
    """AI 기반 매수 점수 계산 (0.0~1.0)"""
    try:
        # 최근 데이터 가져오기
        data = ht.get_past_data(ticker, n=50)
        if len(data) < 30:
            return 0.5  # 데이터 부족시 중립
        
        data = create_ai_features_simple(data)
        latest = data.iloc[-1]
        
        # NaN 체크
        if pd.isna(latest['rsi_14']) or pd.isna(latest['price_ma_ratio_20']):
            return 0.5
        
        score = 0.5  # 기본점수
        
        # 1. RSI 기반 과매도 판단
        rsi = latest['rsi_14']
        if rsi < 25:
            score += 0.25  # 강한 과매도
        elif rsi < 35:
            score += 0.15  # 과매도
        elif rsi > 75:
            score -= 0.2   # 과매수
        
        # 2. 이동평균 대비 위치 (현재 전략과 일치)
        ma_signals = 0
        for period in [5, 10, 20]:
            if latest[f'price_ma_ratio_{period}'] < 0.98:  # 이동평균 아래
                ma_signals += 1
        
        if ma_signals >= 2:
            score += 0.2  # 이동평균 아래에서 매수 기회
        
        # 3. 단기 반등 시그널
        if latest['return_1d'] > 0.01 and latest['return_3d'] < -0.02:
            score += 0.15  # 단기 반등
        
        # 4. 거래량 급증
        if latest['volume_ratio_5d'] > 1.8:
            score += 0.1
        elif latest['volume_ratio_5d'] > 1.3:
            score += 0.05
        
        # 5. 변동성 조정
        if latest['volatility_10d'] > 0.05:  # 고변동성
            score -= 0.1
        
        # 6. 볼린저 밴드 하단 근처
        if latest['bb_position'] < -0.8:
            score += 0.15
        
        return max(0.0, min(1.0, score))
        
    except Exception as e:
        print(f"AI 점수 계산 오류 ({ticker}): {e}")
        return 0.5

def get_ai_hold_signal(ticker):
    """보유 종목에 대한 AI 홀드/매도 시그널"""
    try:
        data = ht.get_past_data(ticker, n=30)
        if len(data) < 20:
            return 0.5
        
        data = create_ai_features_simple(data)
        latest = data.iloc[-1]
        
        hold_score = 0.5
        
        # 1. 단기 모멘텀
        if latest['return_1d'] > 0.02:
            hold_score += 0.3  # 강한 상승
        elif latest['return_1d'] > 0:
            hold_score += 0.1  # 약한 상승
        
        # 2. RSI 과매수 체크
        if latest['rsi_14'] > 80:
            hold_score -= 0.3  # 과매수시 매도 신호
        elif latest['rsi_14'] > 70:
            hold_score -= 0.1
        
        # 3. 볼린저 밴드 상단 근처
        if latest['bb_position'] > 0.8:
            hold_score -= 0.2
        
        return max(0.0, min(1.0, hold_score))
        
    except:
        return 0.5

def enhanced_stock_selection():
    """AI 강화 종목 선정 (기존 전략 + AI)"""
    print("🤖 AI 강화 종목 분석 시작...")
    
    # 기존 전략 로직
    data = ht.get_past_data_total(n=20)
    
    # 5일 종가 최저값, 20일 이동평균 계산하기
    data['5d_min_close'] = data.groupby('ticker')['close'].rolling(5).min().reset_index().set_index('level_1')['close']
    data['20d_ma'] = data.groupby('ticker')['close'].rolling(20).mean().reset_index().set_index('level_1')['close']

    # 기존 조건에 맞는 종목 찾기
    today_data = data[data['timestamp'] == data['timestamp'].max()]
    traditional_candidates = today_data[
        (today_data['5d_min_close'] == today_data['close']) & 
        (today_data['20d_ma'] > today_data['close'])
    ]
    
    print(f"📊 전통적 조건 후보: {len(traditional_candidates)}개")
    
    # AI 점수 추가 분석
    ai_enhanced_candidates = []
    
    for _, row in traditional_candidates.iterrows():
        ticker = row['ticker']
        
        # AI 점수 계산
        ai_score = get_ai_score(ticker)
        
        # 결합 점수: 기존 거래량 가중치 + AI 보정
        # AI 점수가 높을수록 거래량에 추가 가중치
        ai_multiplier = 0.5 + ai_score  # 0.5 ~ 1.5 배수
        combined_score = row['trade_amount'] * ai_multiplier
        
        ai_enhanced_candidates.append({
            'ticker': ticker,
            'trade_amount': row['trade_amount'],
            'ai_score': ai_score,
            'combined_score': combined_score
        })
        
        # AI 예측 정보 저장
        strategy_data['ai_predictions'][ticker] = {
            'score': ai_score,
            'timestamp': datetime.now().isoformat(),
            'traditional_rank': int(row['trade_amount'])
        }
    
    # AI 강화 점수로 정렬
    ai_enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # 결과 출력 및 선정
    selected_tickers = []
    for i, candidate in enumerate(ai_enhanced_candidates[:15]):  # 상위 15개 확인
        ticker = candidate['ticker']
        ai_score = candidate['ai_score']
        
        print(f"{i+1:2d}. {ticker}: AI={ai_score:.3f}, 거래량={candidate['trade_amount']:>10.0f}, 결합점수={candidate['combined_score']:>12.0f}")
        
        # AI 점수가 0.6 이상이고 상위 10개만 선정
        if ai_score >= 0.6 and len(selected_tickers) < 10:
            selected_tickers.append(ticker)
    
    print(f"🎯 AI 최종 선정: {len(selected_tickers)}개 종목")
    return selected_tickers

# 현재 보유중인 종목 조회
holdings = ht.get_holding_stock()

# holding_period를 하루씩 높여줌
for ticker in holdings:
    if ticker not in strategy_data['holding_period']:
        strategy_data['holding_period'][ticker] = 1
    else:
        strategy_data['holding_period'][ticker] += 1

# AI 강화 매도 전략
ticker_to_sell = []
for ticker in holdings:
    holding_days = strategy_data['holding_period'][ticker]
    should_sell = False
    
    # 기본 3일 룰
    if holding_days >= 3:
        should_sell = True
        
        # AI 홀드 시그널 체크 (3일차에만)
        if holding_days == 3 and strategy_data['ai_enabled']:
            hold_signal = get_ai_hold_signal(ticker)
            
            if hold_signal >= 0.75:
                should_sell = False
                print(f"🤖 {ticker}: AI 강홀드 신호로 1일 연장 (신호강도: {hold_signal:.3f})")
            elif hold_signal <= 0.25:
                print(f"⚠️ {ticker}: AI 매도 신호 (신호강도: {hold_signal:.3f})")
        
    # 안전장치: 5일 이상은 무조건 매도
    if holding_days >= 5:
        should_sell = True
        print(f"⏰ {ticker}: 5일 안전룰 적용")
    
    if should_sell:
        ticker_to_sell.append(ticker)

# 전략의 시간을 체크할 while문
while True:
    current_time = datetime.now()

    # 15:20에 전략 실행
    if current_time.hour == 15 and current_time.minute == 20:
        print("🚀 AI 강화 전략 실행 시작!")
        print(f"📊 현재 보유: {len(holdings)}개, 매도 예정: {len(ticker_to_sell)}개")
        
        # === 매도 실행 ===
        for ticker in ticker_to_sell:
            print(f"📤 {ticker} 매도 (보유기간: {strategy_data['holding_period'][ticker]}일)")
            ht.ask(ticker, 'market', holdings[ticker], 'STOCK')
            strategy_data['holding_period'][ticker] = 0

        # === AI 강화 매수 실행 ===
        entry_tickers = enhanced_stock_selection()
        
        # 현재 보유중인 종목은 매수후보에서 제외
        current_holdings = set(holdings.keys())
        final_entry_tickers = [t for t in entry_tickers if t not in current_holdings]
        
        print(f"📥 최종 매수 대상: {len(final_entry_tickers)}개")
        
        # 선정한 종목 매수
        for ticker in final_entry_tickers:
            print(f"📥 {ticker} AI 추천 매수")
            ht.bid(ticker, 'market', 1, 'STOCK')

        # 성과 로깅
        strategy_data['performance_log'].append({
            'timestamp': datetime.now().isoformat(),
            'sold_count': len(ticker_to_sell),
            'bought_count': len(final_entry_tickers),
            'total_holdings': len(holdings) - len(ticker_to_sell) + len(final_entry_tickers),
            'ai_enabled': strategy_data['ai_enabled']
        })

        # 전략 데이터 저장
        with open('ai_strategy_data.json', 'w') as f:
            json.dump(strategy_data, f, indent=2, ensure_ascii=False)
        
        print("💾 AI 전략 데이터 저장 완료")
        print("✅ AI 강화 전략 실행 완료!")
        break

    # 루프 돌때마다 1초씩 쉬어줌
    time.sleep(1)
