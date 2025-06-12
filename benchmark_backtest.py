#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 엔진 성능 벤치마크
Backtest Engine Performance Benchmark
"""

import sys
import os
import time
import json
import psutil
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 기존 백테스트 엔진과 모듈화된 엔진 임포트
try:
    from backtest_engine import BacktestEngine as OriginalBacktestEngine
    ORIGINAL_ENGINE_AVAILABLE = True
except ImportError:
    ORIGINAL_ENGINE_AVAILABLE = False
    print("⚠️ 기존 백테스트 엔진을 찾을 수 없습니다.")

from hanlyang_stock.backtest import BacktestEngine as ModularBacktestEngine
from hanlyang_stock.config.backtest_settings import get_backtest_config


class BacktestBenchmark:
    """백테스트 엔진 성능 벤치마크 클래스"""
    
    def __init__(self):
        self.benchmark_results = {}
        self.test_scenarios = [
            {
                'name': '단기 테스트 (5일)',
                'days': 5,
                'ai_enabled': False,
                'description': '빠른 성능 테스트'
            },
            {
                'name': '중기 테스트 (30일)',
                'days': 30,
                'ai_enabled': False,
                'description': '기본 성능 테스트'
            },
            {
                'name': 'AI 단기 테스트 (5일)',
                'days': 5,
                'ai_enabled': True,
                'description': 'AI 기능 포함 빠른 테스트'
            },
            {
                'name': 'AI 중기 테스트 (30일)',
                'days': 30,
                'ai_enabled': True,
                'description': 'AI 기능 포함 기본 테스트'
            }
        ]
    
    def measure_performance(self, func, *args, **kwargs) -> Dict[str, Any]:
        """함수 실행 성능 측정"""
        # 시작 전 메모리 사용량
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 실행 시간 측정
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        
        # 종료 후 메모리 사용량
        end_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'execution_time': end_time - start_time,
            'start_memory_mb': start_memory,
            'end_memory_mb': end_memory,
            'memory_used_mb': end_memory - start_memory,
            'success': success,
            'error': error,
            'result': result
        }
    
    def run_modular_backtest(self, start_date: str, end_date: str, ai_enabled: bool = False) -> Dict[str, Any]:
        """모듈화된 백테스트 실행"""
        print(f"🔧 모듈화된 엔진 실행: {start_date} ~ {end_date} (AI: {ai_enabled})")
        
        config = get_backtest_config('balanced')
        engine = ModularBacktestEngine(
            initial_capital=config.initial_capital,
            transaction_cost=config.transaction_cost
        )
        
        results = engine.run_backtest(start_date, end_date, ai_enabled=ai_enabled)
        return results
    
    def run_original_backtest(self, start_date: str, end_date: str, ai_enabled: bool = False) -> Dict[str, Any]:
        """기존 백테스트 실행"""
        if not ORIGINAL_ENGINE_AVAILABLE:
            raise ImportError("기존 백테스트 엔진을 사용할 수 없습니다.")
        
        print(f"📊 기존 엔진 실행: {start_date} ~ {end_date} (AI: {ai_enabled})")
        
        engine = OriginalBacktestEngine(
            initial_capital=10_000_000,
            transaction_cost=0.003
        )
        
        results = engine.run_backtest(start_date, end_date, ai_enabled=ai_enabled)
        return results
    
    def compare_results(self, original_results: Dict[str, Any], 
                       modular_results: Dict[str, Any]) -> Dict[str, Any]:
        """결과 비교"""
        comparison = {}
        
        # 기본 성과 지표 비교
        metrics_to_compare = [
            'total_return', 'total_trades', 'win_rate', 
            'max_drawdown', 'avg_profit_per_trade'
        ]
        
        for metric in metrics_to_compare:
            original_value = original_results.get(metric, 0)
            modular_value = modular_results.get(metric, 0)
            
            # 차이 계산
            if isinstance(original_value, (int, float)) and isinstance(modular_value, (int, float)):
                if original_value != 0:
                    difference_pct = ((modular_value - original_value) / original_value) * 100
                else:
                    difference_pct = 0 if modular_value == 0 else float('inf')
                
                comparison[metric] = {
                    'original': original_value,
                    'modular': modular_value,
                    'difference': modular_value - original_value,
                    'difference_pct': difference_pct
                }
        
        return comparison
    
    def run_benchmark_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """개별 벤치마크 시나리오 실행"""
        print(f"\n🏁 벤치마크 시나리오: {scenario['name']}")
        print(f"   설명: {scenario['description']}")
        print("=" * 50)
        
        # 테스트 날짜 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=scenario['days'])
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        scenario_results = {
            'scenario': scenario,
            'test_period': {'start': start_str, 'end': end_str}
        }
        
        # 모듈화된 엔진 테스트
        print("🔧 모듈화된 백테스트 엔진 테스트...")
        modular_perf = self.measure_performance(
            self.run_modular_backtest,
            start_str, end_str, scenario['ai_enabled']
        )
        scenario_results['modular_engine'] = modular_perf
        
        if modular_perf['success']:
            print(f"   ✅ 완료: {modular_perf['execution_time']:.2f}초")
            print(f"   💾 메모리: {modular_perf['memory_used_mb']:.1f}MB 사용")
            
            modular_results = modular_perf['result']
            if modular_results:
                print(f"   📈 수익률: {modular_results.get('total_return', 0)*100:+.2f}%")
                print(f"   🔄 거래: {modular_results.get('total_trades', 0)}회")
        else:
            print(f"   ❌ 실패: {modular_perf['error']}")
        
        # 기존 엔진 테스트 (가능한 경우)
        if ORIGINAL_ENGINE_AVAILABLE:
            print("\n📊 기존 백테스트 엔진 테스트...")
            original_perf = self.measure_performance(
                self.run_original_backtest,
                start_str, end_str, scenario['ai_enabled']
            )
            scenario_results['original_engine'] = original_perf
            
            if original_perf['success']:
                print(f"   ✅ 완료: {original_perf['execution_time']:.2f}초")
                print(f"   💾 메모리: {original_perf['memory_used_mb']:.1f}MB 사용")
                
                original_results = original_perf['result']
                if original_results:
                    print(f"   📈 수익률: {original_results.get('total_return', 0)*100:+.2f}%")
                    print(f"   🔄 거래: {original_results.get('total_trades', 0)}회")
                
                # 성능 비교
                if modular_perf['success'] and modular_perf['result'] and original_results:
                    comparison = self.compare_results(original_results, modular_perf['result'])
                    scenario_results['comparison'] = comparison
                    
                    print("\n📊 결과 비교:")
                    speed_improvement = ((original_perf['execution_time'] - modular_perf['execution_time']) 
                                       / original_perf['execution_time']) * 100
                    memory_difference = modular_perf['memory_used_mb'] - original_perf['memory_used_mb']
                    
                    print(f"   ⏱️ 실행 시간: {speed_improvement:+.1f}% {'개선' if speed_improvement > 0 else '악화'}")
                    print(f"   💾 메모리 사용: {memory_difference:+.1f}MB {'증가' if memory_difference > 0 else '감소'}")
                    
                    # 주요 지표 비교
                    for metric, comp in comparison.items():
                        if abs(comp['difference_pct']) > 0.1:  # 0.1% 이상 차이
                            print(f"   📊 {metric}: {comp['difference_pct']:+.2f}% 차이")
            else:
                print(f"   ❌ 실패: {original_perf['error']}")
        else:
            scenario_results['original_engine'] = None
            print("\n📊 기존 엔진 테스트 스킵 (엔진 없음)")
        
        return scenario_results
    
    def run_full_benchmark(self):
        """전체 벤치마크 실행"""
        print("🏁 백테스트 엔진 성능 벤치마크 시작")
        print("=" * 60)
        print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"시스템 정보: Python {sys.version_info.major}.{sys.version_info.minor}")
        print(f"메모리: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f}GB")
        print(f"CPU: {psutil.cpu_count()}코어")
        
        benchmark_start_time = time.time()
        
        # 각 시나리오별 벤치마크 실행
        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"\n📋 시나리오 {i}/{len(self.test_scenarios)}")
            scenario_results = self.run_benchmark_scenario(scenario)
            self.benchmark_results[scenario['name']] = scenario_results
        
        benchmark_end_time = time.time()
        total_benchmark_time = benchmark_end_time - benchmark_start_time
        
        # 전체 결과 요약
        self.print_benchmark_summary(total_benchmark_time)
        
        # 결과 저장
        self.save_benchmark_results()
    
    def print_benchmark_summary(self, total_time: float):
        """벤치마크 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("🏁 벤치마크 결과 요약")
        print("=" * 60)
        print(f"총 실행 시간: {total_time:.2f}초")
        
        # 시나리오별 요약
        print("\n📊 시나리오별 성능:")
        for scenario_name, results in self.benchmark_results.items():
            print(f"\n🔸 {scenario_name}")
            
            modular = results.get('modular_engine', {})
            original = results.get('original_engine', {})
            
            if modular.get('success'):
                print(f"   🔧 모듈화된 엔진: {modular['execution_time']:.2f}초")
                
                if original and original.get('success'):
                    print(f"   📊 기존 엔진: {original['execution_time']:.2f}초")
                    
                    speed_diff = modular['execution_time'] - original['execution_time']
                    speed_pct = (speed_diff / original['execution_time']) * 100
                    
                    if speed_pct < -5:
                        print(f"   🚀 {abs(speed_pct):.1f}% 더 빠름")
                    elif speed_pct > 5:
                        print(f"   🐌 {speed_pct:.1f}% 더 느림")
                    else:
                        print(f"   ⚖️ 비슷한 성능 ({speed_pct:+.1f}%)")
                else:
                    print("   📊 기존 엔진: 테스트 불가")
            else:
                print(f"   ❌ 모듈화된 엔진: 실패 ({modular.get('error', 'Unknown')})")
        
        # 전체 성능 평가
        print("\n🎯 종합 평가:")
        
        successful_tests = sum(1 for results in self.benchmark_results.values() 
                             if results.get('modular_engine', {}).get('success', False))
        total_tests = len(self.benchmark_results)
        
        print(f"   성공률: {successful_tests}/{total_tests} ({(successful_tests/total_tests)*100:.1f}%)")
        
        if ORIGINAL_ENGINE_AVAILABLE:
            # 평균 성능 비교
            speed_comparisons = []
            for results in self.benchmark_results.values():
                modular = results.get('modular_engine', {})
                original = results.get('original_engine', {})
                
                if (modular.get('success') and original and original.get('success')):
                    speed_ratio = modular['execution_time'] / original['execution_time']
                    speed_comparisons.append(speed_ratio)
            
            if speed_comparisons:
                avg_speed_ratio = sum(speed_comparisons) / len(speed_comparisons)
                if avg_speed_ratio < 0.95:
                    print(f"   🚀 평균 {(1-avg_speed_ratio)*100:.1f}% 성능 향상")
                elif avg_speed_ratio > 1.05:
                    print(f"   🐌 평균 {(avg_speed_ratio-1)*100:.1f}% 성능 저하")
                else:
                    print(f"   ⚖️ 기존 엔진과 비슷한 성능")
        
        print("\n💡 권장사항:")
        if successful_tests == total_tests:
            print("   ✅ 모듈화된 엔진이 안정적으로 작동합니다.")
            print("   ✅ 프로덕션 환경에서 사용 가능합니다.")
        else:
            print("   ⚠️ 일부 테스트가 실패했습니다. 문제를 확인해주세요.")
            print("   ⚠️ 추가 테스트 후 프로덕션 적용을 권장합니다.")
        
        print("=" * 60)
    
    def save_benchmark_results(self, filename: str = None):
        """벤치마크 결과 저장"""
        if filename is None:
            filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 결과 직렬화 (datetime, pandas 객체 처리)
        def serialize_object(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {key: serialize_object(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [serialize_object(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return serialize_object(obj.__dict__)
            else:
                return obj
        
        benchmark_summary = {
            'benchmark_date': datetime.now().isoformat(),
            'system_info': {
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'total_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'cpu_count': psutil.cpu_count(),
                'original_engine_available': ORIGINAL_ENGINE_AVAILABLE
            },
            'test_scenarios': self.test_scenarios,
            'results': serialize_object(self.benchmark_results)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(benchmark_summary, f, indent=2, ensure_ascii=False)
        
        print(f"💾 벤치마크 결과 저장: {filename}")
        return filename


def main():
    """메인 함수"""
    print("🏁 백테스트 엔진 성능 벤치마크")
    
    benchmark = BacktestBenchmark()
    
    try:
        benchmark.run_full_benchmark()
        
    except KeyboardInterrupt:
        print("\n벤치마크 중단됨")
    except Exception as e:
        print(f"❌ 벤치마크 실행 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
