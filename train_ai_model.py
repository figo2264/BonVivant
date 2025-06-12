#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
독립적인 AI 모델 훈련 스크립트
strategy.py의 의존성 없이 실행 가능
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import ta
import warnings
warnings.filterwarnings('ignore')

# AI 모델 임포트
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
import lightgbm as lgb
import os
from sklearn.utils.class_weight import compute_class_weight
from sklearn.utils import resample

# 데이터 소스
import FinanceDataReader as fdr
from pykrx import stock as pystock

def get_past_data_total(n=1000):
    """전체 시장 과거 데이터 조회 (pykrx 사용)"""
    try:
        all_data = []
        end_date = datetime.now()
        current_date = end_date - timedelta(days=n)
        
        collected_days = 0
        max_collect_days = min(n, 365)  # 최대 1년치만 수집
        
        while current_date <= end_date and collected_days < max_collect_days:
            if current_date.weekday() < 5:  # 평일만
                try:
                    date_str = current_date.strftime('%Y%m%d')
                    
                    # 데이터 수집 시도
                    try:
                        kospi = pystock.get_market_ohlcv(date_str, market='KOSPI')
                    except:
                        kospi = pd.DataFrame()
                    
                    try:
                        kosdaq = pystock.get_market_ohlcv(date_str, market='KOSDAQ')
                    except:
                        kosdaq = pd.DataFrame()
                    
                    if kospi.empty and kosdaq.empty:
                        current_date += timedelta(days=1)
                        continue
                        
                    daily_data = pd.concat([kospi, kosdaq])
                    
                    if not daily_data.empty and daily_data['거래대금'].sum() > 0:
                        # 컬럼명 변환
                        daily_data = daily_data.rename(columns={
                            '시가': 'open', '고가': 'high', '저가': 'low', '종가': 'close',
                            '거래량': 'volume', '거래대금': 'trade_amount'
                        })
                        
                        daily_data['timestamp'] = current_date.strftime('%Y-%m-%d')
                        daily_data.index.name = 'ticker'
                        daily_data = daily_data.reset_index()
                        all_data.append(daily_data)
                        collected_days += 1
                        
                except Exception as e:
                    pass  # 데이터 없는 날짜는 스킵
                    
            current_date += timedelta(days=1)
        
        if not all_data:
            print("❌ 학습 데이터 수집 실패")
            return pd.DataFrame()
        
        result = pd.concat(all_data, ignore_index=True)
        result['timestamp'] = pd.to_datetime(result['timestamp'])
        
        print(f"✅ 데이터 수집 완료: {len(result)}개 레코드, {result['ticker'].nunique()}개 종목")
        return result.sort_values(['timestamp', 'ticker']).reset_index(drop=True)
        
    except Exception as e:
        print(f"❌ 데이터 수집 오류: {e}")
        return pd.DataFrame()

def create_technical_features(data):
    """강화된 기술적 분석 지표 생성"""
    try:
        if len(data) < 30:
            # 데이터가 부족하면 기본 지표만 생성
            data['return_1d'] = data['close'].pct_change(1)
            
            # 추가 지표들
            data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
            data['candle_streak'] = data['candle_type'].rolling(3).sum()
            data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
            data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
            data['round_number_proximity'] = (data['close'] % 1000) / 1000
            return data
        
        # 기본 수익률 계산
        for period in [1, 3, 5, 10, 20]:
            data[f'return_{period}d'] = data['close'].pct_change(period)

        # 이동평균 및 비율
        for ma_period in [5, 10, 20, 60]:
            data[f'ma_{ma_period}'] = data['close'].rolling(ma_period).mean()
            data[f'price_ma_ratio_{ma_period}'] = data['close'] / data[f'ma_{ma_period}']

        # 기본 기술적 지표
        data['rsi_14'] = ta.momentum.rsi(data['close'], window=14)
        data['rsi_30'] = ta.momentum.rsi(data['close'], window=30)
        data['volume_ratio_5d'] = data['volume'] / data['volume'].rolling(5).mean()
        data['volume_ratio_20d'] = data['volume'] / data['volume'].rolling(20).mean()
        data['volatility_10d'] = data['close'].pct_change().rolling(10).std()
        data['volatility_20d'] = data['close'].pct_change().rolling(20).std()

        # 볼린저 밴드 관련 지표
        bb_middle = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        data['bb_upper'] = bb_middle + (2 * bb_std)
        data['bb_lower'] = bb_middle - (2 * bb_std)
        data['bb_position'] = (data['close'] - bb_middle) / (2 * bb_std)
        data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / bb_middle

        # MACD 지표
        try:
            macd_line = ta.trend.macd(data['close'])
            macd_signal = ta.trend.macd_signal(data['close'])
            data['macd'] = macd_line
            data['macd_signal'] = macd_signal
            data['macd_histogram'] = macd_line - macd_signal
        except:
            data['macd'] = 0
            data['macd_signal'] = 0
            data['macd_histogram'] = 0

        # 스토캐스틱 지표
        try:
            data['stoch_k'] = ta.momentum.stoch(data['high'], data['low'], data['close'])
            data['stoch_d'] = data['stoch_k'].rolling(3).mean()
        except:
            data['stoch_k'] = 50
            data['stoch_d'] = 50

        # 가격 모멘텀 지표
        data['price_momentum_5'] = data['close'] / data['close'].shift(5) - 1
        data['price_momentum_10'] = data['close'] / data['close'].shift(10) - 1
        data['price_momentum_20'] = data['close'] / data['close'].shift(20) - 1

        # 거래량 가중 평균 가격 (VWAP)
        try:
            data['vwap'] = (data['close'] * data['volume']).rolling(20).sum() / data['volume'].rolling(20).sum()
            data['price_vwap_ratio'] = data['close'] / data['vwap']
        except:
            data['vwap'] = data['close']
            data['price_vwap_ratio'] = 1.0

        # 변동성 기반 지표
        data['high_low_ratio'] = (data['high'] - data['low']) / data['close']
        data['close_open_ratio'] = data['close'] / data['open'] - 1

        # 지지/저항 레벨 근접도
        data['recent_high_20'] = data['high'].rolling(20).max()
        data['recent_low_20'] = data['low'].rolling(20).min()
        data['high_proximity'] = (data['recent_high_20'] - data['close']) / data['recent_high_20']
        data['low_proximity'] = (data['close'] - data['recent_low_20']) / data['recent_low_20']

        # 추가 지표들
        data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
        data['candle_streak'] = data['candle_type'].rolling(3).sum()
        data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
        data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
        data['round_number_proximity'] = (data['close'] % 1000) / 1000
        
        return data
    except Exception as e:
        print(f"기술적 지표 생성 오류: {e}")
        # 최소한의 지표라도 생성
        data['return_1d'] = data['close'].pct_change(1)
        data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
        data['candle_streak'] = data['candle_type'].rolling(3).sum()
        data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
        data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
        data['round_number_proximity'] = (data['close'] % 1000) / 1000
        return data

def prepare_training_data(lookback_days=1000):
    """AI 모델 학습용 데이터 준비"""
    print("📚 AI 모델 학습 데이터 준비 중...")

    try:
        # 과거 데이터 수집
        historical_data = get_past_data_total(n=lookback_days)

        if len(historical_data) < 300:
            print("❌ 학습 데이터 부족 (최소 300일 필요)")
            return None, None

        all_features = []
        all_targets = []
        data_quality_stats = {
            'total_tickers': 0,
            'qualified_tickers': 0,
            'total_samples': 0,
            'skipped_insufficient_data': 0,
            'skipped_insufficient_features': 0,
            'skipped_insufficient_valid': 0
        }

        # 종목별로 데이터 처리
        for ticker in historical_data['ticker'].unique():
            data_quality_stats['total_tickers'] += 1
            ticker_data = historical_data[historical_data['ticker'] == ticker].sort_values('timestamp')

            if len(ticker_data) < 30:
                data_quality_stats['skipped_insufficient_data'] += 1
                continue

            # 강화된 기술적 지표 생성
            ticker_data = create_technical_features(ticker_data.copy())

            # 다중 기간 미래 수익률 계산
            for future_days in [3, 5, 7]:
                ticker_data[f'future_{future_days}d_return'] = ticker_data['close'].shift(-future_days) / ticker_data['close'] - 1

            # 유효한 데이터만 사용
            valid_data = ticker_data.dropna()

            if len(valid_data) < 20:
                data_quality_stats['skipped_insufficient_valid'] += 1
                continue

            data_quality_stats['qualified_tickers'] += 1

            # 핵심 피처만 선택 (25개)
            feature_columns = [
                'return_1d', 'return_3d', 'return_5d', 'return_10d', 'return_20d',
                'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
                'rsi_14', 'volume_ratio_5d', 'volume_ratio_20d',
                'volatility_10d', 'volatility_20d',
                'bb_position', 'bb_width', 'macd_histogram', 'stoch_k',
                'price_momentum_5', 'price_momentum_10', 'low_proximity',
                'candle_streak', 'volume_price_corr', 'price_acceleration', 'round_number_proximity'
            ]

            available_features = [col for col in feature_columns if col in valid_data.columns]

            if len(available_features) < 15:
                data_quality_stats['skipped_insufficient_features'] += 1
                continue

            features = valid_data[available_features].values

            # 개선된 타겟 생성: 이진 분류
            future_5d_return = valid_data['future_5d_return']
            
            # 이진 분류: 0(손실/횡보), 1(수익)
            targets = np.where(future_5d_return >= 0.01, 1, 0)

            # 미래 데이터가 없는 마지막 7개 제외
            if len(features) > 7:
                features = features[:-7]
                targets = targets[:-7]

                all_features.extend(features)
                all_targets.extend(targets)
                data_quality_stats['total_samples'] += len(features)

        if len(all_features) < 200:
            print("❌ 충분한 학습 데이터 확보 실패")
            print(f"📊 수집된 샘플: {len(all_features)}개 (최소 200개 필요)")
            return None, None

        print(f"✅ 학습 데이터 준비 완료:")
        print(f"   📊 총 샘플: {len(all_features)}개")
        print(f"   📈 분석 종목: {data_quality_stats['qualified_tickers']}/{data_quality_stats['total_tickers']}개")
        print(f"   🎯 타겟 분포: {np.bincount(all_targets)}")
        print(f"   📐 피처 수: {len(available_features) if 'available_features' in locals() else len(feature_columns)}개")
        print(f"   ❌ 스킵 원인:")
        print(f"      - 데이터 부족: {data_quality_stats['skipped_insufficient_data']}개")
        print(f"      - 유효 샘플 부족: {data_quality_stats['skipped_insufficient_valid']}개")
        print(f"      - 피처 부족: {data_quality_stats['skipped_insufficient_features']}개")

        return np.array(all_features), np.array(all_targets)

    except Exception as e:
        print(f"❌ 데이터 준비 오류: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def train_ai_model():
    """AI 모델 훈련"""
    print("🤖 AI 모델 훈련 시작...")

    # 학습 데이터 준비
    X, y = prepare_training_data()

    if X is None or len(X) < 200:
        print("❌ 학습 데이터 부족으로 모델 훈련 불가")
        return None

    try:
        # 데이터 분할 (시계열 고려)
        n_samples = len(X)
        train_end = int(n_samples * 0.7)
        val_end = int(n_samples * 0.85)
        
        X_train = X[:train_end]
        y_train = y[:train_end]
        X_val = X[train_end:val_end]
        y_val = y[train_end:val_end]
        X_test = X[val_end:]
        y_test = y[val_end:]

        # 클래스 불균형 해결
        X_train_class0 = X_train[y_train == 0]
        X_train_class1 = X_train[y_train == 1]
        
        if len(X_train_class0) > len(X_train_class1):
            X_train_class0_resampled = resample(X_train_class0, n_samples=int(len(X_train_class1) * 1.5), random_state=42)
            X_train_class1_resampled = X_train_class1
        else:
            X_train_class0_resampled = X_train_class0
            X_train_class1_resampled = resample(X_train_class1, n_samples=int(len(X_train_class0) * 1.5), random_state=42)
        
        X_train = np.vstack([X_train_class0_resampled, X_train_class1_resampled])
        y_train = np.hstack([
            np.zeros(len(X_train_class0_resampled)),
            np.ones(len(X_train_class1_resampled))
        ])
        
        shuffle_idx = np.random.permutation(len(X_train))
        X_train = X_train[shuffle_idx]
        y_train = y_train[shuffle_idx].astype(int)

        print(f"📊 데이터 분할: 훈련({len(X_train)}) / 검증({len(X_val)}) / 테스트({len(X_test)})")

        # LightGBM 파라미터
        lgb_params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_data_in_leaf': 30,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'min_gain_to_split': 0.05,
            'max_depth': 6,
            'verbose': -1,
            'random_state': 42,
            'force_col_wise': True,
            'is_unbalance': True,
            'boost_from_average': True,
        }

        # 클래스 가중치 계산
        class_weights = compute_class_weight(
            'balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        
        print(f"📊 클래스 가중치: {dict(zip(np.unique(y_train), class_weights))}")
        sample_weights = np.array([class_weights[label] for label in y_train])

        # 데이터셋 생성
        train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weights)
        valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        # 모델 훈련
        model = lgb.train(
            lgb_params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=500,
            callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(50)]
        )

        # 성능 평가
        y_pred_val_proba = model.predict(X_val)
        y_pred_test_proba = model.predict(X_test)
        
        y_pred_val = (y_pred_val_proba > 0.5).astype(int)
        y_pred_test = (y_pred_test_proba > 0.5).astype(int)
        
        val_accuracy = accuracy_score(y_val, y_pred_val)
        test_accuracy = accuracy_score(y_test, y_pred_test)

        print(f"✅ 모델 훈련 완료!")
        print(f"📊 검증 정확도: {val_accuracy:.3f}")
        print(f"📊 테스트 정확도: {test_accuracy:.3f}")
        
        print(f"📊 검증 데이터 클래스별 예측 분포:")
        print(f"   실제: {np.bincount(y_val)}")
        print(f"   예측: {np.bincount(y_pred_val)}")

        # 추가 성능 지표
        try:
            auc_score = roc_auc_score(y_test, y_pred_test_proba)
            print(f"📊 AUC 점수: {auc_score:.3f}")
        except:
            auc_score = 0.5

        f1 = f1_score(y_test, y_pred_test)
        precision = precision_score(y_test, y_pred_test)
        recall = recall_score(y_test, y_pred_test)
        
        # 모델 품질 점수 계산
        model_quality_score = 0
        model_quality_score += min(auc_score * 30, 30)
        model_quality_score += f1 * 30
        model_quality_score += precision * 20
        model_quality_score += recall * 20
        
        print(f"🏆 모델 품질 점수: {model_quality_score:.1f}/100")
        print(f"   📊 AUC: {auc_score:.3f}")
        print(f"   📊 정확도: {test_accuracy:.3f}")
        print(f"   📊 정밀도: {precision:.3f}")
        print(f"   📊 재현율: {recall:.3f}")
        print(f"   📊 F1 점수: {f1:.3f}")
        
        # 혼동 행렬
        cm = confusion_matrix(y_test, y_pred_test)
        print(f"   📊 혼동 행렬:")
        print(f"      예측 0    예측 1")
        print(f"   실제 0: {cm[0,0]:6d} {cm[0,1]:6d}")
        print(f"   실제 1: {cm[1,0]:6d} {cm[1,1]:6d}")

        # 모델 저장
        model.save_model('ai_price_prediction_model.txt')
        print("💾 모델 저장 완료: ai_price_prediction_model.txt")

        # 모델 메타데이터 저장
        model_metadata = {
            'train_date': datetime.now().isoformat(),
            'model_type': 'LightGBM_Binary_Independent',
            'train_samples': len(X_train),
            'test_accuracy': float(test_accuracy),
            'val_accuracy': float(val_accuracy),
            'model_quality_score': float(model_quality_score),
            'feature_count': X_train.shape[1],
            'class_count': 2,
            'auc_score': float(auc_score),
            'f1_score': float(f1),
            'precision': float(precision),
            'recall': float(recall),
            'class_distribution': {
                'train': np.bincount(y_train).tolist(),
                'test': np.bincount(y_test).tolist()
            },
            'prediction_distribution': {
                'val': np.bincount(y_pred_val).tolist(),
                'test': np.bincount(y_pred_test).tolist()
            }
        }
        
        with open('ai_model_metadata.json', 'w') as f:
            json.dump(model_metadata, f, indent=2)

        return model

    except Exception as e:
        print(f"❌ 모델 훈련 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """메인 실행 함수"""
    print("🚀 독립적인 AI 모델 훈련 시작...")
    
    # 기존 모델 파일 삭제 (강제 재훈련)
    model_files = ['ai_price_prediction_model.txt', 'ai_model_metadata.json']
    for file in model_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 기존 {file} 삭제")
    
    # AI 모델 훈련 실행
    model = train_ai_model()
    
    if model is not None:
        print("✅ AI 모델 훈련 완료!")
        print("📊 새로운 모델이 저장되었습니다.")
        
        # 모델 메타데이터 확인
        try:
            with open('ai_model_metadata.json', 'r') as f:
                metadata = json.load(f)
                print(f"📈 모델 품질 점수: {metadata.get('model_quality_score', 0):.1f}/100")
                print(f"🎯 테스트 정확도: {metadata.get('test_accuracy', 0):.3f}")
        except:
            pass
        
        return True
    else:
        print("❌ AI 모델 훈련 실패!")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 모델 훈련이 성공적으로 완료되었습니다!")
        print("💡 이제 strategy.py를 실행하면 새로운 모델을 사용합니다.")
    else:
        print("\n💥 모델 훈련에 실패했습니다. 로그를 확인해주세요.")
