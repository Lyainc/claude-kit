# Interview State Template

인터뷰 진행 중 상태 추적을 위한 JSON 스키마.

## State Schema

```json
{
  "target": {
    "name": "분석 대상명",
    "type": "project | plan | decision | idea",
    "description": "간단한 설명"
  },
  "domain": "tech | biz | creative | custom",
  "custom_areas": [],
  "current_phase": 0,
  "interview": {
    "questions_asked": 0,
    "current_area": "assumptions",
    "current_depth": 0,
    "areas_completed": [],
    "areas_in_progress": [],
    "areas_pending": ["assumptions", "trade-offs", "edge-cases", "blindspots"],
    "checkpoint_count": 0,
    "last_checkpoint_at": 0
  },
  "discoveries": [],
  "saturation_signals": {
    "short_responses": 0,
    "repetition": 0,
    "avoidance": 0,
    "consecutive_signals": 0
  },
  "status": "not_started"
}
```

## Discovery Item Schema

```json
{
  "id": 1,
  "area": "assumptions | trade-offs | edge-cases | blindspots | feasibility | stakeholders | counterfactual | dependencies",
  "question": "질문 내용",
  "answer": "응답 요약",
  "finding": "발견된 Unknown Unknown",
  "priority": "critical | important | nice-to-have",
  "why_chain": {
    "question": "Why 질문",
    "answer": "응답"
  },
  "uncertainty_signals": [],
  "timestamp": "ISO 8601 format"
}
```

## Status Values

| Status | 설명 |
|--------|------|
| `not_started` | Phase 0 시작 전 |
| `context_analysis` | Phase 0 진행 중 |
| `interviewing` | Phase 1 진행 중 |
| `saturated` | 포화 상태 감지됨 |
| `synthesizing` | Phase 2 진행 중 |
| `documenting` | Phase 3 진행 중 |
| `completed` | 완료 |
| `aborted` | 사용자에 의해 중단됨 |

## Saturation Detection

```json
{
  "saturation_signals": {
    "short_responses": 2,
    "repetition": 1,
    "avoidance": 0,
    "consecutive_signals": 2
  }
}
```

**포화 판정**: `consecutive_signals >= 3`

## Checkpoint Trigger

```text
checkpoint_needed = (questions_asked - last_checkpoint_at) >= 4
```

## Example State (Mid-Interview)

```json
{
  "target": {
    "name": "마이크로서비스 전환",
    "type": "project",
    "description": "모놀리식에서 마이크로서비스로 아키텍처 전환"
  },
  "domain": "tech",
  "custom_areas": [],
  "current_phase": 1,
  "interview": {
    "questions_asked": 6,
    "current_area": "edge-cases",
    "current_depth": 1,
    "areas_completed": ["assumptions"],
    "areas_in_progress": ["edge-cases"],
    "areas_pending": ["trade-offs", "blindspots"],
    "checkpoint_count": 1,
    "last_checkpoint_at": 4
  },
  "discoveries": [
    {
      "id": 1,
      "area": "assumptions",
      "question": "마이크로서비스 전환이 성공하려면 어떤 전제가 필요한가요?",
      "answer": "팀이 분산 시스템을 다룰 수 있어야 함",
      "finding": "팀 분산 시스템 경험 부족",
      "priority": "critical",
      "why_chain": {
        "question": "팀이 분산 시스템을 다룰 수 있다고 생각하시는 근거는?",
        "answer": "사실 경험이 많지 않음, 학습하면서 진행 예정"
      },
      "uncertainty_signals": ["hedging"],
      "timestamp": "2025-01-15T10:35:00"
    }
  ],
  "saturation_signals": {
    "short_responses": 0,
    "repetition": 0,
    "avoidance": 0,
    "consecutive_signals": 0
  },
  "status": "interviewing"
}
```
