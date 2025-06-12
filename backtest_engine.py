#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스팅 엔진 - strategy.py 기반 백테스팅 시스템
기본적인 백테스팅 기능 구현 (복잡한 예외사항은 추후 추가)
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import ta
import warnings
warnings.filterwarnings('ignore')

# 데이터 소스
import FinanceDataReader as fdr
from pykrx import stock as pystock
from dateutil.relativedelta import relativedelta

# AI 모델 임포트 (strategy.py와 동일)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import lightgbm as lgb
import os

class BacktestEngine:
    def __init__(self, initial_capital=10_000_000, transaction_cost=0.003):
        """
        백테스팅 엔진 초기화
        
        Args:
            initial_capital: 초기 자본금 (기본 1000만원)
            transaction_cost: 거래 비용 (기본 0.3%)
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        
        # 포트폴리오 상태
        self.cash = initial_capital
        self.holdings = {}  # {ticker: {'quantity': int, 'buy_price': float, 'buy_date': str}}
        self.holding_period = {}  # {ticker: days}
        
        # 거래 기록
        self.trade_history = []
        self.portfolio_history = []
        
        # 성과 지표
        self.daily_returns = []
        self.total_return = 0
        self.max_drawdown = 0
        
        print(f"💼 백테스팅 엔진 초기화 완료")
        print(f"   초기 자본: {initial_capital:,}원")
        print(f"   거래 비용: {transaction_cost*100:.1f}%")
        
        # AI 관련 추가 속성
        self.current_model = None
        self.model_trained_date = None
        self.ai_enabled = True  # AI 기능 활성화 여부

    # ============ AI 모델 관련 기능 (strategy.py 기반) ============
    
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
                return None, None
            
            historical_data = pd.concat(all_data, ignore_index=True)
            historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'])
            
            print(f"✅ 수집 완료: {len(historical_data)}개 레코드, {historical_data['ticker'].nunique()}개 종목")
            
            # 날짜 범위 확인
            print(f"   📅 데이터 기간: {historical_data['timestamp'].min()} ~ {historical_data['timestamp'].max()}")
            
            # 강화된 피처 및 타겟 생성
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
                ticker_data = self.create_technical_features(ticker_data.copy())
                
                # 다중 기간 미래 수익률 계산
                for future_days in [3, 5, 7]:
                    ticker_data[f'future_{future_days}d_return'] = ticker_data['close'].shift(-future_days) / ticker_data['close'] - 1
                
                # 유효한 데이터만 사용
                valid_data = ticker_data.dropna()
                
                if len(valid_data) < 20:  # 종목별 최소 유효 샘플
                    data_quality_stats['skipped_insufficient_valid'] += 1
                    continue
                
                data_quality_stats['qualified_tickers'] += 1
                
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
                
                available_features = [col for col in feature_columns if col in valid_data.columns]
                
                if len(available_features) < 10:  # 최소 피처 수 (15개 중 10개 이상)
                    data_quality_stats['skipped_insufficient_features'] += 1
                    continue
                
                features = valid_data[available_features].values
                
                # 개선된 타겟 생성: 이진 분류로 단순화
                future_5d_return = valid_data['future_5d_return']
                
                # 이진 분류: 0(손실/횡보), 1(수익)
                # 수수료 0.3% × 2 = 0.6% 고려하여 1% 이상을 수익으로 정의
                targets = np.where(future_5d_return >= 0.01, 1, 0)
                
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
            print(f"   📐 피처 수: {len(available_features) if 'available_features' in locals() else len(feature_columns)}개")
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
            from sklearn.model_selection import StratifiedKFold
            from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
            
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
            
            # 클래스 불균형 해결을 위한 언더샘플링 (훈련 데이터만)
            from sklearn.utils import resample
            
            # 각 클래스별로 데이터 분리
            X_train_class0 = X_train[y_train == 0]
            X_train_class1 = X_train[y_train == 1]
            
            # 균형잡힌 샘플링
            min_class_size = min(len(X_train_class0), len(X_train_class1))
            
            # 언더샘플링 또는 오버샘플링
            if len(X_train_class0) > len(X_train_class1):
                # 클래스 0이 더 많으면 언더샘플링
                X_train_class0_resampled = resample(X_train_class0, n_samples=int(len(X_train_class1) * 1.5), random_state=42)
                X_train_class1_resampled = X_train_class1
            else:
                # 클래스 1이 더 많으면 언더샘플링
                X_train_class0_resampled = X_train_class0
                X_train_class1_resampled = resample(X_train_class1, n_samples=int(len(X_train_class0) * 1.5), random_state=42)
            
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
            from sklearn.utils.class_weight import compute_class_weight
            
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
            
            # 이진 분류 예측
            y_pred_val = (y_pred_val_proba > 0.5).astype(int)
            y_pred_test = (y_pred_test_proba > 0.5).astype(int)
            
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
            from sklearn.metrics import roc_auc_score
            try:
                auc_score = roc_auc_score(y_test, y_pred_test_proba)
                print(f"📊 AUC 점수: {auc_score:.3f}")
            except:
                auc_score = 0.5

            # 모델 품질 검증 (이진 분류)
            model_quality_score = 0
            
            # 1. AUC 점수 (0-30점)
            model_quality_score += min(auc_score * 30, 30) if 'auc_score' in locals() else 15
            
            # 2. F1 점수 (0-30점)
            from sklearn.metrics import f1_score, precision_score, recall_score
            f1 = f1_score(y_test, y_pred_test)
            precision = precision_score(y_test, y_pred_test)
            recall = recall_score(y_test, y_pred_test)
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
            from sklearn.metrics import confusion_matrix
            cm = confusion_matrix(y_test, y_pred_test)
            print(f"   📊 혼동 행렬:")
            print(f"      예측 0    예측 1")
            print(f"   실제 0: {cm[0,0]:6d} {cm[0,1]:6d}")
            print(f"   실제 1: {cm[1,0]:6d} {cm[1,1]:6d}")
            
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
    
    def get_ai_prediction_score(self, ticker, current_date, model):
        """AI 모델을 사용한 예측 점수 (다중 클래스 대응, strategy.py와 동일)"""
        try:
            # 현재 날짜까지의 데이터만 사용
            data = self.get_past_data(ticker, n=50)  # 충분한 데이터 확보
            if data.empty or len(data) < 30:
                return 0.3  # 데이터 부족시 낮은 점수

            # 현재 날짜 이후 데이터 제거
            current_date_pd = pd.to_datetime(current_date)
            data = data[pd.to_datetime(data['timestamp']) <= current_date_pd].copy()
            if len(data) < 30:
                return 0.3
            
            # 강화된 기술적 지표 생성
            data = self.create_technical_features(data)
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
    
    def ai_enhanced_final_selection(self, entry_tickers, current_date):
        """AI를 활용한 최종 종목 선정 (강화된 버전, strategy.py와 동일)"""
        if not self.ai_enabled or self.current_model is None:
            print("❌ AI 모델을 사용할 수 없어 빈 리스트 반환")
            return []
        
        print("🤖 AI 최종 종목 선정 시작...")
        
        # 모델 품질 확인
        model_quality_score = getattr(self.current_model, 'model_quality_score', 60)
        print(f"📊 모델 품질 점수: {model_quality_score:.1f}/100")
        
        # 모델 품질이 너무 낮으면 거래 중단
        if model_quality_score < 40:
            print("❌ 모델 품질이 너무 낮아 거래를 중단합니다.")
            return []
        
        ai_scored_tickers = []
        
        # 각 종목에 대해 AI 예측 점수 계산
        for candidate in entry_tickers:
            ticker = candidate['ticker']
            ai_score = self.get_ai_prediction_score(ticker, current_date, self.current_model)
            ai_scored_tickers.append({
                'ticker': ticker,
                'ai_score': ai_score,
                'technical_score': candidate['technical_score'],
                'current_price': candidate['current_price'],
                'trade_amount': candidate['trade_amount'],
                'combined_score': candidate['combined_score']
            })
            
            print(f"🎯 {ticker}: AI 예측 점수 = {ai_score:.3f}")
        
        # AI 점수로 정렬
        ai_scored_tickers.sort(key=lambda x: x['ai_score'], reverse=True)
        
        # 신뢰도 기준 현실화: 모델 품질에 따라 동적 조정
        if model_quality_score >= 65:
            min_score_threshold = 0.55  # 우수한 모델: 0.55 이상
            max_selections = 5
        elif model_quality_score >= 50:
            min_score_threshold = 0.60  # 양호한 모델: 0.60 이상
            max_selections = 4
        else:
            min_score_threshold = 0.65  # 보통 모델: 0.65 이상
            max_selections = 3

        print(f"📏 신뢰도 기준: {min_score_threshold:.2f} 이상 (최대 {max_selections}개)")

        # 기준을 만족하는 종목만 선정
        final_selection = []
        high_confidence_count = 0
        medium_confidence_count = 0
        hybrid_count = 0  # 하이브리드 선정 카운트
        
        for item in ai_scored_tickers:
            if len(final_selection) >= max_selections:
                break
                
            # 고신뢰: AI 점수만으로 선정
            if item['ai_score'] >= min_score_threshold:
                final_selection.append(item)
                
                # 신뢰도 분류 (현실적 기준)
                if item['ai_score'] >= 0.65:
                    high_confidence_count += 1
                elif item['ai_score'] >= 0.55:
                    medium_confidence_count += 1
                    
            # 하이브리드 접근: AI 점수가 중간 수준이면 기술적 분석과 결합
            elif item['ai_score'] >= (min_score_threshold - 0.10) and len(final_selection) < max_selections:
                # AI 점수와 기술적 점수의 가중 평균
                combined_score = (item['ai_score'] * 0.7) + (item['technical_score'] * 0.3)
                
                # 결합 점수가 기준을 만족하면 선정
                if combined_score >= (min_score_threshold - 0.05):
                    final_selection.append(item)
                    hybrid_count += 1
                    print(f"🔄 {item['ticker']}: 하이브리드 선정 (AI: {item['ai_score']:.3f}, 기술: {item['technical_score']:.3f}, 결합: {combined_score:.3f})")

        # 선정 결과 출력
        if len(final_selection) == 0:
            print("❌ AI 신뢰도 기준을 만족하는 종목이 없습니다.")
            print("⚠️ 오늘은 매수를 건너뛰겠습니다.")
            
            # 가장 높은 점수라도 출력
            if ai_scored_tickers:
                best_score = ai_scored_tickers[0]['ai_score']
                print(f"📊 최고 점수: {best_score:.3f} (기준: {min_score_threshold:.2f})")
        else:
            print(f"🏆 AI 최종 선정: {len(final_selection)}개 종목")
            print(f"   🟢 고신뢰(0.65+): {high_confidence_count}개")
            print(f"   🟡 중신뢰(0.55+): {medium_confidence_count}개")
            print(f"   🔄 하이브리드: {hybrid_count}개")
        
        return final_selection

    def get_past_data(self, ticker, n=100):
        """개별 종목 과거 원시 데이터 조회 (FinanceDataReader 사용)"""
        try:
            data = fdr.DataReader(ticker, start=None, end=None)
            data.columns = [col.lower() for col in data.columns]
            data.index.name = 'timestamp'
            data = data.reset_index()
            
            if n == 1:
                return data.iloc[-1:].copy()
            else:
                return data.tail(n).copy()
        except Exception as e:
            print(f"❌ {ticker} 데이터 조회 실패: {e}")
            return pd.DataFrame()

    def get_market_data(self, date, n_days_before=20):
        """특정 날짜의 전체 시장 데이터 조회 (pykrx 사용)"""
        try:
            # 지정된 날짜부터 과거 n일 데이터 수집
            all_data = []
            current_date = pd.to_datetime(date)
            
            for i in range(n_days_before):
                target_date = current_date - timedelta(days=i)
                date_str = target_date.strftime('%Y%m%d')
                
                try:
                    # KOSPI + KOSDAQ 데이터
                    kospi = pystock.get_market_ohlcv(date_str, market='KOSPI')
                    kosdaq = pystock.get_market_ohlcv(date_str, market='KOSDAQ')
                    daily_data = pd.concat([kospi, kosdaq])
                    
                    if daily_data.empty or daily_data['거래대금'].sum() == 0:
                        continue  # 휴장일 스킵
                    
                    # 컬럼명 영어로 변환
                    daily_data = daily_data.rename(columns={
                        '시가': 'open', '고가': 'high', '저가': 'low', '종가': 'close',
                        '거래량': 'volume', '거래대금': 'trade_amount'
                    })
                    
                    daily_data['timestamp'] = target_date.strftime('%Y-%m-%d')
                    daily_data.index.name = 'ticker'
                    daily_data = daily_data.reset_index()
                    
                    all_data.append(daily_data)
                    
                except Exception as e:
                    continue
            
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                result['timestamp'] = pd.to_datetime(result['timestamp'])
                return result.sort_values(['timestamp', 'ticker']).reset_index(drop=True)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ {date} 시장 데이터 조회 실패: {e}")
            return pd.DataFrame()

    def create_technical_features(self, data):
        """강화된 기술적 분석 지표 생성 (strategy.py와 동일)"""
        try:
            if len(data) < 30:
                # 데이터가 부족하면 기본 지표만 생성
                # 기본 수익률 계산
                data['return_1d'] = data['close'].pct_change(1)
                
                # 추가 지표들
                # 양봉/음봉 연속성
                data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
                data['candle_streak'] = data['candle_type'].rolling(3).sum()

                # 거래량 가격 상관성
                data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])

                # 가격 가속도
                data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)

                # 심리적 저항선 근접도 (천원 단위)
                data['round_number_proximity'] = (data['close'] % 1000) / 1000

                return data
            
            # 기본 수익률 계산
            for period in [1, 3, 5, 10, 20]:
                data[f'return_{period}d'] = data['close'].pct_change(period)

            # 이동평균 및 비율 (더 다양한 기간)
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
            # 양봉/음봉 연속성
            data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
            data['candle_streak'] = data['candle_type'].rolling(3).sum()
            
            # 거래량 가격 상관성
            data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
            
            # 가격 가속도
            data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
            
            # 심리적 저항선 근접도 (천원 단위)
            data['round_number_proximity'] = (data['close'] % 1000) / 1000
            
            return data
        except Exception as e:
            print(f"기술적 지표 생성 오류: {e}")
            # 최소한의 지표라도 생성
            data['return_1d'] = data['close'].pct_change(1)
            # 추가 지표들
            # 양봉/음봉 연속성
            data['candle_type'] = np.where(data['close'] > data['open'], 1, -1)
            data['candle_streak'] = data['candle_type'].rolling(3).sum()
            
            # 거래량 가격 상관성
            data['volume_price_corr'] = data['close'].rolling(20).corr(data['volume'])
            
            # 가격 가속도
            data['price_acceleration'] = data['return_1d'] - data['return_1d'].shift(1)
            
            # 심리적 저항선 근접도 (천원 단위)
            data['round_number_proximity'] = (data['close'] % 1000) / 1000
            
            return data

    def get_technical_score(self, ticker, current_date):
        """규칙 기반 기술적 분석 점수 계산 (strategy.py와 동일)"""
        try:
            # 현재 날짜까지의 데이터만 사용 (Look-ahead bias 방지)
            data = self.get_past_data(ticker, n=50)
            if data.empty or len(data) < 30:
                return 0.5
            
            # 현재 날짜 이후 데이터 제거
            data = data[data['timestamp'] <= current_date].copy()
            if len(data) < 30:
                return 0.5
            
            # 기술적 지표 생성
            data = self.create_technical_features(data)
            latest = data.iloc[-1]
            
            # NaN 체크
            if pd.isna(latest.get('rsi_14', np.nan)) or pd.isna(latest.get('price_ma_ratio_20', np.nan)):
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
            
            # 2. 이동평균 대비 위치
            ma_signals = 0
            for period in [5, 10, 20]:
                if latest[f'price_ma_ratio_{period}'] < 0.98:
                    ma_signals += 1
            
            if ma_signals >= 2:
                score += 0.2
            
            # 3. 단기 반등 시그널
            if latest['return_1d'] > 0.01 and latest.get('return_3d', 0) < -0.02:
                score += 0.15
            
            # 4. 거래량 급증
            volume_ratio = latest.get('volume_ratio_5d', 1.0)
            if volume_ratio > 1.8:
                score += 0.1
            elif volume_ratio > 1.3:
                score += 0.05
            
            # 5. 변동성 조정
            if latest.get('volatility_10d', 0) > 0.05:
                score -= 0.1
            
            # 6. 볼린저 밴드 하단 근처
            if latest.get('bb_position', 0) < -0.8:
                score += 0.15
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            print(f"기술적 점수 계산 오류 ({ticker}): {e}")
            return 0.5

    def get_technical_hold_signal(self, ticker, current_date):
        """보유 종목에 대한 규칙 기반 홀드/매도 시그널"""
        try:
            data = self.get_past_data(ticker, n=30)
            if data.empty or len(data) < 20:
                return 0.5
            
            # 현재 날짜 이후 데이터 제거
            data = data[data['timestamp'] <= current_date].copy()
            if len(data) < 20:
                return 0.5
            
            # 기술적 지표 생성
            data = self.create_technical_features(data)
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
            if latest.get('bb_position', 0) > 0.8:
                hold_score -= 0.2
            
            return max(0.0, min(1.0, hold_score))
            
        except Exception as e:
            return 0.5

    def enhanced_stock_selection(self, current_date):
        """기술적 분석 강화 종목 선정 (strategy.py 로직 재현)"""
        try:
            print(f"📊 {current_date} 종목 선정 시작...")
            
            # 현재 날짜의 시장 데이터 조회
            market_data = self.get_market_data(current_date, n_days_before=25)
            if market_data.empty:
                print(f"⚠️ {current_date} 시장 데이터 없음")
                return []
            
            # 5일 종가 최저값, 20일 이동평균 계산
            market_data = market_data.sort_values(['ticker', 'timestamp'])
            market_data['5d_min_close'] = market_data.groupby('ticker')['close'].rolling(5, min_periods=1).min().reset_index(0, drop=True)
            market_data['20d_ma'] = market_data.groupby('ticker')['close'].rolling(20, min_periods=1).mean().reset_index(0, drop=True)
            
            # 현재 날짜 데이터만 추출
            today_data = market_data[market_data['timestamp'] == current_date].copy()
            if today_data.empty:
                print(f"⚠️ {current_date} 당일 데이터 없음")
                return []
            
            # 기존 조건에 맞는 종목 찾기
            traditional_candidates = today_data[
                (today_data['5d_min_close'] == today_data['close']) &
                (today_data['20d_ma'] > today_data['close']) &
                (today_data['trade_amount'] > 1_000_000_000)  # 최소 거래대금 10억
            ].copy()
            
            print(f"📊 전통적 조건 후보: {len(traditional_candidates)}개")
            
            if traditional_candidates.empty:
                return []
            
            # 기술적 분석 점수 추가 분석
            enhanced_candidates = []
            
            for _, row in traditional_candidates.iterrows():
                ticker = row['ticker']
                
                # 기술적 분석 점수 계산
                technical_score = self.get_technical_score(ticker, current_date)
                
                # 결합 점수: 기존 거래량 가중치 + 기술적 분석 보정
                technical_multiplier = 0.5 + technical_score  # 0.5 ~ 1.5 배수
                combined_score = row['trade_amount'] * technical_multiplier
                
                enhanced_candidates.append({
                    'ticker': ticker,
                    'trade_amount': row['trade_amount'],
                    'technical_score': technical_score,
                    'combined_score': combined_score,
                    'current_price': row['close']
                })
            
            # 기술적 분석 강화 점수로 정렬
            enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
            
            # 기술적 점수가 0.6 이상인 종목만 1차 선정
            selected_candidates = []
            for candidate in enhanced_candidates[:15]:  # 상위 15개 확인
                if candidate['technical_score'] >= 0.6 and len(selected_candidates) < 10:
                    selected_candidates.append(candidate)
            
            print(f"🎯 기술적 분석 1차 선정: {len(selected_candidates)}개 종목")
            
            # AI 최종 선정 추가
            if self.ai_enabled and self.current_model is not None:
                final_selection = self.ai_enhanced_final_selection(selected_candidates, current_date)
                print(f"🤖 AI 선정 결과: {len(final_selection)}개")
            else:
                final_selection = selected_candidates[:5]  # AI 없으면 상위 5개
                print(f"📊 AI 모델 없음 - 기술적 분석 상위 5개 선정")
            
            return final_selection
            
        except Exception as e:
            print(f"❌ 종목 선정 오류: {e}")
            return []

    def simulate_buy(self, candidates, current_date, max_positions=5):
        """매수 시뮬레이션 (AI 점수 활용)"""
        bought_count = 0
        total_invested = 0
        
        # 현재 보유 종목 수 확인
        current_positions = len([ticker for ticker, holding in self.holdings.items() if holding.get('quantity', 0) > 0])
        available_slots = max_positions - current_positions
        
        print(f"📊 {current_date} 매수 검토...")
        print(f"   현재 보유: {current_positions}개")
        print(f"   매수 가능: {available_slots}개")
        print(f"   후보 종목: {len(candidates)}개")
        
        if available_slots <= 0:
            print(f"📊 포트폴리오 한계 도달 (현재 {current_positions}개 보유)")
            return bought_count, total_invested
        
        # 종목당 투자 금액 계산 (현금의 80%를 사용 가능한 슬롯으로 나누기)
        available_cash = self.cash * 0.8
        investment_per_stock = available_cash / available_slots if available_slots > 0 else 0
        
        print(f"   사용 가능 현금: {available_cash:,.0f}원")
        print(f"   종목당 기본 투자: {investment_per_stock:,.0f}원")
        
        for candidate in candidates[:available_slots]:
            ticker = candidate['ticker']
            current_price = candidate['current_price']
            technical_score = candidate['technical_score']
            ai_score = candidate.get('ai_score', 0.5)  # AI 점수가 없으면 중립 점수
            
            # 이미 보유 중인 종목은 스킵
            if ticker in self.holdings and self.holdings[ticker].get('quantity', 0) > 0:
                print(f"   {ticker}: 이미 보유 중 - 스킵")
                continue
            
            # 개선된 AI 점수 기반 투자 금액 조정 (현실적 기준)
            if ai_score >= 0.65:
                investment_amount = investment_per_stock * 1.5  # 50% 증액 (고신뢰)
                confidence_level = "고신뢰"
            elif ai_score >= 0.55:
                investment_amount = investment_per_stock * 1.2  # 20% 증액 (중신뢰)
                confidence_level = "중신뢰"
            elif ai_score >= 0.45:
                investment_amount = investment_per_stock  # 기본 금액 (저신뢰)
                confidence_level = "저신뢰"
            else:
                investment_amount = investment_per_stock * 0.7  # 30% 감액 (매우저신뢰)
                confidence_level = "매우저신뢰"
            
            # 최소 투자 금액 체크
            if investment_amount < 300_000:
                print(f"   {ticker}: 투자금액 부족 ({investment_amount:,.0f}원 < 300,000원)")
                continue
            
            # 매수 수량 계산
            quantity = int(investment_amount // current_price)
            if quantity <= 0:
                print(f"   {ticker}: 매수 수량 부족 (가격: {current_price:,}원)")
                continue
            
            actual_investment = quantity * current_price
            transaction_fee = actual_investment * self.transaction_cost
            total_cost = actual_investment + transaction_fee
            
            # 현금 부족 체크
            if total_cost > self.cash:
                print(f"   {ticker}: 현금 부족 (필요: {total_cost:,.0f}원, 보유: {self.cash:,.0f}원)")
                continue
            
            # 매수 실행
            self.cash -= total_cost
            
            # holdings 딕셔너리 안전한 업데이트
            if ticker not in self.holdings:
                self.holdings[ticker] = {}
            
            self.holdings[ticker].update({
                'quantity': quantity,
                'buy_price': current_price,
                'buy_date': current_date,
                'technical_score': technical_score,
                'ai_score': ai_score,
                'confidence_level': confidence_level
            })
            
            self.holding_period[ticker] = 1
            
            # 거래 기록
            self.trade_history.append({
                'date': current_date,
                'action': 'BUY',
                'ticker': ticker,
                'quantity': quantity,
                'price': current_price,
                'amount': actual_investment,
                'fee': transaction_fee,
                'technical_score': technical_score,
                'ai_score': ai_score,
                'confidence_level': confidence_level
            })
            
            bought_count += 1
            total_invested += actual_investment
            
            print(f"📥 {ticker} 매수 완료: {quantity:,}주 @ {current_price:,}원")
            print(f"   기술점수: {technical_score:.3f}, AI점수: {ai_score:.3f} ({confidence_level})")
        
        print(f"📊 매수 완료: {bought_count}개 종목, 총 투자 {total_invested:,.0f}원")
        return bought_count, total_invested

    def simulate_sell(self, current_date):
        """매도 시뮬레이션 (3-5일 보유 전략)"""
        sold_count = 0
        total_profit = 0
        tickers_to_sell = []
        
        print(f"🔍 {current_date} 매도 검토 시작...")
        print(f"   현재 보유 종목: {len([t for t, h in self.holdings.items() if h.get('quantity', 0) > 0])}개")
        
        for ticker in list(self.holdings.keys()):
            holding = self.holdings[ticker]
            if holding.get('quantity', 0) <= 0:
                continue
                
            holding_days = self.holding_period.get(ticker, 0)
            should_sell = False
            
            print(f"   {ticker}: {holding_days}일 보유 중")
            
            # 기본 3일 룰
            if holding_days >= 3:
                should_sell = True
                print(f"   → {ticker}: 3일 이상 보유로 매도 검토")
                
                # 기술적 홀드 시그널 체크 (3일차에만)
                if holding_days == 3:
                    try:
                        hold_signal = self.get_technical_hold_signal(ticker, current_date)
                        
                        if hold_signal >= 0.75:
                            should_sell = False
                            print(f"   → {ticker}: 기술적 분석 강홀드 신호로 1일 연장 (신호: {hold_signal:.3f})")
                    except Exception as e:
                        print(f"   → {ticker}: 홀드 시그널 계산 오류: {e}")
            
            # 안전장치: 5일 이상은 무조건 매도
            if holding_days >= 5:
                should_sell = True
                print(f"   → {ticker}: 5일 안전룰 적용")
            
            if should_sell:
                tickers_to_sell.append(ticker)
        
        print(f"📤 매도 대상 종목: {len(tickers_to_sell)}개")
        
        # 매도 실행
        for ticker in tickers_to_sell:
            try:
                # 현재가 조회 - 데이터 소스 통합
                current_data = self.get_past_data(ticker, n=5)  # 여유있게 5일 데이터
                if current_data.empty:
                    print(f"❌ {ticker}: 과거 데이터 조회 실패")
                    continue
                
                # 현재 날짜 이전 데이터만 필터링
                current_date_pd = pd.to_datetime(current_date)
                valid_data = current_data[pd.to_datetime(current_data['timestamp']) <= current_date_pd]
                
                if valid_data.empty:
                    print(f"❌ {ticker}: {current_date} 이전 데이터 없음")
                    continue
                    
                current_price = valid_data.iloc[-1]['close']
                holding = self.holdings[ticker]
                quantity = holding['quantity']
                buy_price = holding['buy_price']
                
                print(f"📤 {ticker} 매도 실행: {quantity}주 @ {current_price:,}원")
                
                # 매도 금액 계산
                sell_amount = quantity * current_price
                transaction_fee = sell_amount * self.transaction_cost
                net_amount = sell_amount - transaction_fee
                
                # 손익 계산
                buy_amount = quantity * buy_price
                profit = net_amount - buy_amount
                profit_rate = (profit / buy_amount) * 100
                
                # 매도 실행
                self.cash += net_amount
                self.holdings[ticker]['quantity'] = 0  # 수량만 0으로 설정
                
                # 거래 기록
                self.trade_history.append({
                    'date': current_date,
                    'action': 'SELL',
                    'ticker': ticker,
                    'quantity': quantity,
                    'price': current_price,
                    'amount': sell_amount,
                    'fee': transaction_fee,
                    'profit': profit,
                    'profit_rate': profit_rate,
                    'holding_days': self.holding_period[ticker]
                })
                
                sold_count += 1
                total_profit += profit
                
                print(f"✅ {ticker} 매도 완료: 수익률 {profit_rate:+.2f}% ({self.holding_period[ticker]}일 보유)")
                
            except Exception as e:
                print(f"❌ {ticker} 매도 오류: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"📊 매도 완료: {sold_count}개 종목, 총 손익 {total_profit:+,.0f}원")
        return sold_count, total_profit

    def update_holding_period(self):
        """보유 기간 업데이트"""
        print("📅 보유 기간 업데이트 중...")
        
        for ticker in self.holdings:
            quantity = self.holdings[ticker].get('quantity', 0)
            if quantity > 0:
                current_days = self.holding_period.get(ticker, 0)
                self.holding_period[ticker] = current_days + 1
                print(f"   {ticker}: {current_days} → {self.holding_period[ticker]}일")
            else:
                # 매도된 종목은 보유 기간 초기화
                if ticker in self.holding_period:
                    print(f"   {ticker}: 매도 완료로 보유 기간 초기화")
                    self.holding_period[ticker] = 0

    def calculate_portfolio_value(self, current_date):
        """현재 포트폴리오 가치 계산"""
        total_value = self.cash
        stock_value = 0
        position_count = 0
        
        print(f"💼 {current_date} 포트폴리오 가치 계산...")
        print(f"   현금: {self.cash:,.0f}원")
        
        for ticker, holding in self.holdings.items():
            quantity = holding.get('quantity', 0)
            if quantity <= 0:
                continue
                
            try:
                # 현재가 조회 - 더 안정적인 방법
                current_data = self.get_past_data(ticker, n=5)
                if current_data.empty:
                    print(f"   ❌ {ticker}: 데이터 조회 실패")
                    # 매수가로 대체 계산
                    position_value = quantity * holding.get('buy_price', 0)
                    stock_value += position_value
                    total_value += position_value
                    position_count += 1
                    print(f"   📊 {ticker}: {quantity}주 × {holding.get('buy_price', 0):,}원 = {position_value:,.0f}원 (매수가 기준)")
                    continue
                
                # 현재 날짜 이전 데이터만 사용
                current_date_pd = pd.to_datetime(current_date)
                valid_data = current_data[pd.to_datetime(current_data['timestamp']) <= current_date_pd]
                
                if valid_data.empty:
                    print(f"   ❌ {ticker}: {current_date} 이전 데이터 없음")
                    # 매수가로 대체 계산
                    position_value = quantity * holding.get('buy_price', 0)
                    stock_value += position_value
                    total_value += position_value
                    position_count += 1
                    print(f"   📊 {ticker}: {quantity}주 × {holding.get('buy_price', 0):,}원 = {position_value:,.0f}원 (매수가 기준)")
                    continue
                    
                current_price = valid_data.iloc[-1]['close']
                position_value = quantity * current_price
                stock_value += position_value
                total_value += position_value
                position_count += 1
                
                # 손익 계산
                buy_price = holding.get('buy_price', 0)
                if buy_price > 0:
                    profit_rate = ((current_price - buy_price) / buy_price) * 100
                    print(f"   📊 {ticker}: {quantity}주 × {current_price:,}원 = {position_value:,.0f}원 ({profit_rate:+.1f}%)")
                else:
                    print(f"   📊 {ticker}: {quantity}주 × {current_price:,}원 = {position_value:,.0f}원")
                
            except Exception as e:
                print(f"   ❌ {ticker} 가치 계산 오류: {e}")
                # 매수가격으로 대체
                position_value = quantity * holding.get('buy_price', 0)
                stock_value += position_value
                total_value += position_value
                position_count += 1
                print(f"   📊 {ticker}: {quantity}주 × {holding.get('buy_price', 0):,}원 = {position_value:,.0f}원 (매수가 기준)")
        
        print(f"   주식 총 가치: {stock_value:,.0f}원 ({position_count}개 종목)")
        print(f"   포트폴리오 총 가치: {total_value:,.0f}원")
        
        return total_value

    def run_backtest(self, start_date, end_date, ai_enabled=True):
        """백테스팅 실행 (매주 AI 모델 재훈련 포함)"""
        print(f"🚀 백테스팅 시작: {start_date} ~ {end_date}")
        print(f"🤖 AI 기능: {'활성화' if ai_enabled else '비활성화'}")
        print("=" * 60)
        
        # AI 기능 설정
        self.ai_enabled = ai_enabled
        
        # 날짜 범위 생성
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        date_range = pd.date_range(start=start, end=end, freq='D')
        
        # 초기 상태
        initial_value = self.initial_capital
        
        for current_date in date_range:
            # 주말은 스킵
            if current_date.weekday() >= 5:
                continue
            
            date_str = current_date.strftime('%Y-%m-%d')
            weekday = current_date.weekday()  # 0=월요일
            
            print(f"\n📅 {date_str} 처리 중... ({'월화수목금'[weekday]}요일)")
            
            # 매주 월요일마다 AI 모델 재훈련
            if self.ai_enabled and (weekday == 0 or self.current_model is None):
                print(f"🤖 {date_str} AI 모델 재훈련 시작...")
                try:
                    temp_model = self.train_ai_model_at_date(date_str)
                    if temp_model is not None:
                        self.current_model = temp_model
                        self.model_trained_date = date_str
                        print(f"✅ AI 모델 훈련 완료 ({date_str})")
                    else:
                        print(f"❌ AI 모델 훈련 실패 - 이번 주는 이전 모델 사용 또는 기술적 분석만 사용")
                except Exception as e:
                    print(f"❌ AI 모델 훈련 오류: {e}")
                    # 이전 모델이 있으면 계속 사용
            
            # AI 모델 사용 현황 출력
            if self.ai_enabled and self.current_model is not None:
                model_accuracy = getattr(self.current_model, 'test_accuracy', 0)
                model_quality = getattr(self.current_model, 'model_quality_score', 0)
                print(f"🤖 AI 모델 사용 중 (훈련일: {self.model_trained_date})")
                print(f"   📊 모델 정확도: {model_accuracy:.1%}, 품질점수: {model_quality:.1f}/100")
            else:
                print(f"📊 기술적 분석만 사용")
            
            # 1. 보유 기간 업데이트
            self.update_holding_period()
            
            # 2. 매도 전략 실행 (아침 8:30 시뮬레이션)
            sold_count, sell_profit = self.simulate_sell(date_str)
            
            # 3. 매수 전략 실행 (오후 15:20 시뮬레이션)
            candidates = self.enhanced_stock_selection(date_str)
            bought_count, invested_amount = self.simulate_buy(candidates, date_str)
            
            # 4. 포트폴리오 가치 계산
            portfolio_value = self.calculate_portfolio_value(date_str)
            daily_return = (portfolio_value - initial_value) / initial_value
            
            # 5. 포트폴리오 기록
            current_positions = len([t for t, h in self.holdings.items() if h.get('quantity', 0) > 0])
            
            # 모델 정보 추가
            if self.ai_enabled and self.current_model is not None:
                model_accuracy = getattr(self.current_model, 'test_accuracy', 0)
                model_quality = getattr(self.current_model, 'model_quality_score', 0)
            else:
                model_accuracy = 0
                model_quality = 0
            
            self.portfolio_history.append({
                'date': date_str,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'daily_return': daily_return,
                'positions': current_positions,
                'sold_count': sold_count,
                'bought_count': bought_count,
                'ai_enabled': self.ai_enabled,
                'model_trained_date': self.model_trained_date,
                'model_accuracy': model_accuracy,
                'model_quality': model_quality
            })
            
            print(f"💼 포트폴리오: {portfolio_value:,.0f}원 (수익률: {daily_return*100:+.2f}%, 보유: {current_positions}개)")
            if model_accuracy > 0:
                print(f"   🤖 모델 정확도: {model_accuracy:.1%}")
        
        # 최종 성과 계산
        self.calculate_performance()
        
        print("\n" + "=" * 60)
        print("✅ 백테스팅 완료!")
        
        return self.get_results()

    def calculate_performance(self):
        """성과 지표 계산"""
        if not self.portfolio_history:
            return
        
        # 포트폴리오 가치 시계열
        portfolio_values = [record['portfolio_value'] for record in self.portfolio_history]
        
        # 총 수익률
        final_value = portfolio_values[-1]
        self.total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # 일별 수익률
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            daily_returns.append(daily_return)
        
        self.daily_returns = daily_returns
        
        # 최대 낙폭 (Maximum Drawdown)
        peak = portfolio_values[0]
        max_dd = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        self.max_drawdown = max_dd

    def get_results(self):
        """백테스팅 결과 반환"""
        if not self.portfolio_history:
            return {}
        
        # 거래 통계
        buy_trades = [t for t in self.trade_history if t['action'] == 'BUY']
        sell_trades = [t for t in self.trade_history if t['action'] == 'SELL']
        
        profitable_trades = [t for t in sell_trades if t['profit'] > 0]
        win_rate = len(profitable_trades) / len(sell_trades) if sell_trades else 0
        
        avg_profit = np.mean([t['profit'] for t in sell_trades]) if sell_trades else 0
        avg_holding_days = np.mean([t['holding_days'] for t in sell_trades]) if sell_trades else 0
        
        # 연간 수익률 (단순 계산)
        days_count = len(self.portfolio_history)
        annualized_return = self.total_return * (365 / days_count) if days_count > 0 else 0
        
        # 샤프 비율 (단순 계산)
        if self.daily_returns and np.std(self.daily_returns) > 0:
            sharpe_ratio = np.mean(self.daily_returns) / np.std(self.daily_returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        results = {
            'initial_capital': self.initial_capital,
            'final_value': self.portfolio_history[-1]['portfolio_value'],
            'total_return': self.total_return,
            'annualized_return': annualized_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit,
            'avg_holding_days': avg_holding_days,
            'final_cash': self.cash,
            'trade_history': self.trade_history,
            'portfolio_history': self.portfolio_history
        }
        
        return results

    def print_summary(self):
        """백테스팅 결과 요약 출력"""
        results = self.get_results()
        if not results:
            print("❌ 백테스팅 결과가 없습니다.")
            return
        
        print("\n" + "=" * 60)
        print("📊 백테스팅 결과 요약")
        print("=" * 60)
        
        print(f"💰 초기 자본: {results['initial_capital']:,}원")
        print(f"💰 최종 자산: {results['final_value']:,}원")
        print(f"📈 총 수익률: {results['total_return']*100:+.2f}%")
        print(f"📈 연환산 수익률: {results['annualized_return']*100:+.2f}%")
        print(f"📉 최대 낙폭: {results['max_drawdown']*100:.2f}%")
        print(f"📊 샤프 비율: {results['sharpe_ratio']:.3f}")
        
        print(f"\n🔄 거래 통계:")
        print(f"   총 거래 횟수: {results['total_trades']}회")
        print(f"   승률: {results['win_rate']*100:.1f}%")
        print(f"   거래당 평균 손익: {results['avg_profit_per_trade']:+,.0f}원")
        print(f"   평균 보유 기간: {results['avg_holding_days']:.1f}일")
        
        # 모델 성능 통계
        if self.portfolio_history:
            avg_accuracy = np.mean([h['model_accuracy'] for h in self.portfolio_history if h.get('model_accuracy', 0) > 0])
            avg_quality = np.mean([h['model_quality'] for h in self.portfolio_history if h.get('model_quality', 0) > 0])
            if avg_accuracy > 0:
                print(f"\n🤖 AI 모델 통계:")
                print(f"   평균 정확도: {avg_accuracy:.1%}")
                print(f"   평균 품질점수: {avg_quality:.1f}/100")
        
        print(f"\n💵 최종 현금: {results['final_cash']:,}원")
        
        print("=" * 60)

    def save_results(self, filename=None):
        """결과를 JSON 파일로 저장"""
        if filename is None:
            filename = f"backtest_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        results = self.get_results()
        
        # datetime 객체를 문자열로 변환
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {key: convert_datetime(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            else:
                return obj
        
        results_serializable = convert_datetime(results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_serializable, f, indent=2, ensure_ascii=False)
        
        print(f"💾 백테스팅 결과 저장: {filename}")
        return filename


# 사용 예시
if __name__ == "__main__":
    # 백테스팅 엔진 초기화
    engine = BacktestEngine(initial_capital=10_000_000, transaction_cost=0.003)
    
    # 백테스팅 실행 (AI 기능 포함)
    # 2025년 6월 현재 기준으로 충분한 과거 데이터가 있는 기간 사용
    start_date = "2025-05-10"
    end_date = "2025-06-10"  # 6개월 테스트
    
    try:
        # AI 기능 활성화하여 백테스팅 실행
        results = engine.run_backtest(start_date, end_date, ai_enabled=True)
        engine.print_summary()
        engine.save_results("ai_backtest_result.json")
        
    except Exception as e:
        print(f"❌ 백테스팅 실행 오류: {e}")
        import traceback
        traceback.print_exc()
