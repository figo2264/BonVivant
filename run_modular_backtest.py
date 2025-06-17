#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모듈화된 백테스트 엔진 실행 스크립트
Modularized Backtest Engine Runner
"""

import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hanlyang_stock.backtest import BacktestEngine
from hanlyang_stock.config.backtest_settings import get_backtest_config, create_custom_config


def run_simple_backtest():
    """간단한 백테스트 실행"""
    print("🚀 간단한 백테스트 실행")
    print("=" * 60)
    
    # 기본 설정으로 백테스트 엔진 생성
    config = get_backtest_config('balanced')
    engine = BacktestEngine(
        initial_capital=config.initial_capital,
        transaction_cost=config.transaction_cost
    )
    
    # 최적화된 백테스트 파라미터 설정
    from hanlyang_stock.utils.storage import get_data_manager
    data_manager = get_data_manager()
    strategy_data = data_manager.get_data()
    
    # 최적화 파라미터를 백테스트 파라미터로 설정
    optimal_params = {
        'min_close_days': 7,
        'ma_period': 20,  # 30 → 20
        'min_trade_amount': 300_000_000,  # 1억 → 3억
        'min_technical_score': 0.7,  # 0.65 → 0.7
        'max_positions': 5
    }
    
    # strategy_data에 백테스트 파라미터 추가
    strategy_data['backtest_params'] = optimal_params
    data_manager.save()
    
    print("📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/1_000_000_000:.1f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']}")
    
    # 최근 10일간 백테스트 (테스트용)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # 백테스트 실행 (기술적 분석만 사용)
        results = engine.run_backtest(start_str, end_str, ai_enabled=False)
        
        # 결과 저장
        filename = engine.save_results("simple_modular_backtest.json")
        
        print(f"\n✅ 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except Exception as e:
        print(f"❌ 백테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_custom_backtest():
    """커스텀 설정 백테스트 실행"""
    print("🛠️ 커스텀 설정 백테스트 실행")
    print("=" * 60)
    
    # 커스텀 설정 생성
    custom_config = create_custom_config(
        initial_capital=20_000_000,     # 2000만원으로 증가
        max_positions=7,                # 7개 종목까지
        stop_loss_rate=-0.04           # -4% 손실제한
    )
    
    print("커스텀 설정:")
    print(f"  초기 자본: {custom_config.initial_capital:,}원")
    print(f"  최대 보유 종목: {custom_config.max_positions}")
    print(f"  손실 제한: {custom_config.stop_loss_rate*100:.1f}%")
    print(f"  거래 비용: {custom_config.transaction_cost*100:.2f}%")
    
    # 백테스트 엔진 생성
    engine = BacktestEngine(
        initial_capital=custom_config.initial_capital,
        transaction_cost=custom_config.transaction_cost
    )
    
    # 최적화된 백테스트 파라미터 설정
    from hanlyang_stock.utils.storage import get_data_manager
    data_manager = get_data_manager()
    strategy_data = data_manager.get_data()
    
    # 최적화 파라미터를 백테스트 파라미터로 설정
    optimal_params = {
        'min_close_days': 7,
        'ma_period': 20,  # 30 → 20
        'min_trade_amount': 300_000_000,  # 1억 → 3억
        'min_technical_score': 0.7,  # 0.65 → 0.7
        'max_positions': custom_config.max_positions  # 커스텀 설정 사용
    }
    
    # strategy_data에 백테스트 파라미터 추가
    strategy_data['backtest_params'] = optimal_params
    data_manager.save()
    
    print("\n📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/1_000_000_000:.1f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']}")
    
    # 1개월간 백테스트
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # 백테스트 실행
        results = engine.run_backtest(start_str, end_str, ai_enabled=False)
        
        # 결과 저장
        filename = engine.save_results("custom_modular_backtest.json")
        
        print(f"\n✅ 커스텀 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except Exception as e:
        print(f"❌ 커스텀 백테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_period_comparison():
    """기간별 성과 비교 백테스트"""
    print("📅 기간별 성과 비교 백테스트")
    print("=" * 60)
    
    # 기본 설정
    config = get_backtest_config('balanced')
    
    # 최적화된 백테스트 파라미터 설정
    from hanlyang_stock.utils.storage import get_data_manager
    data_manager = get_data_manager()
    strategy_data = data_manager.get_data()
    
    # 최적화 파라미터를 백테스트 파라미터로 설정
    optimal_params = {
        'min_close_days': 7,
        'ma_period': 20,  # 30 → 20
        'min_trade_amount': 300_000_000,  # 1억 → 3억
        'min_technical_score': 0.7,  # 0.65 → 0.7
        'max_positions': 5
    }
    
    # strategy_data에 백테스트 파라미터 추가
    strategy_data['backtest_params'] = optimal_params
    data_manager.save()
    
    print("📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/1_000_000_000:.1f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']}")
    print()
    
    periods = [
        ("1주일", 7),
        ("2주일", 14),
        ("1개월", 30),
        ("2개월", 60),
        ("3개월", 90)
    ]
    
    results = {}
    end_date = datetime.now()
    
    for period_name, days in periods:
        print(f"\n📊 {period_name} 백테스트 실행...")
        
        engine = BacktestEngine(config.initial_capital, config.transaction_cost)
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        try:
            period_results = engine.run_backtest(start_str, end_str, ai_enabled=False)
            results[period_name] = period_results
            print(f"✅ {period_name} 완료: 수익률 {period_results['total_return']*100:+.2f}%")
        except Exception as e:
            print(f"❌ {period_name} 백테스트 오류: {e}")
            results[period_name] = None
    
    # 결과 비교
    print("\n" + "=" * 60)
    print("📊 기간별 성과 비교")
    print("=" * 60)
    
    for period_name, period_results in results.items():
        if period_results:
            print(f"\n{period_name}:")
            print(f"  총 수익률: {period_results['total_return']*100:+.2f}%")
            print(f"  거래 횟수: {period_results['total_trades']}회")
            print(f"  승률: {period_results['win_rate']*100:.1f}%")
            print(f"  최대 손실: {period_results['max_drawdown']*100:.1f}%")
    
    return results


def interactive_backtest():
    """대화형 백테스트 실행"""
    print("🎮 대화형 백테스트 실행")
    print("=" * 60)
    
    try:
        # 사용자 입력 받기
        print("백테스트 설정을 입력해주세요:")
        
        # 기간 설정
        print("\n📅 백테스트 기간 설정:")
        period_choice = input("1) 최근 1주일  2) 최근 1개월  3) 직접 입력 (1/2/3): ").strip()
        
        end_date = datetime.now()
        
        if period_choice == '1':
            start_date = end_date - timedelta(days=7)
        elif period_choice == '2':
            start_date = end_date - timedelta(days=30)
        elif period_choice == '3':
            start_input = input("시작 날짜 (YYYY-MM-DD): ").strip()
            end_input = input("종료 날짜 (YYYY-MM-DD): ").strip()
            start_date = datetime.strptime(start_input, '%Y-%m-%d')
            end_date = datetime.strptime(end_input, '%Y-%m-%d')
        else:
            print("잘못된 선택, 기본값(1개월) 사용")
            start_date = end_date - timedelta(days=30)
        
        # 초기 자본 설정
        print("\n💰 초기 자본 설정:")
        capital_choice = input("1) 1000만원  2) 2000만원  3) 직접 입력 (1/2/3): ").strip()
        
        if capital_choice == '1':
            initial_capital = 10_000_000
        elif capital_choice == '2':
            initial_capital = 20_000_000
        elif capital_choice == '3':
            capital_input = input("초기 자본 (원): ").strip()
            initial_capital = int(capital_input)
        else:
            print("잘못된 선택, 기본값(1000만원) 사용")
            initial_capital = 10_000_000
        
        # 설정 확인
        print(f"\n📋 설정 확인:")
        print(f"   기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        print(f"   초기 자본: {initial_capital:,}원")
        print(f"   전략: 기술적 분석")
        
        confirm = input("\n실행하시겠습니까? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes', '예', '네']:
            print("백테스트 취소")
            return None
        
        # 백테스트 실행
        engine = BacktestEngine(initial_capital, 0.003)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        results = engine.run_backtest(start_str, end_str, ai_enabled=False)
        
        # 결과 저장
        filename = engine.save_results("interactive_backtest.json")
        
        print(f"\n✅ 대화형 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except KeyboardInterrupt:
        print("\n백테스트 중단됨")
        return None
    except Exception as e:
        print(f"❌ 대화형 백테스트 오류: {e}")
        return None


def main():
    """메인 함수"""
    print("🚀 모듈화된 백테스트 엔진 (기술적 분석)")
    print("=" * 60)
    
    while True:
        print("\n실행할 백테스트를 선택하세요:")
        print("1) 간단한 백테스트 (기본 설정, 10일)")
        print("2) 커스텀 백테스트 (사용자 설정, 1개월)")
        print("3) 기간별 비교 백테스트")
        print("4) 대화형 백테스트 (사용자 입력)")
        print("5) 종료")
        
        try:
            choice = input("\n선택 (1-5): ").strip()
            
            if choice == '1':
                run_simple_backtest()
            elif choice == '2':
                run_custom_backtest()
            elif choice == '3':
                run_period_comparison()
            elif choice == '4':
                interactive_backtest()
            elif choice == '5':
                print("백테스트 엔진 종료")
                break
            else:
                print("잘못된 선택입니다. 1-5 중에서 선택해주세요.")
                
        except KeyboardInterrupt:
            print("\n백테스트 엔진 종료")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
