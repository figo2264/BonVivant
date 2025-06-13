# 기술적 분석 강화된 6-7 전략 (모듈화 버전)
# Cron 실행 대상 파일
# 백테스트 엔진과 train_ai_model의 모든 강화 기능 완전 적용

import time
from datetime import datetime

# 모듈화된 컴포넌트들 import
from hanlyang_stock.config.settings import get_config
from hanlyang_stock.strategy.executor import SellExecutor, BuyExecutor
from hanlyang_stock.utils.storage import get_data_manager
from hanlyang_stock.utils.notification import get_notifier
from hanlyang_stock.analysis.ai_model import get_ai_manager


def main():
    """메인 실행 함수 - 백테스트 엔진과 독립 훈련 모듈의 모든 강화 기능 적용"""
    print("🚀 한량 주식 전략 시작! (AI 강화 + 데이터 검증 + 손실 제한 + 하이브리드 선정 완전 적용)")
    
    try:
        # 설정 초기화
        config = get_config()
        data_manager = get_data_manager()
        notifier = get_notifier()
        ai_manager = get_ai_manager()
        
        # 🔧 강화된 설정 확인 및 활성화 (백테스트 엔진 모든 기능)
        strategy_data = data_manager.get_data()
        
        # 1. 데이터 검증 강화 설정 (백테스트 엔진 기능)
        if 'enhanced_data_validation' not in strategy_data:
            strategy_data['enhanced_data_validation'] = True
            print("✅ 데이터 검증 강화 기능 활성화")
        
        # 2. 손실 제한 설정 (백테스트 엔진 기능)
        if 'stop_loss_enabled' not in strategy_data:
            strategy_data['stop_loss_enabled'] = True
            strategy_data['stop_loss_rate'] = -0.05  # -5%
            print("✅ 손실 제한 기능 활성화 (기준: -5%)")
        
        # 3. 강화된 분석 활성화 (백테스트 엔진 + AI 강화)
        if 'enhanced_analysis_enabled' not in strategy_data:
            strategy_data['enhanced_analysis_enabled'] = True
            print("✅ 강화된 기술적 분석 + AI 분석 활성화")
        
        # 4. AI 신뢰도 기반 투자 전략 활성화 (백테스트 엔진 핵심 기능)
        if 'ai_confidence_strategy' not in strategy_data:
            strategy_data['ai_confidence_strategy'] = True
            strategy_data['ai_high_confidence_threshold'] = 0.55   # 고신뢰 기준 (0.65 → 0.55)
            strategy_data['ai_medium_confidence_threshold'] = 0.45 # 중신뢰 기준 (0.55 → 0.45)
            strategy_data['ai_low_confidence_threshold'] = 0.35    # 저신뢰 기준 (0.45 → 0.35)
            print("✅ AI 신뢰도 기반 투자 전략 활성화")
            print(f"   🎯 고신뢰 기준: {strategy_data['ai_high_confidence_threshold']}")
            print(f"   🎯 중신뢰 기준: {strategy_data['ai_medium_confidence_threshold']}")
            print(f"   🎯 저신뢰 기준: {strategy_data['ai_low_confidence_threshold']}")
        
        # 5. AI 모델 품질 기반 동적 기준 조정 (백테스트 엔진 기능)
        if 'dynamic_ai_threshold' not in strategy_data:
            strategy_data['dynamic_ai_threshold'] = True
            print("✅ AI 모델 품질 기반 동적 기준 조정 활성화")
        
        # 6. 하이브리드 선정 시스템 (백테스트 엔진 핵심 기능)
        if 'hybrid_selection_enabled' not in strategy_data:
            strategy_data['hybrid_selection_enabled'] = True
            strategy_data['hybrid_ai_weight'] = 0.4      # AI 가중치 40%
            strategy_data['hybrid_technical_weight'] = 0.6  # 기술적 분석 가중치 60%
            strategy_data['hybrid_threshold'] = 0.50     # 하이브리드 최소 기준 (0.60 → 0.50)
            print("✅ 하이브리드 선정 시스템 활성화")
            print(f"   ⚖️ AI 가중치: {strategy_data['hybrid_ai_weight']*100:.0f}%")
            print(f"   📊 기술 가중치: {strategy_data['hybrid_technical_weight']*100:.0f}%")
            print(f"   🎯 하이브리드 기준: {strategy_data['hybrid_threshold']}")
        
        # 7. 안정성 중심 타겟 설정 (백테스트 엔진 + 독립 훈련 모듈 기능)
        if 'stability_focused_target' not in strategy_data:
            strategy_data['stability_focused_target'] = True
            strategy_data['profit_threshold'] = 0.005    # 0.5% 이상 수익 (1.5% → 0.5%)
            strategy_data['volatility_control'] = True   # 변동성 제어
            strategy_data['crash_protection'] = True     # 급락 방지
            print("✅ 안정성 중심 타겟 설정 활성화")
            print(f"   📈 수익 기준: {strategy_data['profit_threshold']*100:.1f}%")
            print(f"   📊 변동성 제어: {'활성화' if strategy_data['volatility_control'] else '비활성화'}")
            print(f"   🛡️ 급락 방지: {'활성화' if strategy_data['crash_protection'] else '비활성화'}")
        
        # 8. SMOTE 기반 클래스 불균형 해결 (독립 훈련 모듈 기능)
        if 'smote_enabled' not in strategy_data:
            strategy_data['smote_enabled'] = True
            print("✅ SMOTE 기반 클래스 불균형 해결 활성화")
        
        # 9. 고급 홀드 시그널 (백테스트 엔진 기능)
        if 'advanced_hold_signal' not in strategy_data:
            strategy_data['advanced_hold_signal'] = True
            strategy_data['rsi_hold_upper'] = 70         # RSI 상한
            strategy_data['rsi_hold_lower'] = 30         # RSI 하한  
            strategy_data['volume_surge_threshold'] = 2.0  # 거래량 급증 기준
            print("✅ 고급 홀드 시그널 활성화")
            print(f"   📊 RSI 홀드 범위: {strategy_data['rsi_hold_lower']}-{strategy_data['rsi_hold_upper']}")
            print(f"   📈 거래량 급증 기준: {strategy_data['volume_surge_threshold']}배")
        
        # 🤖 AI 모델 상태 확인 및 자동 관리 (강화된 버전)
        ai_model_status = check_and_manage_ai_model(ai_manager, strategy_data)
        
        # 설정 저장
        data_manager.save()
        
        print("✅ 모든 모듈 초기화 완료 (백테스트 엔진 + 독립 훈련 모듈 기능 완전 적용)")
        print(f"   📊 데이터 검증 강화: {'활성화' if strategy_data.get('enhanced_data_validation') else '비활성화'}")
        print(f"   🛑 손실 제한: {'활성화' if strategy_data.get('stop_loss_enabled') else '비활성화'} ({strategy_data.get('stop_loss_rate', -0.05)*100:.1f}%)")
        print(f"   🔬 강화된 기술 분석: {'활성화' if strategy_data.get('enhanced_analysis_enabled') else '비활성화'}")
        print(f"   🤖 AI 신뢰도 전략: {'활성화' if strategy_data.get('ai_confidence_strategy') else '비활성화'}")
        print(f"   📈 동적 AI 기준: {'활성화' if strategy_data.get('dynamic_ai_threshold') else '비활성화'}")
        print(f"   🔄 하이브리드 선정: {'활성화' if strategy_data.get('hybrid_selection_enabled') else '비활성화'}")
        print(f"   🎯 안정성 타겟: {'활성화' if strategy_data.get('stability_focused_target') else '비활성화'}")
        print(f"   ⚖️ SMOTE 불균형 해결: {'활성화' if strategy_data.get('smote_enabled') else '비활성화'}")
        print(f"   🔍 고급 홀드 시그널: {'활성화' if strategy_data.get('advanced_hold_signal') else '비활성화'}")
        print(f"   🎯 AI 모델 상태: {ai_model_status}")
        
    except Exception as e:
        print(f"❌ 초기화 오류: {e}")
        import traceback
        traceback.print_exc()
        return
    
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
        # if True:  # 테스트용 (주석 해제하여 즉시 실행)
            try:
                print("🌅 아침 매도 전략 실행 시작! (강화된 홀드 시그널 + 손실 제한 완전 적용)")
                
                # 🔧 강화된 매도 전략 실행 (백테스트 엔진 모든 기능 적용)
                strategy_data = data_manager.get_data()
                
                # 매도 전략 설정
                sell_config = {
                    'stop_loss_rate': strategy_data.get('stop_loss_rate', -0.05),
                    'enhanced_data_validation': strategy_data.get('enhanced_data_validation', True),
                    'advanced_hold_signal': strategy_data.get('advanced_hold_signal', True),
                    'rsi_hold_upper': strategy_data.get('rsi_hold_upper', 70),
                    'rsi_hold_lower': strategy_data.get('rsi_hold_lower', 30),
                    'volume_surge_threshold': strategy_data.get('volume_surge_threshold', 2.0)
                }
                
                sell_executor = SellExecutor(**sell_config)
                sell_results = sell_executor.execute()
                
                print(f"✅ 매도 전략 완료: {sell_results.get('sold_count', 0)}개 종목 매도")
                print(f"   💰 매도 수익: {sell_results.get('total_profit', 0):+,}원")
                
                executed_date = current_date  # 실행 완료 표시
                break
                
            except Exception as e:
                print(f"❌ 매도 전략 실행 오류: {e}")
                import traceback
                traceback.print_exc()
                # 오류 알림 전송
                notifier.notify_error("매도 전략 실행 오류", str(e))
                executed_date = current_date  # 오류가 발생해도 실행 완료로 표시
                break

        # 15시 20분~22분 - 매수 전용 실행 (여유시간 2분)
        elif current_time.hour == 15 and 20 <= current_time.minute <= 22 and not executed_today:
        # elif True:  # 테스트용 (주석 해제하여 즉시 실행)
            try:
                print("🚀 오후 매수 전략 실행 시작! (하이브리드 선정 + AI 신뢰도 + 데이터 검증 완전 적용)")
                
                # 🔧 강화된 매수 전략 실행 (백테스트 엔진 + 독립 훈련 모듈 모든 기능 적용)
                strategy_data = data_manager.get_data()
                
                # 매수 전략 설정 (모든 강화 기능 활성화)
                buy_config = {
                    'enhanced_data_validation': strategy_data.get('enhanced_data_validation', True),
                    'ai_confidence_strategy': strategy_data.get('ai_confidence_strategy', True),
                    'ai_high_confidence_threshold': strategy_data.get('ai_high_confidence_threshold', 0.65),
                    'ai_medium_confidence_threshold': strategy_data.get('ai_medium_confidence_threshold', 0.55),
                    'ai_low_confidence_threshold': strategy_data.get('ai_low_confidence_threshold', 0.45),
                    'dynamic_ai_threshold': strategy_data.get('dynamic_ai_threshold', True),
                    'hybrid_selection_enabled': strategy_data.get('hybrid_selection_enabled', True),
                    'hybrid_ai_weight': strategy_data.get('hybrid_ai_weight', 0.4),
                    'hybrid_technical_weight': strategy_data.get('hybrid_technical_weight', 0.6),
                    'hybrid_threshold': strategy_data.get('hybrid_threshold', 0.60),
                    'stability_focused_target': strategy_data.get('stability_focused_target', True),
                    'profit_threshold': strategy_data.get('profit_threshold', 0.015),
                    'volatility_control': strategy_data.get('volatility_control', True),
                    'crash_protection': strategy_data.get('crash_protection', True)
                }
                
                buy_executor = BuyExecutor(**buy_config)
                buy_results = buy_executor.execute()
                
                print(f"✅ 매수 전략 완료: {buy_results.get('bought_count', 0)}개 종목 매수")
                print(f"   💳 총 투자: {buy_results.get('total_investment', 0):,}원")
                print(f"   🎯 AI 신뢰도별 선정:")
                print(f"      🟢 고신뢰: {buy_results.get('high_confidence_count', 0)}개")
                print(f"      🟡 중신뢰: {buy_results.get('medium_confidence_count', 0)}개")
                print(f"      🔄 하이브리드: {buy_results.get('hybrid_count', 0)}개")
                
                executed_date = current_date  # 실행 완료 표시
                break
                
            except Exception as e:
                print(f"❌ 매수 전략 실행 오류: {e}")
                import traceback
                traceback.print_exc()
                # 오류 알림 전송
                notifier.notify_error("매수 전략 실행 오류", str(e))
                executed_date = current_date  # 오류가 발생해도 실행 완료로 표시
                break

        # 루프 돌때마다 1초씩 쉬어줌
        time.sleep(1)


def check_and_manage_ai_model(ai_manager, strategy_data):
    """AI 모델 상태 확인 및 자동 관리 (백테스트 엔진 + 독립 훈련 모듈 완전 기능)"""
    try:
        print("🤖 AI 모델 상태 확인 중... (품질 기반 관리)")
        
        # 기존 모델 로드 시도
        current_model = ai_manager.load_ai_model()
        
        if current_model is None:
            print("📝 저장된 AI 모델이 없습니다.")
            
            # 자동 훈련 여부 확인
            auto_train = strategy_data.get('auto_train_ai_model', True)
            if auto_train:
                print("🔄 새 AI 모델 자동 훈련 시작... (SMOTE + 안정성 타겟 적용)")
                try:
                    new_model = ai_manager.train_ai_model()
                    if new_model:
                        # 새 모델의 품질 확인
                        if hasattr(new_model, 'model_quality_score'):
                            quality_score = new_model.model_quality_score
                            print(f"✅ AI 모델 훈련 성공! (품질: {quality_score:.1f}/100)")
                            
                            # 품질 기반 동적 임계값 조정
                            if strategy_data.get('dynamic_ai_threshold', True):
                                adjust_ai_thresholds_by_quality(strategy_data, quality_score)
                            
                            return f"새 모델 훈련 완료 (품질: {quality_score:.1f})"
                        else:
                            print("✅ AI 모델 훈련 성공!")
                            return "새 모델 훈련 완료"
                    else:
                        print("❌ AI 모델 훈련 실패")
                        return "모델 없음 (훈련 실패)"
                except Exception as e:
                    print(f"❌ AI 모델 훈련 오류: {e}")
                    return "모델 없음 (훈련 오류)"
            else:
                return "모델 없음 (자동 훈련 비활성화)"
        
        else:
            # 모델 메타데이터 확인 (강화된 품질 관리)
            try:
                import json
                with open('ai_model_metadata.json', 'r') as f:
                    metadata = json.load(f)
                
                train_date = metadata.get('train_date', 'Unknown')
                model_quality = metadata.get('model_quality_score', 0)
                test_accuracy = metadata.get('test_accuracy', 0)
                auc_score = metadata.get('auc_score', 0.5)
                
                print(f"📅 기존 모델 발견:")
                print(f"   훈련일: {train_date}")
                print(f"   품질점수: {model_quality:.1f}/100")
                print(f"   정확도: {test_accuracy:.3f}")
                print(f"   AUC: {auc_score:.3f}")
                
                # 📊 품질 기반 동적 임계값 조정 (백테스트 엔진 핵심 기능)
                if strategy_data.get('dynamic_ai_threshold', True):
                    adjust_ai_thresholds_by_quality(strategy_data, model_quality)
                
                # 모델 품질이 너무 낮으면 재훈련 권장 (기준 강화: 30 → 40)
                quality_threshold = strategy_data.get('min_model_quality_threshold', 40)
                if model_quality < quality_threshold:
                    print(f"⚠️ 모델 품질이 낮음 ({model_quality:.1f} < {quality_threshold}). 재훈련을 권장합니다.")
                    
                    auto_retrain = strategy_data.get('auto_retrain_low_quality', True)
                    if auto_retrain:
                        print("🔄 낮은 품질 모델 자동 재훈련 시작... (SMOTE + 안정성 타겟 적용)")
                        try:
                            new_model = ai_manager.train_ai_model()
                            if new_model and hasattr(new_model, 'model_quality_score'):
                                new_quality = new_model.model_quality_score
                                print(f"✅ AI 모델 재훈련 성공! (품질: {model_quality:.1f} → {new_quality:.1f})")
                                
                                # 품질 개선된 경우만 동적 임계값 재조정
                                if new_quality > model_quality and strategy_data.get('dynamic_ai_threshold', True):
                                    adjust_ai_thresholds_by_quality(strategy_data, new_quality)
                                
                                return f"재훈련 완료 (품질 개선: {model_quality:.1f} → {new_quality:.1f})"
                            else:
                                return f"기존 모델 사용 (품질: {model_quality:.1f}, 재훈련 실패)"
                        except Exception as e:
                            print(f"❌ AI 모델 재훈련 오류: {e}")
                            return f"기존 모델 사용 (품질: {model_quality:.1f}, 재훈련 오류)"
                
                # 모델이 너무 오래됐는지 확인 (기준 강화: 14일 → 10일)
                from datetime import datetime, timedelta
                try:
                    train_datetime = datetime.fromisoformat(train_date.replace('Z', '+00:00'))
                    days_old = (datetime.now() - train_datetime).days
                    
                    old_model_threshold = strategy_data.get('old_model_threshold_days', 10)
                    if days_old > old_model_threshold:
                        print(f"⚠️ 모델이 {days_old}일 전에 훈련됨 (기준: {old_model_threshold}일). 재훈련을 권장합니다.")
                        
                        auto_retrain = strategy_data.get('auto_retrain_old_model', False)  # 기본 비활성화
                        if auto_retrain:
                            print("🔄 오래된 모델 자동 재훈련 시작... (최신 SMOTE + 안정성 타겟)")
                            try:
                                new_model = ai_manager.train_ai_model()
                                if new_model and hasattr(new_model, 'model_quality_score'):
                                    new_quality = new_model.model_quality_score
                                    print(f"✅ AI 모델 재훈련 성공! (품질: {new_quality:.1f})")
                                    
                                    # 동적 임계값 재조정
                                    if strategy_data.get('dynamic_ai_threshold', True):
                                        adjust_ai_thresholds_by_quality(strategy_data, new_quality)
                                    
                                    return f"재훈련 완료 ({days_old}일 된 모델 갱신, 품질: {new_quality:.1f})"
                                else:
                                    return f"기존 모델 사용 (품질: {model_quality:.1f}, {days_old}일 전, 재훈련 실패)"
                            except Exception as e:
                                print(f"❌ AI 모델 재훈련 오류: {e}")
                                return f"기존 모델 사용 (품질: {model_quality:.1f}, {days_old}일 전, 재훈련 오류)"
                        else:
                            return f"기존 모델 사용 (품질: {model_quality:.1f}, {days_old}일 전)"
                    
                    else:
                        return f"최신 모델 사용 (품질: {model_quality:.1f}, {days_old}일 전)"
                        
                except Exception as e:
                    return f"기존 모델 사용 (품질: {model_quality:.1f}, 날짜 확인 실패)"
                
            except Exception as e:
                print(f"⚠️ 모델 메타데이터 읽기 실패: {e}")
                return "기존 모델 사용 (메타데이터 없음)"
    
    except Exception as e:
        print(f"❌ AI 모델 상태 확인 오류: {e}")
        return "모델 상태 확인 실패"


def adjust_ai_thresholds_by_quality(strategy_data, model_quality_score):
    """AI 모델 품질에 따른 동적 임계값 조정 (백테스트 엔진 핵심 기능)"""
    try:
        print(f"🎯 AI 임계값 동적 조정 (모델 품질: {model_quality_score:.1f}/100)")
        
        # 기본 임계값 (대폭 완화)
        base_high = 0.55     # 0.65 → 0.55
        base_medium = 0.45   # 0.55 → 0.45
        base_low = 0.35      # 0.45 → 0.35
        base_hybrid = 0.50   # 0.60 → 0.50
        
        # 품질 점수에 따른 조정 계수
        if model_quality_score >= 70:  # 고품질 모델 (70점 이상)
            # 임계값을 낮춰서 더 많은 종목 선정 가능
            quality_factor = 0.95  # 5% 완화
            print("   🟢 고품질 모델: 임계값 완화 (더 적극적 선정)")
            
        elif model_quality_score >= 50:  # 중품질 모델 (50-70점)
            # 기본 임계값 유지
            quality_factor = 1.0
            print("   🟡 중품질 모델: 기본 임계값 유지")
            
        else:  # 저품질 모델 (50점 미만)
            # 임계값을 높여서 선정을 엄격하게
            quality_factor = 1.1  # 10% 강화
            print("   🔴 저품질 모델: 임계값 강화 (더 보수적 선정)")
        
        # 조정된 임계값 계산 및 적용
        strategy_data['ai_high_confidence_threshold'] = min(base_high * quality_factor, 0.9)
        strategy_data['ai_medium_confidence_threshold'] = min(base_medium * quality_factor, 0.85)
        strategy_data['ai_low_confidence_threshold'] = max(base_low * quality_factor, 0.3)
        strategy_data['hybrid_threshold'] = min(base_hybrid * quality_factor, 0.85)
        
        print(f"   📊 조정된 임계값:")
        print(f"      고신뢰: {strategy_data['ai_high_confidence_threshold']:.3f}")
        print(f"      중신뢰: {strategy_data['ai_medium_confidence_threshold']:.3f}")
        print(f"      저신뢰: {strategy_data['ai_low_confidence_threshold']:.3f}")
        print(f"      하이브리드: {strategy_data['hybrid_threshold']:.3f}")
        
        # 하이브리드 가중치도 품질에 따라 조정
        if model_quality_score >= 70:
            # 고품질 모델: AI 가중치 증가
            strategy_data['hybrid_ai_weight'] = 0.5      # 50%
            strategy_data['hybrid_technical_weight'] = 0.5  # 50%
            print(f"   ⚖️ 고품질: AI/기술 가중치 = 50%/50%")
            
        elif model_quality_score < 40:
            # 저품질 모델: 기술적 분석 가중치 증가
            strategy_data['hybrid_ai_weight'] = 0.3      # 30%
            strategy_data['hybrid_technical_weight'] = 0.7  # 70%
            print(f"   ⚖️ 저품질: AI/기술 가중치 = 30%/70%")
        
        else:
            # 중품질 모델: 기본 가중치 유지
            strategy_data['hybrid_ai_weight'] = 0.4      # 40%
            strategy_data['hybrid_technical_weight'] = 0.6  # 60%
            print(f"   ⚖️ 중품질: AI/기술 가중치 = 40%/60%")
        
    except Exception as e:
        print(f"❌ 임계값 조정 오류: {e}")


if __name__ == "__main__":
    main()
