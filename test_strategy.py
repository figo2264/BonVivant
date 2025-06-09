#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
슬랙 알림 테스트 스크립트
HantuStock 클래스의 슬랙 기능이 정상 작동하는지 확인
"""

import yaml
from datetime import datetime
from HantuStock import HantuStock

# 슬랙 설정
SLACK_API_TOKEN = "SLACK_TOKEN_REMOVED"
HANLYANG_CHANNEL_ID = "C090JHC30CU"

def load_config():
    """설정 로드"""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return config
    except Exception as e:
        print(f"❌ config.yaml 로드 실패: {e}")
        return None

def test_slack_connection():
    """슬랙 연결 테스트"""
    print("🔧 슬랙 연결 테스트 시작...")
    
    try:
        config = load_config()
        if not config:
            return False
        
        # HantuStock 인스턴스 생성
        ht = HantuStock(
            api_key=config['hantu']['api_key'],
            secret_key=config['hantu']['secret_key'], 
            account_id=config['hantu']['account_id']
        )
        
        # 슬랙 활성화
        ht.activate_slack(SLACK_API_TOKEN)
        print("✅ 슬랙 클라이언트 초기화 완료")
        
        return ht
        
    except Exception as e:
        print(f"❌ 슬랙 연결 실패: {e}")
        return None

def test_basic_message(ht):
    """기본 메시지 테스트"""
    print("\n📝 기본 메시지 테스트...")
    
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"🧪 **슬랙 테스트 메시지**\n⏰ 시간: {current_time}\n✅ 연결 테스트 성공!"
        
        response = ht.post_message(message, HANLYANG_CHANNEL_ID)
        
        if response:
            print("✅ 기본 메시지 전송 성공")
            return True
        else:
            print("❌ 기본 메시지 전송 실패")
            return False
            
    except Exception as e:
        print(f"❌ 기본 메시지 테스트 오류: {e}")
        return False

def test_trading_notification(ht):
    """거래 알림 형식 테스트"""
    print("\n📈 거래 알림 형식 테스트...")
    
    try:
        # 매수 알림 테스트
        buy_message = f"📥 **매수 체결 (테스트)**\n종목: 005930 (삼성전자)\n수량: 10주\n선정 방식: AI 추천\n⚠️ 이것은 테스트 메시지입니다"
        
        response1 = ht.post_message(buy_message, HANLYANG_CHANNEL_ID)
        
        if response1:
            print("✅ 매수 알림 형식 테스트 성공")
        else:
            print("❌ 매수 알림 형식 테스트 실패")
            
        # 잠시 대기
        import time
        time.sleep(2)
        
        # 매도 알림 테스트  
        sell_message = f"📤 **매도 체결 (테스트)**\n종목: 000660 (SK하이닉스)\n수량: 15주\n보유기간: 3일\n⚠️ 이것은 테스트 메시지입니다"
        
        response2 = ht.post_message(sell_message, HANLYANG_CHANNEL_ID)
        
        if response2:
            print("✅ 매도 알림 형식 테스트 성공")
            return True
        else:
            print("❌ 매도 알림 형식 테스트 실패")
            return False
            
    except Exception as e:
        print(f"❌ 거래 알림 테스트 오류: {e}")
        return False

def test_selection_notification(ht):
    """종목 선정 알림 테스트"""
    print("\n🎯 종목 선정 알림 테스트...")
    
    try:
        selection_message = f"🎯 **AI 종목 선정 완료! (테스트)**\n"
        selection_message += f"📊 분석 완료: 15개 → AI 선정: 5개\n"
        selection_message += f"📥 매수 예정: 3개\n\n"
        selection_message += f"**선정 종목:**\n"
        selection_message += f"1. 005930 (삼성전자)\n"
        selection_message += f"2. 000660 (SK하이닉스)\n" 
        selection_message += f"3. 035420 (NAVER)\n\n"
        selection_message += f"⚠️ 이것은 테스트 메시지입니다"
        
        response = ht.post_message(selection_message, HANLYANG_CHANNEL_ID)
        
        if response:
            print("✅ 종목 선정 알림 테스트 성공")
            return True
        else:
            print("❌ 종목 선정 알림 테스트 실패")
            return False
            
    except Exception as e:
        print(f"❌ 종목 선정 알림 테스트 오류: {e}")
        return False

def test_summary_notification(ht):
    """전략 실행 완료 요약 테스트"""
    print("\n🏁 전략 완료 요약 테스트...")
    
    try:
        summary_message = f"🏁 **전략 실행 완료! (테스트)**\n"
        summary_message += f"📤 매도: 2개\n"
        summary_message += f"📥 매수: 3개\n"
        summary_message += f"📊 현재 보유: 8개\n"
        summary_message += f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary_message += f"⚠️ 이것은 테스트 메시지입니다"
        
        response = ht.post_message(summary_message, HANLYANG_CHANNEL_ID)
        
        if response:
            print("✅ 전략 완료 요약 테스트 성공")
            return True
        else:
            print("❌ 전략 완료 요약 테스트 실패")
            return False
            
    except Exception as e:
        print(f"❌ 전략 완료 요약 테스트 오류: {e}")
        return False

def test_weekly_report_notification(ht):
    """주간 리포트 알림 테스트"""
    print("\n📊 주간 리포트 알림 테스트...")
    
    try:
        report_message = f"📊 **AI 전략 주간 리포트 (테스트)**\n"
        report_message += f"🕐 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        report_message += f"🤖 AI 예측 기록: 45개\n"
        report_message += f"💼 현재 보유 종목: 8개\n"
        report_message += f"💰 포트폴리오 추정가치: 2,450,000원\n"
        report_message += f"📊 신호 분포: 매수 3개, 매도 1개\n"
        report_message += f"📈 거래 로그: 23개\n"
        report_message += f"💾 상세 리포트: weekly_ai_report.json\n"
        report_message += f"⚠️ 이것은 테스트 메시지입니다"
        
        response = ht.post_message(report_message, HANLYANG_CHANNEL_ID)
        
        if response:
            print("✅ 주간 리포트 알림 테스트 성공")
            return True
        else:
            print("❌ 주간 리포트 알림 테스트 실패")
            return False
            
    except Exception as e:
        print(f"❌ 주간 리포트 알림 테스트 오류: {e}")
        return False

def test_error_notification(ht):
    """오류 알림 테스트"""
    print("\n⚠️ 오류 알림 테스트...")
    
    try:
        error_message = f"⚠️ **시스템 오류 발생 (테스트)**\n"
        error_message += f"🕐 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        error_message += f"❌ 오류: 테스트용 가상 오류입니다\n"
        error_message += f"🔧 확인이 필요합니다\n"
        error_message += f"⚠️ 이것은 테스트 메시지입니다"
        
        response = ht.post_message(error_message, HANLYANG_CHANNEL_ID)
        
        if response:
            print("✅ 오류 알림 테스트 성공")
            return True
        else:
            print("❌ 오류 알림 테스트 실패")
            return False
            
    except Exception as e:
        print(f"❌ 오류 알림 테스트 오류: {e}")
        return False

def run_all_tests():
    """모든 슬랙 테스트 실행"""
    print("🧪 슬랙 알림 종합 테스트 시작")
    print("=" * 50)
    
    # 슬랙 연결 테스트
    ht = test_slack_connection()
    if not ht:
        print("❌ 슬랙 연결 실패로 테스트 중단")
        return False
    
    # 테스트 실행
    test_results = []
    
    # 각 테스트 실행 (간격을 두고)
    import time
    
    test_results.append(test_basic_message(ht))
    time.sleep(3)
    
    test_results.append(test_selection_notification(ht))
    time.sleep(3)
    
    test_results.append(test_trading_notification(ht))
    time.sleep(3)
    
    test_results.append(test_summary_notification(ht))
    time.sleep(3)
    
    test_results.append(test_weekly_report_notification(ht))
    time.sleep(3)
    
    test_results.append(test_error_notification(ht))
    
    # 최종 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f"✅ 성공: {passed_tests}개")
    print(f"❌ 실패: {total_tests - passed_tests}개")
    print(f"📊 성공률: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 모든 슬랙 알림 테스트 성공!")
        
        # 최종 완료 알림
        final_message = f"🎉 **슬랙 테스트 완료!**\n"
        final_message += f"✅ 모든 알림 형식 테스트 성공\n"
        final_message += f"📱 실제 거래시 정상 알림 예상\n"
        final_message += f"⏰ 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            ht.post_message(final_message, HANLYANG_CHANNEL_ID)
            print("✅ 최종 완료 알림 전송")
        except:
            print("⚠️ 최종 완료 알림 전송 실패")
            
        return True
    else:
        print("⚠️ 일부 테스트 실패 - 설정을 확인하세요")
        return False

if __name__ == "__main__":
    print("🚀 슬랙 알림 테스트 스크립트 실행")
    print(f"📱 채널: {HANLYANG_CHANNEL_ID}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        success = run_all_tests()
        
        if success:
            print("\n🎯 슬랙 테스트 완료: 실제 거래 알림 준비 완료!")
        else:
            print("\n🔧 슬랙 테스트 실패: 설정을 점검하세요")
            
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 테스트 중단")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
