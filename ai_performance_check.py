#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 강화 전략 성능 모니터링 스크립트
주간 실행으로 AI 예측 정확도와 전략 성과 분석
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import yaml
from HantuStock import HantuStock

def load_config():
    """설정 로드"""
    with open('config.yaml', 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config

def analyze_ai_performance():
    """AI 예측 성능 분석"""
    try:
        with open('ai_strategy_data.json', 'r') as f:
            strategy_data = json.load(f)
    except:
        print("❌ AI 전략 데이터 파일이 없습니다.")
        return None
    
    config = load_config()
    ht = HantuStock(
        api_key=config['hantu']['api_key'],
        secret_key=config['hantu']['secret_key'],
        account_id=config['hantu']['account_id']
    )
    
    print("📊 AI 전략 성능 분석 시작...")
    print("=" * 60)
    
    # 1. 전체 통계
    ai_predictions = strategy_data.get('ai_predictions', {})
    performance_log = strategy_data.get('performance_log', [])
    holding_period = strategy_data.get('holding_period', {})
    
    print(f"📈 전체 통계:")
    print(f"  AI 예측 기록: {len(ai_predictions)}개")
    print(f"  거래 로그: {len(performance_log)}개")
    print(f"  현재 보유 종목: {len([k for k, v in holding_period.items() if v > 0])}개")
    
    # 2. 최근 일주일 활동 분석
    week_ago = datetime.now() - timedelta(days=7)
    recent_logs = [
        log for log in performance_log 
        if datetime.fromisoformat(log['timestamp']) > week_ago
    ]
    
    if recent_logs:
        print(f"\n📅 최근 7일 활동:")
        total_bought = sum(log['bought_count'] for log in recent_logs)
        total_sold = sum(log['sold_count'] for log in recent_logs)
        print(f"  총 매수: {total_bought}건")
        print(f"  총 매도: {total_sold}건")
        print(f"  거래 일수: {len(recent_logs)}일")
    
    # 3. AI 예측 점수 분포 분석
    if ai_predictions:
        scores = [pred.get('score', 0) for pred in ai_predictions.values()]
        avg_score = sum(scores) / len(scores)
        high_confidence = len([s for s in scores if s >= 0.7])
        low_confidence = len([s for s in scores if s <= 0.3])
        
        print(f"\n🤖 AI 예측 분석:")
        print(f"  평균 AI 점수: {avg_score:.3f}")
        print(f"  고신뢰도 예측 (≥0.7): {high_confidence}개 ({high_confidence/len(scores)*100:.1f}%)")
        print(f"  저신뢰도 예측 (≤0.3): {low_confidence}개 ({low_confidence/len(scores)*100:.1f}%)")
    
    # 4. 현재 포트폴리오 AI 재분석
    current_holdings = ht.get_holding_stock()
    if current_holdings:
        print(f"\n💼 현재 포트폴리오 AI 재분석:")
        
        total_value_estimate = 0
        buy_signals = 0
        sell_signals = 0
        
        for ticker, quantity in current_holdings.items():
            if ticker.startswith('J'):  # 신주인수권 제외
                continue
            
            try:
                # 현재 AI 분석
                analysis = ht.get_ai_enhanced_analysis(ticker)
                signal = analysis['market_signal']['signal']
                score = analysis['final_score']
                risk = analysis['risk_assessment']['risk_level']
                
                # 현재가 추정 (최근 데이터 기준)
                recent_data = ht.get_past_data(ticker, n=1)
                if recent_data is not None and len(recent_data) > 0:
                    current_price = recent_data.iloc[-1]['close']
                    position_value = current_price * quantity
                    total_value_estimate += position_value
                    
                    print(f"  {ticker}: {signal:12} | 점수: {score:+.3f} | 리스크: {risk:10} | 평가: {position_value:>8,.0f}원")
                    
                    if signal in ['BUY', 'STRONG_BUY']:
                        buy_signals += 1
                    elif signal in ['SELL', 'STRONG_SELL']:
                        sell_signals += 1
                
            except Exception as e:
                print(f"  {ticker}: 분석 실패 - {e}")
        
        print(f"\n  💰 포트폴리오 추정가치: {total_value_estimate:,.0f}원")
        print(f"  📊 신호 분포: 매수신호 {buy_signals}개, 매도신호 {sell_signals}개")
    
    # 5. 리스크 경고
    print(f"\n⚠️ 리스크 체크:")
    
    # 과도한 집중 체크
    if current_holdings and len(current_holdings) < 3:
        print("  🔸 포트폴리오 집중도 높음 - 분산투자 권장")
    
    # 오래된 보유 종목 체크
    long_holdings = [k for k, v in holding_period.items() if v >= 5]
    if long_holdings:
        print(f"  🔸 장기보유 종목 {len(long_holdings)}개 - 재검토 필요")
        for ticker in long_holdings[:3]:  # 최대 3개만 표시
            print(f"    - {ticker}: {holding_period[ticker]}일")
    
    # AI 신뢰도 저하 체크
    if ai_predictions:
        recent_predictions = [
            pred for pred in ai_predictions.values()
            if datetime.fromisoformat(pred['timestamp']) > week_ago
        ]
        if recent_predictions:
            recent_avg_score = sum(pred['score'] for pred in recent_predictions) / len(recent_predictions)
            if recent_avg_score < 0.5:
                print(f"  🔸 최근 AI 신뢰도 저하 ({recent_avg_score:.3f}) - 전략 재검토 필요")
    
    # 6. 권장사항
    print(f"\n💡 권장사항:")
    if not current_holdings:
        print("  🔹 현재 보유 종목이 없습니다. 시장 상황을 확인하고 매수 기회를 모색하세요.")
    elif len(current_holdings) > 15:
        print("  🔹 포트폴리오가 과도하게 분산되어 있습니다. 집중도를 높이는 것을 고려하세요.")
    
    if performance_log and len(performance_log) > 10:
        recent_activity = len([log for log in performance_log[-10:] if log.get('bought_count', 0) > 0])
        if recent_activity < 3:
            print("  🔹 최근 거래 활동이 적습니다. 시장 기회를 놓치고 있을 수 있습니다.")
    
    print("  🔹 정기적으로 AI 예측 정확도를 모니터링하고 전략을 조정하세요.")
    print("  🔹 시장 변동성이 높을 때는 리스크 관리를 강화하세요.")
    
    return strategy_data

def generate_weekly_report():
    """주간 리포트 생성"""
    analysis_result = analyze_ai_performance()
    
    if analysis_result:
        # 리포트 요약을 파일로 저장
        report = {
            'generated_at': datetime.now().isoformat(),
            'analysis_summary': '주간 AI 전략 성능 분석 완료',
            'total_predictions': len(analysis_result.get('ai_predictions', {})),
            'current_holdings': len([k for k, v in analysis_result.get('holding_period', {}).items() if v > 0])
        }
        
        try:
            with open('weekly_ai_report.json', 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n💾 주간 리포트 저장 완료: weekly_ai_report.json")
        except Exception as e:
            print(f"❌ 리포트 저장 실패: {e}")

def slack_notification(ht, message):
    """슬랙 알림 전송 (설정되어 있을 경우)"""
    try:
        # 슬랙 설정이 있다면 알림 전송
        ht.post_message(message)
        print("📱 슬랙 알림 전송 완료")
    except:
        print("📱 슬랙 알림 설정 없음")

if __name__ == "__main__":
    print("🤖 AI 전략 주간 성능 체크 시작")
    print(f"🕐 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 성능 분석 실행
        generate_weekly_report()
        
        # 슬랙 알림 (옵션)
        try:
            config = load_config()
            ht = HantuStock(
                api_key=config['hantu']['api_key'],
                secret_key=config['hantu']['secret_key'],
                account_id=config['hantu']['account_id']
            )
            
            message = f"📊 AI 전략 주간 리포트\n실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n상세 내용은 서버 로그를 확인하세요."
            slack_notification(ht, message)
            
        except Exception as e:
            print(f"슬랙 알림 실패: {e}")
        
        print("\n✅ 주간 성능 체크 완료")
        
    except Exception as e:
        print(f"❌ 주간 성능 체크 실패: {e}")
        
        # 오류 발생시 슬랙 알림
        try:
            config = load_config()
            ht = HantuStock(
                api_key=config['hantu']['api_key'],
                secret_key=config['hantu']['secret_key'],
                account_id=config['hantu']['account_id']
            )
            
            error_message = f"⚠️ AI 전략 주간 체크 오류\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n오류: {str(e)}"
            slack_notification(ht, error_message)
            
        except:
            pass
