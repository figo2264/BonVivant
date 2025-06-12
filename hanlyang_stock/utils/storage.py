"""
Data storage and loading utilities
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional


class StrategyDataManager:
    """전략 데이터 관리 클래스"""
    
    def __init__(self, data_file='technical_strategy_data.json'):
        self.data_file = data_file
        self.strategy_data = self._load_strategy_data()
    
    def _load_strategy_data(self) -> Dict[str, Any]:
        """전략 데이터 로드 (호환성 유지)"""
        # 1. 최신 technical_strategy_data.json 시도
        try:
            with open('technical_strategy_data.json', 'r') as f:
                data = json.load(f)
                print("✅ technical_strategy_data.json 로드 완료")
                return data
        except FileNotFoundError:
            print("⚠️ technical_strategy_data.json 없음, 이전 파일 확인 중...")
        except Exception as e:
            print(f"❌ technical_strategy_data.json 로드 오류: {e}")
        
        # 2. 기존 ai_strategy_data.json과 호환성 유지
        try:
            with open('ai_strategy_data.json', 'r') as f:
                old_data = json.load(f)
                print("✅ ai_strategy_data.json에서 마이그레이션")
                return {
                    'holding_period': old_data.get('holding_period', {}),
                    'technical_analysis': old_data.get('ai_predictions', {}),
                    'enhanced_analysis_enabled': old_data.get('ai_enabled', True),
                    'performance_log': old_data.get('performance_log', [])
                }
        except FileNotFoundError:
            print("⚠️ ai_strategy_data.json 없음, legacy 파일 확인 중...")
        except Exception as e:
            print(f"❌ ai_strategy_data.json 로드 오류: {e}")
        
        # 3. legacy strategy_data.json과 호환성 유지
        try:
            with open('strategy_data.json', 'r') as f:
                old_data = json.load(f)
                print("✅ legacy strategy_data.json에서 마이그레이션")
                return {
                    'holding_period': old_data.get('holding_period', {}),
                    'technical_analysis': {},
                    'enhanced_analysis_enabled': True,
                    'performance_log': []
                }
        except FileNotFoundError:
            print("⚠️ legacy strategy_data.json 없음")
        except Exception as e:
            print(f"❌ legacy strategy_data.json 로드 오류: {e}")
        
        # 4. 기본값 반환
        print("📝 새 전략 데이터 생성")
        return {
            'holding_period': {},
            'technical_analysis': {},
            'enhanced_analysis_enabled': True,
            'performance_log': [],
            'ai_predictions': {},
            'purchase_info': {}
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
