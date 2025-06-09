# 기술적 분석 강화된 6-7 전략 (기존 이동평균 + 규칙 기반 분석)

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

# AI 모델 임포트
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import lightgbm as lgb
import pickle
import os
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

# 기술적 분석 전략 데이터 로드
try:
    with open('technical_strategy_data.json', 'r') as f:
        strategy_data = json.load(f)
except:
    # 기존 ai_strategy_data.json과 호환성 유지
    try:
        with open('ai_strategy_data.json', 'r') as f:
            old_data = json.load(f)
            strategy_data = {
                'holding_period': old_data.get('holding_period', {}),
                'technical_analysis': old_data.get('ai_predictions', {}),
                'enhanced_analysis_enabled': old_data.get('ai_enabled', True),
                'performance_log': old_data.get('performance_log', [])
            }
    except:
        # legacy strategy_data.json과 호환성 유지
        try:
            with open('strategy_data.json', 'r') as f:
                old_data = json.load(f)
                strategy_data = {
                    'holding_period': old_data.get('holding_period', {}),
                    'technical_analysis': {},
                    'enhanced_analysis_enabled': True,
                    'performance_log': []
                }
        except:
            strategy_data = {
                'holding_period': {},
                'technical_analysis': {},
                'enhanced_analysis_enabled': True,
                'performance_log': []
            }

def create_technical_features(data):
    """기술적 분석을 위한 지표 생성"""
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
        print(f"기술적 지표 생성 오류: {e}")
        return data

def get_technical_score(ticker):
    """규칙 기반 기술적 분석 점수 계산 (0.0~1.0)"""
    try:
        # 최근 데이터 가져오기
        data = ht.get_past_data(ticker, n=50)
        if len(data) < 30:
            return 0.5  # 데이터 부족시 중립
        
        data = create_technical_features(data)
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
        print(f"기술적 점수 계산 오류 ({ticker}): {e}")
        return 0.5

def get_technical_hold_signal(ticker):
    """보유 종목에 대한 규칙 기반 홀드/매도 시그널"""
    try:
        data = ht.get_past_data(ticker, n=30)
        if len(data) < 20:
            return 0.5
        
        data = create_technical_features(data)
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

def prepare_training_data(lookback_days=100):
    """AI 모델 학습용 데이터 준비"""
    print("📚 AI 모델 학습 데이터 준비 중...")
    
    try:
        # 과거 데이터 수집 (더 많은 데이터 확보)
        historical_data = ht.get_past_data_total(n=lookback_days)
        
        if len(historical_data) < 50:
            print("❌ 학습 데이터 부족")
            return None, None
        
        all_features = []
        all_targets = []
        
        # 종목별로 데이터 처리
        for ticker in historical_data['ticker'].unique():
            ticker_data = historical_data[historical_data['ticker'] == ticker].sort_values('timestamp')
            
            if len(ticker_data) < 30:  # 최소 데이터 확보
                continue
                
            # 기술적 지표 생성
            ticker_data = create_technical_features(ticker_data.copy())
            
            # 미래 수익률 계산 (3일 후)
            ticker_data['future_3d_return'] = ticker_data['close'].shift(-3) / ticker_data['close'] - 1
            
            # 유효한 데이터만 사용 (NaN 제거)
            valid_data = ticker_data.dropna()
            
            if len(valid_data) < 10:
                continue
            
            # 피처 선택 (기존 기술적 지표들)
            feature_columns = [
                'return_1d', 'return_3d', 'return_5d', 'return_10d',
                'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
                'rsi_14', 'volume_ratio_5d', 'volatility_10d', 'bb_position'
            ]
            
            # 피처가 모두 존재하는지 확인
            available_features = [col for col in feature_columns if col in valid_data.columns]
            
            if len(available_features) < 8:  # 최소 8개 피처 필요
                continue
            
            features = valid_data[available_features].values
            
            # 타겟 생성: 3일 후 수익률이 2% 이상이면 1
            targets = (valid_data['future_3d_return'] > 0.02).astype(int).values
            
            # 미래 데이터가 없는 마지막 3개 제외
            if len(features) > 3:
                features = features[:-3]
                targets = targets[:-3]
                
                all_features.extend(features)
                all_targets.extend(targets)
        
        if len(all_features) < 50:
            print("❌ 충분한 학습 데이터 확보 실패")
            return None, None
        
        print(f"✅ 학습 데이터 준비 완료: {len(all_features)}개 샘플")
        return np.array(all_features), np.array(all_targets)
        
    except Exception as e:
        print(f"❌ 데이터 준비 오류: {e}")
        return None, None

def train_ai_model():
    """AI 모델 훈련"""
    print("🤖 AI 모델 훈련 시작...")
    
    # 학습 데이터 준비
    X, y = prepare_training_data()
    
    if X is None or len(X) < 50:
        print("❌ 학습 데이터 부족으로 모델 훈련 불가")
        return None
    
    try:
        # 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # LightGBM 파라미터 (작은 데이터셋에 최적화)
        lgb_params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'num_leaves': 15,
            'learning_rate': 0.1,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_data_in_leaf': 10,
            'verbose': -1,
            'random_state': 42
        }
        
        # 데이터셋 생성
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        # 모델 훈련
        model = lgb.train(
            lgb_params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=100,
            callbacks=[lgb.early_stopping(stopping_rounds=10), lgb.log_evaluation(0)]
        )
        
        # 성능 평가
        y_pred = (model.predict(X_test) > 0.5).astype(int)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"✅ 모델 훈련 완료!")
        print(f"📊 테스트 정확도: {accuracy:.3f}")
        print(f"📊 양성 예측 비율: {np.mean(y_pred):.3f}")
        print(f"📊 실제 양성 비율: {np.mean(y_test):.3f}")
        
        # 모델 저장
        model.save_model('ai_price_prediction_model.txt')
        print("💾 모델 저장 완료: ai_price_prediction_model.txt")
        
        return model
        
    except Exception as e:
        print(f"❌ 모델 훈련 오류: {e}")
        return None

def load_ai_model():
    """저장된 AI 모델 로드"""
    try:
        if os.path.exists('ai_price_prediction_model.txt'):
            model = lgb.Booster(model_file='ai_price_prediction_model.txt')
            return model
        else:
            print("📝 저장된 모델이 없어 새로 훈련합니다...")
            return train_ai_model()
    except Exception as e:
        print(f"❌ 모델 로드 오류: {e}")
        return None

def get_ai_prediction_score(ticker, model):
    """AI 모델을 사용한 실제 예측 점수"""
    try:
        # 최근 데이터 가져오기
        data = ht.get_past_data(ticker, n=50)
        if len(data) < 30:
            return 0.5
        
        # 기술적 지표 생성
        data = create_technical_features(data)
        latest = data.iloc[-1]
        
        # 피처 추출 (훈련시와 동일한 순서)
        feature_columns = [
            'return_1d', 'return_3d', 'return_5d', 'return_10d',
            'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
            'rsi_14', 'volume_ratio_5d', 'volatility_10d', 'bb_position'
        ]
        
        # 피처 벡터 생성
        features = []
        for col in feature_columns:
            if col in latest.index and not pd.isna(latest[col]):
                features.append(latest[col])
            else:
                features.append(0.0)  # 결측치는 0으로 대체
        
        # AI 예측 (상승 확률)
        prediction_prob = model.predict([features])[0]
        
        return float(prediction_prob)
        
    except Exception as e:
        print(f"❌ AI 예측 오류 ({ticker}): {e}")
        return 0.5

def ai_enhanced_final_selection(entry_tickers):
    """AI를 활용한 최종 종목 선정"""
    print("🤖 AI 최종 종목 선정 시작...")
    
    # AI 모델 로드
    ai_model = load_ai_model()
    if ai_model is None:
        print("❌ AI 모델을 사용할 수 없어 기존 선정 결과 반환")
        return entry_tickers[:5]  # 상위 5개만 반환
    
    ai_scored_tickers = []
    
    # 각 종목에 대해 AI 예측 점수 계산
    for ticker in entry_tickers:
        ai_score = get_ai_prediction_score(ticker, ai_model)
        ai_scored_tickers.append({
            'ticker': ticker,
            'ai_score': ai_score
        })
        
        print(f"🎯 {ticker}: AI 예측 점수 = {ai_score:.3f}")
    
    # AI 점수로 정렬
    ai_scored_tickers.sort(key=lambda x: x['ai_score'], reverse=True)
    
    # AI 점수가 0.6 이상인 종목만 선정 (최대 5개)
    final_selection = []
    for item in ai_scored_tickers:
        if item['ai_score'] >= 0.6 and len(final_selection) < 5:
            final_selection.append(item['ticker'])
    
    # AI 조건을 만족하는 종목이 없다면 상위 3개는 선정
    if len(final_selection) == 0:
        final_selection = [item['ticker'] for item in ai_scored_tickers[:3]]
        print("⚠️ AI 조건 만족 종목 없음, 상위 3개 선정")
    
    print(f"🏆 AI 최종 선정: {len(final_selection)}개 종목")
    
    # AI 예측 결과 저장
    strategy_data['ai_predictions'] = {
        item['ticker']: {
            'score': item['ai_score'],
            'timestamp': datetime.now().isoformat(),
            'selected': item['ticker'] in final_selection
        }
        for item in ai_scored_tickers
    }
    
    return final_selection

def enhanced_stock_selection():
    """기술적 분석 강화 종목 선정 (기존 전략 + 규칙 기반 분석)"""
    print("📊 기술적 분석 강화 종목 분석 시작...")
    
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
    
    # 기술적 분석 점수 추가 분석
    enhanced_candidates = []
    
    for _, row in traditional_candidates.iterrows():
        ticker = row['ticker']
        
        # 기술적 분석 점수 계산
        technical_score = get_technical_score(ticker)
        
        # 결합 점수: 기존 거래량 가중치 + 기술적 분석 보정
        # 기술적 점수가 높을수록 거래량에 추가 가중치
        technical_multiplier = 0.5 + technical_score  # 0.5 ~ 1.5 배수
        combined_score = row['trade_amount'] * technical_multiplier
        
        enhanced_candidates.append({
            'ticker': ticker,
            'trade_amount': row['trade_amount'],
            'technical_score': technical_score,
            'combined_score': combined_score
        })
        
        # 기술적 분석 정보 저장
        strategy_data['technical_analysis'][ticker] = {
            'score': technical_score,
            'timestamp': datetime.now().isoformat(),
            'traditional_rank': int(row['trade_amount'])
        }
    
    # 기술적 분석 강화 점수로 정렬
    enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # 결과 출력 및 선정
    selected_tickers = []
    for i, candidate in enumerate(enhanced_candidates[:15]):  # 상위 15개 확인
        ticker = candidate['ticker']
        technical_score = candidate['technical_score']
        
        print(f"{i+1:2d}. {ticker}: 기술점수={technical_score:.3f}, 거래량={candidate['trade_amount']:>10.0f}, 결합점수={candidate['combined_score']:>12.0f}")
        
        # 기술적 점수가 0.6 이상이고 상위 10개만 선정
        if technical_score >= 0.6 and len(selected_tickers) < 10:
            selected_tickers.append(ticker)
    
    print(f"🎯 기술적 분석 최종 선정: {len(selected_tickers)}개 종목")
    return selected_tickers

# 현재 보유중인 종목 조회
holdings = ht.get_holding_stock()

# holding_period를 하루씩 높여줌
for ticker in holdings:
    if ticker not in strategy_data['holding_period']:
        strategy_data['holding_period'][ticker] = 1
    else:
        strategy_data['holding_period'][ticker] += 1

# 기술적 분석 강화 매도 전략
ticker_to_sell = []
for ticker in holdings:
    holding_days = strategy_data['holding_period'][ticker]
    should_sell = False
    
    # 기본 3일 룰
    if holding_days >= 3:
        should_sell = True
        
        # 기술적 홀드 시그널 체크 (3일차에만)
        if holding_days == 3 and strategy_data['enhanced_analysis_enabled']:
            hold_signal = get_technical_hold_signal(ticker)
            
            if hold_signal >= 0.75:
                should_sell = False
                print(f"📊 {ticker}: 기술적 분석 강홀드 신호로 1일 연장 (신호강도: {hold_signal:.3f})")
            elif hold_signal <= 0.25:
                print(f"⚠️ {ticker}: 기술적 분석 매도 신호 (신호강도: {hold_signal:.3f})")
        
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

        # === 기술적 분석 강화 매수 실행 ===
        entry_tickers = enhanced_stock_selection()
        
        # === AI 최종 선정 추가 ===
        final_entry_tickers = ai_enhanced_final_selection(entry_tickers)
        
        # 현재 보유중인 종목은 매수후보에서 제외
        current_holdings = set(holdings.keys())
        final_buy_tickers = [t for t in final_entry_tickers if t not in current_holdings]
        
        print(f"📥 최종 매수 대상: {len(final_buy_tickers)}개")
        
        # 선정한 종목 매수
        for ticker in final_buy_tickers:
            print(f"📥 {ticker} AI 추천 매수")
            ht.bid(ticker, 'market', 1, 'STOCK')

        # 성과 로깅
        strategy_data['performance_log'].append({
            'timestamp': datetime.now().isoformat(),
            'sold_count': len(ticker_to_sell),
            'technical_candidates': len(entry_tickers),
            'ai_selected': len(final_entry_tickers),
            'bought_count': len(final_buy_tickers),
            'total_holdings': len(holdings) - len(ticker_to_sell) + len(final_buy_tickers),
            'enhanced_analysis_enabled': strategy_data['enhanced_analysis_enabled']
        })

        # 전략 데이터 저장
        with open('technical_strategy_data.json', 'w') as f:
            json.dump(strategy_data, f, indent=2, ensure_ascii=False)
        
        print("💾 AI 강화 전략 데이터 저장 완료")
        print("✅ AI 강화 전략 실행 완료!")
        break

    # 루프 돌때마다 1초씩 쉬어줌
    time.sleep(1)
