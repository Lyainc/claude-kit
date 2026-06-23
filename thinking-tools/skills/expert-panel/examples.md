# Expert Panel Discussion - Examples

실제 대화 예시. SKILL.md에서 참조됨.

> **Note**: Example 1·2는 기본(inline) 모드 출력입니다 — 한 모델이 모든 페르소나 발언을 한 응답에 시뮬레이션한 결과예요. "격리 실행" 모드에서는 각 expert 발언이 별도 subagent의 exchange별 재spawn으로 생성되고 exchange 간 실제 반박이 일어나요 — Example 3 참조 (메커니즘은 SKILL.md의 [Isolated Execution: Rebuttal Exchanges]).

---

## Example 1: API 설계 검토

### 사용자 요청

```
User: 이 REST API 설계 문서를 보안전문가, 성능전문가, UX전문가 관점에서 검토해줘.
      인증 방식과 페이지네이션 전략이 적절한지 확인하고 싶어.
```

### Phase 0: 토론 준비

```
[모더레이터]
토론을 준비하겠습니다.

**검토 대상**: REST API 설계 문서
**전문가 집단**: 보안전문가, 성능전문가, UX전문가 (3명)
**토픽 분할**:
  1. 인증 방식 (JWT vs Session)
  2. 페이지네이션 전략 (Offset vs Cursor)
  3. 에러 응답 형식

토론을 시작하겠습니다.
```

### Phase 1: Topic 1 - 인증 방식

```
### TOPIC 1: 인증 방식

**[Optimistic Practitioner]**:
JWT + Refresh Token 방식을 제안합니다.
- Stateless하여 서버 확장에 유리
- 모바일/웹 클라이언트 모두 지원 용이
- Access Token 15분, Refresh Token 7일로 설정 권장

**[Critical Practitioner]**:
JWT 방식의 리스크를 지적합니다.
- Token 탈취 시 만료까지 무효화 불가
- Payload 크기로 인한 네트워크 오버헤드
- Refresh Token 저장 위치 보안 이슈

**[Security Expert]**:
Refresh Token Rotation은 적용 예정인가요?
탈취 감지를 위한 추가 메커니즘이 필요해 보입니다.

**[Optimistic Practitioner]**:
네, Refresh Token Rotation과 함께
Device Fingerprint 검증을 추가할 수 있습니다.

**[Performance Expert]**:
JWT 검증 시 매 요청마다 signature 검증이 필요한데,
Redis 캐싱으로 검증 결과를 저장하면 부하를 줄일 수 있습니다.

**[UX Expert]**:
사용자 관점에서 Silent Refresh가 잘 동작한다면
세션 방식과 UX 차이가 없을 것 같습니다.

**[Critical Practitioner]**:
보안전문가의 우려가 타당합니다.
Refresh Token Rotation + Device Fingerprint 조건으로
JWT 방식에 동의할 수 있습니다.

**결론**:
JWT + Refresh Token 방식 합의
조건: Refresh Token Rotation, Device Fingerprint 검증 필수
```

### Phase 1: Topic 2 - 페이지네이션

```
### TOPIC 2: 페이지네이션 전략

**[Optimistic Practitioner]**:
Cursor 기반 페이지네이션을 제안합니다.
- 실시간 데이터 변경에 일관성 유지
- 대용량 데이터에서 성능 우수 (O(1) vs O(n))

**[Critical Practitioner]**:
Cursor 방식의 단점도 있습니다.
- 특정 페이지로 직접 이동 불가
- 구현 복잡도 증가
- 정렬 기준 변경 시 cursor 무효화

**[UX Expert]**:
관리자 페이지에서는 "5페이지로 이동" 기능이 필요한데,
Cursor 방식으로는 어떻게 처리하나요?

**[Optimistic Practitioner]**:
관리자용 API와 사용자용 API를 분리하여
관리자는 Offset, 사용자는 Cursor를 사용할 수 있습니다.

**[Performance Expert]**:
하이브리드 방식은 유지보수 부담이 됩니다.
사용자 API만이라도 Cursor로 통일하는 게 좋겠습니다.

**[Critical Practitioner]**:
사용자 API는 무한 스크롤이 대부분이므로 Cursor가 적합합니다.
하이브리드 제안에 동의합니다.

**결론**:
하이브리드 방식 합의
- 사용자 API: Cursor 기반
- 관리자 API: Offset 기반 (데이터량 제한적)
```

### Phase 1: Topic 3 - 에러 처리 (보류)

```
### TOPIC 3: 에러 응답 형식

**[Optimistic Practitioner]**:
RFC 7807 (Problem Details) 표준을 제안합니다.
상세한 에러 정보로 디버깅에 유리합니다.

**[Security Expert]**:
상세 에러 정보는 공격자에게 시스템 정보를 노출합니다.
프로덕션에서는 최소 정보만 반환해야 합니다.

**[UX Expert]**:
하지만 사용자에게 "문제가 발생했습니다"만 보여주면
무엇을 잘못했는지 알 수 없습니다.

**[Security Expert]**:
사용자 입력 오류와 시스템 오류를 구분해야 합니다.
4xx는 상세히, 5xx는 최소화하는 방식이 필요합니다.

**[Critical Practitioner]**:
환경별로 다른 응답을 주는 것은 테스트/운영 불일치를 야기합니다.

**[Moderator]**:
의견이 교착 상태입니다.
에러 응답 정책에 대한 보안 가이드라인이 있는지 확인이 필요합니다.

**중단 사유**: 팩트체크 필요
**필요 정보**: 회사 보안 정책에서 API 에러 응답 관련 가이드라인
**재개 조건**: 정책 확인 후 재논의

**결론**: 보류 - 보안 정책 확인 필요
```

### 최종 산출물

**SUMMARY.md**:

| 토픽 | 결론 | 근거 | 출처 / 인용 |
|------|------|------|------------|
| 인증 방식 | JWT + Refresh Token | Rotation + Fingerprint 조건부 합의 | [[decision-2026-03-auth]] |
| 페이지네이션 | 하이브리드 (User: Cursor, Admin: Offset) | 용도별 최적화 | 도메인 판단 (근거 없음) |
| 에러 처리 | 보류 | 보안 정책 확인 필요 | — |

───
*3개 토픽 논의 완료 · 2개 합의, 1개 보류*

---

## Example 2: 정책 문서 검토

### 사용자 요청

```
User: 재택근무 정책안을 법률전문가, HR전문가, 현장관리자 관점에서 검토해줘.
```

### Phase 0: 토론 준비

```
[모더레이터]
토론을 준비하겠습니다.

**검토 대상**: 재택근무 정책안
**전문가 집단**: 법률전문가, HR전문가, 현장관리자 (3명)
**토픽 분할**:
  1. 재택근무 대상 기준
  2. 성과 평가 방식

토론을 시작하겠습니다.
```

### Phase 1: Topic 1 - 재택근무 대상 기준

```
### TOPIC 1: 재택근무 대상 기준

**[Optimistic Practitioner]**:
직무 특성 기반의 재택근무 대상 선정을 제안합니다.
- 독립적 업무 수행이 가능한 직무를 기준으로 분류
- 주 3일 재택근무를 기본 모델로 설정
- 대상 직무: 개발, 디자인, 기획, 마케팅 등 사무직 중심

**[Critical Practitioner]**:
직무 기반 분류의 문제점을 지적합니다.
- 같은 부서 내 재택/출근 혼재 시 형평성 이슈
- 팀 협업이 필요한 프로젝트 기간에는 적용 곤란
- 신입사원의 온보딩 과정에서 재택근무는 부적절

**[Legal Expert]**:
근로기준법상 근무 장소 변경은 근로조건 변경에 해당합니다.
취업규칙 변경 절차를 거쳐야 하며,
기존 근로계약서에 재택근무 관련 조항이 명시되어 있나요?

**[HR Expert]**:
재택근무 대상 선정 기준을 객관화해야 합니다.
- 근속 기간 기준 설정 필요 (예: 6개월 이상)
- 직무 평가 결과 반영 가능
- 신입사원은 온보딩 완료 후 단계적 적용 권장

**[Field Manager]**:
현장에서는 팀 단위 소통이 핵심입니다.
- 주 3일 재택 시 팀 미팅 요일을 고정해야 함
- 긴급 이슈 대응을 위한 출근 요청 권한이 팀 리더에게 필요
- 커뮤니케이션 도구 표준화가 선행되어야 함

**[Optimistic Practitioner]**:
우려 사항을 반영하여 조건을 추가합니다.
- 근무 6개월 이상 조건 수용
- 팀 리더 승인 절차 포함
- 주 1회 팀 전체 출근일 지정

**[Legal Expert]**:
근무 6개월 기준과 팀 리더 승인 절차가 포함되면
취업규칙 변경 시 합리적 기준으로 인정될 수 있습니다.

**[Critical Practitioner]**:
근속 기간 조건과 팀 리더 승인이 포함되면
형평성과 운영상 문제를 완화할 수 있습니다. 동의합니다.

**결론**:
직무 특성 기반 재택근무 대상 선정 합의
조건: 근무 6개월 이상, 팀 리더 승인 필요, 주 1회 팀 출근일 지정
```

### Phase 1: Topic 2 - 성과 평가 방식

```
### TOPIC 2: 성과 평가 방식

**[Optimistic Practitioner]**:
성과물 기반(Output-based) 평가 방식을 제안합니다.
- 업무 결과물과 달성률 중심 평가
- OKR/KPI 기반 분기별 목표 설정 및 리뷰
- 근무 시간이 아닌 성과 품질로 판단

**[Critical Practitioner]**:
성과물 기반 평가의 한계를 지적합니다.
- 협업 기여도나 멘토링 등 정량화 어려운 항목 누락
- 직무별 성과 측정 기준 상이하여 공정성 확보 어려움
- 단기 성과 중심으로 편향될 위험

**[HR Expert]**:
성과물 기반 평가로 전면 전환은 시기상조입니다.
기존 평가 체계와 병행하는 파일럿 프로그램을 먼저 운영하고,
3-6개월 후 결과를 분석한 뒤 확대 적용을 결정해야 합니다.

**[Field Manager]**:
현장 관리자 입장에서는 근태 관리가 기본입니다.
- 재택근무 시 업무 시작/종료 보고는 필수
- 성과물만으로는 업무 몰입도를 파악하기 어려움
- 최소한의 근무 시간 모니터링은 필요하다고 봅니다

**[Legal Expert]**:
근무 시간 모니터링 시 개인정보보호법 이슈가 발생합니다.
- 화면 캡처, 키보드 로깅 등은 과도한 감시에 해당
- 업무 시작/종료 시간 기록 정도만 법적으로 허용 가능
- 모니터링 범위와 방식에 대한 사전 동의가 필수

**[HR Expert]**:
모니터링과 성과 평가는 분리해서 접근해야 합니다.
현 시점에서 평가 체계 전환을 확정하기보다
파일럿을 통해 데이터를 확보하는 것이 합리적입니다.

**[Optimistic Practitioner]**:
파일럿 프로그램 필요성은 인정하지만,
평가 방향성만이라도 합의하고 싶습니다.

**[Critical Practitioner]**:
방향성 합의 없이 파일럿만 진행하면 기준이 모호해집니다.
하지만 현재 데이터가 부족하여 방향을 확정하기 어렵습니다.

**[Moderator]**:
성과 평가 방식에 대해 전문가 간 의견이 분리되어 있습니다.
파일럿 프로그램 결과가 나온 후 재논의하는 것이 적절합니다.

**결론**: 보류 - 성과 평가 파일럿 프로그램 결과 확인 필요
```

### 최종 산출물

**SUMMARY.md**:

| 토픽 | 결론 | 근거 | 출처 / 인용 |
|------|------|------|------------|
| 재택근무 대상 기준 | 직무 특성 기반 선정 | 근무 6개월+, 팀 리더 승인 조건부 합의 | 도메인 판단 (근거 없음) |
| 성과 평가 방식 | 보류 | 파일럿 프로그램 결과 확인 필요 | — |

───
*2개 토픽 논의 완료 · 1개 합의, 1개 보류*

---

## Example 3: 격리 모드 — exchange 흐름

inline 예시(Example 1·2)와 달리 격리 모드는 각 발언이 별도 subagent의 실제 재spawn으로 생성됩니다. 아래는 오케스트레이터 시점의 한 토픽 흐름이에요 (전문가 3인: 보안/성능/UX).

### 사용자 요청

```
User: 이 인증 설계를 보안/성능/UX 전문가 관점에서 격리해서 엄격하게 검토해줘.
```

### Exchange 1 — 독립 (anchoring-free)

오케스트레이터가 3개 expert subagent를 토픽+브리핑만 주고 **동시 spawn**. 서로의 발언 비공개.

- **[Security Expert — independent]**: Access Token 15분은 적절하나 Refresh Token 회수 경로가 없음. Rotation 필수.
- **[Performance Expert — independent]**: 매 요청 signature 검증이 병목. Redis 캐싱 권장.
- **[UX Expert — independent]**: Silent Refresh만 보장되면 세션 방식 대비 UX 손해 없음.

STATE: `Rebuttal: [t1:e1:3/3]` (수집 완료)

### Exchange 2 — 반박 (병렬 재spawn)

오케스트레이터가 각 expert에 packet 주입 = {자기 e1 입장 + 다른 둘의 e1 요약 + anti-conformity}. 3인 **병렬** 재spawn — 서로의 e2 발언은 못 봄.

- **[Security Expert]**: 성능전문가의 Redis 캐싱에 반박 — 검증 결과 캐싱은 탈취 토큰 무효화를 지연시켜 Rotation과 충돌.
- **[Performance Expert]**: 입장 유지하되 수정 — 캐싱 TTL을 Rotation 주기 이하로 두면 양립 가능.
- **[UX Expert]**: 입장 유지. 새 논점 없음.

STATE: `Rebuttal: [t1:e2:3/3]`

### Exchange 3 — 재반박 (병렬 재spawn)

e2에서 보안·성능이 새 논점(캐싱↔Rotation 충돌·TTL 절충)을 냈으므로 — *어느 expert라도* 새 논점이 있으면 루프 계속 — 오케스트레이터가 e2 요약으로 e3를 병렬 spawn.

- **[Security Expert]**: TTL ≤ Rotation 주기면 무효화 지연이 Rotation 윈도 안에 들어오므로 수용. 합의.
- **[Performance Expert]**: 동일 합의.
- **[UX Expert]**: 입장 유지. 새 논점 없음.

STATE: `Rebuttal: [t1:e3:3/3]`

### 조기 종료 판정 (오케스트레이터)

e3는 e2 대비 새 논점·반박이 없음(전원 수렴, UX는 재진술) → early-stop 발동, 종료. e3는 2-rebuttal 캡이기도 함. (만약 e2가 e1 재진술뿐이었다면 e3 없이 e2에서 종료 — early-stop은 캡 전에도 발동합니다.)

### Synthesis (Moderator subagent)

오케스트레이터가 Moderator subagent를 e3 position summary만 주고 spawn:

- **[Moderator]**: Rotation + 캐싱 TTL(≤ Rotation 주기) 양립안으로 수렴. Silent Refresh로 UX 중립.

**결론**: JWT + Refresh Token Rotation, 캐싱 TTL ≤ Rotation 주기 합의.

───
*격리 모드: e1 독립 3 + e2 반박 3 + e3 재반박 3 = expert subagent 9 + Synthesis Moderator 1*
