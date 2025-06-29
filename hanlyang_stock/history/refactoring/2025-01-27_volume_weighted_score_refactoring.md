# Volume Weighted Score 리팩토링

## 날짜: 2025-01-27

## 문제점
- `combined_score`라는 이름이 두 가지 다른 의미로 사용되고 있었음:
  1. 초기 종목 선정 단계: 거래대금 × 기술적 점수 가중치 (정렬용)
  2. 하이브리드 전략: 기술적 점수(70%) + 뉴스 점수(30%)

## 해결책
초기 종목 선정 단계의 `combined_score`를 `volume_weighted_score`로 변경

## 변경 사항

### 1. `hanlyang_stock/strategy/selector.py`
- `combined_score_raw` → `volume_weighted_score_raw`
- `combined_score` (거래대금 기반) → `volume_weighted_score`
- 디버깅 메시지에서 "결합점수" → "거래량가중점수"
- 정렬 키 변경: `combined_score` → `volume_weighted_score`

### 2. `hanlyang_stock/backtest/engine.py`
- 주석 업데이트: "(매우 큰 값)" → "(volume_weighted_score)"

### 3. `hanlyang_stock/strategy/executor.py`
- 주석 업데이트: "(매우 큰 값)" → "(volume_weighted_score)"

## 영향
- 초기 종목 선정 단계의 점수와 하이브리드 전략의 점수가 명확히 구분됨
- 코드 가독성 향상
- 혼란 방지

## 하위 호환성
- `combined_score`는 하이브리드 전략에서만 사용하므로 기존 로직에 영향 없음
- 초기 선정 단계는 내부 처리이므로 외부 API 변경 없음
