"""
Data storage and loading utilities
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from hanlyang_stock.config.strategy_settings import get_strategy_config, StrategyConfig
from hanlyang_stock.config.backtest_settings import get_backtest_config, BacktestConfig


class StrategyDataManager:
    """전략 데이터 관리 클래스 - 실시간 계산 전환"""
    
    def __init__(self, data_file='strategy_data.json', use_config_file=True, preset='balanced', config_type='strategy'):
        self.data_file = data_file
        self.use_config_file = use_config_file
        self.preset = preset
        self.config_type = config_type  # 'strategy' 또는 'backtest'
        self.strategy_data = self._load_strategy_data()
    
    def _load_strategy_data(self) -> Dict[str, Any]:
        """전략 데이터 로드 (technical_analysis 제외)"""
        # 설정 파일 사용 시 기본값 가져오기
        if self.use_config_file:
            # 백테스트 모드 확인 (환경변수로)
            if os.environ.get('USE_BACKTEST_CONFIG') == 'true' or self.config_type == 'backtest':
                # 백테스트 설정 사용
                config = get_backtest_config(self.preset)
                base_data = config.to_dict()
                print(f"✅ backtest_settings.py에서 '{self.preset}' 설정 로드")
            else:
                # 전략 설정 사용 (기본값)
                config = get_strategy_config(self.preset)
                base_data = config.to_dict()
                print(f"✅ strategy_settings.py에서 '{self.preset}' 설정 로드")
        else:
            base_data = self._get_default_data()
        
        # strategy_data.json 로드 (런타임 데이터용)
        try:
            with open(self.data_file, 'r') as f:
                runtime_data = json.load(f)
                print(f"✅ {self.data_file} 로드 완료 (런타임 데이터)")
                
                # technical_analysis가 있으면 제거 (실시간 계산으로 전환)
                if 'technical_analysis' in runtime_data:
                    del runtime_data['technical_analysis']
                    print("   🔄 기술적 분석 데이터 제거 (실시간 계산 전환)")
                
                # 런타임 데이터로 설정값 업데이트 (holding_period, purchase_info 등)
                # 설정값은 config 파일에서, 런타임 데이터는 JSON에서
                for key in ['holding_period', 'performance_log', 'purchase_info']:
                    if key in runtime_data:
                        base_data[key] = runtime_data[key]
                
                return base_data
        except FileNotFoundError:
            print(f"⚠️ {self.data_file} 없음, 설정 파일 기반으로 새로 생성")
        except Exception as e:
            print(f"❌ {self.data_file} 로드 오류: {e}")
        
        # 런타임 데이터 초기화
        base_data.update({
            'holding_period': {},
            'performance_log': [],
            'purchase_info': {}
        })
        
        return base_data
    
    def _get_default_data(self) -> Dict[str, Any]:
        """기본값 반환 (구버전 호환용)"""
        print("📝 새 전략 데이터 생성 (레거시 모드)")
        return {
            'holding_period': {},
            'enhanced_analysis_enabled': True,
            'performance_log': [],
            'purchase_info': {},
            # 전략 설정값들 (최적화된 값)
            'stop_loss_enabled': True,
            'stop_loss_rate': -0.05,              # -5%
            'hybrid_strategy_enabled': True,       # 하이브리드 전략 활성화
            'pyramiding_enabled': True,            # 피라미딩 활성화
            'min_market_cap': 50_000_000_000,     # 500억으로 완화
            'enhanced_min_trade_amount': 100_000_000,  # 1억으로 완화
            'max_selections': 5,                   # 5개 선정
            'position_size_ratio': 0.9,            # 90% 투자
            'safety_cash_amount': 1_000_000,       # 안전자금 100만원
            'pyramiding_max_position': 0.3,
            'pyramiding_investment_ratio': 0.5,
            'pyramiding_max_resets': 2,
            'pyramiding_reset_threshold': 0.80,
            'news_weight': 0.3,
            'technical_weight': 0.7,
            'min_combined_score': 0.55,
            'debug_news': True,
            'trend_strength_filter_enabled': True,  # 추세 강도 필터 활성화
            'trend_strength_weights': {            # 추세 강도 가중치
                'sar': 0.35,
                'rsi': 0.25,
                'support': 0.20,
                'volume': 0.10,
                'candle': 0.10,
                'min_score': 0.6
            },
            # 투자 금액 설정 (50% 증액)
            'investment_amounts': {
                '최고신뢰': 1_200_000,    # 120만원
                '고신뢰': 900_000,        # 90만원
                '중신뢰': 600_000,        # 60만원
                '저신뢰': 400_000         # 40만원
            },
            # 백테스트 파라미터 (최적화된 값)
            'backtest_params': {
                'min_close_days': 7,
                'ma_period': 20,
                'min_trade_amount': 100_000_000,  # 1억
                'min_technical_score': 0.5,       # 0.5로 완화
                'max_positions': 7                # 7개로 증가
            }
        }
    
    def get_data(self) -> Dict[str, Any]:
        """전략 데이터 반환"""
        return self.strategy_data
    
    def update_data(self, key: str, value: Any) -> None:
        """전략 데이터 업데이트"""
        self.strategy_data[key] = value
    
    def get_holding_period(self, ticker: str) -> int:
        """종목별 보유 기간 반환"""
        return self.strategy_data.get('holding_period', {}).get(ticker, 0)
    
    def set_holding_period(self, ticker: str, days: int) -> None:
        """종목별 보유 기간 설정"""
        if 'holding_period' not in self.strategy_data:
            self.strategy_data['holding_period'] = {}
        self.strategy_data['holding_period'][ticker] = days
    
    def increment_holding_period(self, ticker: str) -> int:
        """종목별 보유 기간 1일 증가"""
        current_days = self.get_holding_period(ticker)
        new_days = current_days + 1
        self.set_holding_period(ticker, new_days)
        return new_days
    
    def reset_holding_period(self, ticker: str) -> None:
        """종목별 보유 기간 초기화"""
        if 'holding_period' in self.strategy_data:
            self.strategy_data['holding_period'][ticker] = 0
    
    def add_performance_log(self, log_entry: Dict[str, Any]) -> None:
        """성과 로그 추가"""
        if 'performance_log' not in self.strategy_data:
            self.strategy_data['performance_log'] = []
        
        # 타임스탬프 추가
        log_entry['timestamp'] = datetime.now().isoformat()
        self.strategy_data['performance_log'].append(log_entry)
    
    def get_purchase_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """매수 정보 반환"""
        return self.strategy_data.get('purchase_info', {}).get(ticker)
    
    def set_purchase_info(self, ticker: str, info: Dict[str, Any]) -> None:
        """매수 정보 설정"""
        if 'purchase_info' not in self.strategy_data:
            self.strategy_data['purchase_info'] = {}
        self.strategy_data['purchase_info'][ticker] = info
    
    def remove_purchase_info(self, ticker: str) -> None:
        """매수 정보 삭제"""
        if 'purchase_info' in self.strategy_data and ticker in self.strategy_data['purchase_info']:
            del self.strategy_data['purchase_info'][ticker]
    
    def save(self, filename: Optional[str] = None) -> None:
        """전략 데이터 저장 (런타임 데이터만)"""
        if filename is None:
            filename = self.data_file
        
        # technical_analysis가 있으면 제거 (실시간 계산으로 전환)
        if 'technical_analysis' in self.strategy_data:
            del self.strategy_data['technical_analysis']
        
        # 런타임 데이터만 추출 (설정값 제외)
        runtime_keys = ['holding_period', 'performance_log', 'purchase_info']
        runtime_data = {k: v for k, v in self.strategy_data.items() if k in runtime_keys}
        
        # 직렬화 가능한 형태로 변환
        serializable_data = self._convert_to_serializable(runtime_data)
        
        try:
            with open(filename, 'w') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            print(f"💾 런타임 데이터 저장 완료: {filename}")
            print(f"   (설정값은 strategy_settings.py에서 관리)")
        except Exception as e:
            print(f"❌ 런타임 데이터 저장 오류: {e}")
    
    def _convert_to_serializable(self, obj: Any) -> Any:
        """numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
        if isinstance(obj, dict):
            return {key: self._convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj


# 전역 데이터 매니저 (싱글톤 패턴 - preset별로 관리)
_data_manager_instances = {}

def get_data_manager(use_config_file: bool = True, preset: str = None) -> StrategyDataManager:
    """
    데이터 매니저 인스턴스 반환 (preset별 싱글톤)
    
    Args:
        use_config_file: strategy_settings.py 사용 여부
        preset: 설정 프리셋 ('conservative', 'balanced', 'aggressive', 'small_capital')
                None이면 환경변수 확인
    """
    global _data_manager_instances
    
    # preset이 없으면 환경변수 확인
    if preset is None:
        preset = os.environ.get('STRATEGY_PRESET', 'balanced')
    
    # preset별로 별도의 인스턴스 관리
    key = f"{preset}_{use_config_file}"
    
    if key not in _data_manager_instances:
        _data_manager_instances[key] = StrategyDataManager(
            use_config_file=use_config_file, 
            preset=preset
        )
        print(f"✅ 새로운 데이터 매니저 인스턴스 생성: preset='{preset}'")
    
    return _data_manager_instances[key]

def load_strategy_data() -> Dict[str, Any]:
    """전략 데이터 로드"""
    manager = get_data_manager()
    return manager.get_data()

def save_strategy_data(data: Optional[Dict[str, Any]] = None) -> None:
    """전략 데이터 저장"""
    manager = get_data_manager()
    if data is not None:
        manager.strategy_data = data
    manager.save()
