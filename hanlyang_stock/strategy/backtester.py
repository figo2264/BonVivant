"""
Backtest-specific strategy classes
백테스트 전용 전략 클래스들
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from ..data.fetcher import get_data_fetcher
from ..analysis.technical import get_technical_analyzer
from ..analysis.ai_model import get_ai_manager
from ..backtest.data_validator import get_data_validator
from .selector import get_stock_selector


class BacktestStrategy:
    """백테스트용 전략 실행 클래스"""
    
    def __init__(self, stop_loss_rate: float = -0.05):
        self.data_fetcher = get_data_fetcher()
        self.technical_analyzer = get_technical_analyzer()
        self.ai_manager = get_ai_manager()
        self.data_validator = get_data_validator()
        self.stock_selector = get_stock_selector()
        self.stop_loss_rate = stop_loss_rate
    
    def should_sell_stock(self, ticker: str, holding_info: Dict[str, Any], 
                         current_date: str) -> tuple[bool, str]:
        """
        매도 여부 결정 (백테스트용)
        
        Args:
            ticker: 종목 코드
            holding_info: 보유 정보 (buy_price, quantity, buy_date 등)
            current_date: 현재 날짜
            
        Returns:
            tuple: (should_sell, sell_reason)
        """
        holding_days = self._calculate_holding_days(holding_info.get('buy_date'), current_date)
        buy_price = holding_info.get('buy_price', 0)
        
        # 데이터 검증
        if not self.data_validator.validate_ticker_data(ticker, current_date):
            return False, "데이터 검증 실패"
        
        # 1. 손실 제한 체크 (우선순위 최고)
        stop_loss_sell, current_price, loss_rate = self.data_validator.check_stop_loss(
            ticker, buy_price, current_date, self.stop_loss_rate
        )
        
        if stop_loss_sell:
            return True, f"손실제한 (손실률: {loss_rate*100:.1f}%)"
        
        # 2. 기본 3일 룰
        if holding_days >= 3:
            sell_reason = f"보유기간 ({holding_days}일)"
            
            # 3일차에만 기술적 홀드 시그널 체크 (손실이 크지 않은 경우)
            if holding_days == 3 and loss_rate > -0.02:
                try:
                    hold_signal = self.technical_analyzer.get_technical_hold_signal(ticker, current_date)
                    
                    if hold_signal >= 0.75:
                        return False, "기술적 강홀드"
                except Exception as e:
                    print(f"홀드 시그널 계산 오류 ({ticker}): {e}")
            
            return True, sell_reason
        
        # 3. 안전장치: 5일 이상은 무조건 매도
        if holding_days >= 5:
            return True, "5일 안전룰"
        
        return False, ""
    
    def select_buy_candidates(self, current_date: str, excluded_tickers: List[str] = None) -> List[Dict[str, Any]]:
        """
        매수 후보 종목 선정 (백테스트용)
        
        Args:
            current_date: 현재 날짜
            excluded_tickers: 제외할 종목 리스트 (현재 보유 종목 등)
            
        Returns:
            List[Dict]: 매수 후보 종목 정보
        """
        excluded_tickers = excluded_tickers or []
        
        try:
            # 1단계: 기술적 분석 기반 1차 선정
            entry_candidates = self.stock_selector.enhanced_stock_selection(current_date)
            
            if not entry_candidates:
                return []
            
            # 데이터 검증 및 제외 종목 필터링
            validated_candidates = []
            for candidate in entry_candidates:
                ticker = candidate['ticker']
                
                # 제외 종목 체크
                if ticker in excluded_tickers:
                    continue
                
                # 데이터 검증
                if self.data_validator.validate_ticker_data(ticker, current_date):
                    validated_candidates.append(candidate)
            
            # 2단계: AI 기반 최종 선정
            if validated_candidates:
                final_candidates = self.stock_selector.ai_enhanced_final_selection(
                    validated_candidates, current_date
                )
                return final_candidates
            
            return []
            
        except Exception as e:
            print(f"❌ 매수 후보 선정 오류: {e}")
            return []
    
    def calculate_optimal_position_size(self, ticker: str, available_cash: float, 
                                      ai_score: float = 0.5) -> float:
        """
        최적 포지션 사이즈 계산
        
        Args:
            ticker: 종목 코드
            available_cash: 사용 가능한 현금
            ai_score: AI 예측 점수
            
        Returns:
            float: 투자 금액
        """
        # AI 신뢰도 기반 포지션 사이즈 조정
        if ai_score >= 0.80:           # 최고신뢰
            position_ratio = 0.25      # 25%
        elif ai_score >= 0.70:         # 고신뢰
            position_ratio = 0.20      # 20%
        elif ai_score >= 0.65:         # 중신뢰
            position_ratio = 0.15      # 15%
        else:                          # 저신뢰
            position_ratio = 0.10      # 10%
        
        optimal_amount = available_cash * position_ratio
        
        # 최소/최대 투자 금액 제한
        min_investment = 300_000    # 30만원
        max_investment = 1_000_000  # 100만원
        
        return max(min_investment, min(optimal_amount, max_investment))
    
    def evaluate_market_condition(self, current_date: str) -> Dict[str, Any]:
        """
        시장 상황 평가
        
        Args:
            current_date: 현재 날짜
            
        Returns:
            Dict: 시장 상황 정보
        """
        try:
            # 시장 데이터 조회
            market_data = self.data_fetcher.get_market_data_by_date_range(
                current_date, n_days_before=20
            )
            
            if market_data.empty:
                return {'condition': 'unknown', 'confidence': 0.5}
            
            # 당일 데이터
            today_data = market_data[market_data['timestamp'] == current_date]
            
            if today_data.empty:
                return {'condition': 'unknown', 'confidence': 0.5}
            
            # 시장 지표 계산
            total_volume = today_data['volume'].sum()
            total_trade_amount = today_data['trade_amount'].sum()
            active_stocks = len(today_data[today_data['volume'] > 0])
            
            # 과거 20일 평균과 비교
            past_20d = market_data[market_data['timestamp'] < current_date].tail(20)
            if not past_20d.empty:
                avg_volume = past_20d.groupby('timestamp')['volume'].sum().mean()
                avg_trade_amount = past_20d.groupby('timestamp')['trade_amount'].sum().mean()
                
                volume_ratio = total_volume / avg_volume if avg_volume > 0 else 1
                amount_ratio = total_trade_amount / avg_trade_amount if avg_trade_amount > 0 else 1
            else:
                volume_ratio = 1
                amount_ratio = 1
            
            # 시장 상황 판단
            if volume_ratio > 1.5 and amount_ratio > 1.5:
                condition = 'bullish'
                confidence = min(0.9, (volume_ratio + amount_ratio) / 4)
            elif volume_ratio < 0.7 and amount_ratio < 0.7:
                condition = 'bearish'
                confidence = min(0.9, (2 - volume_ratio - amount_ratio) / 2)
            else:
                condition = 'neutral'
                confidence = 0.6
            
            return {
                'condition': condition,
                'confidence': confidence,
                'volume_ratio': volume_ratio,
                'amount_ratio': amount_ratio,
                'active_stocks': active_stocks,
                'total_volume': total_volume,
                'total_trade_amount': total_trade_amount
            }
            
        except Exception as e:
            print(f"❌ 시장 상황 평가 오류: {e}")
            return {'condition': 'unknown', 'confidence': 0.5}
    
    def _calculate_holding_days(self, buy_date: str, current_date: str) -> int:
        """보유 일수 계산"""
        try:
            if not buy_date:
                return 0
            
            buy_dt = datetime.strptime(buy_date[:10], '%Y-%m-%d')
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            
            return (current_dt - buy_dt).days + 1  # 매수일 포함
        except:
            return 0


class BacktestRiskManager:
    """백테스트용 리스크 관리 클래스"""
    
    def __init__(self, max_portfolio_risk: float = 0.02):
        """
        Args:
            max_portfolio_risk: 포트폴리오 최대 리스크 (일별 VaR 기준)
        """
        self.max_portfolio_risk = max_portfolio_risk
        self.data_validator = get_data_validator()
    
    def check_portfolio_risk(self, holdings: Dict[str, Dict[str, Any]], 
                           current_date: str) -> Dict[str, Any]:
        """
        포트폴리오 리스크 체크
        
        Args:
            holdings: 보유 종목 정보
            current_date: 현재 날짜
            
        Returns:
            Dict: 리스크 분석 결과
        """
        if not holdings:
            return {'risk_level': 'low', 'warnings': []}
        
        warnings = []
        total_positions = len(holdings)
        
        # 1. 포지션 집중도 체크
        if total_positions == 1:
            warnings.append("단일 종목 집중 리스크")
        elif total_positions >= 10:
            warnings.append("과도한 포지션 분산")
        
        # 2. 섹터 집중도 체크 (간단한 버전)
        # 실제로는 종목별 섹터 정보가 필요하지만, 여기서는 생략
        
        # 3. 손실 제한 위반 종목 체크
        stop_loss_warnings = []
        for ticker, holding in holdings.items():
            buy_price = holding.get('buy_price', 0)
            if buy_price > 0:
                stop_loss_sell, current_price, loss_rate = self.data_validator.check_stop_loss(
                    ticker, buy_price, current_date, stop_loss_rate=-0.03  # 3% 경고선
                )
                
                if stop_loss_sell:
                    stop_loss_warnings.append(f"{ticker}: {loss_rate*100:.1f}% 손실")
        
        if stop_loss_warnings:
            warnings.extend(stop_loss_warnings)
        
        # 4. 리스크 레벨 결정
        if len(warnings) >= 3:
            risk_level = 'high'
        elif len(warnings) >= 1:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'warnings': warnings,
            'total_positions': total_positions,
            'stop_loss_violations': len(stop_loss_warnings)
        }
    
    def suggest_risk_mitigation(self, risk_analysis: Dict[str, Any]) -> List[str]:
        """리스크 완화 제안"""
        suggestions = []
        
        if risk_analysis['risk_level'] == 'high':
            suggestions.append("포트폴리오 리밸런싱 권장")
        
        if risk_analysis['stop_loss_violations'] > 0:
            suggestions.append("손실 제한 종목 즉시 매도 검토")
        
        if risk_analysis['total_positions'] == 1:
            suggestions.append("포지션 분산 권장")
        
        return suggestions


# 편의 함수들
def get_backtest_strategy(stop_loss_rate: float = -0.05) -> BacktestStrategy:
    """백테스트 전략 인스턴스 반환"""
    return BacktestStrategy(stop_loss_rate)

def get_backtest_risk_manager(max_portfolio_risk: float = 0.02) -> BacktestRiskManager:
    """백테스트 리스크 매니저 인스턴스 반환"""
    return BacktestRiskManager(max_portfolio_risk)
