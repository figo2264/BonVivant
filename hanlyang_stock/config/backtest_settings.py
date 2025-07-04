"""
Backtest configuration settings
백테스트 설정 관리
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class OptimizedParameters:
    """최적화된 백테스트 파라미터"""
    min_close_days: int = 7              # 최저점 확인 기간
    ma_period: int = 20                  # 이동평균 기간
    min_trade_amount: float = 100_000_000        # 최소 거래대금 (최적화: 1억원)
    min_technical_score: float = 0.5     # 최소 기술적 점수 (0.6에서 0.5로 추가 하향)
    max_positions: int = 7               # 최대 보유 종목 수 (수익률 극대화)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'min_close_days': self.min_close_days,
            'ma_period': self.ma_period,
            'min_trade_amount': self.min_trade_amount,
            'min_technical_score': self.min_technical_score,
            'max_positions': self.max_positions
        }


@dataclass
class BacktestConfig:
    """백테스트 설정 클래스"""
    
    # 기본 설정
    initial_capital: float = 10_000_000      # 초기 자본 (1000만원)
    transaction_cost: float = 0.003          # 거래 비용 (0.3%)
    max_positions: int = 7                   # 최대 보유 종목 수 (수익률 극대화)
    
    # 리스크 관리
    stop_loss_rate: float = -0.03            # 손실 제한 (-5%)
    max_holding_days: int = 5                # 최대 보유 일수
    position_size_ratio: float = 0.9         # 현금 대비 투자 비율 (수익률 극대화)
    safety_cash_amount: float = 1_000_000    # 안전 자금 (100만원으로 감소)
    
    # 기술적 분석 설정
    min_technical_score: float = 0.5         # 최소 기술적 점수 (0.5로 추가 하향)
    enhanced_analysis: bool = True           # 강화된 기술적 분석 사용
    
    # 종목 선정 파라미터 (최적화 결과 반영)
    min_close_days: int = 7                  # 최저점 확인 기간 (최적화: 7일)
    ma_period: int = 20                      # 이동평균 기간 (최적화: 20일)
    min_trade_amount: float = 100_000_000    # 최소 거래대금 (최적화: 1억원)
    
    # 투자 금액 설정 (기술적 점수별)
    investment_amounts: Dict[str, float] = None
    
    # 최적화된 파라미터 (선택적)
    optimized_params: Optional[OptimizedParameters] = None
    
    # 추세 강도 필터 설정
    trend_strength_filter_enabled: bool = True  # 추세 강도 필터 사용
    trend_strength_weights: Dict[str, float] = None  # 추세 강도 가중치
    
    # 기술적 점수 계산 가중치
    technical_score_weights: Dict[str, float] = None  # 기술적 점수 가중치
    
    def __post_init__(self):
        if self.investment_amounts is None:
            self.investment_amounts = {
                '최고신뢰': 1_200_000,    # 120만원 (점수 0.8+) - 증가
                '고신뢰': 900_000,        # 90만원 (점수 0.7-0.8) - 증가
                '중신뢰': 600_000,        # 60만원 (점수 0.65-0.7) - 증가
                '저신뢰': 400_000         # 40만원 (점수 0.65 미만) - 증가
            }
        
        if self.trend_strength_weights is None:
            self.trend_strength_weights = {
                'sar': 0.35,      # 파라볼릭 SAR (가장 중요)
                'rsi': 0.25,      # RSI 반등 신호
                'support': 0.20,  # 지지선 근처
                'volume': 0.10,   # 거래량 급증
                'candle': 0.10,   # 양봉 크기
                'min_score': 0.6  # 최소 통과 점수 (기본값)
            }
        
        if self.technical_score_weights is None:
            self.technical_score_weights = {
                'trend': 0.25,           # 추세 (25%)
                'momentum': 0.20,        # 모멘텀 (20%)
                'oversold': 0.20,        # 과매도 (20%)
                'parabolic_sar': 0.20,   # 파라볼릭 SAR (20%)
                'volume': 0.10,          # 거래량 (10%)
                'volatility': 0.05       # 변동성 (5%)
            }
        
        # 최적화된 파라미터가 없으면 기본값으로 생성
        if self.optimized_params is None:
            self.optimized_params = OptimizedParameters(
                min_close_days=self.min_close_days,
                ma_period=self.ma_period,
                min_trade_amount=self.min_trade_amount,
                min_technical_score=self.min_technical_score,
                max_positions=self.max_positions
            )
    
    def get_investment_amount(self, technical_score: float) -> tuple[float, str]:
        """
        기술적 점수에 따른 투자 금액 반환
        
        Args:
            technical_score: 기술적 분석 점수 (0~1)
            
        Returns:
            tuple: (투자금액, 신뢰도레벨)
        """
        if technical_score >= 0.80:
            return self.investment_amounts['최고신뢰'], '최고신뢰'
        elif technical_score >= 0.70:
            return self.investment_amounts['고신뢰'], '고신뢰'
        elif technical_score >= 0.65:
            return self.investment_amounts['중신뢰'], '중신뢰'
        else:
            return self.investment_amounts['저신뢰'], '저신뢰'
    
    def get_optimal_params(self) -> Dict[str, Any]:
        """최적화된 파라미터를 딕셔너리로 반환"""
        return self.optimized_params.to_dict()
    
    def update_optimal_params(self, **kwargs) -> None:
        """최적화 파라미터 업데이트"""
        params_dict = self.optimized_params.to_dict()
        params_dict.update(kwargs)
        self.optimized_params = OptimizedParameters(**params_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환"""
        return {
            'initial_capital': self.initial_capital,
            'transaction_cost': self.transaction_cost,
            'max_positions': self.max_positions,
            'stop_loss_rate': self.stop_loss_rate,
            'max_holding_days': self.max_holding_days,
            'position_size_ratio': self.position_size_ratio,
            'safety_cash_amount': self.safety_cash_amount,
            'min_technical_score': self.min_technical_score,
            'enhanced_analysis': self.enhanced_analysis,
            'investment_amounts': self.investment_amounts,
            'min_close_days': self.min_close_days,
            'ma_period': self.ma_period,
            'min_trade_amount': self.min_trade_amount,
            'trend_strength_filter_enabled': self.trend_strength_filter_enabled,
            'trend_strength_weights': self.trend_strength_weights,
            'technical_score_weights': self.technical_score_weights,
            'optimized_params': self.optimized_params.to_dict() if self.optimized_params else None
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BacktestConfig':
        """딕셔너리에서 설정 생성"""
        # 이전 버전 호환성을 위한 처리
        if 'ai_enabled' in config_dict:
            config_dict.pop('ai_enabled')
        if 'ai_retrain_frequency' in config_dict:
            config_dict.pop('ai_retrain_frequency')
        if 'min_ai_confidence' in config_dict:
            config_dict['min_technical_score'] = config_dict.pop('min_ai_confidence')
        if 'ai_lookback_days' in config_dict:
            config_dict.pop('ai_lookback_days')
        
        # optimized_params 처리
        if 'optimized_params' in config_dict and config_dict['optimized_params']:
            opt_params = config_dict.pop('optimized_params')
            config_dict['optimized_params'] = OptimizedParameters(**opt_params)
            
        return cls(**config_dict)


# 사전 정의된 설정들
CONSERVATIVE_CONFIG = BacktestConfig(
    initial_capital=10_000_000,
    transaction_cost=0.003,
    max_positions=3,                    # 보수적: 3개 종목만
    stop_loss_rate=-0.03,              # 보수적: -3% 손실제한
    max_holding_days=3,                 # 보수적: 3일 최대 보유
    position_size_ratio=0.6,            # 보수적: 60%만 투자
    min_technical_score=0.75,           # 보수적: 높은 점수만
    min_close_days=7,                   # 최적화 결과 반영
    ma_period=20,                       # 최적화 결과 반영
    min_trade_amount=500_000_000,       # 보수적: 5억원
    investment_amounts={
        '최고신뢰': 600_000,
        '고신뢰': 500_000,
        '중신뢰': 400_000,
        '저신뢰': 300_000
    },
    trend_strength_filter_enabled=True,
    trend_strength_weights={
        'sar': 0.40,      # SAR 중시 (안정성)
        'rsi': 0.20,      # RSI
        'support': 0.25,  # 지지선 중시 (리스크 관리)
        'volume': 0.10,   # 거래량
        'candle': 0.05,   # 양봉
        'min_score': 0.70 # 높은 기준 (보수적)
    },
    technical_score_weights={
        'trend': 0.30,           # 추세 중시 (30%)
        'momentum': 0.15,        # 모멘텀 축소 (15%)
        'oversold': 0.15,        # 과매도 축소 (15%)
        'parabolic_sar': 0.25,   # SAR 중시 (25%)
        'volume': 0.10,          # 거래량 (10%)
        'volatility': 0.05       # 변동성 (5%)
    },
    optimized_params=OptimizedParameters(
        min_close_days=7,
        ma_period=20,
        min_trade_amount=500_000_000,
        min_technical_score=0.75,
        max_positions=3
    )
)

AGGRESSIVE_CONFIG = BacktestConfig(
    initial_capital=10_000_000,
    transaction_cost=0.003,
    max_positions=7,                    # 공격적: 7개 종목
    stop_loss_rate=-0.08,              # 공격적: -8% 손실제한
    max_holding_days=7,                 # 공격적: 7일 최대 보유
    position_size_ratio=0.9,            # 공격적: 90% 투자
    min_technical_score=0.55,           # 공격적: 낮은 점수도 허용
    min_close_days=7,                   # 최적화 결과 반영
    ma_period=20,                       # 최적화 결과 반영
    min_trade_amount=100_000_000,       # 공격적: 1억원
    investment_amounts={
        '최고신뢰': 1_200_000,
        '고신뢰': 1_000_000,
        '중신뢰': 800_000,
        '저신뢰': 600_000
    },
    trend_strength_filter_enabled=True,
    trend_strength_weights={
        'sar': 0.25,      # SAR (기본)
        'rsi': 0.20,      # RSI (기본)
        'support': 0.15,  # 지지선
        'volume': 0.25,   # 거래량 중시 (모멘텀)
        'candle': 0.15,   # 양봉 중시 (당일 강세)
        'min_score': 0.50 # 낮은 기준 (공격적)
    },
    technical_score_weights={
        'trend': 0.20,           # 추세 축소 (20%)
        'momentum': 0.25,        # 모멘텀 중시 (25%)
        'oversold': 0.25,        # 과매도 중시 (25%)
        'parabolic_sar': 0.15,   # SAR 축소 (15%)
        'volume': 0.10,          # 거래량 (10%)
        'volatility': 0.05       # 변동성 (5%)
    },
    optimized_params=OptimizedParameters(
        min_close_days=7,
        ma_period=20,
        min_trade_amount=100_000_000,
        min_technical_score=0.55,
        max_positions=7
    )
)

BALANCED_CONFIG = BacktestConfig(
    # 기본값 사용 (균형잡힌 설정)
    max_positions=7,                     # 수익률 극대화
    position_size_ratio=0.9,             # 수익률 극대화
    safety_cash_amount=1_000_000,        # 안전 자금 감소
    min_technical_score=0.5,             # 기술점수 기준 완화
    trend_strength_filter_enabled=True,
    trend_strength_weights={
        'sar': 0.35,      # SAR (중요)
        'rsi': 0.25,      # RSI (중요)
        'support': 0.20,  # 지지선 (보조)
        'volume': 0.10,   # 거래량 (보조)
        'candle': 0.10,   # 양봉 (보조)
        'min_score': 0.50 # 균형잡힌 기준
    },
    technical_score_weights={
        'trend': 0.25,           # 추세 (25%)
        'momentum': 0.20,        # 모멘텀 (20%)
        'oversold': 0.20,        # 과매도 (20%)
        'parabolic_sar': 0.20,   # 파라볼릭 SAR (20%)
        'volume': 0.10,          # 거래량 (10%)
        'volatility': 0.05       # 변동성 (5%)
    },
    optimized_params=OptimizedParameters(
        max_positions=7,                 # OptimizedParameters도 7로
        min_technical_score=0.5          # 기술점수 기준도 동일하게
    )
)

# 소액 투자자를 위한 설정 (100만원)
SMALL_CAPITAL_CONFIG = BacktestConfig(
    initial_capital=1_000_000,           # 100만원
    transaction_cost=0.003,
    max_positions=5,                     # 적은 자본이므로 5개로 제한
    stop_loss_rate=-0.03,                # 손실 제한 -3%
    max_holding_days=5,
    position_size_ratio=0.8,             # 80% 투자 (20만원은 예비)
    safety_cash_amount=100_000,          # 안전 자금 10만원
    min_technical_score=0.5,             # 중간 수준의 기술점수
    min_close_days=7,
    ma_period=20,
    min_trade_amount=100_000_000,        # 유동성 있는 종목만
    investment_amounts={
        '최고신뢰': 180_000,             # 18만원 (점수 0.8+)
        '고신뢰': 160_000,               # 16만원 (점수 0.7-0.8)
        '중신뢰': 120_000,               # 12만원 (점수 0.65-0.7)
        '저신뢰': 100_000                # 10만원 (점수 0.65 미만)
    },
    trend_strength_filter_enabled=True,   # 추세 강도 필터 활성화
    trend_strength_weights={
        'sar': 0.35,      # SAR (중요)
        'rsi': 0.25,      # RSI (중요)
        'support': 0.20,  # 지지선 (보조)
        'volume': 0.10,   # 거래량 (보조)
        'candle': 0.10,   # 양봉 (보조)
        'min_score': 0.50 # 소액 투자용 완화된 기준 (기존 0.60에서 하향)
    },
    technical_score_weights={
        'trend': 0.25,           # 추세 (25%)
        'momentum': 0.20,        # 모멘텀 (20%)
        'oversold': 0.20,        # 과매도 (20%)
        'parabolic_sar': 0.20,   # 파라볼릭 SAR (20%)
        'volume': 0.10,          # 거래량 (10%)
        'volatility': 0.05       # 변동성 (5%)
    },
    optimized_params=OptimizedParameters(
        min_close_days=7,
        ma_period=20,
        min_trade_amount=100_000_000,
        min_technical_score=0.5,
        max_positions=5
    )
)

# 설정 프리셋
CONFIG_PRESETS = {
    'conservative': CONSERVATIVE_CONFIG,
    'balanced': BALANCED_CONFIG,
    'aggressive': AGGRESSIVE_CONFIG,
    'small_capital': SMALL_CAPITAL_CONFIG
}


def get_backtest_config(preset: str = 'balanced') -> BacktestConfig:
    """
    백테스트 설정 반환
    
    Args:
        preset: 설정 프리셋 ('conservative', 'balanced', 'aggressive', 'small_capital')
        
    Returns:
        BacktestConfig: 백테스트 설정
    """
    if preset in CONFIG_PRESETS:
        return CONFIG_PRESETS[preset]
    else:
        print(f"⚠️ 알 수 없는 설정 프리셋: {preset}, 기본 설정 사용")
        return BALANCED_CONFIG


def create_custom_config(**kwargs) -> BacktestConfig:
    """
    커스텀 백테스트 설정 생성
    
    Args:
        **kwargs: 설정 파라미터들
        
    Returns:
        BacktestConfig: 커스텀 백테스트 설정
    """
    # 기본 설정에서 시작
    base_config = BALANCED_CONFIG.to_dict()
    
    # optimized_params 처리
    if 'optimized_params' in kwargs:
        opt_params = kwargs.pop('optimized_params')
        if isinstance(opt_params, dict):
            kwargs['optimized_params'] = OptimizedParameters(**opt_params)
    
    # 커스텀 파라미터로 업데이트
    base_config.update(kwargs)
    
    # 이전 버전 호환성
    if 'ai_enabled' in base_config:
        base_config.pop('ai_enabled')
    if 'min_ai_confidence' in base_config:
        base_config['min_technical_score'] = base_config.pop('min_ai_confidence')
    
    return BacktestConfig.from_dict(base_config)


def get_default_optimal_params() -> Dict[str, Any]:
    """기본 최적화 파라미터 반환"""
    return OptimizedParameters().to_dict()


# 사용 예시
if __name__ == "__main__":
    # 기본 설정
    config = get_backtest_config('balanced')
    print("기본 설정:", config.to_dict())
    print("최적화 파라미터:", config.get_optimal_params())
    
    # 보수적 설정
    conservative = get_backtest_config('conservative')
    print("\n보수적 설정:", conservative.to_dict())
    print("최적화 파라미터:", conservative.get_optimal_params())
    
    # 커스텀 설정
    custom = create_custom_config(
        initial_capital=20_000_000,
        max_positions=10,
        stop_loss_rate=-0.06
    )
    print("\n커스텀 설정:", custom.to_dict())
    
    # 최적화 파라미터 업데이트
    custom.update_optimal_params(min_close_days=10, ma_period=30)
    print("업데이트된 최적화 파라미터:", custom.get_optimal_params())
