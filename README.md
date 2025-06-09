# 🤖 Hanlyang Stock - AI 강화 자동 거래 시스템

한량 주식 거래 프로젝트를 기반으로 한 **AI 강화 자동 거래 시스템**입니다.
기존의 이동평균 기반 전략에 머신러닝 기술적 분석을 통합하여 더욱 정교한 거래 결정을 내립니다.

## 📋 목차
- [주요 특징](#주요-특징)
- [시스템 구조](#시스템-구조)
- [설치 및 설정](#설치-및-설정)
- [사용 방법](#사용-방법)
- [AI 분석 기능](#ai-분석-기능)
- [자동화 설정](#자동화-설정)
- [성능 모니터링](#성능-모니터링)
- [파일 구조](#파일-구조)
- [라이선스](#라이선스)

## 🚀 주요 특징

### 📊 **기존 전략 + AI 강화**
- ✅ **기존 이동평균 전략 유지**: 5일 최저가 + 20일 이동평균 조건
- 🤖 **AI 기술적 분석 추가**: RSI, MACD, 볼린저밴드, 스토캐스틱
- 📈 **동적 보유기간 조정**: AI 예측에 따른 스마트 매도 타이밍
- 🛡️ **리스크 관리 강화**: 변동성 및 최대낙폭 기반 위험 평가

### 🎯 **자동화 및 모니터링**
- ⏰ **완전 자동 실행**: crontab 기반 무인 거래 시스템
- 📱 **실시간 알림**: Slack 연동으로 거래 결과 즉시 확인
- 📊 **성과 추적**: AI 예측 정확도 및 수익률 모니터링
- 📈 **백테스팅**: 과거 데이터 기반 전략 성능 검증

## 🏗️ 시스템 구조

```
Hanlyang_Stock/
├── HantuStock.py              # 핵심 거래 클래스 (AI 분석 기능 포함)
├── strategy.py                # AI 강화 거래 전략 실행
├── ai_performance_check.py    # 주간 성능 분석 및 리포트
├── config.yaml               # API 키 및 설정
├── crontab.ipynb             # Jupyter 노트북 가이드
└── README.md                 # 프로젝트 문서
```

## 🔧 설치 및 설정

### 1️⃣ **필수 라이브러리 설치**

```bash
pip install pandas numpy requests pykrx FinanceDataReader
pip install ta scikit-learn python-dateutil pyyaml
pip install slack-sdk
```

### 2️⃣ **API 설정**

`config.yaml` 파일을 생성하고 한국투자증권 API 정보를 입력하세요:

```yaml
hantu:
  api_key: "your_api_key_here"
  secret_key: "your_secret_key_here"
  account_id: "your_account_id_here"

# 선택사항: Slack 알림
slack:
  token: "your_slack_token_here"
  channel: "#trading-alerts"
```

## 📖 사용 방법

### 🎮 **기본 사용법**

```python
from HantuStock import HantuStock
import yaml

# 설정 로드
with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# 시스템 초기화
ht = HantuStock(
    api_key=config['hantu']['api_key'],
    secret_key=config['hantu']['secret_key'],
    account_id=config['hantu']['account_id']
)

# AI 분석 실행
analysis = ht.get_ai_enhanced_analysis('005930')  # 삼성전자
print(f"추천: {analysis['recommendation']}")
print(f"신뢰도: {analysis['confidence']:.2f}")
```

### 🚀 **전략 실행**

```bash
# 즉시 실행
python strategy.py

# 백그라운드 실행
nohup python strategy.py &
```

## 🤖 AI 분석 기능

### 📊 **기술적 지표 분석**

```python
# 종목별 상세 기술적 분석
tech_data = ht.get_technical_indicators('005930', n=100)

# 주요 지표들
# - 이동평균선 (5, 10, 20, 60일)
# - RSI (14일)
# - MACD 및 시그널
# - 볼린저 밴드
# - 스토캐스틱
# - 거래량 지표
```

### 🎯 **AI 시장 신호**

```python
# AI 기반 매매 신호 생성
signal = ht.get_ai_market_signal('005930')

print(f"신호: {signal['signal']}")        # STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
print(f"신뢰도: {signal['confidence']}")   # 0.0 ~ 1.0
print(f"근거: {signal['reasons']}")        # 분석 근거 리스트
```

### ⚠️ **리스크 평가**

```python
# 종목별 위험도 분석
risk = ht.get_ai_risk_assessment('005930')

print(f"리스크 레벨: {risk['risk_level']}")     # VERY_LOW/LOW/MEDIUM/HIGH/VERY_HIGH
print(f"변동성: {risk['volatility']:.1%}")      # 연환산 변동성
print(f"최대낙폭: {risk['max_drawdown']:.1%}")  # 최대 하락률
```

### 🔍 **종합 분석**

```python
# 모든 분석을 통합한 최종 추천
analysis = ht.get_ai_enhanced_analysis('005930')

print(f"최종 추천: {analysis['recommendation']}")  # BUY/SELL/HOLD
print(f"종합 점수: {analysis['final_score']:.3f}")  # -1.0 ~ +1.0
```

## ⏰ 자동화 설정

### 🕐 **crontab 설정**

```bash
# crontab 편집
crontab -e

# 매일 오전 8:30 전략 실행
30 8 * * 1-5 /usr/bin/python3 /path/to/strategy.py

# 매주 월요일 오전 9시 성능 체크
0 9 * * 1 /usr/bin/python3 /path/to/ai_performance_check.py
```

### 📱 **Slack 알림 설정**

```python
# HantuStock 클래스에서 자동으로 Slack 알림 전송
ht.post_message("🤖 AI 전략 실행 완료!")
```

## 📈 성능 모니터링

### 📊 **주간 성능 리포트**

```bash
# 수동 실행
python ai_performance_check.py

# 출력 예시:
# 📊 AI 전략 성능 분석 시작...
# 📈 전체 통계:
#   AI 예측 기록: 45개
#   거래 로그: 12개
#   현재 보유 종목: 8개
# 🤖 AI 예측 분석:
#   평균 AI 점수: 0.650
#   고신뢰도 예측 (≥0.7): 18개 (40.0%)
```

### 📋 **실시간 포트폴리오 분석**

```python
# 현재 보유 종목의 AI 재분석
holdings = ht.get_holding_stock()
for ticker, quantity in holdings.items():
    analysis = ht.get_ai_enhanced_analysis(ticker)
    print(f"{ticker}: {analysis['recommendation']} (점수: {analysis['final_score']:+.3f})")
```

### 🔄 **백테스팅**

```python
# 간단한 전략 성과 검증
def simple_backtest(ticker, days=30):
    # 과거 데이터로 전략 효과 측정
    # 실제 수익률과 AI 예측 정확도 비교
    pass
```

## 📁 파일 구조

### 🔧 **핵심 파일들**

| 파일명 | 설명 | 주요 기능 |
|--------|------|-----------|
| `HantuStock.py` | 메인 클래스 | API 통신, AI 분석, 거래 실행 |
| `strategy.py` | 전략 실행기 | 매매 로직, 종목 선정, 포지션 관리 |
| `ai_performance_check.py` | 성능 분석기 | 주간 리포트, 성과 추적 |
| `config.yaml` | 설정 파일 | API 키, 계정 정보 |
| `crontab.ipynb` | 가이드 노트북 | 사용법, 테스트, 모니터링 |

### 📄 **생성되는 데이터 파일들**

- `ai_strategy_data.json`: AI 전략 실행 데이터
- `weekly_ai_report.json`: 주간 성과 리포트
- `*.pkl`: 훈련된 AI 모델 파일들

## 🎯 전략 상세

### 📊 **매수 조건 (AI 강화)**

1. **기존 조건**:
   - 최근 5일 중 오늘 종가가 최저
   - 20일 이동평균보다 현재가가 낮음

2. **AI 추가 조건**:
   - AI 신뢰도 점수 ≥ 0.6
   - 리스크 레벨이 VERY_HIGH가 아님
   - 거래량 상위 종목 우선 선정

### 📉 **매도 조건 (동적 조정)**

1. **기본 매도**: 3일 보유 후 종가 매도
2. **AI 연장**: 강한 상승 신호 시 1일 추가 보유
3. **AI 조기매도**: 강한 하락 신호 시 즉시 매도
4. **안전장치**: 5일 이상 무조건 매도

## 🔒 리스크 관리

### ⚠️ **기본 안전장치**

- **분산투자**: 최대 10종목 동시 보유
- **손절선**: 5일 강제 매도 룰
- **포지션 크기**: 균등 분할 투자
- **시장 시간**: 장중에만 거래 실행

### 📊 **AI 리스크 모니터링**

- **변동성 체크**: 고변동성 종목 회피
- **최대낙폭 분석**: 과도한 하락 이력 종목 제외
- **거래량 검증**: 유동성 부족 종목 배제

## 🚦 시작하기

### 1️⃣ **설정 완료 후 테스트**

```bash
# Jupyter 노트북으로 기능 테스트
jupyter notebook crontab.ipynb
```

### 2️⃣ **소액 실전 테스트**

```python
# 소액으로 시작 (예: 종목당 1주)
# strategy.py에서 수량 조정 후 실행
python strategy.py
```

### 3️⃣ **자동화 설정**

```bash
# crontab 등록 후 모니터링
crontab -e
# 위의 crontab 설정 추가
```

## 📚 추가 자료

- **한국투자증권 API 문서**: [링크](https://apiportal.koreainvestment.com/)
- **기술적 분석 라이브러리**: [TA-Lib Documentation](https://ta-lib.org/)
- **백테스팅 가이드**: `crontab.ipynb` 노트북 참조

## ⚡ 트러블슈팅

### 🔧 **자주 발생하는 문제들**

1. **API 연결 오류**
   ```python
   # config.yaml 설정 재확인
   # API 키 유효성 검사
   ```

2. **모듈 import 오류**
   ```bash
   pip install --upgrade ta scikit-learn
   ```

3. **데이터 없음 오류**
   ```python
   # 첫 실행 시 정상 - 거래 후 데이터 생성됨
   ```

## 📞 지원 및 기여

- **이슈 리포트**: GitHub Issues 활용
- **기능 요청**: Pull Request 환영
- **질문사항**: Discussion 활용

## ⚖️ 면책사항

이 프로젝트는 **교육 및 연구 목적**으로 제작되었습니다.
- 실제 투자 시 발생하는 손실에 대해 책임지지 않습니다
- 투자는 본인의 판단과 책임하에 진행하세요
- 소액으로 충분한 테스트 후 사용을 권장합니다

## 📄 라이선스

MIT License - 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

**🚀 Happy Trading with AI! 📈**

> *"기술과 투자의 만남, 더 스마트한 거래를 위하여"*
