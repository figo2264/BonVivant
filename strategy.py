# 기술적 분석 강화된 6-7 전략 (모듈화 버전)
# Cron 실행 대상 파일
# 백테스트 엔진의 기술적 분석 기능 완전 적용

import time
from datetime import datetime

# 모듈화된 컴포넌트들 import
from hanlyang_stock.config.settings import get_config
from hanlyang_stock.strategy.executor import SellExecutor, BuyExecutor
from hanlyang_stock.utils.storage import get_data_manager
from hanlyang_stock.utils.notification import get_notifier


def main():
    """메인 실행 함수 - 백테스트 엔진의 기술적 분석 강화 기능 적용"""
    print("🚀 한량 주식 전략 시작! (기술적 분석 + 데이터 검증 + 손실 제한 완전 적용)")
    
    try:
        # 설정 초기화
        config = get_config()
        data_manager = get_data_manager()
        notifier = get_notifier()
        
        # 🔧 강화된 설정 확인 및 활성화 (백테스트 엔진 기술적 분석 기능)
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
        
        # 3. 강화된 기술적 분석 활성화 (백테스트 엔진)
        if 'enhanced_analysis_enabled' not in strategy_data:
            strategy_data['enhanced_analysis_enabled'] = True
            print("✅ 강화된 기술적 분석 활성화")
        
        # 4. 고급 홀드 시그널 (백테스트 엔진 기능)
        if 'advanced_hold_signal' not in strategy_data:
            strategy_data['advanced_hold_signal'] = True
            strategy_data['rsi_hold_upper'] = 70         # RSI 상한
            strategy_data['rsi_hold_lower'] = 30         # RSI 하한  
            strategy_data['volume_surge_threshold'] = 2.0  # 거래량 급증 기준
            print("✅ 고급 홀드 시그널 활성화")
            print(f"   📊 RSI 홀드 범위: {strategy_data['rsi_hold_lower']}-{strategy_data['rsi_hold_upper']}")
            print(f"   📈 거래량 급증 기준: {strategy_data['volume_surge_threshold']}배")
        
        # 5. 안정성 중심 타겟 설정
        if 'stability_focused_target' not in strategy_data:
            strategy_data['stability_focused_target'] = True
            strategy_data['profit_threshold'] = 0.005    # 0.5% 이상 수익
            strategy_data['volatility_control'] = True   # 변동성 제어
            strategy_data['crash_protection'] = True     # 급락 방지
            print("✅ 안정성 중심 타겟 설정 활성화")
            print(f"   📈 수익 기준: {strategy_data['profit_threshold']*100:.1f}%")
            print(f"   📊 변동성 제어: {'활성화' if strategy_data['volatility_control'] else '비활성화'}")
            print(f"   🛡️ 급락 방지: {'활성화' if strategy_data['crash_protection'] else '비활성화'}")
        
        # 설정 저장
        data_manager.save()
        
        print("✅ 모든 모듈 초기화 완료 (백테스트 엔진 기술적 분석 기능 완전 적용)")
        print(f"   📊 데이터 검증 강화: {'활성화' if strategy_data.get('enhanced_data_validation') else '비활성화'}")
        print(f"   🛑 손실 제한: {'활성화' if strategy_data.get('stop_loss_enabled') else '비활성화'} ({strategy_data.get('stop_loss_rate', -0.05)*100:.1f}%)")
        print(f"   🔬 강화된 기술 분석: {'활성화' if strategy_data.get('enhanced_analysis_enabled') else '비활성화'}")
        print(f"   🎯 안정성 타겟: {'활성화' if strategy_data.get('stability_focused_target') else '비활성화'}")
        print(f"   🔍 고급 홀드 시그널: {'활성화' if strategy_data.get('advanced_hold_signal') else '비활성화'}")
        
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
                
                # 🔧 강화된 매도 전략 실행 (백테스트 엔진 기술적 분석 기능 적용)
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
                print("🚀 오후 매수 전략 실행 시작! (강화된 기술적 분석 + 데이터 검증 완전 적용)")
                
                # 🔧 강화된 매수 전략 실행 (백테스트 엔진 기술적 분석 기능 적용)
                strategy_data = data_manager.get_data()
                
                # 매수 전략 설정 (기술적 분석 기능만 활성화)
                buy_config = {
                    'enhanced_data_validation': strategy_data.get('enhanced_data_validation', True),
                    'enhanced_analysis_enabled': strategy_data.get('enhanced_analysis_enabled', True),
                    'stability_focused_target': strategy_data.get('stability_focused_target', True),
                    'profit_threshold': strategy_data.get('profit_threshold', 0.005),
                    'volatility_control': strategy_data.get('volatility_control', True),
                    'crash_protection': strategy_data.get('crash_protection', True)
                }
                
                buy_executor = BuyExecutor(**buy_config)
                buy_results = buy_executor.execute()
                
                print(f"✅ 매수 전략 완료: {buy_results.get('bought_count', 0)}개 종목 매수")
                print(f"   💳 총 투자: {buy_results.get('total_investment', 0):,}원")
                print(f"   📊 기술적 분석 기반 선정")
                
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


if __name__ == "__main__":
    main()
