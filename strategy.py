# 기술적 분석 강화된 6-7 전략 (기존 이동평균 + 규칙 기반 분석)

import pandas as pd
import time
import json
from datetime import datetime
import numpy as np

import yaml
import ta

# AI 모델 임포트
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import lightgbm as lgb
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

# 슬랙 설정
SLACK_API_TOKEN = "SLACK_TOKEN_REMOVED"
HANLYANG_CHANNEL_ID = "C090JHC30CU"

# 슬랙 활성화
ht.activate_slack(SLACK_API_TOKEN)

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

# 전략의 시간을 체크할 while문
executed_date = None  # 실행 완료된 날짜 저장

while True:
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')

    # 날짜가 바뀌면 실행 플래그 리셋
    if executed_date != current_date:
        executed_today = False
    else:
        executed_today = True

    # 8시 30분~32분 - 매도 전용 실행 (여유시간 2분)
    if current_time.hour == 8 and 30 <= current_time.minute <= 32 and not executed_today:
    # if True:
        print("🌅 아침 매도 전략 실행 시작!")

        # === 현재 보유중인 종목 조회 ===
        holdings = ht.get_holding_stock()
        print(f"📊 현재 보유: {len(holdings)}개")

        # === holding_period를 하루씩 높여줌 ===
        for ticker in holdings:
            if ticker not in strategy_data['holding_period']:
                strategy_data['holding_period'][ticker] = 1
            else:
                strategy_data['holding_period'][ticker] += 1

        # === 기술적 분석 강화 매도 전략 ===
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

        print(f"📤 매도 예정: {len(ticker_to_sell)}개")

        # === 수익률 추적 매도 실행 ===
        sold_tickers = []
        total_sell_profit = 0

        for ticker in ticker_to_sell:
            holding_days = strategy_data['holding_period'][ticker]

            try:
                # 매도 전 수익률 계산
                purchase_info = strategy_data.get('purchase_info', {}).get(ticker, {})
                try:
                    current_data = ht.get_past_data(ticker, n=1)
                    current_price = current_data['close']
                except:
                    current_price = None

                profit_info = ""
                if purchase_info and current_price:
                    buy_price = purchase_info.get('buy_price', 0)
                    quantity = holdings[ticker]

                    if buy_price > 0:
                        sell_value = quantity * current_price
                        buy_value = quantity * buy_price
                        profit = sell_value - buy_value
                        profit_rate = (profit / buy_value) * 100

                        total_sell_profit += profit
                        profit_info = f" | 수익률: {profit_rate:+.2f}% ({profit:+,}원)"

                print(f"📤 {ticker} 매도 (보유기간: {holding_days}일{profit_info})")
                order_id, quantity = ht.ask(ticker, 'market', holdings[ticker], 'STOCK')

                if order_id:
                    sold_tickers.append(ticker)

                    # 슬랙 알림: 매도 체결 (수익률 포함)
                    sell_message = f"📤 **아침 매도 체결**\n"
                    sell_message += f"종목: {ticker}\n"
                    sell_message += f"수량: {quantity}주\n"
                    sell_message += f"보유기간: {holding_days}일"

                    if profit_info:
                        sell_message += f"\n수익률: {profit_rate:+.2f}%"
                        sell_message += f"\n손익: {profit:+,}원"
                        if purchase_info:
                            confidence = purchase_info.get('confidence_level', 'Unknown')
                            sell_message += f"\n신뢰도: {confidence}"

                    try:
                        ht.post_message(sell_message, HANLYANG_CHANNEL_ID)
                        print(f"✅ {ticker} 매도 슬랙 알림 전송")
                    except Exception as e:
                        print(f"❌ {ticker} 매도 슬랙 알림 실패: {e}")

                    # 매도 완료 후 구매 정보 정리
                    if ticker in strategy_data.get('purchase_info', {}):
                        del strategy_data['purchase_info'][ticker]

                strategy_data['holding_period'][ticker] = 0

            except Exception as e:
                print(f"❌ {ticker} 매도 처리 오류: {e}")

        if total_sell_profit != 0:
            print(f"💰 총 매도 손익: {total_sell_profit:+,}원")

        # === 아침 매도 완료 슬랙 알림 ===
        morning_summary_message = f"🌅 **아침 매도 완료!**\n"
        morning_summary_message += f"📤 매도: {len(sold_tickers)}개"
        if total_sell_profit != 0:
            morning_summary_message += f" (손익: {total_sell_profit:+,}원)"
        morning_summary_message += f"\n📊 현재 보유: {len(holdings) - len(sold_tickers)}개"
        morning_summary_message += f"\n⏰ 실행 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        morning_summary_message += f"\n🔔 오후 3시 20분에 매수 전략 실행 예정"

        try:
            ht.post_message(morning_summary_message, HANLYANG_CHANNEL_ID)
            print("✅ 슬랙 아침 매도 완료 알림 전송")
        except Exception as e:
            print(f"❌ 슬랙 알림 실패: {e}")

        # 성과 로깅 (매도 전용)
        strategy_data['performance_log'].append({
            'timestamp': datetime.now().isoformat(),
            'strategy_type': 'sell_only',
            'sold_count': len(sold_tickers),
            'sell_profit': total_sell_profit,
            'current_holdings': len(holdings) - len(sold_tickers),
            'enhanced_analysis_enabled': strategy_data['enhanced_analysis_enabled']
        })

        # 전략 데이터 저장
        def convert_to_serializable(obj):
            """numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
            if isinstance(obj, dict):
                return {key: convert_to_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            else:
                return obj

        serializable_data = convert_to_serializable(strategy_data)

        with open('technical_strategy_data.json', 'w') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

        print("💾 매도 전략 데이터 저장 완료")
        print("✅ 아침 매도 전략 실행 완료!")
        executed_date = current_date  # 실행 완료 표시
        break

    # 15시 20분~22분 - 매수 전용 실행 (여유시간 2분)
    # elif current_time.hour == 15 and 20 <= current_time.minute <= 22 and not executed_today:
    elif True:  # 테스트용
        print("🚀 오후 매수 전략 실행 시작!")

        # === 현재 보유중인 종목 조회 (매수 전) ===
        holdings = ht.get_holding_stock()
        print(f"📊 현재 보유: {len(holdings)}개")

        # === 기술적 분석 강화 매수 실행 ===
        entry_tickers = enhanced_stock_selection()

        # === AI 최종 선정 추가 ===
        final_entry_tickers = ai_enhanced_final_selection(entry_tickers)

        # 현재 보유중인 종목은 매수후보에서 제외
        current_holdings = set(holdings.keys())
        final_buy_tickers = [t for t in final_entry_tickers if t not in current_holdings]

        print(f"📥 최종 매수 대상: {len(final_buy_tickers)}개")

        # === 슬랙 알림: 최종 선정 종목 ===
        if final_buy_tickers:
            selection_message = f"🎯 **AI 종목 선정 완료!**\n"
            selection_message += f"📊 분석 완료: {len(entry_tickers)}개 → AI 선정: {len(final_entry_tickers)}개\n"
            selection_message += f"📥 매수 예정: {len(final_buy_tickers)}개\n\n"
            selection_message += "**선정 종목:**\n"
            for i, ticker in enumerate(final_buy_tickers, 1):
                selection_message += f"{i}. {ticker}\n"

            try:
                ht.post_message(selection_message, HANLYANG_CHANNEL_ID)
                print("✅ 슬랙 종목 선정 알림 전송 완료")
            except Exception as e:
                print(f"❌ 슬랙 알림 전송 실패: {e}")

        # === AI 신뢰도 기반 차등 투자 매수 ===
        bought_tickers = []
        total_invested = 0

        # 현재 계좌 잔고 조회
        current_balance = 0  # 기본값 초기화
        balance_check_success = False

        try:
            current_balance = ht.get_holding_cash()
            balance_check_success = True
            print(f"💰 현재 계좌 잔고: {current_balance:,}원")
        except Exception as e:
            print(f"❌ 계좌 잔고 조회 실패: {e}")
            print("⚠️ 잔고 확인 불가로 매수 전략을 건너뜁니다.")

            # 슬랙 알림: 잔고 조회 실패
            error_message = f"❌ **계좌 잔고 조회 실패**\n"
            error_message += f"오류: {str(e)}\n"
            error_message += f"매수 전략을 건너뛰고 매도만 실행합니다."

            try:
                ht.post_message(error_message, HANLYANG_CHANNEL_ID)
            except:
                pass

        # 잔고 조회가 실패한 경우 매수를 건너뜀
        if not balance_check_success:
            print("⚠️ 계좌 잔고 조회 실패로 매수를 건너뜁니다.")
        else:
            for ticker in final_buy_tickers:
                try:
                    # AI 점수 가져오기
                    ai_score = strategy_data.get('ai_predictions', {}).get(ticker, {}).get('score', 0.5)

                    # AI 신뢰도 기반 투자 금액 계산
                    if ai_score >= 0.8:
                        investment_amount = 500_000    # 고신뢰: 50만원
                        confidence_level = "고신뢰"
                    elif ai_score >= 0.7:
                        investment_amount = 400_000    # 중신뢰: 40만원
                        confidence_level = "중신뢰"
                    elif ai_score >= 0.6:
                        investment_amount = 300_000    # 저신뢰: 30만원
                        confidence_level = "저신뢰"
                    else:
                        investment_amount = 200_000      # 매우 저신뢰: 20만원
                        confidence_level = "매우저신뢰"

                    # 투자 가능 금액 계산 (400만원 안전자금 제외)
                    available_balance = current_balance - total_invested - 4_000_000

                    # 투자 가능 금액이 0 이하면 바로 건너뛰기
                    if available_balance <= 0:
                        print(f"⚠️ {ticker}: 투자 가능 금액 부족 (남은 금액: {available_balance:,}원)")
                        continue
                    
                    # 투자 가능 금액이 계획된 금액보다 작으면 조정
                    if available_balance < investment_amount:
                        # 최소 투자금액(10만원) 확인
                        if available_balance < 100_000:
                            print(f"⚠️ {ticker}: 최소 투자금액 부족 (가능: {available_balance:,}원, 최소: 100,000원)")
                            continue
                        investment_amount = available_balance

                    # 현재가 조회
                    try:
                        current_data = ht.get_past_data(ticker, n=1)
                        current_price = current_data['close']
                    except:
                        current_price = None

                    if not current_price or current_price <= 0:
                        print(f"❌ {ticker}: 현재가 조회 실패")
                        continue

                    # 매수 수량 계산 (소수점 버림)
                    quantity_to_buy = int(investment_amount // current_price)

                    if quantity_to_buy <= 0:
                        print(f"⚠️ {ticker}: 투자금액 부족 (필요: {current_price:,}원)")
                        continue

                    actual_investment = quantity_to_buy * current_price

                    print(f"📥 {ticker} AI 신뢰도 기반 매수:")
                    print(f"   AI점수: {ai_score:.3f} ({confidence_level})")
                    print(f"   투자금액: {actual_investment:,}원")
                    print(f"   수량: {quantity_to_buy:,}주")
                    print(f"   단가: {current_price:,}원")

                    # 매수 주문 실행
                    order_id, actual_quantity = ht.bid(ticker, 'market', quantity_to_buy, 'STOCK')

                    if order_id:
                        bought_tickers.append({
                            'ticker': ticker,
                            'quantity': actual_quantity,
                            'investment': actual_investment,
                            'ai_score': ai_score,
                            'confidence_level': confidence_level
                        })
                        total_invested += actual_investment

                        # 매수 정보 저장 (수익률 계산용)
                        strategy_data.setdefault('purchase_info', {})[ticker] = {
                            'buy_price': current_price,
                            'quantity': actual_quantity,
                            'investment': actual_investment,
                            'buy_date': datetime.now().isoformat(),
                            'ai_score': ai_score,
                            'confidence_level': confidence_level
                        }

                        # 슬랙 알림: 매수 체결
                        buy_message = f"📥 **오후 매수 체결**\n"
                        buy_message += f"종목: {ticker}\n"
                        buy_message += f"수량: {actual_quantity:,}주\n"
                        buy_message += f"투자금액: {actual_investment:,}원\n"
                        buy_message += f"AI점수: {ai_score:.3f} ({confidence_level})\n"
                        buy_message += f"단가: {current_price:,}원"

                        try:
                            ht.post_message(buy_message, HANLYANG_CHANNEL_ID)
                            print(f"✅ {ticker} 매수 완료 및 슬랙 알림 전송")
                        except Exception as e:
                            print(f"❌ {ticker} 슬랙 알림 실패: {e}")
                    else:
                        print(f"❌ {ticker} 매수 주문 실패")

                except Exception as e:
                    print(f"❌ {ticker} 매수 처리 오류: {e}")

        print(f"\n💼 AI 신뢰도 기반 매수 완료:")
        print(f"   매수 종목 수: {len(bought_tickers)}개")
        print(f"   총 투자금액: {total_invested:,}원")
        if balance_check_success:
            print(f"   남은 현금: {current_balance - total_invested:,}원")

        # === 슬랙 알림: 오후 매수 완료 요약 ===
        evening_summary_message = f"🚀 **오후 매수 완료!**\n"
        evening_summary_message += f"📥 매수: {len(bought_tickers)}개"
        if total_invested > 0:
            evening_summary_message += f" (투자: {total_invested:,}원)"
        evening_summary_message += f"\n📊 현재 보유: {len(holdings) + len(bought_tickers)}개\n"

        # AI 신뢰도별 투자 현황
        if bought_tickers:
            evening_summary_message += "\n**신뢰도별 투자:**\n"
            confidence_stats = {}
            for stock in bought_tickers:
                level = stock['confidence_level']
                if level not in confidence_stats:
                    confidence_stats[level] = {'count': 0, 'amount': 0}
                confidence_stats[level]['count'] += 1
                confidence_stats[level]['amount'] += stock['investment']

            for level, stats in confidence_stats.items():
                evening_summary_message += f"• {level}: {stats['count']}개 ({stats['amount']:,}원)\n"

        evening_summary_message += f"\n⏰ 실행 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        evening_summary_message += f"\n🔔 내일 오전 8시 30분에 매도 검토 예정"

        try:
            ht.post_message(evening_summary_message, HANLYANG_CHANNEL_ID)
            print("✅ 슬랙 오후 매수 완료 요약 알림 전송")
        except Exception as e:
            print(f"❌ 슬랙 요약 알림 실패: {e}")

        # 성과 로깅 (매수 전용)
        strategy_data['performance_log'].append({
            'timestamp': datetime.now().isoformat(),
            'strategy_type': 'buy_only',
            'technical_candidates': len(entry_tickers),
            'ai_selected': len(final_entry_tickers),
            'bought_count': len(bought_tickers),
            'total_invested': total_invested,
            'current_holdings': len(holdings) + len(bought_tickers),
            'enhanced_analysis_enabled': strategy_data['enhanced_analysis_enabled'],
            'ai_confidence_strategy': True
        })

        # 전략 데이터 저장
        def convert_to_serializable(obj):
            """numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
            if isinstance(obj, dict):
                return {key: convert_to_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            else:
                return obj

        serializable_data = convert_to_serializable(strategy_data)

        with open('technical_strategy_data.json', 'w') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

        print("💾 매수 전략 데이터 저장 완료")
        print("✅ 오후 매수 전략 실행 완료!")
        executed_date = current_date  # 실행 완료 표시
        break

    # 루프 돌때마다 1초씩 쉬어줌
    time.sleep(1)
