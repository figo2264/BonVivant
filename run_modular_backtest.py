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
from hanlyang_stock.config.backtest_settings import get_backtest_config, create_custom_config, BacktestConfig


def run_simple_backtest():
    """간단한 백테스트 실행"""
    print("🚀 간단한 백테스트 실행")
    print("=" * 60)
    
    # 기본 설정으로 백테스트 엔진 생성
    config = get_backtest_config('balanced')
    
    # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
    config_dict = {
        'initial_capital': config.initial_capital,
        'transaction_cost': config.transaction_cost,
        'max_positions': config.max_positions,
        'position_size_ratio': config.position_size_ratio,
        'safety_cash_amount': config.safety_cash_amount,
        'stop_loss_rate': config.stop_loss_rate,
        'investment_amounts': config.investment_amounts,
        'backtest_params': config.get_optimal_params(),
        'min_technical_score': config.min_technical_score,
        'trend_strength_filter_enabled': config.trend_strength_filter_enabled,
        'trend_strength_weights': config.trend_strength_weights,
        'technical_score_weights': config.technical_score_weights,  # 추가
        'preset': 'balanced'
    }
    
    engine = BacktestEngine(
        initial_capital=config.initial_capital,
        transaction_cost=config.transaction_cost,
        config=config_dict  # 설정을 명시적으로 전달
    )
    
    # 설정에서 최적화 파라미터 가져오기
    optimal_params = config.get_optimal_params()
    
    print("📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/100_000_000:.0f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']}")
    
    # 최근 10일간 백테스트 (테스트용)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # 백테스트 실행 (기술적 분석만 사용)
        results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        
        # 결과 저장
        filename = engine.save_results("simple_modular_backtest.json")
        
        print(f"\n✅ 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except Exception as e:
        print(f"❌ 백테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_profit_maximized_backtest():
    """수익률 극대화 백테스트 실행"""
    print("💰 수익률 극대화 백테스트 실행")
    print("=" * 60)
    
    # 수익률 극대화를 위한 커스텀 설정
    custom_config = create_custom_config(
        initial_capital=10_000_000,      # 1000만원
        max_positions=7,                 # 7개 종목까지
        position_size_ratio=0.9,         # 90% 투자
        safety_cash_amount=1_000_000,    # 안전 자금 100만원
        stop_loss_rate=-0.03,            # -3% 손실제한
        min_technical_score=0.5,         # 기술점수 기준 완화
        investment_amounts={              # 투자 금액 증액
            '최고신뢰': 1_200_000,       # 120만원 (점수 0.8+)
            '고신뢰': 900_000,           # 90만원 (점수 0.7-0.8)
            '중신뢰': 600_000,           # 60만원 (점수 0.65-0.7)
            '저신뢰': 400_000            # 40만원 (점수 0.65 미만)
        }
    )
    
    print("💰 수익률 극대화 설정:")
    print(f"  초기 자본: {custom_config.initial_capital:,}원")
    print(f"  최대 보유 종목: {custom_config.max_positions}")
    print(f"  투자 비율: {custom_config.position_size_ratio*100:.0f}%")
    print(f"  안전 자금: {custom_config.safety_cash_amount:,}원")
    print(f"  손실 제한: {custom_config.stop_loss_rate*100:.1f}%")
    print(f"  최소 기술점수: {custom_config.min_technical_score}")
    
    # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
    config_dict = {
        'initial_capital': custom_config.initial_capital,
        'transaction_cost': custom_config.transaction_cost,
        'max_positions': custom_config.max_positions,
        'position_size_ratio': custom_config.position_size_ratio,
        'safety_cash_amount': custom_config.safety_cash_amount,
        'stop_loss_rate': custom_config.stop_loss_rate,
        'investment_amounts': custom_config.investment_amounts,
        'backtest_params': custom_config.get_optimal_params(),
        'min_technical_score': custom_config.min_technical_score,
        'preset': 'balanced'
    }
    
    # 백테스트 엔진 생성 (설정 전달)
    engine = BacktestEngine(
        initial_capital=custom_config.initial_capital,
        transaction_cost=custom_config.transaction_cost,
        config=config_dict  # 설정을 명시적으로 전달
    )
    
    # 커스텀 설정에서 최적화 파라미터 가져오기
    optimal_params = custom_config.get_optimal_params()
    # 커스텀 설정 적용
    optimal_params['max_positions'] = custom_config.max_positions
    optimal_params['min_technical_score'] = custom_config.min_technical_score
    
    print("\n📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/100_000_000:.0f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']:.2f}")  # 소수점 2자리로 명시
    print(f"   - 최대 보유종목: {optimal_params['max_positions']}개")
    
    # 1개월간 백테스트
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # 백테스트 실행
        results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        
        # 결과 저장
        filename = engine.save_results("profit_maximized_backtest.json")
        
        print(f"\n✅ 수익률 극대화 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except Exception as e:
        print(f"❌ 수익률 극대화 백테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_custom_backtest():
    """커스텀 설정 백테스트 실행"""
    print("🛠️ 커스텀 설정 백테스트 실행")
    print("=" * 60)
    
    # 커스텀 설정 생성
    custom_config = create_custom_config(
        initial_capital=10_000_000,     # 2000만원으로 증가
        max_positions=7,                # 7개 종목까지
        stop_loss_rate=-0.04           # -4% 손실제한
    )
    
    print("커스텀 설정:")
    print(f"  초기 자본: {custom_config.initial_capital:,}원")
    print(f"  최대 보유 종목: {custom_config.max_positions}")
    print(f"  손실 제한: {custom_config.stop_loss_rate*100:.1f}%")
    print(f"  거래 비용: {custom_config.transaction_cost*100:.2f}%")
    
    # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
    config_dict = {
        'initial_capital': custom_config.initial_capital,
        'transaction_cost': custom_config.transaction_cost,
        'max_positions': custom_config.max_positions,
        'position_size_ratio': custom_config.position_size_ratio,
        'safety_cash_amount': custom_config.safety_cash_amount,
        'stop_loss_rate': custom_config.stop_loss_rate,
        'investment_amounts': custom_config.investment_amounts,
        'backtest_params': custom_config.get_optimal_params(),
        'min_technical_score': custom_config.min_technical_score,
        'preset': 'balanced'
    }
    
    # 백테스트 엔진 생성 (설정 전달)
    engine = BacktestEngine(
        initial_capital=custom_config.initial_capital,
        transaction_cost=custom_config.transaction_cost,
        config=config_dict  # 설정을 명시적으로 전달
    )
    
    # 커스텀 설정에서 최적화 파라미터 가져오기
    optimal_params = custom_config.get_optimal_params()
    # 커스텀 max_positions 적용
    optimal_params['max_positions'] = custom_config.max_positions
    
    print("\n📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/100_000_000:.0f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']}")
    
    # 1개월간 백테스트
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # 백테스트 실행
        results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        
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
    
    # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
    config_dict = {
        'initial_capital': config.initial_capital,
        'transaction_cost': config.transaction_cost,
        'max_positions': config.max_positions,
        'position_size_ratio': config.position_size_ratio,
        'safety_cash_amount': config.safety_cash_amount,
        'stop_loss_rate': config.stop_loss_rate,
        'investment_amounts': config.investment_amounts,
        'backtest_params': config.get_optimal_params(),
        'min_technical_score': config.min_technical_score,
        'trend_strength_filter_enabled': config.trend_strength_filter_enabled,
        'trend_strength_weights': config.trend_strength_weights,
        'technical_score_weights': config.technical_score_weights,  # 추가
        'preset': 'balanced'
    }
    
    # 설정에서 최적화 파라미터 가져오기
    optimal_params = config.get_optimal_params()
    
    print("📊 최적화 파라미터 적용:")
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/100_000_000:.0f}억원")
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
        
        engine = BacktestEngine(
            config.initial_capital, 
            config.transaction_cost,
            config=config_dict  # 설정 전달
        )
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        try:
            period_results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
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
        
        # 커스텀 설정 생성
        from hanlyang_stock.config.backtest_settings import create_custom_config
        custom_config = create_custom_config(
            initial_capital=initial_capital,
            transaction_cost=0.003
        )
        
        # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
        config_dict = {
            'initial_capital': custom_config.initial_capital,
            'transaction_cost': custom_config.transaction_cost,
            'max_positions': custom_config.max_positions,
            'position_size_ratio': custom_config.position_size_ratio,
            'safety_cash_amount': custom_config.safety_cash_amount,
            'stop_loss_rate': custom_config.stop_loss_rate,
            'investment_amounts': custom_config.investment_amounts,
            'backtest_params': custom_config.get_optimal_params(),
            'min_technical_score': custom_config.min_technical_score,
            'preset': 'balanced'
        }
        
        # 백테스트 실행
        engine = BacktestEngine(
            initial_capital, 
            0.003,
            config=config_dict  # 설정 전달
        )
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        
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


def run_small_capital_backtest():
    """소액 투자자를 위한 백테스트 실행 (100만원)"""
    print("💵 소액 투자 백테스트 실행 (100만원)")
    print("=" * 60)
    
    # 소액 투자 설정 사용 (backtest_settings.py에서)
    config = get_backtest_config('small_capital')
    
    # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
    config_dict = {
        'initial_capital': config.initial_capital,
        'transaction_cost': config.transaction_cost,
        'max_positions': config.max_positions,
        'position_size_ratio': config.position_size_ratio,
        'safety_cash_amount': config.safety_cash_amount,
        'stop_loss_rate': config.stop_loss_rate,
        'investment_amounts': config.investment_amounts,
        'backtest_params': config.get_optimal_params(),
        'min_technical_score': config.min_technical_score,
        'trend_strength_filter_enabled': config.trend_strength_filter_enabled,
        'trend_strength_weights': config.trend_strength_weights,
        'technical_score_weights': config.technical_score_weights,  # 추가
        'preset': 'small_capital',
        # 소액 투자용 추가 설정
        'min_market_cap': 50_000_000_000,  # 시가총액 500억원 이상 (200억에서 완화)
    }
    
    print("💵 소액 투자 설정 (backtest_settings.py 사용):")
    print(f"  초기 자본: {config.initial_capital:,}원")
    print(f"  최대 보유 종목: {config.max_positions}")
    print(f"  투자 비율: {config.position_size_ratio*100:.0f}%")
    print(f"  안전 자금: {config.safety_cash_amount:,}원")
    print(f"  손실 제한: {config.stop_loss_rate*100:.1f}%")
    print(f"  최소 기술점수: {config.min_technical_score}")
    print(f"  최소 시가총액: 500억원 (소액 투자용 완화)")
    
    print("\n📊 백테스트 파라미터:")
    optimal_params = config.get_optimal_params()
    print(f"   - 최저점 기간: {optimal_params['min_close_days']}일")
    print(f"   - 이동평균: {optimal_params['ma_period']}일")
    print(f"   - 최소 거래대금: {optimal_params['min_trade_amount']/100_000_000:.0f}억원")
    print(f"   - 최소 기술점수: {optimal_params['min_technical_score']:.2f}")
    print(f"   - 최대 보유종목: {optimal_params['max_positions']}개")
    
    # 백테스트 엔진 생성 (설정 전달)
    engine = BacktestEngine(
        initial_capital=config.initial_capital,
        transaction_cost=config.transaction_cost,
        config=config_dict  # 설정을 명시적으로 전달
    )
    
    # 1개월 백테스트
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    try:
        # 백테스트 실행
        results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        
        # 결과 저장
        filename = engine.save_results("small_capital_backtest.json")
        
        print(f"\n✅ 소액 투자 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except Exception as e:
        print(f"❌ 소액 투자 백테스트 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_capital_based_config(capital: float) -> BacktestConfig:
    """
    투자금액에 따라 자동으로 설정을 생성하는 함수
    
    Args:
        capital: 투자 금액
        
    Returns:
        BacktestConfig: 투자금액에 최적화된 백테스트 설정
    """
    # 투자금액에 따른 적정 파라미터 계산
    if capital <= 1_000_000:
        max_positions = 5
        position_ratio = 0.8
        safety_cash = capital * 0.1
        investment_base = capital * 0.12  # 최고신뢰 기준
        min_score = 0.7  # 소액이므로 높은 기준
    elif capital <= 5_000_000:
        max_positions = 7
        position_ratio = 0.85
        safety_cash = capital * 0.1
        investment_base = capital * 0.15
        min_score = 0.65
    elif capital <= 10_000_000:
        max_positions = 10
        position_ratio = 0.9
        safety_cash = capital * 0.1
        investment_base = capital * 0.12
        min_score = 0.6
    else:
        max_positions = 7
        position_ratio = 0.9
        safety_cash = min(1_000_000, capital * 0.05)
        investment_base = capital * 0.1
        min_score = 0.55
    
    return create_custom_config(
        initial_capital=capital,
        max_positions=max_positions,
        position_size_ratio=position_ratio,
        safety_cash_amount=safety_cash,
        min_technical_score=min_score,
        investment_amounts={
            '최고신뢰': investment_base,
            '고신뢰': investment_base * 0.75,
            '중신뢰': investment_base * 0.5,
            '저신뢰': investment_base * 0.33
        }
    )


def run_dynamic_capital_backtest():
    """동적 투자금액 백테스트"""
    print("💸 동적 투자금액 백테스트")
    print("=" * 60)
    
    try:
        # 투자금액 입력
        capital_input = input("투자금액을 입력하세요 (원): ").strip()
        capital = int(capital_input)
        
        # 동적 설정 생성
        config = create_capital_based_config(capital)
        
        print(f"\n💸 {capital:,}원에 최적화된 설정:")
        print(f"  최대 보유 종목: {config.max_positions}")
        print(f"  투자 비율: {config.position_size_ratio*100:.0f}%")
        print(f"  안전 자금: {config.safety_cash_amount:,}원")
        print(f"  최소 기술점수: {config.min_technical_score}")
        print("\n투자 금액 배분:")
        for level, amount in config.investment_amounts.items():
            print(f"  {level}: {amount:,}원")
        
        # 설정을 딕셔너리로 변환 (BacktestEngine에 전달용)
        config_dict = {
            'initial_capital': config.initial_capital,
            'transaction_cost': config.transaction_cost,
            'max_positions': config.max_positions,
            'position_size_ratio': config.position_size_ratio,
            'safety_cash_amount': config.safety_cash_amount,
            'stop_loss_rate': config.stop_loss_rate,
            'investment_amounts': config.investment_amounts,
            'backtest_params': config.get_optimal_params(),
            'min_technical_score': config.min_technical_score,
            'preset': 'balanced'
        }
        
        # 백테스트 엔진 생성 (설정 전달)
        engine = BacktestEngine(
            initial_capital=config.initial_capital,
            transaction_cost=config.transaction_cost,
            config=config_dict  # 설정을 명시적으로 전달
        )
        
        # 기간 설정
        print("\n📅 백테스트 기간:")
        period_choice = input("1) 1주일  2) 1개월  3) 3개월 (1/2/3): ").strip()
        
        end_date = datetime.now()
        if period_choice == '1':
            start_date = end_date - timedelta(days=7)
        elif period_choice == '3':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # 백테스트 실행
        results = engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        
        # 결과 저장
        filename = engine.save_results(f"dynamic_{capital}_backtest.json")
        
        print(f"\n✅ 동적 투자금액 백테스트 완료! 결과 파일: {filename}")
        return results
        
    except ValueError:
        print("❌ 잘못된 금액 형식입니다.")
        return None
    except Exception as e:
        print(f"❌ 동적 백테스트 오류: {e}")
        import traceback
        traceback.print_exc()
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
        print("5) 💰 수익률 극대화 백테스트 (NEW)")
        print("6) 💵 소액 투자 백테스트 (100만원)")
        print("7) 💸 동적 투자금액 백테스트 (자동 최적화)")
        print("8) 종료")
        
        try:
            choice = input("\n선택 (1-8): ").strip()
            
            if choice == '1':
                run_simple_backtest()
            elif choice == '2':
                run_custom_backtest()
            elif choice == '3':
                run_period_comparison()
            elif choice == '4':
                interactive_backtest()
            elif choice == '5':
                run_profit_maximized_backtest()
            elif choice == '6':
                run_small_capital_backtest()
            elif choice == '7':
                run_dynamic_capital_backtest()
            elif choice == '8':
                print("백테스트 엔진 종료")
                break
            else:
                print("잘못된 선택입니다. 1-8 중에서 선택해주세요.")
                
        except KeyboardInterrupt:
            print("\n백테스트 엔진 종료")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
