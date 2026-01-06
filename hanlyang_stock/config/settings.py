"""
Configuration management for Hanlyang Stock Strategy
"""

import os
import yaml
import warnings
from dotenv import load_dotenv
from HantuStock import HantuStock

# .env 파일 로드
load_dotenv()

# 경고 메시지 무시
warnings.filterwarnings('ignore')

class Config:
    """설정 관리 클래스"""
    
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self._load_config()
        self._setup_hantustock()
        self._setup_slack()
    
    def _load_config(self):
        """config.yaml 파일 로드"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError:
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
        except Exception as e:
            raise Exception(f"설정 파일 로드 오류: {e}")
    
    def _setup_hantustock(self):
        """HantuStock 객체 초기화"""
        try:
            # trade_mode 확인 (환경변수 우선)
            trade_mode = os.environ.get('TRADE_MODE', self.config.get('trade_mode', 'simulation'))
            
            # 모드에 따른 계좌 정보 선택
            if trade_mode not in ['simulation', 'real']:
                print(f"⚠️ 알 수 없는 trade_mode: {trade_mode}. 기본값(simulation) 사용")
                trade_mode = 'simulation'
            
            account_config = self.config[trade_mode]
            
            # HantuStock 객체 생성
            self.ht = HantuStock(
                api_key=account_config['api_key'],
                secret_key=account_config['secret_key'],
                account_id=account_config['account_id'],
                mode=trade_mode  # 모드 전달
            )
            
            print(f"✅ HantuStock 초기화 완료 (모드: {trade_mode})")
            
        except KeyError as e:
            raise KeyError(f"설정 파일에서 필수 키를 찾을 수 없습니다: {e}")
        except Exception as e:
            raise Exception(f"HantuStock 초기화 오류: {e}")
    
    def _setup_slack(self):
        """슬랙 설정"""
        # 슬랙 설정 (환경변수에서 로드)
        self.SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN')
        self.HANLYANG_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

        if not self.SLACK_API_TOKEN:
            print("⚠️ SLACK_API_TOKEN 환경변수가 설정되지 않았습니다.")
            return

        try:
            # 슬랙 활성화
            self.ht.activate_slack(self.SLACK_API_TOKEN)
            print("✅ 슬랙 연동 완료")
        except Exception as e:
            print(f"⚠️ 슬랙 연동 실패: {e}")
    
    def get_hantustock(self):
        """HantuStock 객체 반환"""
        return self.ht
    
    def get_slack_config(self):
        """슬랙 설정 반환"""
        return {
            'token': self.SLACK_API_TOKEN,
            'channel_id': self.HANLYANG_CHANNEL_ID
        }


# 전역 설정 객체 (싱글톤 패턴)
_config_instance = None

def get_config(config_path='config.yaml'):
    """설정 객체 반환 (싱글톤)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance

def get_hantustock():
    """HantuStock 객체 반환"""
    config = get_config()
    return config.get_hantustock()

def get_slack_config():
    """슬랙 설정 반환"""
    config = get_config()
    return config.get_slack_config()
