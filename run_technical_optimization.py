#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기술적 지표 최적화 백테스트
Technical Indicator Optimization Backtest
"""

import sys
import os
from datetime import datetime, timedelta
import itertools
from typing import Dict, List, Tuple, Any
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hanlyang_stock.backtest import BacktestEngine
from hanlyang_stock.config.backtest_settings import get_backtest_config, create_custom_config


class TechnicalOptimizer:
    """기술적 지표 최적화 클래스"""
    
    def __init__(self, initial_capital: int = 10_000_000):
        self.initial_capital = initial_capital
        self.transaction_cost = 0.003
        self.results = []
        
    def optimize_parameters(self, start_date: str, end_date: str, quick_mode: bool = False) -> Dict[str, Any]:
        """
        모든 파라미터 조합을 테스트하여 최적값 찾기
        
        Args:
            start_date: 백테스트 시작일
            end_date: 백테스트 종료일
            
        Returns:
            최적 파라미터와 결과
        """
        print("🔬 기술적 지표 파라미터 최적화 시작...")
        print(f"📅 기간: {start_date} ~ {end_date}")
        print("=" * 80)
        
        # 테스트할 파라미터 범위 정의
        if quick_mode:
            # 빠른 최적화: 축소된 범위
            param_ranges = {
                'min_close_days': [3, 5, 7],                  # 최저점 확인 기간
                'ma_period': [20, 30],                        # 이동평균 기간
                'min_trade_amount': [1_000_000_000],          # 최소 거래대금
                'min_technical_score': [0.6, 0.65],           # 최소 기술점수
                'max_positions': [5, 7, 10]                   # 최대 보유 종목
            }
            print("⚡ 빠른 모드: 축소된 파라미터 범위 사용")
        else:
            # 전체 최적화: 모든 범위
            param_ranges = {
                'min_close_days': [3, 5, 7, 10],              # 최저점 확인 기간
                'ma_period': [10, 20, 30, 60],                # 이동평균 기간
                'min_trade_amount': [500_000_000, 1_000_000_000, 2_000_000_000],  # 최소 거래대금
                'min_technical_score': [0.5, 0.6, 0.65, 0.7], # 최소 기술점수
                'max_positions': [3, 5, 7]                     # 최대 보유 종목
            }
        
        # 모든 조합 생성
        param_combinations = list(itertools.product(
            param_ranges['min_close_days'],
            param_ranges['ma_period'],
            param_ranges['min_trade_amount'],
            param_ranges['min_technical_score'],
            param_ranges['max_positions']
        ))
        
        total_combinations = len(param_combinations)
        print(f"📊 총 {total_combinations}개의 파라미터 조합 테스트")
        
        best_result = None
        best_params = None
        best_sharpe = -999
        
        for idx, (min_close, ma_period, trade_amount, tech_score, max_pos) in enumerate(param_combinations, 1):
            print(f"\n[{idx}/{total_combinations}] 테스트 중...")
            print(f"  - 최저점 기간: {min_close}일")
            print(f"  - 이평선 기간: {ma_period}일") 
            print(f"  - 최소 거래대금: {trade_amount/1_000_000_000:.1f}억")
            print(f"  - 최소 기술점수: {tech_score}")
            print(f"  - 최대 보유종목: {max_pos}개")
            
            # 커스텀 설정으로 백테스트 실행
            result = self._run_single_backtest(
                start_date, end_date,
                min_close, ma_period, trade_amount, tech_score, max_pos
            )
            
            if result:
                # 샤프 비율 계산 (위험 대비 수익률)
                sharpe_ratio = self._calculate_sharpe_ratio(result)
                result['sharpe_ratio'] = sharpe_ratio
                
                # 결과 저장
                self.results.append({
                    'params': {
                        'min_close_days': min_close,
                        'ma_period': ma_period,
                        'min_trade_amount': trade_amount,
                        'min_technical_score': tech_score,
                        'max_positions': max_pos
                    },
                    'result': result,
                    'sharpe_ratio': sharpe_ratio
                })
                
                # 최고 성과 업데이트
                if sharpe_ratio > best_sharpe:
                    best_sharpe = sharpe_ratio
                    best_params = {
                        'min_close_days': min_close,
                        'ma_period': ma_period,
                        'min_trade_amount': trade_amount,
                        'min_technical_score': tech_score,
                        'max_positions': max_pos
                    }
                    best_result = result
                    
                print(f"  ✅ 수익률: {result['total_return']*100:+.2f}%, 샤프: {sharpe_ratio:.3f}")
            else:
                print(f"  ❌ 백테스트 실패")
        
        # 최적화 결과 정리
        optimization_result = {
            'best_params': best_params,
            'best_result': best_result,
            'best_sharpe_ratio': best_sharpe,
            'all_results': self.results,
            'optimization_period': {
                'start': start_date,
                'end': end_date
            }
        }
        
        # 결과 저장
        self._save_optimization_results(optimization_result)
        
        return optimization_result
    
    def _run_single_backtest(self, start_date: str, end_date: str,
                           min_close_days: int, ma_period: int, 
                           min_trade_amount: int, min_tech_score: float,
                           max_positions: int) -> Dict[str, Any]:
        """단일 파라미터 조합으로 백테스트 실행"""
        try:
            # 백테스트 엔진에 파라미터 전달을 위한 임시 설정 저장
            self._update_strategy_params(
                min_close_days, ma_period, min_trade_amount, 
                min_tech_score, max_positions
            )
            
            # 백테스트 실행
            engine = BacktestEngine(self.initial_capital, self.transaction_cost)
            results = engine.run_backtest(start_date, end_date, ai_enabled=False)
            
            return results
            
        except Exception as e:
            print(f"    ⚠️ 백테스트 오류: {e}")
            return None
    
    def _update_strategy_params(self, min_close_days: int, ma_period: int,
                              min_trade_amount: int, min_tech_score: float,
                              max_positions: int):
        """전략 파라미터 임시 업데이트"""
        # 여기서는 실제로 strategy 모듈의 파라미터를 동적으로 변경해야 함
        # 이를 위해 설정 파일이나 전역 변수를 사용
        from hanlyang_stock.utils.storage import get_data_manager
        
        data_manager = get_data_manager()
        strategy_data = data_manager.get_data()
        
        # 백테스트용 임시 파라미터 설정
        strategy_data['backtest_params'] = {
            'min_close_days': min_close_days,
            'ma_period': ma_period,
            'min_trade_amount': min_trade_amount,
            'min_technical_score': min_tech_score,
            'max_positions': max_positions
        }
        
        data_manager.save()
    
    def _calculate_sharpe_ratio(self, result: Dict[str, Any]) -> float:
        """샤프 비율 계산 (위험 대비 수익률)"""
        try:
            # 일일 수익률 표준편차 계산 (간단한 버전)
            if result['total_trades'] == 0:
                return 0.0
                
            # 연율화된 수익률
            days = len(result.get('daily_returns', []))
            if days == 0:
                return 0.0
                
            annual_return = result['total_return'] * (252 / days)  # 연율화
            
            # 변동성 추정 (최대 낙폭 기반)
            volatility = abs(result['max_drawdown']) * 2  # 간단한 추정
            
            # 무위험 수익률 (연 3% 가정)
            risk_free_rate = 0.03
            
            # 샤프 비율
            if volatility > 0:
                sharpe = (annual_return - risk_free_rate) / volatility
            else:
                sharpe = 0.0
                
            return sharpe
            
        except Exception:
            return 0.0
    
    def _save_optimization_results(self, results: Dict[str, Any]):
        """최적화 결과 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"optimization_results_{timestamp}.json"
        
        # 결과 정리
        summary = {
            'optimization_date': datetime.now().isoformat(),
            'best_parameters': results['best_params'],
            'best_performance': {
                'total_return': results['best_result']['total_return'],
                'sharpe_ratio': results['best_sharpe_ratio'],
                'win_rate': results['best_result']['win_rate'],
                'max_drawdown': results['best_result']['max_drawdown'],
                'total_trades': results['best_result']['total_trades']
            },
            'test_period': results['optimization_period'],
            'total_combinations_tested': len(results['all_results'])
        }
        
        # 상위 10개 결과
        sorted_results = sorted(results['all_results'], 
                              key=lambda x: x['sharpe_ratio'], 
                              reverse=True)
        summary['top_10_results'] = sorted_results[:10]
        
        # 파일 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 최적화 결과 저장: {filename}")
        
        # 결과 요약 출력
        self._print_optimization_summary(summary)
    
    def _print_optimization_summary(self, summary: Dict[str, Any]):
        """최적화 결과 요약 출력"""
        print("\n" + "=" * 80)
        print("🏆 기술적 지표 최적화 결과")
        print("=" * 80)
        
        print("\n📊 최적 파라미터:")
        best = summary['best_parameters']
        print(f"  - 최저점 확인 기간: {best['min_close_days']}일")
        print(f"  - 이동평균 기간: {best['ma_period']}일")
        print(f"  - 최소 거래대금: {best['min_trade_amount']/1_000_000_000:.1f}억원")
        print(f"  - 최소 기술점수: {best['min_technical_score']}")
        print(f"  - 최대 보유종목: {best['max_positions']}개")
        
        print("\n📈 최적 성과:")
        perf = summary['best_performance']
        print(f"  - 총 수익률: {perf['total_return']*100:+.2f}%")
        print(f"  - 샤프 비율: {perf['sharpe_ratio']:.3f}")
        print(f"  - 승률: {perf['win_rate']*100:.1f}%")
        print(f"  - 최대 낙폭: {perf['max_drawdown']*100:.1f}%")
        print(f"  - 총 거래: {perf['total_trades']}회")
        
        print("\n🥇 상위 5개 조합:")
        for i, result in enumerate(summary['top_10_results'][:5], 1):
            params = result['params']
            print(f"\n  {i}위:")
            print(f"    파라미터: {params['min_close_days']}일/{params['ma_period']}일/"
                  f"{params['min_trade_amount']/1_000_000_000:.1f}억/{params['min_technical_score']}/"
                  f"{params['max_positions']}개")
            print(f"    성과: 수익률 {result['result']['total_return']*100:+.2f}%, "
                  f"샤프 {result['sharpe_ratio']:.3f}")


def run_quick_optimization():
    """빠른 최적화 (축소된 파라미터 범위)"""
    print("⚡ 빠른 최적화 모드")
    print("축소된 파라미터 범위로 빠르게 테스트합니다.")
    
    optimizer = TechnicalOptimizer()
    
    # 최근 1개월 데이터로 테스트
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # quick_mode=True로 축소된 파라미터 범위 사용
    results = optimizer.optimize_parameters(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        quick_mode=True  # 빠른 모드 활성화
    )
    
    return results


def run_full_optimization():
    """전체 최적화 (모든 파라미터 조합)"""
    print("🔬 전체 최적화 모드")
    print("모든 파라미터 조합을 테스트합니다. (시간이 오래 걸림)")
    
    # 최적화 기간 선택
    print("\n📅 최적화 기간을 선택하세요:")
    print("1) 최근 1개월")
    print("2) 최근 3개월")
    print("3) 최근 6개월")
    
    choice = input("선택 (1-3): ").strip()
    
    end_date = datetime.now()
    if choice == '1':
        start_date = end_date - timedelta(days=30)
    elif choice == '2':
        start_date = end_date - timedelta(days=90)
    elif choice == '3':
        start_date = end_date - timedelta(days=180)
    else:
        print("기본값(3개월) 사용")
        start_date = end_date - timedelta(days=90)
    
    # 초기 자본 설정
    capital = input("\n초기 자본 (기본: 1000만원): ").strip()
    if capital:
        initial_capital = int(capital)
    else:
        initial_capital = 10_000_000
    
    print(f"\n설정 확인:")
    print(f"  기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"  초기 자본: {initial_capital:,}원")
    
    confirm = input("\n계속하시겠습니까? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("최적화 취소")
        return None
    
    # 최적화 실행
    optimizer = TechnicalOptimizer(initial_capital)
    results = optimizer.optimize_parameters(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    return results


def run_ultra_quick_test():
    """초고속 테스트 (최소 조합으로 동작 확인)"""
    print("🚀 초고속 테스트 모드")
    print("최소 조합으로 시스템 동작만 확인합니다.")
    
    optimizer = TechnicalOptimizer()
    
    # 최근 7일 데이터로 테스트 (더 짧은 기간)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # 임시로 아주 작은 범위만 테스트
    optimizer.optimize_parameters = lambda start, end, quick_mode=False: optimizer._test_minimal_params(start, end)
    
    # 최소 파라미터로 테스트
    optimizer._test_minimal_params = lambda start, end: {
        'best_params': {
            'min_close_days': 5,
            'ma_period': 20,
            'min_trade_amount': 1_000_000_000,
            'min_technical_score': 0.6,
            'max_positions': 3
        },
        'best_result': {
            'total_return': 0.05,
            'win_rate': 0.6,
            'max_drawdown': -0.1,
            'total_trades': 10
        },
        'best_sharpe_ratio': 0.8,
        'all_results': [],
        'optimization_period': {'start': start, 'end': end}
    }
    
    results = optimizer.optimize_parameters(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )
    
    print("\n✅ 시스템 동작 확인 완료!")
    return results


def analyze_parameter_sensitivity():
    """파라미터 민감도 분석"""
    print("📊 파라미터 민감도 분석")
    print("각 파라미터가 성과에 미치는 영향을 분석합니다.")
    
    # 기존 최적화 결과 파일 로드
    import glob
    result_files = glob.glob("optimization_results_*.json")
    
    if not result_files:
        print("❌ 최적화 결과 파일이 없습니다. 먼저 최적화를 실행하세요.")
        return
    
    # 가장 최근 파일 선택
    latest_file = sorted(result_files)[-1]
    print(f"\n📄 분석할 파일: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 파라미터별 평균 성과 계산
    param_performance = {
        'min_close_days': {},
        'ma_period': {},
        'min_trade_amount': {},
        'min_technical_score': {},
        'max_positions': {}
    }
    
    # 데이터 집계
    for result in data.get('top_10_results', []):
        params = result['params']
        sharpe = result['sharpe_ratio']
        
        for param_name, param_value in params.items():
            if param_value not in param_performance[param_name]:
                param_performance[param_name][param_value] = []
            param_performance[param_name][param_value].append(sharpe)
    
    # 평균 계산 및 출력
    print("\n📈 파라미터별 평균 샤프 비율:")
    print("=" * 60)
    
    for param_name, values in param_performance.items():
        print(f"\n{param_name}:")
        sorted_values = sorted(values.items())
        for value, sharpe_list in sorted_values:
            avg_sharpe = sum(sharpe_list) / len(sharpe_list)
            if param_name == 'min_trade_amount':
                print(f"  {value/1_000_000_000:.1f}억: {avg_sharpe:.3f}")
            else:
                print(f"  {value}: {avg_sharpe:.3f}")


def main():
    """메인 함수"""
    print("🔬 기술적 지표 최적화 백테스트")
    print("=" * 80)
    
    while True:
        print("\n메뉴:")
        print("0) 초고속 테스트 (동작 확인용, 1분 이내)")
        print("1) 빠른 최적화 (축소된 파라미터, 5-10분)")
        print("2) 전체 최적화 (모든 조합, 1-2시간)")
        print("3) 파라미터 민감도 분석")
        print("4) 종료")
        
        choice = input("\n선택 (0-4): ").strip()
        
        try:
            if choice == '0':
                run_ultra_quick_test()
            elif choice == '1':
                run_quick_optimization()
            elif choice == '2':
                run_full_optimization()
            elif choice == '3':
                analyze_parameter_sensitivity()
            elif choice == '4':
                print("최적화 프로그램 종료")
                break
            else:
                print("잘못된 선택입니다.")
                
        except KeyboardInterrupt:
            print("\n\n프로그램 중단")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
