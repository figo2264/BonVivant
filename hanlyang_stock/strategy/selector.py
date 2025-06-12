"""
Stock selection strategies
Enhanced with complete AI features from backtest_engine
"""

import json
from datetime import datetime
from typing import List, Dict, Any
from ..data.fetcher import get_data_fetcher
from ..analysis.technical import get_technical_score, validate_ticker_data
from ..analysis.ai_model import get_ai_manager
from ..utils.storage import get_data_manager


class StockSelector:
    """종목 선정 클래스 - 백테스트 엔진의 AI 향상 기능 완전 적용"""
    
    def __init__(self):
        self.data_fetcher = get_data_fetcher()
        self.ai_manager = get_ai_manager()
        self.data_manager = get_data_manager()
    
    def enhanced_stock_selection(self, current_date=None) -> List[Dict[str, Any]]:
        """
        기술적 분석 강화 종목 선정 (백테스트 엔진 로직 재현)
        
        Args:
            current_date: 현재 날짜 (백테스트 시 사용)
            
        Returns:
            List[Dict]: 선정된 종목 정보 리스트
        """
        try:
            print(f"📊 {'기술적 분석 강화 종목 분석 시작...' if not current_date else f'{current_date} 종목 선정 시작...'}")
            
            # 현재 날짜의 시장 데이터 조회
            if current_date:
                market_data = self.data_fetcher.get_market_data_by_date_range(current_date, n_days_before=25)
            else:
                market_data = self.data_fetcher.get_past_data_total(n=25)
            
            if market_data.empty:
                print(f"⚠️ 시장 데이터 없음")
                return []
            
            # 5일 종가 최저값, 20일 이동평균 계산
            market_data = market_data.sort_values(['ticker', 'timestamp'])
            market_data['5d_min_close'] = market_data.groupby('ticker')['close'].rolling(5, min_periods=1).min().reset_index(0, drop=True)
            market_data['20d_ma'] = market_data.groupby('ticker')['close'].rolling(20, min_periods=1).mean().reset_index(0, drop=True)
            
            # 현재 날짜 데이터만 추출
            if current_date:
                today_data = market_data[market_data['timestamp'] == current_date].copy()
            else:
                today_data = market_data[market_data['timestamp'] == market_data['timestamp'].max()].copy()
                
            if today_data.empty:
                print(f"⚠️ 당일 데이터 없음")
                return []
            
            # 기존 조건에 맞는 종목 찾기
            traditional_candidates = today_data[
                (today_data['5d_min_close'] == today_data['close']) &
                (today_data['20d_ma'] > today_data['close']) &
                (today_data['trade_amount'] > 1_000_000_000)  # 최소 거래대금 10억
            ].copy()
            
            print(f"📊 전통적 조건 후보: {len(traditional_candidates)}개")
            
            if traditional_candidates.empty:
                return []
            
            # 기술적 분석 점수 추가 분석
            enhanced_candidates = []
            
            for _, row in traditional_candidates.iterrows():
                ticker = row['ticker']
                
                # 🔧 데이터 검증 강화 (백테스트 엔진 기능 적용)
                if not validate_ticker_data(ticker):
                    print(f"   ❌ {ticker}: 데이터 검증 실패 - 스킵")
                    continue
                
                # 기술적 분석 점수 계산
                technical_score = get_technical_score(ticker)
                
                # 결합 점수: 기존 거래량 가중치 + 기술적 분석 보정
                technical_multiplier = 0.5 + technical_score  # 0.5 ~ 1.5 배수
                combined_score = row['trade_amount'] * technical_multiplier
                
                enhanced_candidates.append({
                    'ticker': ticker,
                    'trade_amount': row['trade_amount'],
                    'technical_score': technical_score,
                    'combined_score': combined_score,
                    'current_price': row['close']
                })
            
            # 기술적 분석 강화 점수로 정렬
            enhanced_candidates.sort(key=lambda x: x['combined_score'], reverse=True)
            
            # 기술적 점수가 0.6 이상인 종목만 1차 선정
            selected_candidates = []
            for candidate in enhanced_candidates[:15]:  # 상위 15개 확인
                if candidate['technical_score'] >= 0.6 and len(selected_candidates) < 10:
                    selected_candidates.append(candidate)
            
            print(f"🎯 기술적 분석 1차 선정: {len(selected_candidates)}개 종목")
            
            return selected_candidates
            
        except Exception as e:
            print(f"❌ 종목 선정 오류: {e}")
            return []

    def ai_enhanced_final_selection(self, entry_tickers: List[Dict[str, Any]], current_date=None) -> List[str]:
        """
        AI를 활용한 최종 종목 선정 (백테스트 엔진 강화 버전 완전 적용)
        
        Args:
            entry_tickers: 기술적 분석으로 선정된 종목들
            current_date: 현재 날짜 (백테스트 시)
            
        Returns:
            List[str]: AI 분석으로 최종 선정된 종목들
        """
        print("🤖 AI 최종 종목 선정 시작...")

        # AI 모델 로드
        ai_model = self.ai_manager.load_ai_model()
        if ai_model is None:
            print("❌ AI 모델을 사용할 수 없어 빈 리스트 반환")
            return []

        # 모델 품질 확인
        model_quality_score = getattr(ai_model, 'model_quality_score', 60)
        try:
            with open('ai_model_metadata.json', 'r') as f:
                metadata = json.load(f)
                model_quality_score = metadata.get('model_quality_score', 60)
        except:
            pass
            
        print(f"📊 모델 품질 점수: {model_quality_score:.1f}/100")
        
        # 모델 품질이 너무 낮으면 거래 중단
        if model_quality_score < 40:
            print("❌ 모델 품질이 너무 낮아 거래를 중단합니다.")
            return []
        
        ai_scored_tickers = []
        
        # 각 종목에 대해 AI 예측 점수 계산
        for candidate in entry_tickers:
            ticker = candidate['ticker']
            ai_score = self.ai_manager.get_ai_prediction_score(ticker, current_date, ai_model)
            ai_scored_tickers.append({
                'ticker': ticker,
                'ai_score': ai_score,
                'technical_score': candidate['technical_score'],
                'current_price': candidate['current_price'],
                'trade_amount': candidate['trade_amount'],
                'combined_score': candidate['combined_score']
            })
            
            print(f"🎯 {ticker}: AI 예측 점수 = {ai_score:.3f}")
        
        # AI 점수로 정렬
        ai_scored_tickers.sort(key=lambda x: x['ai_score'], reverse=True)
        
        # 신뢰도 기준 강화: 모델 품질에 따라 동적 조정 (백테스트 엔진과 동일)
        if model_quality_score >= 65:
            min_score_threshold = 0.65  # 우수한 모델: 0.65 이상 (기존 0.55에서 상향)
            max_selections = 5
        elif model_quality_score >= 50:
            min_score_threshold = 0.70  # 양호한 모델: 0.70 이상 (기존 0.60에서 상향)
            max_selections = 4
        else:
            min_score_threshold = 0.75  # 보통 모델: 0.75 이상 (기존 0.65에서 상향)
            max_selections = 3

        print(f"📏 신뢰도 기준: {min_score_threshold:.2f} 이상 (최대 {max_selections}개)")

        # 기준을 만족하는 종목만 선정
        final_selection = []
        high_confidence_count = 0
        medium_confidence_count = 0
        hybrid_count = 0  # 하이브리드 선정 카운트
        
        for item in ai_scored_tickers:
            if len(final_selection) >= max_selections:
                break
                
            # 고신뢰: AI 점수만으로 선정
            if item['ai_score'] >= min_score_threshold:
                final_selection.append(item)
                
                # 신뢰도 분류 (현실적 기준)
                if item['ai_score'] >= 0.65:
                    high_confidence_count += 1
                elif item['ai_score'] >= 0.55:
                    medium_confidence_count += 1
                    
            # 하이브리드 접근: AI 점수가 중간 수준이면 기술적 분석과 결합
            elif item['ai_score'] >= (min_score_threshold - 0.10) and len(final_selection) < max_selections:
                # AI 점수와 기술적 점수의 가중 평균
                combined_score = (item['ai_score'] * 0.7) + (item['technical_score'] * 0.3)
                
                # 결합 점수가 기준을 만족하면 선정
                if combined_score >= (min_score_threshold - 0.05):
                    final_selection.append(item)
                    hybrid_count += 1
                    print(f"🔄 {item['ticker']}: 하이브리드 선정 (AI: {item['ai_score']:.3f}, 기술: {item['technical_score']:.3f}, 결합: {combined_score:.3f})")

        # 선정 결과 출력
        if len(final_selection) == 0:
            print("❌ AI 신뢰도 기준을 만족하는 종목이 없습니다.")
            print("⚠️ 오늘은 매수를 건너뛰겠습니다.")
            
            # 가장 높은 점수라도 출력
            if ai_scored_tickers:
                best_score = ai_scored_tickers[0]['ai_score']
                print(f"📊 최고 점수: {best_score:.3f} (기준: {min_score_threshold:.2f})")
        else:
            print(f"🏆 AI 최종 선정: {len(final_selection)}개 종목")
            print(f"   🟢 고신뢰(0.65+): {high_confidence_count}개")
            print(f"   🟡 중신뢰(0.55+): {medium_confidence_count}개")
            print(f"   🔄 하이브리드: {hybrid_count}개")

        # AI 예측 결과 저장 (모든 종목의 점수 저장)
        strategy_data = self.data_manager.get_data()
        if 'ai_predictions' not in strategy_data:
            strategy_data['ai_predictions'] = {}
            
        for item in ai_scored_tickers:
            # 강화된 신뢰도 레벨 분류 (executor.py와 일관성 맞춤)
            if item['ai_score'] >= 0.80:
                confidence_level = "최고신뢰"
            elif item['ai_score'] >= 0.70:
                confidence_level = "고신뢰"
            elif item['ai_score'] >= 0.65:
                confidence_level = "중신뢰"
            else:
                confidence_level = "저신뢰"
                
            strategy_data['ai_predictions'][item['ticker']] = {
                'score': item['ai_score'],
                'confidence_level': confidence_level,
                'timestamp': datetime.now().isoformat(),
                'selected': item in final_selection,
                'model_quality': model_quality_score
            }

        # 기술적 분석 정보도 저장
        if 'technical_analysis' not in strategy_data:
            strategy_data['technical_analysis'] = {}
        
        for item in ai_scored_tickers:
            strategy_data['technical_analysis'][item['ticker']] = {
                'score': item['technical_score'],
                'timestamp': datetime.now().isoformat(),
                'traditional_rank': int(item['trade_amount'])
            }

        return final_selection

    def select_stocks_for_buy(self, current_date=None) -> List[str]:
        """
        매수용 종목 선정 (전체 워크플로우) - 데이터 검증 강화
        
        Args:
            current_date: 현재 날짜 (백테스트 시)
            
        Returns:
            List[str]: 최종 선정된 종목 코드 리스트
        """
        try:
            # 1단계: 기술적 분석 기반 1차 선정 (데이터 검증 포함)
            entry_candidates = self.enhanced_stock_selection(current_date)
            
            if not entry_candidates:
                print("📊 기술적 분석에서 선정된 종목이 없습니다.")
                return []
            
            # 2단계: AI 기반 최종 선정
            strategy_data = self.data_manager.get_data()
            ai_enabled = strategy_data.get('enhanced_analysis_enabled', True)
            
            if ai_enabled:
                final_tickers = self.ai_enhanced_final_selection(entry_candidates, current_date)
                print(f"🤖 AI 선정 결과: {len(final_tickers)}개")
            else:
                final_tickers = [item['ticker'] for item in entry_candidates[:5]]  # AI 없으면 상위 5개
                print(f"📊 AI 모델 없음 - 기술적 분석 상위 5개 선정")
            
            return final_tickers
            
        except Exception as e:
            print(f"❌ 종목 선정 전체 워크플로우 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_selection_summary(self) -> Dict[str, Any]:
        """
        선정 과정 요약 정보 반환
        
        Returns:
            dict: 선정 과정 요약
        """
        strategy_data = self.data_manager.get_data()
        
        summary = {
            'technical_analysis_count': len(strategy_data.get('technical_analysis', {})),
            'ai_predictions_count': len(strategy_data.get('ai_predictions', {})),
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'selected_count': 0
        }
        
        # AI 예측 통계
        for prediction in strategy_data.get('ai_predictions', {}).values():
            if prediction.get('selected', False):
                summary['selected_count'] += 1
            
            confidence = prediction.get('confidence_level', '')
            if confidence == '고신뢰':
                summary['high_confidence_count'] += 1
            elif confidence == '중신뢰':
                summary['medium_confidence_count'] += 1
        
        return summary


# 전역 스톡 셀렉터 (싱글톤 패턴)
_selector_instance = None

def get_stock_selector() -> StockSelector:
    """스톡 셀렉터 인스턴스 반환 (싱글톤)"""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = StockSelector()
    return _selector_instance

# 편의 함수들
def enhanced_stock_selection(current_date=None) -> List[Dict[str, Any]]:
    """기술적 분석 기반 종목 선정"""
    selector = get_stock_selector()
    return selector.enhanced_stock_selection(current_date)

def ai_enhanced_final_selection(entry_tickers: List[Dict[str, Any]], current_date=None) -> List[str]:
    """AI 기반 최종 종목 선정"""
    selector = get_stock_selector()
    return selector.ai_enhanced_final_selection(entry_tickers, current_date)

def select_stocks_for_buy(current_date=None) -> List[str]:
    """매수용 종목 선정 (전체 워크플로우)"""
    selector = get_stock_selector()
    return selector.select_stocks_for_buy(current_date)
