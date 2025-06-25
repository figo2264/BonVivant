"""
Performance analysis for backtesting
백테스트 성과 분석 클래스
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Any, Optional


class PerformanceAnalyzer:
    """백테스트 성과 분석 클래스"""
    
    def __init__(self):
        self.results = {}
    
    def calculate_performance_metrics(self, portfolio_history: List[Dict[str, Any]], 
                                    trade_history: List[Dict[str, Any]], 
                                    initial_capital: float) -> Dict[str, Any]:
        """
        성과 지표 계산 (백테스트 엔진과 동일)
        
        Args:
            portfolio_history: 포트폴리오 히스토리
            trade_history: 거래 히스토리
            initial_capital: 초기 자본
            
        Returns:
            Dict: 성과 지표
        """
        if not portfolio_history:
            return {}
        
        # 포트폴리오 가치 시계열
        portfolio_values = [record['portfolio_value'] for record in portfolio_history]
        
        # 총 수익률
        final_value = portfolio_values[-1]
        total_return = (final_value - initial_capital) / initial_capital
        
        # 일별 수익률
        daily_returns = []
        for i in range(1, len(portfolio_values)):
            daily_return = (portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1]
            daily_returns.append(daily_return)
        
        # 최대 낙폭 (Maximum Drawdown)
        max_drawdown = self._calculate_max_drawdown(portfolio_values)
        
        # 거래 통계
        trade_stats = self._calculate_trade_statistics(trade_history)
        
        # 연간 수익률 (단순 계산)
        days_count = len(portfolio_history)
        annualized_return = total_return * (365 / days_count) if days_count > 0 else 0
        
        # 샤프 비율 (단순 계산)
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        
        # 승률 및 평균 손익
        win_rate = trade_stats['win_rate']
        avg_profit_per_trade = trade_stats['avg_profit_per_trade']
        avg_holding_days = trade_stats['avg_holding_days']
        
        results = {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': trade_stats['total_trades'],
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit_per_trade,
            'avg_holding_days': avg_holding_days,
            'daily_returns': daily_returns,
            'portfolio_values': portfolio_values
        }
        
        self.results = results
        return results
    
    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """최대 낙폭 계산"""
        if not portfolio_values:
            return 0
        
        peak = portfolio_values[0]
        max_dd = 0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_trade_statistics(self, trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """거래 통계 계산"""
        buy_trades = [t for t in trade_history if t['action'] == 'BUY']
        sell_trades = [t for t in trade_history if t['action'] == 'SELL']
        
        if not sell_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit_per_trade': 0,
                'avg_holding_days': 0
            }
        
        profitable_trades = [t for t in sell_trades if t.get('profit', 0) > 0]
        win_rate = len(profitable_trades) / len(sell_trades)
        
        avg_profit = np.mean([t.get('profit', 0) for t in sell_trades])
        avg_holding_days = np.mean([t.get('holding_days', 0) for t in sell_trades])
        
        return {
            'total_trades': len(sell_trades),
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit,
            'avg_holding_days': avg_holding_days
        }
    
    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """샤프 비율 계산"""
        if not daily_returns or np.std(daily_returns) == 0:
            return 0
        
        return np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    
    def analyze_ai_performance(self, trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        전략별 성과 분석 (AI/기술적/하이브리드)
        
        Args:
            trade_history: 거래 히스토리
            
        Returns:
            Dict: 전략 성과 분석 결과
        """
        sell_trades = [t for t in trade_history if t['action'] == 'SELL']
        
        if not sell_trades:
            return {}
        
        # 신뢰도별 성과 분석
        confidence_performance = {}
        
        for trade in sell_trades:
            confidence_level = trade.get('confidence_level', 'Unknown')
            profit = trade.get('profit', 0)
            profit_rate = trade.get('profit_rate', 0)
            
            if confidence_level not in confidence_performance:
                confidence_performance[confidence_level] = {
                    'trades': [],
                    'total_profit': 0,
                    'avg_profit_rate': 0,
                    'win_rate': 0
                }
            
            confidence_performance[confidence_level]['trades'].append(trade)
            confidence_performance[confidence_level]['total_profit'] += profit
        
        # 신뢰도별 통계 계산
        for level, data in confidence_performance.items():
            trades = data['trades']
            profitable_trades = [t for t in trades if t.get('profit', 0) > 0]
            
            data['trade_count'] = len(trades)
            data['win_rate'] = len(profitable_trades) / len(trades) if trades else 0
            data['avg_profit_rate'] = np.mean([t.get('profit_rate', 0) for t in trades]) if trades else 0
            data['avg_holding_days'] = np.mean([t.get('holding_days', 0) for t in trades]) if trades else 0
        
        # AI 점수별 성과 분석
        ai_score_performance = self._analyze_ai_score_performance(sell_trades)
        
        return {
            'confidence_performance': confidence_performance,
            'ai_score_performance': ai_score_performance,
            'total_ai_trades': len(sell_trades)
        }
    
    def _analyze_ai_score_performance(self, sell_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI/기술적/하이브리드 점수별 성과 분석"""
        score_ranges = {
            'very_high': {'min': 0.8, 'max': 1.0, 'trades': []},
            'high': {'min': 0.7, 'max': 0.8, 'trades': []},
            'medium': {'min': 0.6, 'max': 0.7, 'trades': []},
            'low': {'min': 0.0, 'max': 0.6, 'trades': []}
        }
        
        # 거래를 점수 범위별로 분류
        for trade in sell_trades:
            # 하위 호환성: 새로운 필드를 먼저 확인하고, 없으면 ai_score 사용
            score = trade.get('hybrid_score') or trade.get('technical_score') or trade.get('ai_score', 0.5)
            
            for range_name, range_data in score_ranges.items():
                if range_data['min'] <= score < range_data['max']:
                    range_data['trades'].append(trade)
                    break
        
        # 범위별 통계 계산
        for range_name, range_data in score_ranges.items():
            trades = range_data['trades']
            if trades:
                profitable_trades = [t for t in trades if t.get('profit', 0) > 0]
                range_data['trade_count'] = len(trades)
                range_data['win_rate'] = len(profitable_trades) / len(trades)
                range_data['avg_profit_rate'] = np.mean([t.get('profit_rate', 0) for t in trades])
                range_data['total_profit'] = sum([t.get('profit', 0) for t in trades])
            else:
                range_data.update({
                    'trade_count': 0,
                    'win_rate': 0,
                    'avg_profit_rate': 0,
                    'total_profit': 0
                })
        
        return score_ranges
    
    def print_performance_summary(self):
        """성과 요약 출력 (백테스트 엔진과 동일)"""
        if not self.results:
            print("❌ 성과 분석 결과가 없습니다.")
            return
        
        print("\n" + "=" * 60)
        print("📊 백테스팅 결과 요약")
        print("=" * 60)
        
        print(f"💰 초기 자본: {self.results['initial_capital']:,}원")
        print(f"💰 최종 자산: {self.results['final_value']:,}원")
        print(f"📈 총 수익률: {self.results['total_return']*100:+.2f}%")
        print(f"📈 연환산 수익률: {self.results['annualized_return']*100:+.2f}%")
        print(f"📉 최대 낙폭: {self.results['max_drawdown']*100:.2f}%")
        print(f"📊 샤프 비율: {self.results['sharpe_ratio']:.3f}")
        
        print(f"\n🔄 거래 통계:")
        print(f"   총 거래 횟수: {self.results['total_trades']}회")
        print(f"   승률: {self.results['win_rate']*100:.1f}%")
        print(f"   거래당 평균 손익: {self.results['avg_profit_per_trade']:+,.0f}원")
        print(f"   평균 보유 기간: {self.results['avg_holding_days']:.1f}일")
        
        print("=" * 60)
    
    def print_ai_performance_summary(self, ai_performance: Dict[str, Any]):
        """AI/전략 성과 요약 출력"""
        if not ai_performance:
            print("❌ 성과 분석 결과가 없습니다.")
            return
        
        print("\n" + "=" * 60)
        print("🤖 전략별 성과 분석")
        print("=" * 60)
        
        # 신뢰도별 성과
        print("\n📊 신뢰도별 성과:")
        confidence_perf = ai_performance.get('confidence_performance', {})
        
        for level, data in confidence_perf.items():
            if data['trade_count'] > 0:
                print(f"   {level}: {data['trade_count']}회 거래")
                print(f"      승률: {data['win_rate']*100:.1f}%")
                print(f"      평균 수익률: {data['avg_profit_rate']:+.2f}%")
                print(f"      총 손익: {data['total_profit']:+,.0f}원")
        
        # 점수별 성과
        print("\n📈 점수별 성과:")
        score_perf = ai_performance.get('ai_score_performance', {})
        
        score_labels = {
            'very_high': '매우 높음 (0.8+)',
            'high': '높음 (0.7-0.8)',
            'medium': '중간 (0.6-0.7)',
            'low': '낮음 (0.6 미만)'
        }
        
        for range_name, data in score_perf.items():
            if data['trade_count'] > 0:
                label = score_labels.get(range_name, range_name)
                print(f"   {label}: {data['trade_count']}회 거래")
                print(f"      승률: {data['win_rate']*100:.1f}%")
                print(f"      평균 수익률: {data['avg_profit_rate']:+.2f}%")
                print(f"      총 손익: {data['total_profit']:+,.0f}원")
        
        print("=" * 60)
    
    def save_results_to_json(self, filename: str = None) -> str:
        """
        결과를 JSON 파일로 저장 (백테스트 엔진과 동일)
        
        Args:
            filename: 저장할 파일명
            
        Returns:
            str: 저장된 파일명
        """
        if filename is None:
            filename = f"backtest_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
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
        
        results_serializable = convert_datetime(self.results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_serializable, f, indent=2, ensure_ascii=False)
        
        print(f"💾 백테스팅 결과 저장: {filename}")
        return filename
    
    def generate_monthly_report(self, portfolio_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """월별 성과 리포트 생성"""
        if not portfolio_history:
            return {}
        
        # 날짜별로 포트폴리오 값을 데이터프레임으로 변환
        df = pd.DataFrame(portfolio_history)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 월별 수익률 계산
        monthly_returns = df['portfolio_value'].resample('M').last().pct_change().dropna()
        
        monthly_report = {
            'monthly_returns': monthly_returns.to_dict(),
            'best_month': {
                'date': monthly_returns.idxmax().strftime('%Y-%m'),
                'return': monthly_returns.max()
            },
            'worst_month': {
                'date': monthly_returns.idxmin().strftime('%Y-%m'),
                'return': monthly_returns.min()
            },
            'avg_monthly_return': monthly_returns.mean(),
            'monthly_volatility': monthly_returns.std(),
            'positive_months': (monthly_returns > 0).sum(),
            'total_months': len(monthly_returns)
        }
        
        return monthly_report


# 전역 성과 분석기 (싱글톤 패턴)
_analyzer_instance = None

def get_performance_analyzer() -> PerformanceAnalyzer:
    """성과 분석기 인스턴스 반환 (싱글톤)"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = PerformanceAnalyzer()
    return _analyzer_instance
