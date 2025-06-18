"""
Data storage and loading utilities
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional


class StrategyDataManager:
    """전략 데이터 관리 클래스 - 실시간 계산 전환"""
    
    def __init__(self, data_file='strategy_data.json'):
        self.data_file = data_file
        self.strategy_data = self._load_strategy_data()
    
    def _load_strategy_data(self) -> Dict[str, Any]:
        """전략 데이터 로드 (technical_analysis 제외)"""
        # strategy_data.json 로드 (technical_strategy_data.json 사용 안 함)
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                print(f"✅ {self.data_file} 로드 완료")
                
                # technical_analysis가 있으면 제거 (실시간 계산으로 전환)
                if 'technical_analysis' in data:
                    del data['technical_analysis']
                    print("   🔄 기술적 분석 데이터 제거 (실시간 계산 전환)")
                
                return data
        except FileNotFoundError:
            print(f"⚠️ {self.data_file} 없음, 새로 생성")
        except Exception as e:
            print(f"❌ {self.data_file} 로드 오류: {e}")
        
        # 기본값 반환
        print("📝 새 전략 데이터 생성")
        return {
            'holding_period': {},
            'enhanced_analysis_enabled': True,
            'performance_log': [],
            'purchase_info': {},
            # 전략 설정값들
            'stop_loss_enabled': True,
            'hybrid_strategy_enabled': False,
            'pyramiding_enabled': False,
            'min_market_cap': 2_000_000_000_000,  # 2천억
            'enhanced_min_trade_amount': 300_000_000,  # 3억
            'max_selections': 3,
            'pyramiding_max_position': 0.3,
            'pyramiding_investment_ratio': 0.5,
            'pyramiding_max_resets': 2,
            'pyramiding_reset_threshold': 0.80,
            'news_weight': 0.5,
            'technical_weight': 0.5,
            'min_combined_score': 0.7,
            'debug_news': True,
            # 백테스트 파라미터
            'backtest_params': {
                'min_close_days': 7,
                'ma_period': 20,
                'min_trade_amount': 300_000_000,
                'min_technical_score': 0.7,
                'max_positions': 5
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
        """전략 데이터 저장"""
        if filename is None:
            filename = self.data_file
        
        # technical_analysis가 있으면 제거 (실시간 계산으로 전환)
        if 'technical_analysis' in self.strategy_data:
            del self.strategy_data['technical_analysis']
        
        # 직렬화 가능한 형태로 변환
        serializable_data = self._convert_to_serializable(self.strategy_data)
        
        try:
            with open(filename, 'w') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            print(f"💾 전략 데이터 저장 완료: {filename}")
        except Exception as e:
            print(f"❌ 전략 데이터 저장 오류: {e}")
    
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


# 전역 데이터 매니저 (싱글톤 패턴)
_data_manager_instance = None

def get_data_manager() -> StrategyDataManager:
    """데이터 매니저 인스턴스 반환 (싱글톤)"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = StrategyDataManager()
    return _data_manager_instance

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
