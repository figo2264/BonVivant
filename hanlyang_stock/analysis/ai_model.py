"""
AI model training and prediction utilities
Enhanced with complete features from backtest_engine and train_ai_model
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.utils.class_weight import compute_class_weight
from sklearn.utils import resample
import lightgbm as lgb

from ..data.fetcher import get_data_fetcher
from ..data.preprocessor import create_technical_features

warnings.filterwarnings('ignore')


class AIModelManager:
    """AI 모델 관리 클래스 - 백테스트 엔진 및 독립 훈련 모듈의 모든 기능 적용"""

    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        self.model = None
        self.model_metadata = {}

    def _safe_import_smote(self):
        """SMOTE를 안전하게 import"""
        try:
            from imblearn.over_sampling import SMOTE
            return SMOTE
        except ImportError:
            print("⚠️ imbalanced-learn 라이브러리가 설치되지 않았습니다.")
            print("   pip install imbalanced-learn 으로 설치하거나")
            print("   기존 리샘플링 방법을 사용합니다.")
            return None

    def _balance_classes_with_smote(self, X_train: np.ndarray, y_train: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """SMOTE를 사용한 클래스 불균형 해결 (안전한 처리)"""
        SMOTE = self._safe_import_smote()

        if SMOTE is not None:
            try:
                # SMOTE 적용 (k_neighbors를 데이터 크기에 맞게 조정)
                X_train_class0 = X_train[y_train == 0]
                X_train_class1 = X_train[y_train == 1]
                min_class_size = min(len(X_train_class0), len(X_train_class1))
                k_neighbors = min(5, min_class_size - 1) if min_class_size > 1 else 1

                if k_neighbors >= 1:
                    smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
                    X_train, y_train = smote.fit_resample(X_train, y_train)
                    print(f"📊 SMOTE 적용 완료: 균형 데이터 생성")
                    return X_train, y_train.astype(int)
                else:
                    print("⚠️ SMOTE 적용 불가 (데이터 부족), 기존 방법 사용")
            except Exception as e:
                print(f"⚠️ SMOTE 적용 실패: {e}")

        # SMOTE 없거나 실패시 기존 리샘플링 방법 사용
        return self._balance_classes_traditional(X_train, y_train)

    def _balance_classes_traditional(self, X_train: np.ndarray, y_train: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """전통적인 방법으로 클래스 불균형 해결"""
        print("📊 기존 리샘플링 방법 사용")

        # 각 클래스별로 데이터 분리
        X_train_class0 = X_train[y_train == 0]
        X_train_class1 = X_train[y_train == 1]

        # 균형잡힌 샘플링
        if len(X_train_class0) > len(X_train_class1):
            # 클래스 0이 더 많으면 언더샘플링
            X_train_class0_resampled = resample(X_train_class0, n_samples=int(len(X_train_class1) * 1.5),
                                                random_state=42)
            X_train_class1_resampled = X_train_class1
        else:
            # 클래스 1이 더 많으면 언더샘플링
            X_train_class0_resampled = X_train_class0
            X_train_class1_resampled = resample(X_train_class1, n_samples=int(len(X_train_class0) * 1.5),
                                                random_state=42)

        # 재결합
        X_train = np.vstack([X_train_class0_resampled, X_train_class1_resampled])
        y_train = np.hstack([
            np.zeros(len(X_train_class0_resampled)),
            np.ones(len(X_train_class1_resampled))
        ])

        # 셔플
        shuffle_idx = np.random.permutation(len(X_train))
        X_train = X_train[shuffle_idx]
        y_train = y_train[shuffle_idx].astype(int)

        return X_train, y_train

    def prepare_training_data_until(self, end_date, lookback_days=1000):
        """특정 날짜까지의 AI 모델 학습용 데이터 준비 (강화된 버전, Look-ahead bias 방지)"""
        print(f"📚 {end_date}까지 AI 학습 데이터 준비 중...")

        try:
            # 종료 날짜 이전의 데이터만 수집 (1000일)
            end_date_pd = pd.to_datetime(end_date)
            start_date_pd = end_date_pd - timedelta(days=lookback_days)

            print(f"   📅 데이터 수집 기간: {start_date_pd.strftime('%Y-%m-%d')} ~ {end_date_pd.strftime('%Y-%m-%d')}")

            # 날짜별로 시장 데이터 수집 (과거 데이터만)
            all_data = []
            current_date = start_date_pd
            collected_days = 0
            max_collect_days = min(lookback_days, 365)  # 최대 1년치만 수집

            while current_date <= end_date_pd and collected_days < max_collect_days:
                if current_date.weekday() < 5:  # 평일만
                    try:
                        # 데이터 fetcher를 통해 수집 (실제 구현에서는 pykrx 사용)
                        daily_data = self.data_fetcher.get_market_data_by_date(current_date.strftime('%Y-%m-%d'))

                        if not daily_data.empty and daily_data['trade_amount'].sum() > 0:
                            daily_data['timestamp'] = current_date.strftime('%Y-%m-%d')
                            all_data.append(daily_data)
                            collected_days += 1

                    except Exception as e:
                        pass  # 데이터 없는 날짜는 스킵

                current_date += timedelta(days=1)

            if not all_data:
                print("❌ 학습 데이터 수집 실패")
                return None, None

            historical_data = pd.concat(all_data, ignore_index=True)
            historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'])

            print(f"✅ 수집 완료: {len(historical_data)}개 레코드, {historical_data['ticker'].nunique()}개 종목")

            # 날짜 범위 확인
            print(f"   📅 데이터 기간: {historical_data['timestamp'].min()} ~ {historical_data['timestamp'].max()}")

            # 핵심 피처만 선택 (25개로 확대)
            feature_columns = [
                # 핵심 수익률
                'return_1d', 'return_3d', 'return_5d', 'return_10d', 'return_20d',

                # 핵심 이동평균 비율
                'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',

                # RSI
                'rsi_14',

                # 거래량
                'volume_ratio_5d', 'volume_ratio_20d',

                # 변동성
                'volatility_10d', 'volatility_20d',

                # 볼린저 밴드
                'bb_position', 'bb_width',

                # MACD
                'macd_histogram',

                # 스토캐스틱
                'stoch_k',

                # 모멘텀
                'price_momentum_5', 'price_momentum_10',

                # 지지저항
                'low_proximity',

                # 추가 지표
                'candle_streak', 'volume_price_corr', 'price_acceleration', 'round_number_proximity'
            ]

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

            for ticker in historical_data['ticker'].unique():
                data_quality_stats['total_tickers'] += 1
                ticker_data = historical_data[historical_data['ticker'] == ticker].sort_values('timestamp')

                if len(ticker_data) < 30:  # 종목별 최소 데이터 요구사항
                    data_quality_stats['skipped_insufficient_data'] += 1
                    continue

                # 강화된 기술적 지표 생성
                ticker_data = create_technical_features(ticker_data.copy())

                # 다중 기간 미래 수익률 계산
                for future_days in [3, 5, 7]:
                    ticker_data[f'future_{future_days}d_return'] = ticker_data['close'].shift(-future_days) / \
                                                                   ticker_data['close'] - 1

                # 유효한 데이터만 사용
                valid_data = ticker_data.dropna()

                if len(valid_data) < 20:  # 종목별 최소 유효 샘플
                    data_quality_stats['skipped_insufficient_valid'] += 1
                    continue

                data_quality_stats['qualified_tickers'] += 1

                available_features = [col for col in feature_columns if col in valid_data.columns]

                if len(available_features) < 10:  # 최소 피처 수 (15개 중 10개 이상)
                    data_quality_stats['skipped_insufficient_features'] += 1
                    continue

                features = valid_data[available_features].values

                # 개선된 타겟 생성: 안정성 중심 이진 분류
                future_5d_return = valid_data['future_5d_return']

                # 🎯 타겟 재정의 - 안정성 중심 접근
                # 수수료 0.3% × 2 = 0.6% + 슬리피지 고려하여 1.5% 이상을 의미있는 수익으로 정의
                # 기존 1% → 1.5%로 상향 조정 (더 엄격한 기준으로 노이즈 제거)

                # 1단계: 기본 수익률 기준 상향
                basic_profit_threshold = 0.015  # 1.5%

                # 🎯 2단계: 안정성 조건 추가 (점진적 도입)
                try:
                    # 변동성 계산 (5일간 일별 수익률의 표준편차)
                    volatility_5d = valid_data['return_1d'].rolling(5).std()
                    volatility_median = volatility_5d.median()

                    # 급격한 하락 방지 (5일간 최대 하락률 체크)
                    min_return_5d = valid_data['return_1d'].rolling(5).min()

                    # 안정성 기반 조건들
                    basic_profit = future_5d_return >= basic_profit_threshold  # 1.5% 이상 수익
                    stable_volatility = volatility_5d <= volatility_median  # 중간 이하 변동성
                    no_major_crash = min_return_5d >= -0.05  # 5일간 최대 5% 하락까지만

                    # 최종 안정성 타겟: 모든 조건을 만족하는 경우만 1
                    stable_targets = basic_profit & stable_volatility & no_major_crash

                    # 안정성 타겟의 유효성 검증
                    if len(stable_targets.dropna()) > len(valid_data) * 0.7:  # 70% 이상 유효한 경우만
                        targets = np.where(stable_targets.fillna(False), 1, 0)
                    else:
                        # 안정성 조건이 너무 엄격하면 기본 타겟 사용
                        targets = np.where(future_5d_return >= basic_profit_threshold, 1, 0)

                except Exception as e:
                    # 안정성 계산 실패시 기본 타겟으로 대체
                    targets = np.where(future_5d_return >= basic_profit_threshold, 1, 0)

                # 미래 데이터가 없는 마지막 7개 제외
                if len(features) > 7:
                    features = features[:-7]
                    targets = targets[:-7]

                    all_features.extend(features)
                    all_targets.extend(targets)
                    data_quality_stats['total_samples'] += len(features)

            if len(all_features) < 200:  # 최소 샘플 수 강화
                print("❌ 충분한 학습 데이터 확보 실패")
                print(f"📊 수집된 샘플: {len(all_features)}개 (최소 200개 필요)")
                return None, None

            print(f"✅ 학습 데이터 준비 완료:")
            print(f"   📊 총 샘플: {len(all_features)}개")
            print(f"   📈 분석 종목: {data_quality_stats['qualified_tickers']}/{data_quality_stats['total_tickers']}개")
            print(f"   🎯 타겟 분포: {np.bincount(all_targets) if all_targets else []}")
            print(f"   📐 피처 수: {len(feature_columns)}개")
            print(f"   ❌ 스킵 원인:")
            print(f"      - 데이터 부족: {data_quality_stats['skipped_insufficient_data']}개")
            print(f"      - 유효 샘플 부족: {data_quality_stats['skipped_insufficient_valid']}개")
            print(f"      - 피처 부족: {data_quality_stats['skipped_insufficient_features']}개")

            return np.array(all_features), np.array(all_targets)

        except Exception as e:
            print(f"❌ 데이터 준비 오류: {e}")
            return None, None

    def train_ai_model_at_date(self, end_date):
        """특정 날짜 시점에서 AI 모델 훈련 (강화된 버전)"""
        print(f"🤖 {end_date} 시점 AI 모델 훈련 시작...")

        # 학습 데이터 준비
        X, y = self.prepare_training_data_until(end_date)

        if X is None or len(X) < 200:
            print("❌ 학습 데이터 부족으로 모델 훈련 불가")
            return None

        try:
            # 데이터 분할 (시계열 고려)
            # 학습:검증:테스트 = 70:15:15
            n_samples = len(X)
            train_end = int(n_samples * 0.7)
            val_end = int(n_samples * 0.85)

            X_train = X[:train_end]
            y_train = y[:train_end]
            X_val = X[train_end:val_end]
            y_val = y[train_end:val_end]
            X_test = X[val_end:]
            y_test = y[val_end:]

            # 클래스 불균형 해결을 위한 SMOTE 오버샘플링 (훈련 데이터만)
            X_train, y_train = self._balance_classes_with_smote(X_train, y_train)

            # 셔플 (공통)
            shuffle_idx = np.random.permutation(len(X_train))
            X_train = X_train[shuffle_idx]
            y_train = y_train[shuffle_idx].astype(int)

            print(f"📊 데이터 분할: 훈련({len(X_train)}) / 검증({len(X_val)}) / 테스트({len(X_test)})")

            # 개선된 LightGBM 파라미터 (이진 분류)
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

            # 클래스 가중치 계산 (수동으로 계산하여 적용)
            class_weights = compute_class_weight(
                'balanced',
                classes=np.unique(y_train),
                y=y_train
            )

            print(f"📊 클래스 가중치: {dict(zip(np.unique(y_train), class_weights))}")

            # 가중치를 적용한 샘플 가중치 생성
            sample_weights = np.array([class_weights[label] for label in y_train])

            # 데이터셋 생성 (클래스 가중치 적용)
            train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weights)
            valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            # 모델 훈련 (조기 종료 조건 완화)
            model = lgb.train(
                lgb_params,
                train_data,
                valid_sets=[valid_data],
                num_boost_round=500,  # 증가
                callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(50)]
            )

            # 다중 성능 평가 (이진 분류)
            y_pred_val_proba = model.predict(X_val)
            y_pred_test_proba = model.predict(X_test)

            # 이진 분류 예측 (임계값 강화: 0.5 → 0.7)
            y_pred_val = (y_pred_val_proba > 0.7).astype(int)
            y_pred_test = (y_pred_test_proba > 0.7).astype(int)

            val_accuracy = accuracy_score(y_val, y_pred_val)
            test_accuracy = accuracy_score(y_test, y_pred_test)

            print(f"✅ 모델 훈련 완료!")
            print(f"📊 검증 정확도: {val_accuracy:.3f}")
            print(f"📊 테스트 정확도: {test_accuracy:.3f}")

            # 클래스별 성능 분석
            print(f"📊 검증 데이터 클래스별 예측 분포:")
            print(f"   실제: {np.bincount(y_val)}")
            print(f"   예측: {np.bincount(y_pred_val)}")

            # 추가 성능 지표 출력
            try:
                auc_score = roc_auc_score(y_test, y_pred_test_proba)
                print(f"📊 AUC 점수: {auc_score:.3f}")
            except:
                auc_score = 0.5

            # 모델 품질 검증 (이진 분류)
            f1 = f1_score(y_test, y_pred_test)
            precision = precision_score(y_test, y_pred_test)
            recall = recall_score(y_test, y_pred_test)

            model_quality_score = 0

            # 1. AUC 점수 (0-30점)
            model_quality_score += min(auc_score * 30, 30) if 'auc_score' in locals() else 15

            # 2. F1 점수 (0-30점)
            model_quality_score += f1 * 30

            # 3. 정밀도 (0-20점) - 거짓 양성을 줄이는 것이 중요
            model_quality_score += precision * 20

            # 4. 재현율 (0-20점)
            model_quality_score += recall * 20

            print(f"🏆 모델 품질 점수: {model_quality_score:.1f}/100")
            print(f"   📊 AUC: {auc_score:.3f}" if 'auc_score' in locals() else "   📊 AUC: N/A")
            print(f"   📊 정확도: {test_accuracy:.3f}")
            print(f"   📊 정밀도: {precision:.3f}")
            print(f"   📊 재현율: {recall:.3f}")
            print(f"   📊 F1 점수: {f1:.3f}")

            # 혼동 행렬 출력
            cm = confusion_matrix(y_test, y_pred_test)
            print(f"   📊 혼동 행렬:")
            print(f"      예측 0    예측 1")
            print(f"   실제 0: {cm[0, 0]:6d} {cm[0, 1]:6d}")
            print(f"   실제 1: {cm[1, 0]:6d} {cm[1, 1]:6d}")

            # 모델 메타데이터 저장
            model.model_quality_score = model_quality_score
            model.test_accuracy = test_accuracy
            model.train_date = end_date

            return model

        except Exception as e:
            print(f"❌ 모델 훈련 오류: {e}")
            import traceback
            print(traceback.format_exc())
            return None

    def get_ai_prediction_score(self, ticker: str, current_date=None, model=None) -> float:
        """AI 모델을 사용한 예측 점수 (다중 클래스 대응, backtest_engine과 동일)"""
        try:
            if model is None:
                model = self.model or self.load_ai_model()
                if model is None:
                    return 0.3

            # 현재 날짜까지의 데이터만 사용
            data = self.data_fetcher.get_past_data_enhanced(ticker, n=50)  # 충분한 데이터 확보
            if data.empty or len(data) < 30:
                return 0.3  # 데이터 부족시 낮은 점수

            # 현재 날짜 이후 데이터 제거 (백테스트 시)
            if current_date:
                current_date_pd = pd.to_datetime(current_date)
                data = data[pd.to_datetime(data['timestamp']) <= current_date_pd].copy()
                if len(data) < 30:
                    return 0.3

            # 강화된 기술적 지표 생성
            data = create_technical_features(data)
            latest = data.iloc[-1]

            # 핵심 피처 추출 (훈련시와 동일한 순서 - 25개)
            feature_columns = [
                'return_1d', 'return_3d', 'return_5d', 'return_10d', 'return_20d',
                'price_ma_ratio_5', 'price_ma_ratio_10', 'price_ma_ratio_20',
                'rsi_14', 'volume_ratio_5d', 'volume_ratio_20d',
                'volatility_10d', 'volatility_20d',
                'bb_position', 'bb_width', 'macd_histogram', 'stoch_k',
                'price_momentum_5', 'price_momentum_10', 'low_proximity',
                'candle_streak', 'volume_price_corr', 'price_acceleration', 'round_number_proximity'
            ]

            # 피처 벡터 생성 (결측치 처리 강화)
            features = []
            missing_features = 0

            for col in feature_columns:
                if col in latest.index and not pd.isna(latest[col]) and np.isfinite(latest[col]):
                    features.append(float(latest[col]))
                else:
                    # 피처별 기본값 설정
                    if 'return' in col:
                        features.append(0.0)
                    elif 'ratio' in col:
                        features.append(1.0)
                    elif 'rsi' in col:
                        features.append(50.0)
                    elif 'bb_position' in col:
                        features.append(0.0)
                    elif 'volume_ratio' in col:
                        features.append(1.0)
                    elif 'volatility' in col:
                        features.append(0.02)
                    elif 'candle_streak' in col:
                        features.append(0.0)
                    elif 'corr' in col:
                        features.append(0.0)
                    elif 'acceleration' in col:
                        features.append(0.0)
                    elif 'proximity' in col:
                        features.append(0.5)
                    else:
                        features.append(0.0)
                    missing_features += 1

            # 너무 많은 피처가 누락되면 낮은 점수 반환
            if missing_features > len(feature_columns) * 0.3:  # 30% 이상 누락
                print(f"⚠️ {ticker}: 피처 누락 비율 높음 ({missing_features}/{len(feature_columns)})")
                return 0.2

            # AI 예측 (이진 분류)
            prediction_prob = model.predict([features])[0]  # 수익 확률 (0~1)

            # 예측 확률을 그대로 점수로 사용
            final_score = float(prediction_prob)

            # 신뢰도 보정
            # 극단적인 예측(0.8 이상 또는 0.2 이하)에 보너스
            if prediction_prob > 0.8 or prediction_prob < 0.2:
                confidence = abs(prediction_prob - 0.5) * 2  # 0~1 범위
                final_score = final_score * 0.8 + confidence * 0.2

            return float(final_score)

        except Exception as e:
            print(f"❌ AI 예측 오류 ({ticker}): {e}")
            return 0.2

    def prepare_training_data(self, lookback_days: int = 1000) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """AI 모델 학습용 데이터 준비 (독립 훈련 모듈과 동일)"""
        print("📚 AI 모델 학습 데이터 준비 중...")

        try:
            # 과거 데이터 수집
            historical_data = self.data_fetcher.get_past_data_total(n=lookback_days)

            if len(historical_data) < 300:
                print("❌ 학습 데이터 부족 (최소 300일 필요)")
                return None, None

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
                    ticker_data[f'future_{future_days}d_return'] = ticker_data['close'].shift(-future_days) / \
                                                                   ticker_data['close'] - 1

                # 유효한 데이터만 사용
                valid_data = ticker_data.dropna()

                if len(valid_data) < 20:
                    data_quality_stats['skipped_insufficient_valid'] += 1
                    continue

                data_quality_stats['qualified_tickers'] += 1

                available_features = [col for col in feature_columns if col in valid_data.columns]

                if len(available_features) < 15:
                    data_quality_stats['skipped_insufficient_features'] += 1
                    continue

                features = valid_data[available_features].values

                # 🎯 개선된 타겟 생성: 안정성 중심 이진 분류 (백테스트 엔진과 동일)
                future_5d_return = valid_data['future_5d_return']

                # 🎯 타겟 재정의 - 안정성 중심 접근
                # 수수료 0.3% × 2 = 0.6% + 슬리피지 고려하여 1.5% 이상을 의미있는 수익으로 정의
                # 기존 1% → 1.5%로 상향 조정 (더 엄격한 기준으로 노이즈 제거)

                # 1단계: 기본 수익률 기준 상향
                basic_profit_threshold = 0.015  # 1.5%

                # 🎯 2단계: 안정성 조건 추가 (점진적 도입)
                try:
                    # 변동성 계산 (5일간 일별 수익률의 표준편차)
                    volatility_5d = valid_data['return_1d'].rolling(5).std()
                    volatility_median = volatility_5d.median()

                    # 급격한 하락 방지 (5일간 최대 하락률 체크)
                    min_return_5d = valid_data['return_1d'].rolling(5).min()

                    # 안정성 기반 조건들
                    basic_profit = future_5d_return >= basic_profit_threshold  # 1.5% 이상 수익
                    stable_volatility = volatility_5d <= volatility_median  # 중간 이하 변동성
                    no_major_crash = min_return_5d >= -0.05  # 5일간 최대 5% 하락까지만

                    # 최종 안정성 타겟: 모든 조건을 만족하는 경우만 1
                    stable_targets = basic_profit & stable_volatility & no_major_crash

                    # 안정성 타겟의 유효성 검증
                    if len(stable_targets.dropna()) > len(valid_data) * 0.7:  # 70% 이상 유효한 경우만
                        targets = np.where(stable_targets.fillna(False), 1, 0)
                    else:
                        # 안정성 조건이 너무 엄격하면 기본 타겟 사용
                        targets = np.where(future_5d_return >= basic_profit_threshold, 1, 0)

                except Exception as e:
                    # 안정성 계산 실패시 기본 타겟으로 대체
                    targets = np.where(future_5d_return >= basic_profit_threshold, 1, 0)

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
            print(f"   📐 피처 수: {len(feature_columns)}개")
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

    def train_ai_model(self) -> Optional[lgb.Booster]:
        """AI 모델 훈련 (독립 훈련 모듈과 동일)"""
        print("🤖 AI 모델 훈련 시작...")

        # 학습 데이터 준비
        X, y = self.prepare_training_data()

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

            # 클래스 불균형 해결 (SMOTE 오버샘플링 우선 적용)
            try:
                from imblearn.over_sampling import SMOTE

                # SMOTE 적용 (k_neighbors를 데이터 크기에 맞게 조정)
                X_train_class0 = X_train[y_train == 0]
                X_train_class1 = X_train[y_train == 1]
                min_class_size = min(len(X_train_class0), len(X_train_class1))
                k_neighbors = min(5, min_class_size - 1) if min_class_size > 1 else 1

                if k_neighbors >= 1:
                    smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
                    X_train, y_train = smote.fit_resample(X_train, y_train)
                    print(f"📊 SMOTE 적용 완료: 균형 데이터 생성 ({len(X_train)} 샘플)")
                else:
                    raise ValueError("SMOTE 적용 불가")

            except Exception as e:
                print(f"⚠️ SMOTE 적용 실패, 기존 리샘플링 사용: {e}")
                # 기존 리샘플링 방식
                X_train_class0 = X_train[y_train == 0]
                X_train_class1 = X_train[y_train == 1]

                if len(X_train_class0) > len(X_train_class1):
                    X_train_class0_resampled = resample(X_train_class0, n_samples=int(len(X_train_class1) * 1.5),
                                                        random_state=42)
                    X_train_class1_resampled = X_train_class1
                else:
                    X_train_class0_resampled = X_train_class0
                    X_train_class1_resampled = resample(X_train_class1, n_samples=int(len(X_train_class0) * 1.5),
                                                        random_state=42)

                X_train = np.vstack([X_train_class0_resampled, X_train_class1_resampled])
                y_train = np.hstack([
                    np.zeros(len(X_train_class0_resampled)),
                    np.ones(len(X_train_class1_resampled))
                ])

            # 셔플 (공통)
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

            # 이진 분류 예측 (임계값 강화: 0.5 → 0.7)
            y_pred_val = (y_pred_val_proba > 0.7).astype(int)
            y_pred_test = (y_pred_test_proba > 0.7).astype(int)

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
            print(f"   실제 0: {cm[0, 0]:6d} {cm[0, 1]:6d}")
            print(f"   실제 1: {cm[1, 0]:6d} {cm[1, 1]:6d}")

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

            self.model = model
            return model

        except Exception as e:
            print(f"❌ 모델 훈련 오류: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_ai_model(self) -> Optional[lgb.Booster]:
        """저장된 AI 모델 로드 (강화된 버전)"""
        try:
            if os.path.exists('ai_price_prediction_model.txt'):
                model = lgb.Booster(model_file='ai_price_prediction_model.txt')

                # 모델 메타데이터 검증
                self._load_model_metadata()

                self.model = model
                return model
            else:
                print("📝 저장된 모델이 없어 새로 훈련합니다...")
                return self.train_ai_model()

        except Exception as e:
            print(f"❌ 모델 로드 오류: {e}")
            print("🔄 새 모델 훈련 시도...")
            return self.train_ai_model()

    def _load_model_metadata(self) -> None:
        """모델 메타데이터 로드"""
        try:
            with open('ai_model_metadata.json', 'r') as f:
                metadata = json.load(f)

            print(f"📅 모델 훈련일: {metadata.get('train_date', 'Unknown')}")
            print(f"📊 모델 품질: {metadata.get('model_quality_score', 0):.1f}/100")
            print(f"🔢 클래스 수: {metadata.get('class_count', 'Unknown')}")
            print(f"📐 피처 수: {metadata.get('feature_count', 'Unknown')}")

            # 모델이 너무 오래되었는지 확인 (7일 이상)
            train_date = metadata.get('train_date')
            if train_date:
                train_datetime = datetime.fromisoformat(train_date.replace('Z', '+00:00'))
                days_old = (datetime.now() - train_datetime).days

                if days_old > 7:
                    print(f"⚠️ 모델이 {days_old}일 전에 훈련됨. 재훈련을 권장합니다.")

                    # 자동 재훈련 여부 결정
                    if days_old > 14:  # 2주 이상 된 모델은 자동 재훈련
                        print("🔄 모델이 너무 오래되어 자동 재훈련 시작...")
                        self.train_ai_model()
                        return

            self.model_metadata = metadata
            return

        except FileNotFoundError:
            print("⚠️ 모델 메타데이터 없음")
            return
        except Exception as e:
            print(f"⚠️ 메타데이터 읽기 오류: {e}")
            return


# 전역 AI 모델 매니저 (싱글톤 패턴)
_ai_manager_instance = None


def get_ai_manager() -> AIModelManager:
    """AI 모델 매니저 인스턴스 반환 (싱글톤)"""
    global _ai_manager_instance
    if _ai_manager_instance is None:
        _ai_manager_instance = AIModelManager()
    return _ai_manager_instance


# 편의 함수들
def train_ai_model() -> Optional[lgb.Booster]:
    """AI 모델 훈련"""
    manager = get_ai_manager()
    return manager.train_ai_model()


def load_ai_model() -> Optional[lgb.Booster]:
    """AI 모델 로드"""
    manager = get_ai_manager()
    return manager.load_ai_model()


def get_ai_prediction_score(ticker: str) -> float:
    """AI 예측 점수 계산"""
    manager = get_ai_manager()
    return manager.get_ai_prediction_score(ticker)


def prepare_training_data(lookback_days: int = 1000) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """학습 데이터 준비"""
    manager = get_ai_manager()
    return manager.prepare_training_data(lookback_days)
