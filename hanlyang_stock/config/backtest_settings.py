"""
Backtest configuration settings
백테스트 설정 관리
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class BacktestConfig:
    """백테스트 설정 클래스"""
    
    # 기본 설정
    initial_capital: float = 10_000_000      # 초기 자본 (1000만원)
    transaction_cost: float = 0.003          # 거래 비용 (0.3%)
    max_positions: int = 5                   # 최대 보유 종목 수
    
    # 리스크 관리
    stop_loss_rate: float = -0.05            # 손실 제한 (-5%)
    max_holding_days: int = 5                # 최대 보유 일수
    position_size_ratio: float = 0.8         # 현금 대비 투자 비율
    safety_cash_amount: float = 2_000_000    # 안전 자금 (200만원)
    
    # 기술적 분석 설정
    min_technical_score: float = 0.70        # 최소 기술적 점수 (최적화 결과: 0.7)
    enhanced_analysis: bool = True           # 강화된 기술적 분석 사용
    
    # 종목 선정 파라미터 (최적화 결과 반영)
    min_close_days: int = 7                  # 최저점 확인 기간 (최적화: 7일)
    ma_period: int = 20                      # 이동평균 기간 (최적화: 20일)
    min_trade_amount: float = 300_000_000    # 최소 거래대금 (최적화: 3억원)
    
    # 투자 금액 설정 (기술적 점수별)
    investment_amounts: Dict[str, float] = None
    
    def __post_init__(self):
        if self.investment_amounts is None:
            self.investment_amounts = {
                '최고신뢰': 800_000,    # 80만원 (점수 0.8+)
                '고신뢰': 600_000,      # 60만원 (점수 0.7-0.8)
                '중신뢰': 400_000,      # 40만원 (점수 0.65-0.7)
                '저신뢰': 300_000       # 30만원 (점수 0.65 미만)
            }
    
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
            'min_trade_amount': self.min_trade_amount
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
    }
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
    }
)

BALANCED_CONFIG = BacktestConfig(
    # 기본값 사용 (균형잡힌 설정)
)

# 설정 프리셋
CONFIG_PRESETS = {
    'conservative': CONSERVATIVE_CONFIG,
    'balanced': BALANCED_CONFIG,
    'aggressive': AGGRESSIVE_CONFIG
}


def get_backtest_config(preset: str = 'balanced') -> BacktestConfig:
    """
    백테스트 설정 반환
    
    Args:
        preset: 설정 프리셋 ('conservative', 'balanced', 'aggressive')
        
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
    
    # 커스텀 파라미터로 업데이트
    base_config.update(kwargs)
    
    # 이전 버전 호환성
    if 'ai_enabled' in base_config:
        base_config.pop('ai_enabled')
    if 'min_ai_confidence' in base_config:
        base_config['min_technical_score'] = base_config.pop('min_ai_confidence')
    
    return BacktestConfig.from_dict(base_config)


# 사용 예시
if __name__ == "__main__":
    # 기본 설정
    config = get_backtest_config('balanced')
    print("기본 설정:", config.to_dict())
    
    # 보수적 설정
    conservative = get_backtest_config('conservative')
    print("보수적 설정:", conservative.to_dict())
    
    # 커스텀 설정
    custom = create_custom_config(
        initial_capital=20_000_000,
        max_positions=10,
        stop_loss_rate=-0.06
    )
    print("커스텀 설정:", custom.to_dict())
