"""
Slack notification utilities
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from ..config.settings import get_hantustock, get_slack_config


class SlackNotifier:
    """슬랙 알림 관리 클래스"""
    
    def __init__(self):
        self.ht = get_hantustock()
        self.slack_config = get_slack_config()
        self.channel_id = self.slack_config['channel_id']
    
    def send_message(self, message: str, channel_id: Optional[str] = None) -> bool:
        """
        슬랙 메시지 전송
        
        Args:
            message: 전송할 메시지
            channel_id: 채널 ID (None이면 기본 채널)
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            target_channel = channel_id or self.channel_id
            self.ht.post_message(message, target_channel)
            return True
        except Exception as e:
            print(f"❌ 슬랙 메시지 전송 실패: {e}")
            return False
    
    def notify_sell_execution(self, ticker: str, quantity: int, holding_days: int, 
                            profit_rate: Optional[float] = None, profit: Optional[float] = None,
                            confidence_level: Optional[str] = None) -> bool:
        """
        매도 체결 알림
        
        Args:
            ticker: 종목 코드
            quantity: 매도 수량
            holding_days: 보유 기간
            profit_rate: 수익률 (%)
            profit: 손익 (원)
            confidence_level: 신뢰도 등급
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"📤 **아침 매도 체결**\n"
        message += f"종목: {ticker}\n"
        message += f"수량: {quantity:,}주\n"
        message += f"보유기간: {holding_days}일"
        
        if profit_rate is not None and profit is not None:
            message += f"\n수익률: {profit_rate:+.2f}%"
            message += f"\n손익: {profit:+,}원"
        
        if confidence_level:
            message += f"\n신뢰도: {confidence_level}"
        
        return self.send_message(message)
    
    def notify_buy_execution(self, ticker: str, quantity: int, investment: float, 
                           current_price: float, ai_score: float, 
                           confidence_level: str) -> bool:
        """
        매수 체결 알림
        
        Args:
            ticker: 종목 코드
            quantity: 매수 수량
            investment: 투자 금액
            current_price: 매수 단가
            ai_score: AI 점수
            confidence_level: 신뢰도 등급
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"📥 **오후 매수 체결**\n"
        message += f"종목: {ticker}\n"
        message += f"수량: {quantity:,}주\n"
        message += f"투자금액: {investment:,}원\n"
        message += f"AI점수: {ai_score:.3f} ({confidence_level})\n"
        message += f"단가: {current_price:,}원"
        
        return self.send_message(message)
    
    def notify_morning_sell_summary(self, sold_count: int, total_profit: float, 
                                  current_holdings: int) -> bool:
        """
        아침 매도 완료 요약 알림
        
        Args:
            sold_count: 매도 종목 수
            total_profit: 총 손익
            current_holdings: 현재 보유 종목 수
            
        Returns:
            bool: 전송 성공 여부
        """
        current_time = datetime.now()
        
        message = f"🌅 **아침 매도 완료!**\n"
        message += f"📤 매도: {sold_count}개"
        if total_profit != 0:
            message += f" (손익: {total_profit:+,}원)"
        message += f"\n📊 현재 보유: {current_holdings}개"
        message += f"\n⏰ 실행 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        message += f"\n🔔 오후 3시 20분에 매수 전략 실행 예정"
        
        return self.send_message(message)
    
    def notify_evening_buy_summary(self, bought_count: int, total_invested: float, 
                                 current_holdings: int, 
                                 confidence_stats: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
        """
        오후 매수 완료 요약 알림
        
        Args:
            bought_count: 매수 종목 수
            total_invested: 총 투자 금액
            current_holdings: 현재 보유 종목 수
            confidence_stats: 신뢰도별 통계
            
        Returns:
            bool: 전송 성공 여부
        """
        current_time = datetime.now()
        
        message = f"🚀 **오후 매수 완료!**\n"
        message += f"📥 매수: {bought_count}개"
        if total_invested > 0:
            message += f" (투자: {total_invested:,}원)"
        message += f"\n📊 현재 보유: {current_holdings}개\n"

        # AI 신뢰도별 투자 현황
        if confidence_stats:
            message += "\n**신뢰도별 투자:**\n"
            for level, stats in confidence_stats.items():
                message += f"• {level}: {stats['count']}개 ({stats['amount']:,}원)\n"

        message += f"\n⏰ 실행 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        message += f"\n🔔 내일 오전 8시 30분에 매도 검토 예정"
        
        return self.send_message(message)
    
    def notify_stock_selection(self, analyzed_count: int, ai_selected_count: int, 
                             final_count: int, selected_tickers: List[str]) -> bool:
        """
        종목 선정 완료 알림
        
        Args:
            analyzed_count: 분석된 종목 수
            ai_selected_count: AI 선정 종목 수
            final_count: 최종 매수 대상 수
            selected_tickers: 선정된 종목 리스트
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"🎯 **AI 종목 선정 완료!**\n"
        message += f"📊 분석 완료: {analyzed_count}개 → AI 선정: {ai_selected_count}개\n"
        message += f"📥 매수 예정: {final_count}개\n\n"
        message += "**선정 종목:**\n"
        for i, ticker in enumerate(selected_tickers, 1):
            message += f"{i}. {ticker}\n"
        
        return self.send_message(message)
    
    def notify_error(self, error_type: str, error_message: str, details: Optional[str] = None) -> bool:
        """
        오류 알림
        
        Args:
            error_type: 오류 유형
            error_message: 오류 메시지
            details: 상세 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"❌ **{error_type}**\n"
        message += f"오류: {error_message}\n"
        if details:
            message += f"상세: {details}\n"
        message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(message)
    
    def notify_balance_check_failure(self, error_message: str) -> bool:
        """
        잔고 조회 실패 알림
        
        Args:
            error_message: 오류 메시지
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"❌ **계좌 잔고 조회 실패**\n"
        message += f"오류: {error_message}\n"
        message += f"매수 전략을 건너뛰고 매도만 실행합니다."
        
        return self.send_message(message)
    
    def notify_ai_model_retrain(self, reason: str) -> bool:
        """
        AI 모델 재훈련 알림
        
        Args:
            reason: 재훈련 사유
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"🤖 **AI 모델 재훈련 시작**\n"
        message += f"사유: {reason}\n"
        message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"완료까지 시간이 소요될 수 있습니다."
        
        return self.send_message(message)
    
    def notify_ai_model_quality(self, quality_score: float, action: str) -> bool:
        """
        AI 모델 품질 알림
        
        Args:
            quality_score: 모델 품질 점수
            action: 취한 조치
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"🤖 **AI 모델 품질 체크**\n"
        message += f"품질 점수: {quality_score:.1f}/100\n"
        message += f"조치: {action}"
        
        return self.send_message(message)
    
    def notify_strategy_status(self, status: str, details: Dict[str, Any]) -> bool:
        """
        전략 상태 알림
        
        Args:
            status: 전략 상태
            details: 상세 정보
            
        Returns:
            bool: 전송 성공 여부
        """
        message = f"📊 **전략 상태: {status}**\n"
        for key, value in details.items():
            message += f"{key}: {value}\n"
        message += f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(message)


# 전역 슬랙 알리미 (싱글톤 패턴)
_notifier_instance = None

def get_notifier() -> SlackNotifier:
    """슬랙 알리미 인스턴스 반환 (싱글톤)"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = SlackNotifier()
    return _notifier_instance

# 편의 함수들
def send_message(message: str, channel_id: Optional[str] = None) -> bool:
    """슬랙 메시지 전송"""
    notifier = get_notifier()
    return notifier.send_message(message, channel_id)

def notify_sell_execution(ticker: str, quantity: int, holding_days: int, 
                        profit_rate: Optional[float] = None, profit: Optional[float] = None,
                        confidence_level: Optional[str] = None) -> bool:
    """매도 체결 알림"""
    notifier = get_notifier()
    return notifier.notify_sell_execution(ticker, quantity, holding_days, profit_rate, profit, confidence_level)

def notify_buy_execution(ticker: str, quantity: int, investment: float, 
                       current_price: float, ai_score: float, 
                       confidence_level: str) -> bool:
    """매수 체결 알림"""
    notifier = get_notifier()
    return notifier.notify_buy_execution(ticker, quantity, investment, current_price, ai_score, confidence_level)

def notify_morning_sell_summary(sold_count: int, total_profit: float, current_holdings: int) -> bool:
    """아침 매도 완료 요약"""
    notifier = get_notifier()
    return notifier.notify_morning_sell_summary(sold_count, total_profit, current_holdings)

def notify_evening_buy_summary(bought_count: int, total_invested: float, 
                             current_holdings: int, 
                             confidence_stats: Optional[Dict[str, Dict[str, Any]]] = None) -> bool:
    """오후 매수 완료 요약"""
    notifier = get_notifier()
    return notifier.notify_evening_buy_summary(bought_count, total_invested, current_holdings, confidence_stats)

def notify_stock_selection(analyzed_count: int, ai_selected_count: int, 
                         final_count: int, selected_tickers: List[str]) -> bool:
    """종목 선정 완료 알림"""
    notifier = get_notifier()
    return notifier.notify_stock_selection(analyzed_count, ai_selected_count, final_count, selected_tickers)

def notify_error(error_type: str, error_message: str, details: Optional[str] = None) -> bool:
    """오류 알림"""
    notifier = get_notifier()
    return notifier.notify_error(error_type, error_message, details)
