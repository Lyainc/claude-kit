# Expert Panel Discussion - Examples

실제 대화 예시. SKILL.md에서 참조됨.

> **Note**: Example 1·2는 기본(inline) 모드 출력입니다 — 한 모델(진행자)이 모든 페르소나 발언을 한 응답에 시뮬레이션한 결과예요. 시뮬레이션된 발언은 검증된 사실도 독립 실행도 아니고, `[Moderator]` 결론은 진행자의 종합이지 독립 검토가 아니에요. "격리 실행" 모드에서는 각 expert 발언이 별도 subagent의 exchange별 재spawn으로 생성되고 exchange 간 실제 반박이 일어나요 — Example 3 참조 (메커니즘은 [reference.md](reference.md)의 § Isolated execution: exchange-loop contract — SKILL.md의 같은 이름 섹션은 그 계약을 가리키는 포인터예요).
>
> **토픽 진행 순서**: 진행자의 중립 브리핑(사실·제약) → 전문가 독립 발언 → Q&A/반박(Optimistic Practitioner의 실행안 검토와 Critical Practitioner의 실패 검토로 시작) → 논의 → 결론. Practitioner는 별도 agent가 아닌 검토 관점이고, 투표하지 않으며 정족수에도 포함되지 않아요. 예시 속 주장은 사실(출처) / 가정 / 추정 / 검증 계획으로 구분해서 적어요.

---

## Example 1: API 설계 검토

### 사용자 요청

```
User: 이 REST API 설계 문서를 보안전문가, 성능전문가, UX전문가 관점에서 검토해줘.
      인증 방식과 페이지네이션 전략이 적절한지 확인하고 싶어.
```

### Phase 0: 토론 준비

```
[진행자]
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

**[진행자 — 브리핑: 사실·제약]**
- 사실(설계 문서): 웹과 모바일 클라이언트를 모두 지원하고, 인증 방식은 JWT와 Session 두 후보가 검토 대상
- 가정: 서버는 수평 확장 가능성을 열어 둠 (문서에 확장 계획 수치는 없음)
- 미확인: 토큰 만료 시간, Refresh Token 저장 위치는 문서에 명시되지 않음

**[Security Expert — independent]**:
JWT는 탈취된 토큰을 만료 전에 무효화하기 어렵습니다.
Refresh Token Rotation과 탈취 감지 메커니즘 없이는 동의하기 어렵습니다.

**[Performance Expert — independent]**:
JWT는 요청마다 signature 검증이 필요합니다. 검증 결과 캐싱으로
부하를 줄일 수 있는지는 측정해 봐야 합니다 (검증 계획).

**[UX Expert — independent]**:
Silent Refresh가 정상 동작하면 사용자 관점에서 Session 방식과의 차이는 작을 것으로 추정합니다.

**[Optimistic Practitioner — 실행안 검토]**:
최소 실행안은 JWT + Refresh Token입니다 (Access Token 15분, Refresh Token 7일은 시작값 제안).
- 선행 조건: Refresh Token Rotation, Refresh Token 저장 위치 결정
- 적용 순서: 인증 서버 → 웹 클라이언트 → 모바일 클라이언트
- 성공 확인: 토큰 갱신 실패율과 재로그인 횟수를 로그로 확인 (검증 계획)

**[Critical Practitioner — 실패 검토]**:
- 실패 시나리오: Refresh Token 탈취 시 Rotation이 없으면 장기간 악용 가능
- 운영 부담: Rotation 실패 시 사용자가 반복 로그아웃될 수 있음
- 중단 조건: 갱신 실패가 반복되면 Session 방식으로 되돌리는 경로를 남겨 둠
- 대안: 서버 측 세션 저장소를 둔 Session 방식

**[Security Expert]**:
Device Fingerprint 검증을 더하면 Rotation 탈취 감지에 도움이 되지만,
오탐 시 사용자 경험 영향은 확인이 필요합니다 (가정).

**[Performance Expert]**:
캐싱 TTL을 Rotation 주기 이하로 두는 조건이면 보안 우려와 양립할 수 있습니다.

**[Moderator — 진행자 종합]**:
JWT + Refresh Token 방식으로 수렴.
조건: Refresh Token Rotation 필수, Device Fingerprint 검증은 오탐 영향 확인 후 적용

**결론**:
JWT + Refresh Token 방식 합의
조건: Refresh Token Rotation 필수, Device Fingerprint 검증은 오탐 영향 확인 후 적용
소수 의견: 없음 (Practitioner 검토는 투표 대상이 아님)
```

### Phase 1: Topic 2 - 페이지네이션

```
### TOPIC 2: 페이지네이션 전략

**[진행자 — 브리핑: 사실·제약]**
- 사실(설계 문서): 사용자용 목록 API와 관리자용 목록 API가 모두 대상
- 사실(일반 동작): Offset 방식은 건너뛸 행을 스캔하므로 깊은 페이지일수록 비용이 늘고, Cursor 방식은 특정 페이지로 직접 이동할 수 없음
- 미확인: 데이터 규모와 정렬 기준 변경 빈도

**[Performance Expert — independent]**:
대용량 목록에서는 Cursor가 유리합니다. 다만 실제 데이터 규모는 확인이 필요합니다 (가정).

**[UX Expert — independent]**:
관리자 페이지에서는 "5페이지로 이동" 기능이 필요한데,
Cursor 방식으로는 어떻게 처리하나요?

**[Security Expert — independent]**:
페이지 크기 상한이 없으면 대량 조회로 악용될 수 있으므로 두 방식 모두 상한이 필요합니다.

**[Optimistic Practitioner — 실행안 검토]**:
최소 실행안은 사용자 API는 Cursor, 관리자 API는 Offset으로 나누는 것입니다.
- 선행 조건: 정렬 기준과 cursor 인코딩 형식 확정
- 적용 순서: 사용자 API 먼저, 관리자 API는 기존 방식 유지
- 성공 확인: 깊은 페이지 요청의 응답 시간을 전후로 측정 (검증 계획)

**[Critical Practitioner — 실패 검토]**:
- 실패 시나리오: 정렬 기준 변경 시 cursor가 무효화되어 클라이언트가 오류를 받음
- 운영 부담: 두 방식을 함께 유지해야 하는 비용
- 중단 조건: 관리자 API 데이터가 커져 Offset이 느려지면 Cursor 전환을 재논의
- 대안: 전 구간 Offset + 페이지 크기 상한

**[Performance Expert]**:
하이브리드는 유지보수 부담이 되지만, 사용자 API만이라도 Cursor로 통일하는 것이 좋겠습니다.

**[UX Expert]**:
사용자 API가 무한 스크롤 중심이라면 Cursor가 적합합니다. 하이브리드에 동의합니다.

**[Moderator — 진행자 종합]**:
사용자 API Cursor, 관리자 API Offset으로 수렴. 관리자 API 데이터 증가는 재논의 조건으로 남김.

**결론**:
하이브리드 방식 합의
- 사용자 API: Cursor 기반
- 관리자 API: Offset 기반 (관리자 데이터가 커지면 재논의)
```

### Phase 1: Topic 3 - 에러 처리 (보류)

```
### TOPIC 3: 에러 응답 형식

**[진행자 — 브리핑: 사실·제약]**
- 사실(공개 표준): RFC 7807(Problem Details)은 HTTP API 에러 응답의 표준 형식을 정의
- 제약: 상세 에러 정보는 디버깅에 유용하지만 시스템 정보 노출 위험과 맞닿아 있음
- 미확인: 회사의 API 에러 응답 보안 가이드라인

**[Security Expert — independent]**:
상세 에러 정보는 공격자에게 시스템 정보를 노출합니다.
프로덕션에서는 최소 정보만 반환해야 합니다.

**[UX Expert — independent]**:
하지만 사용자에게 "문제가 발생했습니다"만 보여주면
무엇을 잘못했는지 알 수 없습니다.

**[Performance Expert — independent]**:
에러 형식은 성능에 큰 영향이 없어 의견을 보류합니다.

**[Optimistic Practitioner — 실행안 검토]**:
최소 실행안은 RFC 7807 형식을 쓰되 4xx는 상세, 5xx는 최소 정보로 나누는 것입니다.

**[Critical Practitioner — 실패 검토]**:
환경별로 다른 응답을 주면 테스트/운영 불일치가 생길 수 있습니다.
회사 가이드라인을 확인하기 전에는 실행안의 허용 범위를 정할 수 없습니다.

**[Security Expert]**:
사용자 입력 오류와 시스템 오류를 구분해야 합니다.
4xx는 상세히, 5xx는 최소화하는 방식이 필요합니다.

**[Moderator — 진행자 종합]**:
결정을 가르는 주장(상세 에러 정보의 허용 범위)이 사용자가 줘야 할 사실, 즉 회사 보안 가이드라인 없이는
검증할 수 없습니다 → `held:evidence`.

**[진행자]** (사용자에게 사실 요청):
**사유**: 팩트체크 필요
**필요 정보**: 회사 보안 정책에서 API 에러 응답 관련 가이드라인
**재개 조건**: 정책 확인 후 재논의

**결론**: 보류(`held:evidence`) - 보안 정책 확인 필요
```

### 최종 산출물

**SUMMARY.md**:

| 토픽 | 결론 | 근거 | 출처 / 인용 |
|------|------|------|------------|
| 인증 방식 | JWT + Refresh Token | Rotation + Fingerprint 조건부 합의 | [[decision-2026-03-auth]] |
| 페이지네이션 | 하이브리드 (User: Cursor, Admin: Offset) | 용도별 최적화 | 도메인 판단 (근거 없음) |
| 에러 처리 | 보류 | 보안 정책 확인 필요 | — |

실행안·실패·중단 조건은 토픽별 Practitioner 검토에서 가져오고, 소수 의견은 없으며, 보류 토픽은 `UNRESOLVED.md`로 가요.

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
[진행자]
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

**[진행자 — 브리핑: 사실·제약]**
- 사실(정책안 초안): 직무 특성 기반 대상 선정과 주 3일 재택 모델이 제안되어 있음
- 제약: 근무 장소 변경은 취업규칙·근로계약과 연결될 수 있음 (법률 해석은 법률전문가 발언 참조)
- 미확인: 기존 근로계약서의 재택근무 조항, 대상 직무 범위

**[Legal Expert — independent]**:
근로기준법상 근무 장소 변경은 근로조건 변경에 해당할 수 있습니다.
취업규칙 변경 절차를 거쳐야 하며,
기존 근로계약서에 재택근무 관련 조항이 명시되어 있나요?

**[HR Expert — independent]**:
재택근무 대상 선정 기준을 객관화해야 합니다.
- 근속 기간 기준 설정 필요 (예: 6개월 이상은 제안값)
- 직무 평가 결과 반영 가능
- 신입사원은 온보딩 완료 후 단계적 적용 권장

**[Field Manager — independent]**:
현장에서는 팀 단위 소통이 핵심입니다.
- 주 3일 재택 시 팀 미팅 요일을 고정하는 편이 좋음
- 긴급 이슈 대응을 위한 출근 요청 권한이 팀 리더에게 필요
- 커뮤니케이션 도구 표준화가 선행되어야 함

**[Optimistic Practitioner — 실행안 검토]**:
최소 실행안은 직무 기반 대상 선정에 근속·승인 조건을 얹는 것입니다.
- 선행 조건: 취업규칙 변경 절차, 커뮤니케이션 도구 표준화
- 적용 순서: 대상 직무 지정 → 팀 리더 승인 → 주 1회 팀 전체 출근일 지정
- 성공 확인: 팀 단위 협업 지연이나 형평성 불만 접수 여부를 점검 (검증 계획)

**[Critical Practitioner — 실패 검토]**:
- 실패 시나리오: 같은 부서 내 재택/출근 혼재로 형평성 문제 발생, 협업이 필요한 시기에 적용 곤란
- 운영 부담: 팀 리더 승인 절차가 업무 부담이 됨
- 중단 조건: 형평성 이슈가 반복되면 대상 기준을 재검토
- 대안: 부서 단위 일괄 적용

**[Legal Expert]**:
근속 기준과 팀 리더 승인 절차가 포함되면
취업규칙 변경 시 합리적 기준으로 인정될 가능성이 높아집니다 (추정, 최종 판단은 법무 검토).

**[HR Expert]**:
근속 기간 조건과 팀 리더 승인이 포함되면 형평성 우려를 완화할 수 있습니다.

**[Moderator — 진행자 종합]**:
직무 특성 기반 선정으로 수렴. 법무 검토는 후속 조치로 남김.

**결론**:
직무 특성 기반 재택근무 대상 선정 합의
조건: 근무 6개월 이상, 팀 리더 승인 필요, 주 1회 팀 출근일 지정
```

### Phase 1: Topic 2 - 성과 평가 방식

```
### TOPIC 2: 성과 평가 방식

**[진행자 — 브리핑: 사실·제약]**
- 사실(정책안 초안): 성과물 기반 평가 도입이 제안되어 있음
- 제약: 근무 시간 모니터링은 개인정보 보호 관련 제약이 있을 수 있음
- 미확인: 현재 평가 체계의 항목, 재택 중 성과 데이터

**[HR Expert — independent]**:
성과물 기반 평가로 전면 전환은 시기상조입니다.
기존 평가 체계와 병행하는 파일럿 프로그램을 먼저 운영하고,
기간을 정해 결과를 분석한 뒤 확대 여부를 결정해야 합니다 (파일럿 기간은 검증 계획에서 정함).

**[Field Manager — independent]**:
현장 관리자 입장에서는 근태 관리가 기본입니다.
- 재택근무 시 업무 시작/종료 보고는 필요하다고 봄
- 성과물만으로는 업무 몰입도를 파악하기 어려움
- 최소한의 근무 시간 확인은 필요하다고 봅니다

**[Legal Expert — independent]**:
근무 시간 모니터링 시 개인정보보호법 이슈가 발생할 수 있습니다.
- 화면 캡처, 키보드 로깅 등은 과도한 감시에 해당할 소지가 큼
- 업무 시작/종료 시간 기록 정도가 상대적으로 허용 가능한 범위
- 모니터링 범위와 방식에 대한 사전 동의가 필요

**[Optimistic Practitioner — 실행안 검토]**:
최소 실행안은 성과물 기반 평가를 기존 평가와 병행하는 파일럿입니다.
- 선행 조건: 직무별 성과 지표 초안, 모니터링 범위에 대한 동의 절차
- 적용 순서: 일부 팀 파일럿 → 결과 검토 → 확대 여부 결정
- 성공 확인: 파일럿 대상 팀의 평가 결과와 기존 평가의 차이를 비교 (검증 계획)

**[Critical Practitioner — 실패 검토]**:
- 실패 시나리오: 협업 기여나 멘토링 같은 정량화 어려운 항목이 누락되고 단기 성과로 편향
- 운영 부담: 직무별 기준이 달라 공정성 확보가 어려움
- 중단 조건: 파일럿에서 평가 기준 이견이 해소되지 않으면 확대 중단
- 대안: 기존 평가 유지 + 재택 관련 항목만 보완

**[HR Expert]**:
모니터링과 성과 평가는 분리해서 접근해야 합니다.
현 시점에서 평가 체계 전환을 확정하기보다
파일럿을 통해 데이터를 확보하는 것이 합리적입니다.

**[Field Manager]**:
방향성만이라도 정해야 파일럿 기준이 모호해지지 않습니다.

**[Legal Expert]**:
방향성 합의 이전에 모니터링 범위부터 확정해야 하는데, 현재 정보로는 확정이 어렵습니다.

**[Moderator — 진행자 종합]**:
성과 평가 방식에 대해 전문가 간 의견이 분리되어 있고 근거 데이터가 없습니다.
파일럿 프로그램 결과가 나온 후 재논의하는 것이 적절합니다.

**결론**: 보류 - 성과 평가 파일럿 프로그램 결과 확인 필요
```

### 최종 산출물

**SUMMARY.md**:

| 토픽 | 결론 | 근거 | 출처 / 인용 |
|------|------|------|------------|
| 재택근무 대상 기준 | 직무 특성 기반 선정 | 근무 6개월+, 팀 리더 승인 조건부 합의 | 도메인 판단 (근거 없음) |
| 성과 평가 방식 | 보류 | 파일럿 프로그램 결과 확인 필요 | — |

실행안·실패·중단 조건은 토픽별 Practitioner 검토에서 가져오고, 보류 토픽은 `UNRESOLVED.md`로 가요.

───
*2개 토픽 논의 완료 · 1개 합의, 1개 보류*

---

## Example 3: 격리 모드 — exchange 흐름

inline 예시(Example 1·2)와 달리 격리 모드는 각 발언이 별도 subagent의 실제 재spawn으로 생성됩니다. 아래는 진행자(오케스트레이터) 시점의 한 토픽 흐름이에요 (전문가 3인: 보안/성능/UX). Practitioner 검토는 별도 subagent가 아니라 진행자가 한 번 작성해요.

### 사용자 요청

```
User: 이 인증 설계를 보안/성능/UX 전문가 관점에서 격리해서 엄격하게 검토해줘.
```

### 브리핑 — 사실·제약

진행자가 찬반 프레이밍 없이 사실(출처) / 제약 / 가정 / 미확인을 정리한 브리핑을 expert packet에 넣어요.

### Exchange 1 — 독립 (anchoring-free)

진행자(오케스트레이터)가 3개 expert subagent를 토픽+브리핑만 주고 **동시 spawn**. 서로의 발언 비공개.

- **[Security Expert — independent]**: Access Token 15분은 적절하나 Refresh Token 회수 경로가 없음. Rotation 필수.
- **[Performance Expert — independent]**: 매 요청 signature 검증이 병목이 될 수 있음. Redis 캐싱을 검토하되 측정 필요(검증 계획).
- **[UX Expert — independent]**: Silent Refresh만 보장되면 세션 방식 대비 UX 손해가 작을 것으로 추정.

진행자가 3개 발언을 `_exchanges/t1-e1-security.md` 등 3개 record로 Write한 **뒤에야** STATE를 갱신: `Rebuttal: [t1:e1:3/3]` · `Collected: [t1:e1:security,performance,ux]`

### Practitioner 검토 — 진행자가 e1 직후 1회 작성

e1 record 3개를 읽은 진행자가 두 관점으로 검토를 써서 `_exchanges/t1-review.md`에 Write해요. 추가 spawn도, 추가 exchange도 없어요.

- **[Optimistic Practitioner — 실행안 검토]**: 최소 실행안은 JWT + Refresh Token Rotation. 선행 조건은 Refresh Token 저장 위치 결정, 성공 확인은 갱신 실패 로그 점검(검증 계획).
- **[Critical Practitioner — 실패 검토]**: Rotation 실패 시 반복 로그아웃, 캐싱이 무효화를 지연시킬 위험. 중단 조건과 Session 방식 복귀 경로 필요.

Practitioner는 투표하지 않고 정족수에도 포함되지 않아요. 이 검토는 e2·e3 packet에 함께 들어가요.

### Exchange 2 — 반박 (병렬 재spawn)

진행자가 각 expert에 packet 주입 = {자기 e1 입장 + 다른 둘의 e1 요약 + `t1-review.md` + anti-conformity}. 3인 **병렬** 재spawn — 서로의 e2 발언은 못 봄.

- **[Security Expert]**: 성능전문가의 Redis 캐싱에 반박 — 검증 결과 캐싱은 탈취 토큰 무효화를 지연시켜 Rotation과 충돌.
- **[Performance Expert]**: 입장 유지하되 수정 — 캐싱 TTL을 Rotation 주기 이하로 두면 양립 가능. 실패 검토의 지연 위험도 이 조건으로 완화.
- **[UX Expert]**: 입장 유지. 새 논점 없음.

진행자가 `_exchanges/t1-e2-security.md` 등 3개 record를 Write한 뒤 STATE 갱신: `Rebuttal: [t1:e2:3/3]` · `Collected: [t1:e2:security,performance,ux]`

### Exchange 3 — 재반박 (병렬 재spawn)

e2에서 보안·성능이 새 논점(캐싱↔Rotation 충돌·TTL 절충)을 냈으므로 — *어느 expert라도* 새 논점이 있으면 루프 계속 — 진행자가 e2 요약과 `t1-review.md`로 e3를 병렬 spawn.

- **[Security Expert]**: TTL ≤ Rotation 주기면 무효화 지연이 Rotation 윈도 안에 들어오므로 수용. 합의.
- **[Performance Expert]**: 동일 합의.
- **[UX Expert]**: 입장 유지. 새 논점 없음.

진행자가 `_exchanges/t1-e3-security.md` 등 3개 record를 Write한 뒤 STATE 갱신: `Rebuttal: [t1:e3:3/3]` · `Collected: [t1:e3:security,performance,ux]`

### 조기 종료 판정 (진행자)

e3는 e2 대비 새 논점·반박이 없음(전원 수렴, UX는 재진술) → early-stop 발동, 종료. e3는 2-rebuttal 캡이기도 함. (만약 e2가 e1 재진술뿐이었다면 e3 없이 e2에서 종료 — early-stop은 캡 전에도 발동합니다.) 다만 캡이든 조기 종료든 루프를 끝내는 것일 뿐 결론이 아니에요 — 결론은 Moderator가 Topic Conclusion 규칙으로 냅니다.

### Synthesis (Moderator subagent — 독립 최종 검토)

진행자가 Moderator subagent를 한 번 spawn해요. 입력은 각 expert의 최종 position summary(입장, 근거 출처, 조건, 반대 이유, 투표)와 Practitioner 검토(`t1-review.md`)이고, 전체 Q&A는 주지 않아요. Moderator는 누락·근거 부족을 점검하며, `held:evidence`로 보류할 수는 있지만 expert의 투표를 바꾸거나 루프를 재실행하지 않아요.

- **[Moderator — 독립 최종 검토]**: Rotation + 캐싱 TTL(≤ Rotation 주기) 양립안으로 수렴. Silent Refresh로 UX 중립은 추정이므로 검증 계획(갱신 실패 로그)에 포함. 실패 검토의 중단 조건을 실행안에 반영.

**결론**: JWT + Refresh Token Rotation, 캐싱 TTL ≤ Rotation 주기 합의.
- 실행안: Rotation 적용 → 캐싱 TTL 설정 → 갱신 실패 로그 점검
- 실패·중단 조건: 갱신 실패 반복 시 Session 방식 복귀 재논의
- 소수 의견: 없음

───
*격리 모드: e1 독립 3 + e2 반박 3 + e3 재반박 3 = expert subagent 9 (3N 상한) + Synthesis Moderator 1 (Practitioner 검토는 진행자 작성, spawn 아님)*

---

## Example 4: 격리 모드 — 보류와 부분 복구

격리 모드에서 결론이 안 나거나 중간에 끊겼을 때의 세 장면이에요. 토픽당 한 사이클(e1 → e2 → 선택 e3 → 결론)이라 라운드를 다시 돌리지 않고, 발언 record는 요약 출력 모드에서도 남아요. 투표와 정족수는 도메인 전문가만 세고, Practitioner 검토(`t{n}-review.md`)는 어느 쪽에도 들어가지 않아요.

### (a) 동점 보류

전문가 4인, e3까지 갔는데 합의 실패. 가중 투표(High 3 / Medium 2 / Low 1): 2명이 선택지 A에 High(6점), 2명이 선택지 B에 High(6점). Practitioner 두 관점은 표가 없어서 점수에 더하지 않아요.

STATE: `Votes: [t1:security:A:High, t1:performance:A:High, t1:ux:B:High, t1:legal:B:High]` · `Tie-break: [t1:margin:0]` · `Topic-status: [t1:held:tie]`

SUMMARY.md 행: | 인증 방식 | 보류 (동점 6:6) | 선택지 A·B 동점 | — |
UNRESOLVED.md 행: | 1 | 인증 방식 | A vs B | 동점 | 추가 근거 확보 후 재논의 |

승자도 조건부 승인도 기록하지 않아요. Moderator subagent는 expert의 최종 position summary와 `t1-review.md`를 받아 독립 최종 검토를 하지만, 투표를 바꾸거나 동점을 깨지 못해요. 참고로 4명 중 1명이 Medium이었다면 6 대 5(margin 1)라 `tie-broken` + SUMMARY에 "조건부"가 붙었을 거예요.

### (b) 정족수 미달

전문가 3인. e2에서 2명이 재시도 1회씩 뒤에도 또 실패해서 유효 전문가 1명. 유효 3명 미만이라 루프를 멈추고 투표는 하지 않아요. Practitioner 검토는 정족수에 세지 않으니 검토가 있어도 유효 인원은 늘지 않아요. 실패 내역은 `_exchanges/t2-e2-*.md` record에 남겨요.

STATE: `Topic-status: [t2:held:quorum]`

전문가 1명의 의견은 합의도 종합도 아니라서, 그 발언을 결론처럼 쓰지 않고 UNRESOLVED.md로 보내요. UNRESOLVED.md의 Practitioner 항목은 입장이 아니라 실행안·실패 검토 노트로 적어요.

### (c) 요약 출력 모드에서 e2 부분 복구

전문가 4인(security, performance, ux, legal), 요약 출력 켜짐. e2 도중 `t3-e2-security.md`, `t3-e2-performance.md` 두 record가 써졌고 그 뒤 compaction이 일어났어요. 마지막 STATE는 `Rebuttal: [t3:e2:3/4]` · `Collected: [t3:e2:security,performance,ux]`인데, `t3-e2-ux.md`는 디스크에 없어요.

복구 순서:
1. record가 있는 expert만 끝난 걸로 쳐요. ux는 카운터에는 있지만 record가 없으니 끝난 게 아니에요.
2. 없는 ux와 legal만 다시 spawn하고, packet은 e1 record 4개와 `t3-review.md`로 다시 만들어요. review record가 이미 있으면 새로 쓰지 않고 그대로 써요.
3. security·performance의 e2 결과는 record에서 읽어오고 두 번 세지 않아요.

요약 출력 모드에는 transcript가 없어서, 복구의 근거는 record뿐이에요.

비용: e2에서 복구 spawn 2건, 3N 상한 밖에서 따로 셈해요.

───
*보류·복구 예시: 토픽당 expert 최대 3N + Moderator 1, 재시도·추가 expert·복구 spawn은 별도 집계*
