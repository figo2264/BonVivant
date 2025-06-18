#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 감정 분석 기반 백테스트 실행 스크립트
News sentiment analysis based backtest runner
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# .env 파일 로드
def load_env():
    """환경 변수 파일 로드"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# 환경 변수 로드
load_env()

from hanlyang_stock.backtest import BacktestEngine
from hanlyang_stock.config.backtest_settings import get_backtest_config
from hanlyang_stock.strategy.news_based_selector import get_news_based_selector
from hanlyang_stock.analysis.news_sentiment import NewsAnalyzer
from pykrx import stock


def get_company_name(ticker: str) -> str:
    """종목 코드로 회사명 조회"""
    try:
        name = stock.get_market_ticker_name(ticker)
        if name:
            return name
        else:
            return ticker  # 조회 실패 시 종목 코드 반환
    except Exception as e:
        print(f"  ⚠️ 회사명 조회 실패 ({ticker}): {e}")
        return ticker


def test_news_collection_for_tickers(tickers: List[str], test_date: str = None, debug: bool = False):
    """특정 종목들의 뉴스 수집 테스트"""
    print("\n📰 뉴스 수집 테스트")
    print("=" * 60)
    
    if test_date is None:
        test_date = datetime.now().strftime('%Y-%m-%d')
    
    analyzer = NewsAnalyzer(debug=debug)
    
    # API 키 상태 확인
    print(f"📍 환경 설정 확인")
    print(f"Claude API 키: {'✅ 설정됨' if analyzer.api_key else '❌ 없음'}")
    print(f"Claude 클라이언트: {'✅ 활성' if analyzer.client else '❌ 비활성'}")
    print("-" * 60)
    
    results = {}
    
    for ticker in tickers:
        company_name = get_company_name(ticker)
        print(f"\n🔍 {ticker} ({company_name}) 테스트")
        print("-" * 40)
        
        # 뉴스 수집
        news_list = analyzer.fetch_ticker_news(ticker, company_name, test_date)
        
        print(f"📰 수집된 뉴스: {len(news_list)}개")
        
        if news_list:
            print("\n📋 뉴스 제목 (최대 3개):")
            for i, news in enumerate(news_list[:3]):
                title = news['title']
                if len(title) > 60:
                    title = title[:57] + "..."
                print(f"  {i+1}. {title}")
            
            # 감정 분석
            if analyzer.client:
                print("\n🤖 Claude API 분석 중...")
                try:
                    analysis = analyzer.analyze_news_sentiment(news_list, ticker, company_name)
                    print(f"  - 감정: {analysis.get('sentiment', 'N/A')}")
                    print(f"  - 신뢰도: {analysis.get('avg_confidence', 0) * 100:.1f}%")
                    print(f"  - 5일 상승 확률: {analysis.get('prob_5', 0) * 100:.1f}%")
                    
                    results[ticker] = {
                        'company_name': company_name,
                        'news_count': len(news_list),
                        'analysis': analysis
                    }
                except Exception as e:
                    print(f"  ❌ 분석 오류: {e}")
        else:
            print("  ⚠️ 수집된 뉴스가 없습니다!")
    
    return results


def run_news_strategy_optimization():
    """뉴스 전략 최적화 실행"""
    print("🔍 뉴스 전략 파라미터 최적화")
    print("=" * 60)
    
    # 학습 기간 설정 (2010~2019)
    train_start = "2010-01-01"
    train_end = "2019-12-31"
    
    # 뉴스 기반 선택기 생성
    news_selector = get_news_based_selector()
    
    # 최적 파라미터 학습
    optimal_days, optimal_threshold = news_selector.train_optimal_parameters(
        train_start, train_end
    )
    
    print(f"\n✅ 최적화 완료!")
    print(f"   - 최적 보유 기간: {optimal_days}일")
    print(f"   - 최적 매수 기준: {optimal_threshold:.2f}")
    
    return optimal_days, optimal_threshold


def run_news_backtest(test_period_days: int = 10, debug: bool = False):
    """뉴스 기반 백테스트 실행 (하이브리드 전략)"""
    # 최소 기간 검증
    if test_period_days < 10:
        print(f"⚠️ 백테스트 기간이 너무 짧습니다. 최소 10일로 설정합니다.")
        test_period_days = 10
    
    print("📰 하이브리드 백테스트 실행 (기술적 분석 50% + 뉴스 감정 분석 50%)")
    print("=" * 60)
    
    # 기본 설정으로 백테스트 엔진 생성
    config = get_backtest_config('balanced')
    engine = BacktestEngine(
        initial_capital=config.initial_capital,
        transaction_cost=config.transaction_cost,
        debug=debug  # 디버그 모드 전달
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
    
    # 테스트 기간 설정
    end_date = datetime.now()
    start_date = end_date - timedelta(days=test_period_days)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"📅 백테스트 기간: {start_str} ~ {end_str}")
    
    # 디버그 모드 설정
    if debug:
        print("🐛 디버그 모드 활성화")
        # NewsAnalyzer 인스턴스에 디버그 플래그 설정 (필요시)
    
    try:
        # 뉴스 기반 전략으로 백테스트 실행
        results = engine.run_backtest(
            start_str, 
            end_str, 
            news_analysis_enabled=True,  # 뉴스 분석 기능 활성화
            use_news_strategy=True       # 뉴스 전략 사용
        )
        
        # 결과 저장
        filename = engine.save_results("news_strategy_backtest.json")
        
        print(f"\n✅ 백테스트 완료! 결과 파일: {filename}")
        
        # 주요 결과 출력
        print(f"\n📊 백테스트 결과:")
        print(f"   - 총 수익률: {results['total_return']*100:+.2f}%")
        print(f"   - 거래 횟수: {results['total_trades']}회")
        print(f"   - 승률: {results['win_rate']*100:.1f}%")
        print(f"   - 최대 손실: {results['max_drawdown']*100:.1f}%")
        
        # 뉴스 분석 통계 출력 (거래 내역에서 추출)
        if 'trade_history' in results:
            news_trades = [t for t in results['trade_history'] 
                          if 'news_signal' in t.get('additional_info', {})]
            if news_trades:
                print(f"\n📰 뉴스 분석 통계:")
                print(f"   - 뉴스 기반 거래: {len(news_trades)}건")
                
                # 감정별 통계
                sentiments = {}
                for trade in news_trades:
                    sentiment = trade['additional_info']['news_signal'].get('sentiment', '중립')
                    sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
                
                for sentiment, count in sentiments.items():
                    print(f"   - {sentiment}: {count}건")
        
        return results
        
    except Exception as e:
        print(f"❌ 백테스트 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_strategies(test_period_days: int = 30):
    """기술적 분석 vs 하이브리드 전략 비교"""
    # 최소 기간 검증
    if test_period_days < 10:
        print(f"⚠️ 백테스트 기간이 너무 짧습니다. 최소 10일로 설정합니다.")
        test_period_days = 10
    
    print("📊 전략 비교: 기술적 분석 vs 하이브리드 (기술적 + 뉴스)")
    print("=" * 60)
    
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
    
    # 테스트 기간
    end_date = datetime.now()
    start_date = end_date - timedelta(days=test_period_days)
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"📅 백테스트 기간: {start_str} ~ {end_str} ({test_period_days}일)")
    
    results = {}
    
    # 1. 기술적 분석만
    print("\n📈 기술적 분석 전략 실행...")
    tech_engine = BacktestEngine(config.initial_capital, config.transaction_cost)
    
    try:
        tech_results = tech_engine.run_backtest(start_str, end_str, news_analysis_enabled=False)
        results['technical'] = tech_results
        print(f"✅ 기술적 분석 완료")
    except Exception as e:
        print(f"❌ 기술적 분석 오류: {e}")
        results['technical'] = None
    
    # 2. 하이브리드 전략 (기술적 + 뉴스 감정 분석)
    print("\n📰 하이브리드 전략 실행...")
    news_engine = BacktestEngine(config.initial_capital, config.transaction_cost)
    
    try:
        news_results = news_engine.run_backtest(
            start_str, end_str, 
            news_analysis_enabled=True,  # 뉴스 분석 기능 활성화
            use_news_strategy=True
        )
        results['news'] = news_results
        print(f"✅ 하이브리드 전략 완료")
    except Exception as e:
        print(f"❌ 하이브리드 전략 오류: {e}")
        results['news'] = None
    
    # 결과 비교
    print("\n" + "=" * 60)
    print("📊 전략 비교 결과")
    print("=" * 60)
    
    if results['technical'] and results['news']:
        tech_return = results['technical']['total_return'] * 100
        news_return = results['news']['total_return'] * 100
        
        print(f"\n📈 기술적 분석 전략:")
        print(f"   총 수익률: {tech_return:+.2f}%")
        print(f"   거래 횟수: {results['technical']['total_trades']}회")
        print(f"   승률: {results['technical']['win_rate']*100:.1f}%")
        
        print(f"\n📰 하이브리드 전략 (기술적 + 뉴스):")
        print(f"   총 수익률: {news_return:+.2f}%")
        print(f"   거래 횟수: {results['news']['total_trades']}회")
        print(f"   승률: {results['news']['win_rate']*100:.1f}%")
        
        print(f"\n🎯 성과 차이:")
        print(f"   수익률 차이: {news_return - tech_return:+.2f}%p")
        
        if news_return > tech_return:
            print("🏆 하이브리드 전략이 더 우수한 성과!")
        elif tech_return > news_return:
            print("🏆 기술적 분석 전략이 더 우수한 성과!")
        else:
            print("🤝 비슷한 성과!")
        
        # 비교 결과 저장
        comparison_file = f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 비교 결과가 {comparison_file}에 저장되었습니다.")
    
    return results


def main():
    """메인 함수"""
    print("📰 하이브리드 백테스트 시스템 (기술적 분석 + 뉴스 감정 분석)")
    print("=" * 60)
    
    # API 키 확인
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n⚠️  경고: Claude API 키가 설정되지 않았습니다.")
        print("   .env 파일에 ANTHROPIC_API_KEY='your-api-key'를 추가하세요.")
        print("   또는 export ANTHROPIC_API_KEY='your-api-key' 명령으로 설정하세요.\n")
    
    while True:
        print("\n실행할 작업을 선택하세요:")
        print("1) 뉴스 수집 테스트 (종목별)")
        print("2) 뉴스 전략 파라미터 최적화 (2010~2019 데이터)")
        print("3) 하이브리드 백테스트 (최근 10일)")
        print("4) 하이브리드 백테스트 (커스텀 기간, 최소 10일)")
        print("5) 전략 비교 (기술적 vs 하이브리드, 기본 30일)")
        print("6) 전략 비교 (커스텀 기간, 최소 10일)")
        print("7) 종료")
        
        try:
            choice = input("\n선택 (1-7): ").strip()
            
            if choice == '1':
                # 뉴스 수집 테스트
                print("\n테스트할 종목 코드를 입력하세요 (쉼표로 구분):")
                print("예시: 005930,035420,000660")
                tickers_input = input("종목 코드: ").strip()
                
                debug = input("디버그 모드를 사용하시겠습니까? (y/n): ").strip().lower() == 'y'
                
                if tickers_input:
                    tickers = [t.strip() for t in tickers_input.split(',')]
                    test_news_collection_for_tickers(tickers, debug=debug)
                else:
                    # 기본 테스트 종목
                    default_tickers = ['005930', '000660', '035420', '035720', '051910']
                    print(f"기본 종목으로 테스트: {', '.join(default_tickers)}")
                    test_news_collection_for_tickers(default_tickers, debug=debug)
                    
            elif choice == '2':
                run_news_strategy_optimization()
                
            elif choice == '3':
                debug = input("\n디버그 모드를 사용하시겠습니까? (y/n): ").strip().lower() == 'y'
                run_news_backtest(10, debug=debug)  # 기본 10일로 변경
                
            elif choice == '4':
                try:
                    days = int(input("\n백테스트 기간 (일, 최소 10일): ").strip())
                    if days < 10:
                        print(f"⚠️ 최소 10일 이상이어야 합니다. 10일로 설정합니다.")
                        days = 10
                    debug = input("디버그 모드를 사용하시겠습니까? (y/n): ").strip().lower() == 'y'
                    run_news_backtest(days, debug=debug)
                except ValueError:
                    print("올바른 숫자를 입력하세요.")
                    
            elif choice == '5':
                compare_strategies(30)  # 기본 30일
                
            elif choice == '6':
                try:
                    days = int(input("\n비교 백테스트 기간 (일, 최소 10일): ").strip())
                    if days < 10:
                        print(f"⚠️ 최소 10일 이상이어야 합니다. 10일로 설정합니다.")
                        days = 10
                    compare_strategies(days)
                except ValueError:
                    print("올바른 숫자를 입력하세요.")
                    
            elif choice == '7':
                print("프로그램을 종료합니다.")
                break
                
            else:
                print("잘못된 선택입니다. 1-7 중에서 선택해주세요.")
                
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
