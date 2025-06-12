# 📊 백테스팅 엔진 사용 가이드

## 🎯 개요

이 백테스팅 엔진은 `strategy.py`의 기술적 분석 기반 전략을 과거 데이터로 시뮬레이션하여 성과를 검증하는 도구입니다.

## 🚀 주요 기능

### ✅ 구현된 기능
- **종목 선정**: strategy.py의 `enhanced_stock_selection()` 로직 재현
- **매수/매도**: 3-5일 보유 전략 시뮬레이션
- **기술적 분석**: RSI, 이동평균, 볼린저밴드 등 지표 계산
- **포트폴리오 관리**: 가상 계좌 및 현금 관리
- **성과 분석**: 수익률, MDD, 샤프비율 등 지표 계산
- **거래 비용**: 수수료 및 세금 반영

### 📊 데이터 소스
- **개별 종목**: FinanceDataReader (10년+ 일봉 데이터)
- **전체 시장**: pykrx (한국거래소 공식 데이터)
- **기술적 지표**: ta 라이브러리

## 📁 파일 구조

```
├── backtest_engine.py      # 메인 백테스팅 엔진
├── test_backtest.py        # 테스트 스크립트
└── BACKTEST_README.md      # 이 파일
```

## 🔧 설치 및 설정

### 필요한 라이브러리
```bash
pip install pandas numpy FinanceDataReader pykrx ta
```

### 기본 사용법

#### 1. 간단한 테스트 실행
```python
# 기본 기능 테스트
python test_backtest.py
```

#### 2. 커스텀 백테스팅 실행
```python
from backtest_engine import BacktestEngine

# 엔진 초기화
engine = BacktestEngine(
    initial_capital=10_000_000,  # 초기 자본 (원)
    transaction_cost=0.003       # 거래 비용 (0.3%)
)

# 백테스팅 실행
results = engine.run_backtest(
    start_date="2024-01-01",
    end_date="2024-12-01"
)

# 결과 출력
engine.print_summary()

# 결과 저장
engine.save_results("my_backtest_result.json")
```

## 📈 백테스팅 로직

### 매일의 거래 흐름

1. **08:30 매도 전략**
   - 보유 종목의 보유 기간 확인
   - 3일 이상 보유 종목 매도 검토
   - 기술적 홀드 시그널 확인 (3일차)
   - 5일 이상은 무조건 매도

2. **15:20 매수 전략**
   - 전체 시장에서 조건부 종목 스크리닝
   - 5일 종가 최저값 == 현재 종가
   - 20일 이동평균 > 현재 종가
   - 기술적 분석 점수 0.6 이상
   - 최대 5개 종목까지 매수

### 종목 선정 기준

```python
# 1차 필터링 (전통적 조건)
- 5일 종가 최저값 == 현재 종가
- 20일 이동평균 > 현재 종가  
- 최소 거래대금 10억원 이상

# 2차 필터링 (기술적 분석)
- RSI 과매도 구간 (+점수)
- 이동평균 하락 (+점수)
- 거래량 급증 (+점수)
- 볼린저밴드 하단 (+점수)
- 최종 점수 0.6 이상
```

## 📊 성과 지표

### 주요 지표
- **총 수익률**: (최종자산 - 초기자본) / 초기자본
- **연환산 수익률**: 총 수익률을 1년 기준으로 환산
- **최대 낙폭 (MDD)**: 최고점 대비 최대 하락폭
- **샤프 비율**: 위험 대비 수익률
- **승률**: 수익 거래 / 전체 거래
- **평균 보유기간**: 매도까지 평균 일수

### 거래 통계
```python
{
    "total_trades": 45,           # 총 거래 횟수
    "win_rate": 0.62,            # 승률 62%
    "avg_profit_per_trade": 15000, # 거래당 평균 손익
    "avg_holding_days": 3.2       # 평균 보유기간
}
```

## 💻 실제 사용 예시

### 예시 1: 기본 백테스팅
```python
from backtest_engine import BacktestEngine

# 1000만원으로 6개월 백테스팅
engine = BacktestEngine(initial_capital=10_000_000)
results = engine.run_backtest("2024-06-01", "2024-12-01")

print(f"수익률: {results['total_return']*100:+.2f}%")
print(f"승률: {results['win_rate']*100:.1f}%")
```

### 예시 2: 파라미터 조정
```python
# 거래 비용 높게 설정
engine = BacktestEngine(
    initial_capital=5_000_000,
    transaction_cost=0.005  # 0.5%
)

results = engine.run_backtest("2024-01-01", "2024-12-01")
```

### 예시 3: 결과 분석
```python
# 상세 거래 내역 확인
for trade in results['trade_history']:
    if trade['action'] == 'SELL':
        print(f"{trade['date']}: {trade['ticker']} "
              f"{trade['profit_rate']:+.2f}% "
              f"({trade['holding_days']}일)")
```

## ⚠️ 현재 제약사항

### 데이터 제약
- **일봉 단위**: 분봉 데이터 미지원
- **생존자 편향**: 상장폐지 종목 제외
- **AI 모델 제외**: 규칙 기반 로직으로 대체

### 거래 제약  
- **상하한가 미반영**: 거래정지 상황 고려 안됨
- **유동성 제약 단순화**: 실제 거래량 제약 미반영
- **슬리피지 단순화**: 고정 거래 비용만 적용

## 🔮 향후 개선 계획

### 1단계: 현실성 강화
- [ ] 상하한가 제도 반영
- [ ] 유동성 제약 모델링
- [ ] 거래정지 상황 처리

### 2단계: 분석 고도화
- [ ] 시장 환경별 성과 분석
- [ ] 계절성 효과 분석
- [ ] 리스크 지표 확장

### 3단계: 최적화
- [ ] 파라미터 최적화 기능
- [ ] 워크포워드 분석
- [ ] 몬테카를로 시뮬레이션

## 🚨 주의사항

### 결과 해석
- **과최적화 위험**: 과거 데이터에만 맞춘 결과일 수 있음
- **현실과 차이**: 실제 거래에서는 심리적 요인, 거래 제약 등으로 차이 발생
- **보수적 접근**: 백테스팅 결과의 70-80%를 실제 기댓값으로 설정 권장

### 데이터 한계
- **미래 정보 누설**: 현재는 기본적인 방지만 구현
- **시장 환경 변화**: 과거 패턴이 미래에도 유효하지 않을 수 있음

## 📞 문의 및 개선사항

백테스팅 엔진 사용 중 문제가 발생하거나 개선사항이 있으면 이슈로 등록해주세요.

### 로그 확인
```python
# 백테스팅 실행 중 상세 로그 출력
engine.run_backtest("2024-01-01", "2024-12-01")
```

### 디버깅 모드
```python
# 특정 날짜 종목 선정 확인
candidates = engine.enhanced_stock_selection("2024-12-06")
for candidate in candidates:
    print(f"{candidate['ticker']}: {candidate['technical_score']:.3f}")
```

---

**💡 팁**: 처음 사용할 때는 `test_backtest.py`를 실행하여 기본 기능을 확인해보세요!
