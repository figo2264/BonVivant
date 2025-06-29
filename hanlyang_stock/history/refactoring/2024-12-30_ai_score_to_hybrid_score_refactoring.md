# AI Score to Hybrid/Technical Score 리팩토링

**작업일**: 2024-12-30  
**작업자**: Assistant  
**목적**: 코드의 명확성을 위해 모호한 'ai_score' 명칭을 전략에 따라 'hybrid_score' 또는 'technical_score'로 변경

## 배경

기존 코드에서 `ai_score`라는 명칭이 실제 내용과 일치하지 않는 문제가 있었습니다:
- 하이브리드 전략: 실제로는 기술적 분석(70%) + 뉴스 분석(30%)의 종합점수
- 일반 전략: 실제로는 순수 기술적 분석 점수

이로 인해 코드 가독성과 유지보수성에 문제가 있어 리팩토링을 진행했습니다.

## 주요 변경사항

### 1. `hanlyang_stock/strategy/executor.py`

#### 1.1 `_determine_investment_amount` 함수
```python
# 변경 전
return {
    'amount': investment_amount,
    'ai_score': score,  # 모호한 명칭
    'confidence_level': confidence_level,
    ...
}

# 변경 후 (하이브리드 전략)
return {
    'amount': investment_amount,
    'hybrid_score': score,  # 명확한 명칭
    'confidence_level': confidence_level,
    ...
}

# 변경 후 (일반 전략)
return {
    'amount': investment_amount,
    'technical_score': technical_score,  # 명확한 명칭
    'confidence_level': confidence_level,
    ...
}
```

#### 1.2 `_execute_buys` 함수
- 점수 출력 메시지 개선:
  ```python
  # 변경 전
  print(f"   🤖 AI점수: {investment_info['ai_score']:.3f} ({investment_info['confidence_level']})")
  
  # 변경 후
  if investment_info.get('is_hybrid'):
      print(f"   🤝 하이브리드 점수: {score:.3f} ({investment_info['confidence_level']})")
  else:
      print(f"   📊 기술적 점수: {score:.3f} ({investment_info['confidence_level']})")
  ```

- bought_tickers 저장 시 전략별 점수 키 사용
- purchase_info 저장 시 하위 호환성 유지:
  ```python
  # 전략에 따른 점수 저장
  if investment_info.get('is_hybrid'):
      purchase_info['hybrid_score'] = investment_info['hybrid_score']
      purchase_info['ai_score'] = investment_info['hybrid_score']  # 하위 호환성
  else:
      purchase_info['technical_score'] = investment_info['technical_score']
      purchase_info['ai_score'] = investment_info['technical_score']  # 하위 호환성
  ```

- 리셋 조건 체크 시 전략별 점수 사용
- 슬랙 알림 호출 개선

### 2. `hanlyang_stock/utils/notification.py`

#### 2.1 `notify_buy_execution` 함수 개선
```python
# 변경 전
def notify_buy_execution(..., ai_score: float, ...):
    message += f"AI점수: {ai_score:.3f} ({confidence_level})\n"

# 변경 후
def notify_buy_execution(..., score: float, score_type: str, ...):
    if score_type == 'hybrid':
        message += f"하이브리드점수: {score:.3f} ({confidence_level})\n"
        if technical_score is not None and news_score is not None:
            message += f"  - 기술적: {technical_score:.3f}\n"
            message += f"  - 뉴스: {news_score:.3f}"
    elif score_type == 'technical':
        message += f"기술점수: {score:.3f} ({confidence_level})\n"
```

- 하위 호환성 유지: 기존 `ai_score` 파라미터도 계속 지원

### 3. `hanlyang_stock/backtest/performance.py`

#### 3.1 `_analyze_ai_score_performance` 함수
```python
# 변경 전
ai_score = trade.get('ai_score', 0.5)

# 변경 후
# 하위 호환성: 새로운 필드를 먼저 확인하고, 없으면 ai_score 사용
score = trade.get('hybrid_score') or trade.get('technical_score') or trade.get('ai_score', 0.5)
```

#### 3.2 함수 설명 및 출력 메시지 개선
- "AI 모델 성과 분석" → "전략별 성과 분석"
- "AI 점수별 성과" → "점수별 성과"

### 4. `hanlyang_stock/backtest/engine.py`

#### 4.1 `_execute_buy_strategy` 함수
- 피라미딩 후보 추가 시 `hybrid_score` 필드 추가
- 출력 메시지 개선: "피라미딩 후보 추가 (하이브리드 점수: ...)"

#### 4.2 `_select_buy_candidates` 함수
- 모든 candidate에 `hybrid_score` 필드 추가
- 뉴스 없는 경우나 오류 시에도 일관성 유지

#### 4.3 `_execute_buy_orders` 함수
- 피라미딩 점수 체크 시 전략별 점수 사용:
  ```python
  # 하이브리드 전략인 경우
  if self.use_news_strategy:
      score = candidate.get('hybrid_score', ...)
  else:
      score = candidate.get('technical_score', 0)
  ```
- 점수 타입에 따른 메시지 개선
- additional_info에 `hybrid_score` 추가

#### 4.4 `_determine_investment_amount` 함수
- 전략에 따라 적절한 점수 사용
- 하이브리드: `hybrid_score` → `normalized_score` → `combined_score`
- 기술적: `technical_score`

#### 4.5 매수 완료 메시지
- "종합점수" → "하이브리드점수"
- 전략별로 명확한 용어 사용

## 하위 호환성

기존 데이터와의 호환성을 위해 다음과 같은 조치를 취했습니다:

1. **데이터 저장**: 새로운 점수 키와 함께 기존 'ai_score' 키도 저장
2. **데이터 읽기**: 새로운 키가 없으면 기존 'ai_score' 사용
3. **함수 파라미터**: 기존 ai_score 파라미터를 받을 수 있도록 유지

## 영향 범위

- 로직 변경: 없음 (네이밍만 변경)
- 슬랙 알림: 메시지가 더 명확해짐
- 로그 출력: 전략에 따라 적절한 용어 사용
- 백테스트 결과: 기존 데이터도 정상 분석 가능

## 테스트 필요 항목

1. 하이브리드 전략 매수/매도 정상 작동
2. 일반 전략 매수/매도 정상 작동
3. 슬랙 알림 메시지 확인
4. 기존 저장된 데이터 로드 시 오류 없음
5. 백테스트 성과 분석 정상 작동
6. 백테스트 엔진의 하이브리드 전략 실행
