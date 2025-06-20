"""
Strategy configuration settings
전략 실행 설정 관리
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class TechnicalParameters:
    """기술적 분석 파라미터"""
    min_close_days: int = 7              # 최저점 확인 기간
    ma_period: int = 20                  # 이동평균 기간
    min_technical_score: float = 0.6     # 최소 기술적 점수 (0.65에서 0.6으로 하향)
    rsi_hold_upper: int = 70             # RSI 상한선
    rsi_hold_lower: int = 30             # RSI 하한선
    volume_surge_threshold: float = 2.0   # 거래량 급증 기준
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'min_close_days': self.min_close_days,
            'ma_period': self.ma_period,
            'min_technical_score': self.min_technical_score,
            'rsi_hold_upper': self.rsi_hold_upper,
            'rsi_hold_lower': self.rsi_hold_lower,
            'volume_surge_threshold': self.volume_surge_threshold
        }


@dataclass
class HybridStrategyParameters:
    """하이브리드 전략 파라미터"""
    enabled: bool = True
    news_weight: float = 0.3            # 뉴스 가중치 (0~1)
    technical_weight: float = 0.7       # 기술적 분석 가중치 (0~1)
    min_combined_score: float = 0.7     # 최소 종합 점수
    block_negative_news: bool = True    # 부정적 뉴스 차단
    debug_news: bool = True             # 뉴스 디버깅 모드
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'enabled': self.enabled,
            'news_weight': self.news_weight,
            'technical_weight': self.technical_weight,
            'min_combined_score': self.min_combined_score,
            'block_negative_news': self.block_negative_news,
            'debug_news': self.debug_news
        }


@dataclass
class PyramidingParameters:
    """피라미딩 전략 파라미터"""
    enabled: bool = True
    min_score: float = 0.75              # 피라미딩 최소 점수
    max_position: float = 0.3            # 종목당 최대 포지션 비율
    investment_ratio: float = 0.5        # 추가 매수 비율
    reset_threshold: float = 0.80        # 보유기간 리셋 기준
    max_resets: int = 2                  # 최대 리셋 횟수
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'enabled': self.enabled,
            'min_score': self.min_score,
            'max_position': self.max_position,
            'investment_ratio': self.investment_ratio,
            'reset_threshold': self.reset_threshold,
            'max_resets': self.max_resets
        }


@dataclass
class QualityFilterParameters:
    """품질 필터 파라미터"""
    enabled: bool = True
    min_market_cap: float = 50_000_000_000       # 최소 시가총액 (500억) - 하향 조정
    min_trade_amount: float = 300_000_000        # 최소 거래대금 (3억) - 백테스트와 일치
    trend_strength_filter_enabled: bool = True   # 추세 강도 필터 사용
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'enabled': self.enabled,
            'min_market_cap': self.min_market_cap,
            'min_trade_amount': self.min_trade_amount,
            'trend_strength_filter_enabled': self.trend_strength_filter_enabled
        }


@dataclass
class StrategyConfig:
    """전략 실행 설정 클래스"""
    
    # 기본 설정
    max_selections: int = 5                       # 최대 선정 종목 수 - 백테스트 기본값과 일치
    stop_loss_enabled: bool = True                # 손실 제한 사용
    stop_loss_rate: float = -0.05                 # 손실 제한 비율 (-5%)
    
    # 최대 보유 기간
    max_holding_days: Dict[str, int] = field(default_factory=lambda: {
        'basic': 5,      # 기본 전략
        'hybrid': 10     # 하이브리드 전략
    })
    
    # 안정성 설정
    stability_focused_target: bool = True
    profit_threshold: float = 0.005               # 최소 수익률 (0.5%)
    volatility_control: bool = True               # 변동성 제어
    crash_protection: bool = True                 # 급락 방지
    
    # 데이터 검증
    enhanced_data_validation: bool = True         # 강화된 데이터 검증
    enhanced_analysis_enabled: bool = True        # 강화된 분석 사용
    advanced_hold_signal: bool = True             # 고급 홀드 시그널
    
    # 전략 파라미터들
    technical_params: TechnicalParameters = field(default_factory=TechnicalParameters)
    hybrid_strategy: HybridStrategyParameters = field(default_factory=HybridStrategyParameters)
    pyramiding: PyramidingParameters = field(default_factory=PyramidingParameters)
    quality_filter: QualityFilterParameters = field(default_factory=QualityFilterParameters)
    
    def to_dict(self) -> Dict[str, Any]:
        """설정을 딕셔너리로 변환 (storage.py 호환)"""
        return {
            'max_selections': self.max_selections,
            'stop_loss_enabled': self.stop_loss_enabled,
            'stop_loss_rate': self.stop_loss_rate,
            'max_holding_days': self.max_holding_days,
            'stability_focused_target': self.stability_focused_target,
            'profit_threshold': self.profit_threshold,
            'volatility_control': self.volatility_control,
            'crash_protection': self.crash_protection,
            'enhanced_data_validation': self.enhanced_data_validation,
            'enhanced_analysis_enabled': self.enhanced_analysis_enabled,
            'advanced_hold_signal': self.advanced_hold_signal,
            
            # 기술적 파라미터
            'technical_params': self.technical_params.to_dict(),
            'min_technical_score': self.technical_params.min_technical_score,  # 호환성
            'rsi_hold_upper': self.technical_params.rsi_hold_upper,
            'rsi_hold_lower': self.technical_params.rsi_hold_lower,
            'volume_surge_threshold': self.technical_params.volume_surge_threshold,
            
            # 하이브리드 전략
            'hybrid_strategy_enabled': self.hybrid_strategy.enabled,
            'news_weight': self.hybrid_strategy.news_weight,
            'technical_weight': self.hybrid_strategy.technical_weight,
            'min_combined_score': self.hybrid_strategy.min_combined_score,
            'block_negative_news': self.hybrid_strategy.block_negative_news,
            'debug_news': self.hybrid_strategy.debug_news,
            
            # 피라미딩
            'pyramiding_enabled': self.pyramiding.enabled,
            'pyramiding_min_score': self.pyramiding.min_score,
            'pyramiding_max_position': self.pyramiding.max_position,
            'pyramiding_investment_ratio': self.pyramiding.investment_ratio,
            'pyramiding_reset_threshold': self.pyramiding.reset_threshold,
            'pyramiding_max_resets': self.pyramiding.max_resets,
            
            # 품질 필터
            'quality_filter_enabled': self.quality_filter.enabled,
            'min_market_cap': self.quality_filter.min_market_cap,
            'enhanced_min_trade_amount': self.quality_filter.min_trade_amount,
            'trend_strength_filter_enabled': self.quality_filter.trend_strength_filter_enabled,
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'StrategyConfig':
        """딕셔너리에서 설정 생성 (기존 JSON 호환)"""
        # 기술적 파라미터 추출
        technical_params = TechnicalParameters(
            min_close_days=config_dict.get('technical_params', {}).get('min_close_days', 7),
            ma_period=config_dict.get('technical_params', {}).get('ma_period', 20),
            min_technical_score=config_dict.get('min_technical_score', 0.6),
            rsi_hold_upper=config_dict.get('rsi_hold_upper', 70),
            rsi_hold_lower=config_dict.get('rsi_hold_lower', 30),
            volume_surge_threshold=config_dict.get('volume_surge_threshold', 2.0)
        )
        
        # 하이브리드 전략 파라미터 추출
        hybrid_strategy = HybridStrategyParameters(
            enabled=config_dict.get('hybrid_strategy_enabled', True),
            news_weight=config_dict.get('news_weight', 0.3),
            technical_weight=config_dict.get('technical_weight', 0.7),
            min_combined_score=config_dict.get('min_combined_score', 0.7),
            block_negative_news=config_dict.get('block_negative_news', True),
            debug_news=config_dict.get('debug_news', True)
        )
        
        # 피라미딩 파라미터 추출
        pyramiding = PyramidingParameters(
            enabled=config_dict.get('pyramiding_enabled', True),
            min_score=config_dict.get('pyramiding_min_score', 0.75),
            max_position=config_dict.get('pyramiding_max_position', 0.3),
            investment_ratio=config_dict.get('pyramiding_investment_ratio', 0.5),
            reset_threshold=config_dict.get('pyramiding_reset_threshold', 0.80),
            max_resets=config_dict.get('pyramiding_max_resets', 2)
        )
        
        # 품질 필터 파라미터 추출
        quality_filter = QualityFilterParameters(
            enabled=config_dict.get('quality_filter_enabled', True),
            min_market_cap=config_dict.get('min_market_cap', 100_000_000_000),
            min_trade_amount=config_dict.get('enhanced_min_trade_amount', 300_000_000),  # 3억원으로 수정
            trend_strength_filter_enabled=config_dict.get('trend_strength_filter_enabled', True)
        )
        
        return cls(
            max_selections=config_dict.get('max_selections', 3),
            stop_loss_enabled=config_dict.get('stop_loss_enabled', True),
            stop_loss_rate=config_dict.get('stop_loss_rate', -0.05),
            max_holding_days=config_dict.get('max_holding_days', {'basic': 5, 'hybrid': 10}),
            stability_focused_target=config_dict.get('stability_focused_target', True),
            profit_threshold=config_dict.get('profit_threshold', 0.005),
            volatility_control=config_dict.get('volatility_control', True),
            crash_protection=config_dict.get('crash_protection', True),
            enhanced_data_validation=config_dict.get('enhanced_data_validation', True),
            enhanced_analysis_enabled=config_dict.get('enhanced_analysis_enabled', True),
            advanced_hold_signal=config_dict.get('advanced_hold_signal', True),
            technical_params=technical_params,
            hybrid_strategy=hybrid_strategy,
            pyramiding=pyramiding,
            quality_filter=quality_filter
        )


# 사전 정의된 설정들
CONSERVATIVE_STRATEGY = StrategyConfig(
    max_selections=3,  # 백테스트 CONSERVATIVE max_positions와 일치
    stop_loss_rate=-0.03,
    max_holding_days={'basic': 3, 'hybrid': 5},
    profit_threshold=0.01,  # 1% 이상 수익
    technical_params=TechnicalParameters(
        min_technical_score=0.75,
        min_close_days=7  # 백테스트와 일치 (기본값 7일)
    ),
    quality_filter=QualityFilterParameters(
        min_market_cap=500_000_000_000,  # 5000억
        min_trade_amount=500_000_000     # 5억 - 백테스트 CONSERVATIVE와 일치
    ),
    pyramiding=PyramidingParameters(
        enabled=False  # 보수적: 피라미딩 비활성화
    )
)

AGGRESSIVE_STRATEGY = StrategyConfig(
    max_selections=7,  # 백테스트 AGGRESSIVE max_positions와 일치
    stop_loss_rate=-0.08,
    max_holding_days={'basic': 7, 'hybrid': 14},
    profit_threshold=0.003,  # 0.3% 이상 수익
    technical_params=TechnicalParameters(
        min_technical_score=0.55,  # 백테스트 AGGRESSIVE와 일치
        min_close_days=7  # 백테스트와 일치 (기본값 7일)
    ),
    quality_filter=QualityFilterParameters(
        min_market_cap=50_000_000_000,   # 500억
        min_trade_amount=100_000_000     # 1억 - 백테스트 AGGRESSIVE와 일치
    ),
    pyramiding=PyramidingParameters(
        enabled=True,
        max_position=0.5  # 공격적: 50%까지 허용
    )
)

BALANCED_STRATEGY = StrategyConfig()  # 기본값 사용

# 설정 프리셋
STRATEGY_PRESETS = {
    'conservative': CONSERVATIVE_STRATEGY,
    'balanced': BALANCED_STRATEGY,
    'aggressive': AGGRESSIVE_STRATEGY
}


def get_strategy_config(preset: str = 'balanced') -> StrategyConfig:
    """
    전략 설정 반환
    
    Args:
        preset: 설정 프리셋 ('conservative', 'balanced', 'aggressive')
        
    Returns:
        StrategyConfig: 전략 설정
    """
    if preset in STRATEGY_PRESETS:
        return STRATEGY_PRESETS[preset]
    else:
        print(f"⚠️ 알 수 없는 설정 프리셋: {preset}, 기본 설정 사용")
        return BALANCED_STRATEGY


def create_custom_strategy(**kwargs) -> StrategyConfig:
    """
    커스텀 전략 설정 생성
    
    Args:
        **kwargs: 설정 파라미터들
        
    Returns:
        StrategyConfig: 커스텀 전략 설정
    """
    # 기본 설정에서 시작
    base_config = BALANCED_STRATEGY.to_dict()
    
    # 커스텀 파라미터로 업데이트
    base_config.update(kwargs)
    
    return StrategyConfig.from_dict(base_config)


# 사용 예시
if __name__ == "__main__":
    # 기본 설정
    config = get_strategy_config('balanced')
    print("기본 설정:", config.to_dict())
    
    # 보수적 설정
    conservative = get_strategy_config('conservative')
    print("\n보수적 설정:", conservative.to_dict())
    
    # 공격적 설정
    aggressive = get_strategy_config('aggressive')
    print("\n공격적 설정:", aggressive.to_dict())
    
    # 커스텀 설정
    custom = create_custom_strategy(
        max_selections=4,
        stop_loss_rate=-0.06,
        news_weight=0.6,
        technical_weight=0.4
    )
    print("\n커스텀 설정:", custom.to_dict())
