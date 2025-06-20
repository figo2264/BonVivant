# 기술적 분석 강화된 6-7 전략 (모듈화 버전)
# Cron 실행 대상 파일
# 백테스트 엔진의 기술적 분석 기능 완전 적용
# 설정값은 hanlyang_stock/config/strategy_settings.py에서 관리

import time
from datetime import datetime
import os

# 모듈화된 컴포넌트들 import
from hanlyang_stock.config.settings import get_config
from hanlyang_stock.strategy.executor import SellExecutor, BuyExecutor
from hanlyang_stock.utils.storage import get_data_manager
from hanlyang_stock.utils.notification import get_notifier


def main():
    """메인 실행 함수 - 하이브리드 전략 (기술적 분석 + 뉴스 감정 분석)"""
    print("🚀 한량 주식 하이브리드 전략 시작! (기술적 분석 + 뉴스 감정 분석)")
    print("📋 설정값 관리: hanlyang_stock/config/strategy_settings.py")
    
    # 환경변수로 프리셋 선택 가능 (기본값: balanced)
    preset = os.environ.get('STRATEGY_PRESET', 'balanced')
    
    try:
        # 설정 초기화 (strategy_settings.py 사용)
        config = get_config()
        data_manager = get_data_manager(use_config_file=True, preset=preset)
        notifier = get_notifier()
        
        # 설정값 가져오기
        strategy_data = data_manager.get_data()
        
        print(f"✅ 모든 모듈 초기화 완료 (프리셋: {preset})")
        print("📊 주요 설정값:")
        print(f"   🎯 최대 선정 종목: {strategy_data.get('max_selections')}개")
        print(f"   🛑 손실 제한: {strategy_data.get('stop_loss_rate')*100:.1f}%")
        print(f"   🤝 하이브리드 전략: {'활성화' if strategy_data.get('hybrid_strategy_enabled') else '비활성화'}")
        if strategy_data.get('hybrid_strategy_enabled'):
            print(f"      - 기술적 분석: {strategy_data.get('technical_weight')*100:.0f}%")
            print(f"      - 뉴스 감정: {strategy_data.get('news_weight')*100:.0f}%")
        print(f"   💎 품질 필터:")
        print(f"      - 최소 시가총액: {strategy_data.get('min_market_cap')/1_000_000_000:.0f}억원")
        print(f"      - 최소 거래대금: {strategy_data.get('enhanced_min_trade_amount')/100_000_000:.0f}억원")
        print(f"   🔄 피라미딩: {'활성화' if strategy_data.get('pyramiding_enabled') else '비활성화'}")
        print(f"   📅 최대 보유기간: 기본 {strategy_data.get('max_holding_days', {}).get('basic', 5)}일, "
              f"하이브리드 {strategy_data.get('max_holding_days', {}).get('hybrid', 10)}일")
        
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
                print("🌅 아침 매도 전략 실행 시작!")
                
                # 최신 설정 다시 로드 (설정 파일 기반)
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
                print("🚀 오후 매수 전략 실행 시작!")
                
                # 최신 설정 다시 로드 (설정 파일 기반)
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
