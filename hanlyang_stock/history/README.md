# 📚 Hanlyang Stock 전략 개선 히스토리

이 디렉토리는 Hanlyang Stock 프로젝트의 전략 개선 사항과 변경 이력을 관리합니다.

## 📁 디렉토리 구조

```
history/
├── README.md                    # 이 파일
├── improvements/               # 개선 사항 문서
│   ├── 01_trend_strength_filter.md    # 추세 강도 필터
│   └── 02_adaptive_strategy.md        # 적응형 전략
├── backtest_results/          # 백테스트 결과
└── performance_logs/          # 실전 성과 기록
```

## 🚀 개선 로드맵

### Phase 1: 추세 강도 필터 (2024.01)
- 양봉 크기 검증
- 거래량 급증 확인
- RSI 반등 신호
- 지지선 근처 확인

### Phase 2: 적응형 전략 (2024.02)
- 시장 상황 판단
- 상황별 파라미터 조정
- 매매 중단 조건

### Phase 3: 다단계 진입/청산 (예정)
- 분할 매수
- 분할 매도
- 동적 포지션 관리

## 📊 성과 추적

각 개선 사항 적용 후 최소 2-3주간의 실전 데이터를 수집하여 효과를 검증합니다.

## 🔗 관련 문서

- [추세 강도 필터 상세](improvements/01_trend_strength_filter.md)
- [적응형 전략 상세](improvements/02_adaptive_strategy.md)
