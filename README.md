# 🤖 Hanlyang Stock - AI 강화 자동 거래 시스템

한량 주식 거래 프로젝트를 기반으로 한 **AI 강화 자동 거래 시스템**입니다.
기존의 이동평균 기반 전략에 **LightGBM 머신러닝 모델**을 통합하여 더욱 정교한 거래 결정을 내립니다.

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

### 📊 **3단계 하이브리드 전략**
- ✅ **1단계 - 기존 이동평균 전략**: 5일 최저가 + 20일 이동평균 조건
- 📊 **2단계 - 기술적 분석 필터링**: RSI, 볼린저밴드, 거래량 등 11개 지표
- 🤖 **3단계 - AI 예측 모델**: LightGBM으로 3일 후 수익률 예측
- 🎯 **최종 선정**: 전체 3000+ 종목 → 10-15개 후보 → 최대 5개 AI 선정

### 🧠 **실제 머신러닝 AI**
- **모델**: LightGBM (Gradient Boosting)
- **예측 목표**: 3일 후 2% 이상 수익률 달성 확률
- **입력 데이터**: 11개 기술적 지표 (수익률, 이동평균, RSI, 변동성 등)
- **자동 학습**: 과거 100일 데이터로 자동 훈련 및 모델 저장

### 🎯 **자동화 및 모니터링**
- ⏰ **완전 자동 실행**: crontab 기반 무인 거래 시스템 (매일 15:20)
- 📱 **실시간 로깅**: AI 예측 점수 및 선정 과정 상세 기록
- 📊 **성과 추적**: AI 예측 정확도 및 종목별 성과 모니터링
- 🛡️ **리스크 관리**: 5일 강제 매도 + AI 기반 홀드/매도 시그널

## 🏗️ 시스템 구조

```
Hanlyang_Stock/
├── strategy.py                      # 메인 AI 강화 거래 전략
├── config.yaml                     # API 키 및 설정
├── ai_price_prediction_model.txt   # 훈련된 LightGBM 모델 (자동 생성)
├── technical_strategy_data.json    # 전략 실행 데이터 (자동 생성)
├── crontab.ipynb                   # 설정 및 테스트 가이드
└── README.md                       # 프로젝트 문서
```

## 🔧 설치 및 설정

### 1️⃣ **필수 라이브러리 설치**

#### **pip 사용시:**
```bash
pip install pandas numpy requests pykrx FinanceDataReader
pip install ta scikit-learn python-dateutil pyyaml
pip install lightgbm
```

#### **uv 사용시 (권장):**
```bash
uv add pandas numpy requests pykrx FinanceDataReader
uv add ta scikit-learn python-dateutil pyyaml
uv add lightgbm
```

### 2️⃣ **API 설정**

`config.yaml` 파일을 생성하고 한국투자증권 API 정보를 입력하세요:

```yaml
hantu:
  api_key: "your_api_key_here"
  secret_key: "your_secret_key_here"
  account_id: "your_account_id_here"
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
```

### 🚀 **전략 실행**

```bash
# 즉시 실행 (15:20까지 대기 후 자동 실행)
python strategy.py

# 백그라운드 실행
nohup python strategy.py &
```

## 🤖 AI 분석 기능

### 📊 **실제 AI 모델 특징**

```python
# AI 모델 정보
# - 알고리즘: LightGBM (Light Gradient Boosting Machine)
# - 타겟: 3일 후 수익률 > 2% 달성 여부 (이진 분류)
# - 피처: 11개 기술적 지표
#   * 수익률 (1일, 3일, 5일, 10일)
#   * 이동평균 비율 (5일, 10일, 20일)
#   * RSI (14일)
#   * 거래량 비율 (5일)
#   * 변동성 (10일)
#   * 볼린저밴드 위치
```

### 🎯 **AI 예측 점수**

```python
# 실제 AI 예측 과정 (strategy.py 내부)
def get_ai_prediction_score(ticker, model):
    # 1. 최근 50일 데이터 수집
    # 2. 기술적 지표 계산
    # 3. LightGBM 모델로 예측
    # 4. 3일 후 상승 확률 반환 (0.0 ~ 1.0)
    return prediction_probability
```

### 🧠 **모델 학습 과정**

```python
# 자동 학습 프로세스
def train_ai_model():
    # 1. 과거 100일 전체 종목 데이터 수집
    # 2. 기술적 지표 생성
    # 3. 3일 후 실제 수익률로 라벨링
    # 4. LightGBM 모델 훈련 (80/20 분할)
    # 5. 모델 성능 검증 및 저장
    # 6. ai_price_prediction_model.txt 저장
```

### 🔍 **3단계 종목 선정 과정**

```python
# 실제 선정 프로세스
def selection_process():
    # 1단계: 기존 조건 필터링 (전체 → 10-15개)
    candidates = enhanced_stock_selection()
    
    # 2단계: 각 후보에 AI 점수 부여
    for ticker in candidates:
        ai_score = get_ai_prediction_score(ticker, ai_model)
    
    # 3단계: AI 점수 0.6 이상만 최종 선정 (최대 5개)
    final = ai_enhanced_final_selection(candidates)
    
    return final
```

## ⏰ 자동화 설정

### 🕐 **crontab 설정**

```bash
# crontab 편집
crontab -e

# 매일 15:10에 전략 실행 (15:20 실행을 위해 10분 전 시작)
10 15 * * 1-5 cd /path/to/Hanlyang_Stock && python strategy.py

# 매주 일요일 AI 모델 재훈련 (선택사항)
0 10 * * 0 cd /path/to/Hanlyang_Stock && python -c "from strategy import train_ai_model; train_ai_model()"
```

## 📈 성능 모니터링

### 📊 **AI 예측 로그 확인**

```python
# technical_strategy_data.json 파일에서 확인 가능
{
  "ai_predictions": {
    "005930": {
      "score": 0.753,
      "timestamp": "2024-01-15T15:20:00",
      "selected": true
    }
  },
  "performance_log": [
    {
      "timestamp": "2024-01-15T15:20:00",
      "technical_candidates": 12,
      "ai_selected": 5,
      "bought_count": 5
    }
  ]
}
```

### 🎯 **AI 성능 지표**

```bash
# 실행 시 콘솔 출력 예시:
# 🤖 AI 모델 훈련 시작...
# ✅ 모델 훈련 완료!
# 📊 테스트 정확도: 0.652
# 📊 양성 예측 비율: 0.285
# 📊 실제 양성 비율: 0.234
# 💾 모델 저장 완료: ai_price_prediction_model.txt

# 🤖 AI 최종 종목 선정 시작...
# 🎯 005930: AI 예측 점수 = 0.753
# 🎯 000660: AI 예측 점수 = 0.689
# 🎯 035420: AI 예측 점수 = 0.612
# 🏆 AI 최종 선정: 3개 종목
```

## 📁 파일 구조

### 🔧 **핵심 파일들**

| 파일명 | 설명 | 주요 기능 |
|--------|------|-----------|
| `strategy.py` | 메인 전략 실행기 | AI 모델 훈련, 종목 선정, 매매 실행 |
| `config.yaml` | 설정 파일 | API 키, 계정 정보 |
| `crontab.ipynb` | 가이드 노트북 | 사용법, 테스트, 설정 가이드 |

### 📄 **자동 생성 파일들**

- `ai_price_prediction_model.txt`: 훈련된 LightGBM 모델
- `technical_strategy_data.json`: 전략 실행 및 AI 예측 데이터
- `ai_strategy_data.json`: 레거시 호환성 (자동 마이그레이션)

## 🎯 전략 상세

### 📊 **매수 조건 (3단계 필터링)**

1. **1단계 - 기존 조건** (전체 종목 → 10-15개):
   - 최근 5일 중 오늘 종가가 최저
   - 20일 이동평균보다 현재가가 낮음
   - 거래량 상위 종목 우선

2. **2단계 - 기술적 분석** (규칙 기반 점수):
   - RSI, 이동평균 비율, 변동성 등 종합 평가
   - 기술적 점수 0.6 이상만 통과

3. **3단계 - AI 예측** (머신러닝 모델):
   - LightGBM으로 3일 후 상승 확률 예측
   - AI 점수 0.6 이상만 최종 선정
   - 최대 5개 종목 선정

### 📉 **매도 조건 (AI 강화)**

1. **기본 매도**: 3일 보유 후 시장가 매도
2. **AI 홀드 연장**: 3일차에 AI 홀드 신호 ≥ 0.75시 1일 연장
3. **AI 조기 매도**: AI 홀드 신호 ≤ 0.25시 즉시 매도
4. **안전장치**: 5일 이상 무조건 매도

## 🔒 리스크 관리

### ⚠️ **기본 안전장치**

- **분산투자**: 최대 5종목 동시 보유 (AI 선정)
- **손절선**: 5일 강제 매도 룰
- **포지션 크기**: 종목당 1주 (테스트용)
- **시장 시간**: 15:20 고정 실행 (장 마감 전)

### 📊 **AI 리스크 모니터링**

- **예측 신뢰도**: 0.6 미만 종목 자동 제외
- **모델 성능**: 정확도 50% 미만시 재훈련 권장
- **데이터 품질**: NaN 값 자동 처리 및 대체

## 🚦 시작하기

### 1️⃣ **설정 완료 후 테스트**

```bash
# 1. 의존성 설치
uv add lightgbm scikit-learn pandas ta

# 2. config.yaml 설정
# 3. 첫 실행 (모델 자동 훈련)
python strategy.py
```

### 2️⃣ **AI 모델 성능 확인**

```python
# 모델 훈련 결과 확인
# 테스트 정확도가 60% 이상이면 양호
# 55% 미만이면 더 많은 학습 데이터 필요
```

### 3️⃣ **자동화 설정**

```bash
# crontab 등록
crontab -e
# 10 15 * * 1-5 cd /path/to/Hanlyang_Stock && python strategy.py
```

## 📚 추가 자료

- **LightGBM 공식 문서**: [https://lightgbm.readthedocs.io/](https://lightgbm.readthedocs.io/)
- **기술적 분석 라이브러리**: [TA-Lib Documentation](https://ta-lib.org/)
- **한국투자증권 API**: [API Portal](https://apiportal.koreainvestment.com/)

## ⚡ 트러블슈팅

### 🔧 **자주 발생하는 문제들**

1. **LightGBM 설치 오류**
   ```bash
   # Windows의 경우
   pip install lightgbm
   
   # Mac/Linux의 경우
   uv add lightgbm
   ```

2. **AI 모델 훈련 실패**
   ```python
   # 데이터 부족 오류 시:
   # - 첫 실행에서는 정상 (과거 데이터 부족)
   # - 며칠 후 재시도 권장
   ```

3. **API 연결 오류**
   ```python
   # config.yaml 설정 재확인
   # API 키 유효성 검사
   ```

## 🆕 최신 업데이트

### v2.0 (현재)
- ✅ **실제 AI 모델 통합**: LightGBM 기반 예측 시스템
- ✅ **3단계 필터링**: 기존 → 기술적 분석 → AI 예측
- ✅ **자동 모델 훈련**: 첫 실행시 자동 학습
- ✅ **AI 성과 로깅**: 예측 점수 및 성과 추적

### v1.0 (이전)
- 기존 이동평균 기반 전략
- 규칙 기반 기술적 분석

## 📞 지원 및 기여

- **이슈 리포트**: GitHub Issues 활용
- **기능 요청**: Pull Request 환영
- **질문사항**: Discussion 활용

## ⚖️ 면책사항

이 프로젝트는 **교육 및 연구 목적**으로 제작되었습니다.
- **AI 예측의 한계**: 과거 데이터 기반 예측으로 미래 수익을 보장하지 않음
- **투자 리스크**: 실제 투자 시 발생하는 손실에 대해 책임지지 않습니다
- **모델 성능**: AI 정확도가 항상 수익으로 이어지지는 않음
- **테스트 권장**: 소액으로 충분한 테스트 후 사용을 권장합니다

## 📄 라이선스

MIT License - 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

**🚀 Happy Trading with Real AI! 📈🤖**

> *"머신러닝과 투자의 만남, 데이터 기반 스마트 거래"*
