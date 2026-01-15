# Expert Panel Discussion - Examples

Practical conversation examples. Referenced from SKILL.md.

---

## Example 1: API Design Review (English)

### User Request

```
User: Review this REST API design document from security, performance, and UX expert perspectives.
      I want to verify if the authentication method and pagination strategy are appropriate.
```

### Phase 0: Discussion Preparation

```
[Moderator]
Preparing for discussion.

**Review Target**: REST API design document
**Expert Panel**: Security Expert, Performance Expert, UX Expert (3 members)
**Topic Division**:
  1. Authentication Method (JWT vs Session)
  2. Pagination Strategy (Offset vs Cursor)
  3. Error Response Format

Starting discussion.
```

### Phase 1: Topic 1 - Authentication Method

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 TOPIC 1: Authentication Method
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎤 [Optimistic Practitioner]:
I propose JWT + Refresh Token approach.
- Stateless, advantageous for server scaling
- Easy support for both mobile/web clients
- Recommend Access Token 15min, Refresh Token 7 days

🎤 [Critical Practitioner]:
I'd like to point out risks with JWT approach.
- Cannot invalidate token until expiry if stolen
- Network overhead due to payload size
- Security issues with Refresh Token storage location

🎤 [Security Expert]:
Is Refresh Token Rotation planned?
Additional mechanisms for theft detection seem necessary.

🎤 [Optimistic Practitioner]:
Yes, we can add Device Fingerprint verification
along with Refresh Token Rotation.

🎤 [Performance Expert]:
JWT verification requires signature verification on every request,
but Redis caching can reduce the load by storing verification results.

🎤 [UX Expert]:
From a user perspective, if Silent Refresh works well,
there should be no UX difference from session-based approach.

🎤 [Critical Practitioner]:
The security expert's concern is valid.
I can agree to JWT approach with conditions:
Refresh Token Rotation + Device Fingerprint.

✅ CONCLUSION:
JWT + Refresh Token approach agreed
Conditions: Refresh Token Rotation, Device Fingerprint verification required
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Phase 1: Topic 2 - Pagination

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 TOPIC 2: Pagination Strategy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎤 [Optimistic Practitioner]:
I propose Cursor-based pagination.
- Maintains consistency with real-time data changes
- Superior performance with large datasets (O(1) vs O(n))

🎤 [Critical Practitioner]:
Cursor approach has drawbacks too.
- Cannot jump directly to specific page
- Increased implementation complexity
- Cursor invalidation when sort criteria changes

🎤 [UX Expert]:
Admin pages need "Go to page 5" functionality,
how would this be handled with Cursor approach?

🎤 [Optimistic Practitioner]:
We can separate Admin API and User API -
Admin uses Offset, User uses Cursor.

🎤 [Performance Expert]:
Hybrid approach increases maintenance burden.
Better to unify at least User API with Cursor.

🎤 [Critical Practitioner]:
User API is mostly infinite scroll, so Cursor is suitable.
I agree with the hybrid proposal.

✅ CONCLUSION:
Hybrid approach agreed
- User API: Cursor-based
- Admin API: Offset-based (limited data volume)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Phase 1: Topic 3 - Error Handling (Deferred)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 TOPIC 3: Error Response Format
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎤 [Optimistic Practitioner]:
I propose RFC 7807 (Problem Details) standard.
Detailed error information aids debugging.

🎤 [Security Expert]:
Detailed error information exposes system info to attackers.
Production should return minimal information only.

🎤 [UX Expert]:
But showing users only "An error occurred"
doesn't tell them what they did wrong.

🎤 [Security Expert]:
We need to distinguish user input errors from system errors.
4xx should be detailed, 5xx should be minimal.

🎤 [Critical Practitioner]:
Different responses per environment causes test/production inconsistency.

[Moderator]
Opinions are at an impasse.
Need to verify if there are security guidelines for error responses.

**Suspension Reason**: Fact-check needed
**Required Information**: Company security policy guidelines for API error responses
**Resumption Condition**: Re-discuss after policy verification

⏸️ CONCLUSION: Deferred - Security policy verification needed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Final Output

**SUMMARY.md**:

| Topic | Conclusion | Rationale |
|-------|------------|-----------|
| Authentication | JWT + Refresh Token | Conditional agreement with Rotation + Fingerprint |
| Pagination | Hybrid (User: Cursor, Admin: Offset) | Optimization by use case |
| Error Handling | Deferred | Security policy verification needed |

---

## Example 2: API 설계 검토 (한국어)

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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 TOPIC 1: 인증 방식
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎤 [긍정적 실무자]:
JWT + Refresh Token 방식을 제안합니다.
- Stateless하여 서버 확장에 유리
- 모바일/웹 클라이언트 모두 지원 용이
- Access Token 15분, Refresh Token 7일로 설정 권장

🎤 [부정적 실무자]:
JWT 방식의 리스크를 지적합니다.
- Token 탈취 시 만료까지 무효화 불가
- Payload 크기로 인한 네트워크 오버헤드
- Refresh Token 저장 위치 보안 이슈

🎤 [보안전문가]:
Refresh Token Rotation은 적용 예정인가요?
탈취 감지를 위한 추가 메커니즘이 필요해 보입니다.

🎤 [긍정적 실무자]:
네, Refresh Token Rotation과 함께
Device Fingerprint 검증을 추가할 수 있습니다.

🎤 [성능전문가]:
JWT 검증 시 매 요청마다 signature 검증이 필요한데,
Redis 캐싱으로 검증 결과를 저장하면 부하를 줄일 수 있습니다.

🎤 [UX전문가]:
사용자 관점에서 Silent Refresh가 잘 동작한다면
세션 방식과 UX 차이가 없을 것 같습니다.

🎤 [부정적 실무자]:
보안전문가의 우려가 타당합니다.
Refresh Token Rotation + Device Fingerprint 조건으로
JWT 방식에 동의할 수 있습니다.

✅ CONCLUSION:
JWT + Refresh Token 방식 합의
조건: Refresh Token Rotation, Device Fingerprint 검증 필수
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 최종 산출물

**SUMMARY.md**:

| 토픽 | 결론 | 근거 |
|------|------|------|
| 인증 방식 | JWT + Refresh Token | Rotation + Fingerprint 조건부 합의 |
| 페이지네이션 | 하이브리드 (User: Cursor, Admin: Offset) | 용도별 최적화 |
| 에러 처리 | 보류 | 보안 정책 확인 필요 |

---

## Example 3: Policy Document Review (English)

### User Request

```
User: Review the remote work policy proposal from legal, HR, and field manager perspectives.
```

### Phase 0: Discussion Preparation

```
[Moderator]
Preparing for discussion.

**Review Target**: Remote Work Policy Proposal
**Expert Panel**: Legal Expert, HR Expert, Field Manager (3 members)
**Topic Division**:
  1. Work Hour Tracking
  2. Equipment/Expense Policies
  3. Performance Evaluation Criteria

Starting discussion.
```

(Discussion proceeds with same structure...)
