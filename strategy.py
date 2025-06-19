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
    """메인 실행 함수 - 하이브리드 전략 (기술적 분석 + 뉴스 감정 분석)"""
    print("🚀 한량 주식 하이브리드 전략 시작! (기술적 분석 + 뉴스 감정 분석)")
    
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
        
        # 6. 하이브리드 전략 설정 (기술적 분석 + 뉴스 감정 분석)
        if 'hybrid_strategy_enabled' not in strategy_data:
            strategy_data['hybrid_strategy_enabled'] = True
            strategy_data['news_weight'] = 0.5  # 뉴스 가중치 50% (5:5 비율로 변경)
            strategy_data['technical_weight'] = 0.5  # 기술적 가중치 50% (5:5 비율로 변경)
            strategy_data['min_combined_score'] = 0.7  # 최소 종합 점수 (백테스트 엔진과 동일)
            strategy_data['block_negative_news'] = True  # 뉴스 감정이 부정적일 때 매수 차단
            print("✅ 하이브리드 전략 활성화 (기술적 50% + 뉴스 50%)")
            print(f"   📊 기술적 가중치: {strategy_data['technical_weight']*100:.0f}%")
            print(f"   📰 뉴스 가중치: {strategy_data['news_weight']*100:.0f}%")
            print(f"   🎯 최소 종합 점수: {strategy_data['min_combined_score']*100:.0f}%")
            print(f"   🚫 부정적 뉴스 차단: {'활성화' if strategy_data['block_negative_news'] else '비활성화'}")
        
        # 7. 기본 품질 필터 설정 (1단계 다층적 필터링)
        if 'quality_filter_enabled' not in strategy_data:
            strategy_data['quality_filter_enabled'] = True
            strategy_data['min_market_cap'] = 100_000_000_000  # 최소 시가총액 1000억 (백테스트와 동일)
            strategy_data['enhanced_min_trade_amount'] = 30_000_000  # 최소 거래대금 0.3억 (백테스트와 동일)
            print("✅ 기본 품질 필터 활성화 (1단계 다층적 필터링)")
            print(f"   💎 최소 시가총액: {strategy_data['min_market_cap']/1_000_000_000:.0f}억원")
            print(f"   💰 최소 거래대금: {strategy_data['enhanced_min_trade_amount']/100_000_000:.1f}억원")
            print(f"   🚫 거래정지/관리종목 자동 제외")
            print(f"   📊 예상 종목 풀: 약 500-700개 (백테스트와 동일한 선택 폭)")
        
        # 8. 최대 선정 종목 수 설정
        if 'max_selections' not in strategy_data:
            strategy_data['max_selections'] = 3  # 최대 3개 종목 선정
            print("✅ 최대 선정 종목 수: 3개")
        
        # 9. 기술적 분석 최적화 파라미터 (최적화 결과 반영)
        if 'technical_params' not in strategy_data:
            strategy_data['technical_params'] = {
                'min_close_days': 7,          # 최저점 확인 기간 (최적화: 7일)
                'ma_period': 20,              # 이동평균 기간 (유지: 20일)
                'min_technical_score': 0.7    # 최소 기술점수 (최적화: 0.7로 상향)
            }
            print("✅ 기술적 분석 최적화 파라미터 설정")
            print(f"   📊 최저점 확인 기간: {strategy_data['technical_params']['min_close_days']}일")
            print(f"   📈 이동평균 기간: {strategy_data['technical_params']['ma_period']}일")
            print(f"   🎯 최소 기술점수: {strategy_data['technical_params']['min_technical_score']}")
        
        # 10. 뉴스 디버깅 모드 설정
        if 'debug_news' not in strategy_data:
            strategy_data['debug_news'] = True  # 뉴스 분석 디버깅 모드 활성화
            print("🔍 뉴스 분석 디버깅 모드: 활성화")
        
        # 11. 피라미딩 전략 설정 (백테스트 엔진과 동일하게)
        if 'pyramiding_enabled' not in strategy_data:
            strategy_data['pyramiding_enabled'] = True  # 피라미딩 활성화
            strategy_data['pyramiding_min_score'] = 0.75  # 피라미딩 최소 점수 (75%)
            strategy_data['pyramiding_max_position'] = 0.3  # 종목당 최대 포지션 (30%)
            strategy_data['pyramiding_investment_ratio'] = 0.5  # 추가 매수 비율 (50%)
            strategy_data['pyramiding_reset_threshold'] = 0.80  # 보유기간 리셋 기준 (80%)
            strategy_data['pyramiding_max_resets'] = 2  # 최대 리셋 횟수
            print("🔄 피라미딩 전략 활성화")
            print(f"   📊 최소 점수: {strategy_data['pyramiding_min_score']*100:.0f}%")
            print(f"   💰 최대 포지션: {strategy_data['pyramiding_max_position']*100:.0f}%")
            print(f"   📈 추가 매수 비율: {strategy_data['pyramiding_investment_ratio']*100:.0f}%")
            print(f"   🔄 보유기간 리셋: {strategy_data['pyramiding_reset_threshold']*100:.0f}% 이상")
            print(f"   🔢 최대 리셋 횟수: {strategy_data['pyramiding_max_resets']}회")
            print(f"   📌 리셋 시 보유기간이 1일로 초기화됩니다")
        
        # 12. 전략별 최대 보유기간 설정
        if 'max_holding_days' not in strategy_data:
            strategy_data['max_holding_days'] = {
                'basic': 5,      # 기본 전략: 5일
                'hybrid': 10     # 하이브리드 전략: 10일
            }
            print("📅 전략별 최대 보유기간 설정")
            print(f"   📊 기본 전략: {strategy_data['max_holding_days']['basic']}일")
            print(f"   🤝 하이브리드 전략: {strategy_data['max_holding_days']['hybrid']}일")
        
        # 설정 저장
        data_manager.save()
        
        print("✅ 모든 모듈 초기화 완료 (하이브리드 전략 적용)")
        print(f"   📊 데이터 검증 강화: {'활성화' if strategy_data.get('enhanced_data_validation') else '비활성화'}")
        print(f"   🛑 손실 제한: {'활성화' if strategy_data.get('stop_loss_enabled') else '비활성화'} ({strategy_data.get('stop_loss_rate', -0.05)*100:.1f}%)")
        print(f"   🔬 강화된 기술 분석: {'활성화' if strategy_data.get('enhanced_analysis_enabled') else '비활성화'}")
        print(f"   🎯 안정성 타겟: {'활성화' if strategy_data.get('stability_focused_target') else '비활성화'}")
        print(f"   🔍 고급 홀드 시그널: {'활성화' if strategy_data.get('advanced_hold_signal') else '비활성화'}")
        print(f"   🤝 하이브리드 전략: {'활성화' if strategy_data.get('hybrid_strategy_enabled') else '비활성화'}")
        if strategy_data.get('hybrid_strategy_enabled'):
            print(f"      - 기술적 분석: {strategy_data.get('technical_weight', 0.5)*100:.0f}%")
            print(f"      - 뉴스 감정: {strategy_data.get('news_weight', 0.5)*100:.0f}%")
            print(f"      - 부정적 뉴스 차단: {'활성화' if strategy_data.get('block_negative_news', True) else '비활성화'}")
        print(f"   💎 품질 필터: {'활성화' if strategy_data.get('quality_filter_enabled') else '비활성화'}")
        if strategy_data.get('quality_filter_enabled'):
            print(f"      - 최소 시가총액: {strategy_data.get('min_market_cap', 100_000_000_000)/1_000_000_000:.0f}억원")
            print(f"      - 최소 거래대금: {strategy_data.get('enhanced_min_trade_amount', 30_000_000)/100_000_000:.1f}억원")
        print(f"   📈 최대 선정 종목: {strategy_data.get('max_selections', 3)}개")
        print(f"   🔄 피라미딩 전략: {'활성화' if strategy_data.get('pyramiding_enabled') else '비활성화'}")
        if strategy_data.get('pyramiding_enabled'):
            print(f"      - 최소 점수: {strategy_data.get('pyramiding_min_score', 0.75)*100:.0f}%")
            print(f"      - 최대 포지션: {strategy_data.get('pyramiding_max_position', 0.3)*100:.0f}%")
            print(f"      - 최대 리셋: {strategy_data.get('pyramiding_max_resets', 2)}회")
        print(f"   📅 최대 보유기간: 기본 {strategy_data.get('max_holding_days', {}).get('basic', 5)}일, "
              f"하이브리드 {strategy_data.get('max_holding_days', {}).get('hybrid', 10)}일")
        print(f"   🔍 뉴스 디버깅 모드: {'활성화' if strategy_data.get('debug_news') else '비활성화'}")
        
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

                sell_executor = SellExecutor(stop_loss_rate=strategy_data.get('stop_loss_rate', -0.05))
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
                print("🚀 오후 매수 전략 실행 시작! (하이브리드: 기술적 분석 + 뉴스 감정 분석)")
                
                # 🔧 강화된 매수 전략 실행 (백테스트 엔진 기술적 분석 기능 적용)
                strategy_data = data_manager.get_data()
                
                # 매수 전략 설정 (하이브리드 전략에 필요한 파라미터만 전달)
                buy_config = {
                    'hybrid_strategy_enabled': strategy_data.get('hybrid_strategy_enabled', True),
                    'news_weight': strategy_data.get('news_weight', 0.5),
                    'technical_weight': strategy_data.get('technical_weight', 0.5),
                    'min_combined_score': strategy_data.get('min_combined_score', 0.7),
                    'debug_news': strategy_data.get('debug_news', True)
                }

                buy_executor = BuyExecutor(**buy_config)
                buy_results = buy_executor.execute()
                
                print(f"✅ 매수 전략 완료: {buy_results.get('bought_count', 0)}개 종목 매수")
                print(f"   💳 총 투자: {buy_results.get('total_investment', 0):,}원")
                if strategy_data.get('hybrid_strategy_enabled'):
                    print(f"   📊 하이브리드 전략 기반 선정 (기술적 + 뉴스)")
                else:
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
