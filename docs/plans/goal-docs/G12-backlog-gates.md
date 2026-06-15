---
goal_id: G12
title: backlog/deferred 결정 게이트 추적
issues: [94, 113, 114, 115, 117]
wave: 게이트
depends_on: []
recommended_model: haiku
status: gated
work_type: decision-only
created: 2026-06-03
---

# G12 — backlog/deferred 결정 게이트 추적

## 배경 / 목적

claude-kit 백로그에는 착수가 연기된 항목 5개가 있어요. 이들은 기술적으로는 타당하지만, 선행 결정이나 외부 조건에 의존해서 현재는 차단돼 있어요. 이 문서는 **각 항목의 착수 불가 사유, 해제 기준, 재평가 시점**을 명확히 기록하는 게이트 추적용 문서예요. 실행 계획이 아니라 *언제 풀릴지*에 대한 명시적 조건을 남기는 거죠.

**응집도**: 모두 "이제는 아니다"라는 공통점. 단순히 우선순위가 낮은 게 아니라, 각각 정확한 해제 조건이 있어요.

**가치**: 6개월 뒤 누군가 이 이슈들을 다시 봤을 때 "왜 건들지 않았나" 하는 의문을 즉시 풀 수 있게 합니다.

---

## 포함 이슈

- **#94**: vault-bridge: migrate commands/ → skills/ (deferred to v2.0)
  - 슬래시 커맨드 6개를 skills/ 포맷으로 마이그레이션하는 아키텍처 변경. v2.0 출시 대기 중.
  
- **#113**: [backlog] documentation-only plugin set — gated on 3rd doc primitive
  - doc-concretize + doc-polish만으로는 얇은 플러그인. 3번째 format-agnostic primitive(예: md↔html 변환, template-fill) 등장 시 `doc-authoring` 플러그인 신설.
  
- **#114**: [backlog] multi-model expert-panel via MCP (perspective diversity)
  - 현재 single-model 역할 프롬프트 기반 expert-panel(#106 shipped). 다양성을 multi-model MCP로 확장하는 제안. 비용↑ + 효과 불확실로 보류.
  
- **#115**: [backlog] adversarial-review D5 — MORE/SAMRE protocols (surfaced, not discussed)
  - arXiv:2410.04663 기반 budgeted-stopping advocate 프로토콜(MORE, SAMRE). 아직 미논의 상태에서 표면화만 됨.
  
- **#117**: [backlog] W4 setup-wizard — claude-kit-welcome 온보딩 플러그인
  - 설계 완료(`docs/design/setup-wizard.md`) but 착수 안 됨. 재설계 스파인(#99~105) 완료 후 "여전히 필요한가" 재평가 필요.

---

## 완료 조건 (Definition of Done)

이 문서는 **실행 목표가 아니라 게이트 추적 문서**예요. 따라서 일반적인 "코드 완성" DoD 대신, **게이트 조건 확정 + 재평가 시점 기록**을 대신합니다:

- [ ] 각 이슈의 해제 조건이 명확하게 문서화됨 (쟁점과 트레이드오프 테이블)
- [ ] 각 항목의 현재 상태 확인 (이슈 comment history 검토, dependencies 재확인)
- [ ] 크로스청크 의존성 정리: #99~108(재설계 스파인)과의 순서 관계 명시
- [ ] 문서가 착수 전 재평가 기준으로 사용 가능한 수준

---

## 쟁점과 트레이드오프

| 이슈 | 현재 상태 | 해제 조건 | 우선도 | 근거 |
|------|---------|---------|--------|------|
| **#94** | 아키텍처 stable | v2.0 버전 결정 + marketplace migration 안정화 | Low | commands/ 포맷 검증됨; 기술부채 아님. skills/ 마이그레이션은 UI 개선이지만 런타임 이득 없음. |
| **#113** | thin plugin 위험 | 3번째 doc primitive 출현(md↔html, template-fill, issue-authoring 등) | Very Low | 현재 2개 스킬(doc-concretize, doc-polish)만으로는 전용 플러그인 정당화 부족. #101/#102 수렴 후 자연스럽게 진행됨. |
| **#114** | single-model shipped | 다중 모델 효과 실측 검증 + 비용 정당화 | Blocked | 현재 역할 프롬프트 기반(#106)이 이미 다양성 추구. MCP 추가는 토큰 3배↑인데, 실측 효과 없으면 비용낭비. |
| **#115** | 미논의(표면화만) | #107(C2: saturation 일반화) 통합 검토 + adversarial-review current STATE와의 정합성 검증 | Blocked | arXiv:2410.04663 논문 참고. 착수 전 현재 adversarial-review 아키텍처와 통합 방식 검토 필수. |
| **#117** | 설계 완료, 착수 안 됨 | 재설계 스파인(#99~105) 안정화 + "여전히 필요한가" 재평가 | Deferred | 설계 문서(`docs/design/setup-wizard.md`) 있으나, 3주 stale + 재설계 세션 미언급 = deprioritize 신호. 레이어 재설계 완료 후 필요성 재평가. |

---

## 슬라이스 순서

1. **게이트 조건 문서화** → 바인딩: 직접(메인 컨텍스트, 게이트 조건 + 해제 기준 분석·기록) | 대상 파일: 본 문서 | 산출: 이슈별 게이트 조건 표 + 착수 전 검증 체크리스트 | 검증: 모든 이슈의 해제 조건이 §쟁점과 트레이드오프 표에 명확히 기록됨

이 문서는 실행 goal이 아니라 게이트 추적 문서라, 위 슬라이스는 "각 이슈의 게이트 조건을 분석·기록"하는 단일 `직접` 슬라이스 하나뿐이에요(다단계 실행 시퀀스가 아님). 그 단일 슬라이스의 실제 작업 내용을 **착수 전 필요한 검증 체크리스트**로 아래에 풀어 적어요:

### 착수 전 검증 (각 이슈별)

**#94 착수 조건 확인**
- 확인 대상: vault-bridge/commands/ 현재 테스트 코드
- 명령어:
  ```bash
  # 기존 vault-bridge 테스트 확인
  python3 vault-bridge/scripts/test/test-discover.py
  python3 vault-bridge/scripts/test/test-pre-write-guard.py
  python3 vault-bridge/scripts/test/test-pre-access-guard.py
  python3 vault-bridge/scripts/test/test-vault-commit-message.py
  python3 vault-bridge/scripts/test/test-manifest-type-optin.py
  
  # JSON 매니페스트 유효성
  python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null
  python3 -m json.tool .claude-plugin/marketplace.json > /dev/null
  ```
- 통과 기준: 모든 테스트 통과 + JSON 유효성 확인
- 재평가: v2.0 versioning 결정 시점. 현재 v1.9.x 안정화 추적.

**#113 착수 조건 확인**
- 확인 대상: thinking-tools/skills/ 디렉토리 + #101/#102 결정 상태
- 명령어:
  ```bash
  # 현재 doc 관련 스킬 목록
  ls -la thinking-tools/skills/ | grep -E "doc-concretize|doc-polish"
  
  # trigger-regression 검사 (description 변경 감지)
  python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test
  ```
- 통과 기준: doc-concretize, doc-polish 외 3번째 doc primitive 감지될 때까지 차단
- 재평가: #101(output adapter), #102(centralized vs distributed) 이슈 resolve 후 자동 수렴

**#114 착수 조건 확인**
- 확인 대상: expert-panel shipped 상태 + MCP 가용성
- 명령어:
  ```bash
  # expert-panel 현재 구현 확인
  head -30 thinking-tools/skills/expert-panel/SKILL.md
  
  # MCP 서버 상태 (있다면)
  grep -r "mcp_servers" ~/.claude/settings.json 2>/dev/null || echo "No MCP configured"
  ```
- 통과 기준: 다중 모델 호출의 실측 효과(성능/비용 분석) 완료 + 블로깅/논문 수준의 근거 제시
- 재평가: 실제 dogfooding 1인+ 에서 multi-perspective 이득 측정 시점. telemetry 데이터 필요.

**#115 착수 조건 확인**
- 확인 대상: adversarial-review 현재 implementation + #107 C2 상태
- 명령어:
  ```bash
  # adversarial-review 현재 구조
  head -50 thinking-tools/skills/adversarial-review/SKILL.md
  
  # #107 issue 상태 확인 (외부)
  gh issue view 107 --json state,title
  ```
- 통과 기준: 
  - arXiv:2410.04663 논문 숙지 (MORE vs SAMRE 프로토콜 정리)
  - #107 C2(STATE/saturation 일반화) 통합 설계 완료
  - adversarial-review MECE(expert-panel과의 역할 분담) 재확인
- 재평가: #107 resolve 직후. 착수 전 설계 리뷰 필수.

**#117 착수 조건 확인**
- 확인 대상: 재설계 스파인(#99~105) 안정화 + 필요성 재평가
- 명령어:
  ```bash
  # 재설계 이슈 상태 확인
  gh issue view 99 --json state,title
  gh issue view 100 --json state,title
  gh issue view 101 --json state,title
  gh issue view 102 --json state,title
  gh issue view 103 --json state,title
  gh issue view 104 --json state,title
  gh issue view 105 --json state,title
  
  # 설계 문서 확인 (이미 있음)
  ls -lh docs/design/setup-wizard.md
  ```
- 통과 기준:
  - #99~105 모두 resolve 또는 안정화 도달
  - 설계 문서 재검토: 여전히 필요한가? (UI/UX 변화 반영)
  - 플러그인 이름 확정(`claude-kit-welcome` vs `claude-kit-tour` vs `claude-kit-onboarding`)
- 재평가: 재설계 스파인 완료 예상 시점(예: 2주 뒤). 워크스트림 활성화 판단.

---

## E2E 자가검증

이 문서의 검증은 **각 게이트가 여전히 활성인가**를 확인하는 것입니다:

```bash
# 1. 이슈 상태 확인 (모두 OPEN이어야 함)
echo "=== Issue Status ==="
gh issue view 94 --json state,title
gh issue view 113 --json state,title
gh issue view 114 --json state,title
gh issue view 115 --json state,title
gh issue view 117 --json state,title

# 2. vault-bridge 테스트 통과 (현재 착수 가능 상태 확인)
echo "=== Vault-Bridge Tests ==="
python3 vault-bridge/scripts/test/test-discover.py && echo "✓ test-discover" || echo "✗ test-discover"
python3 vault-bridge/scripts/test/test-pre-write-guard.py && echo "✓ test-pre-write-guard" || echo "✗ test-pre-write-guard"
python3 vault-bridge/scripts/test/test-pre-access-guard.py && echo "✓ test-pre-access-guard" || echo "✗ test-pre-access-guard"

# 3. thinking-tools trigger-regression 자가테스트
echo "=== Thinking-Tools Triggers ==="
python3 thinking-tools/scripts/test/check-trigger-regression.py --self-test && echo "✓ trigger-regression self-test" || echo "✗ trigger-regression self-test"

# 4. JSON 매니페스트 유효성
echo "=== JSON Validation ==="
python3 -m json.tool .claude-plugin/marketplace.json > /dev/null && echo "✓ marketplace.json" || echo "✗ marketplace.json"
python3 -m json.tool thinking-tools/.claude-plugin/plugin.json > /dev/null && echo "✓ thinking-tools plugin.json" || echo "✗ thinking-tools plugin.json"
python3 -m json.tool vault-bridge/.claude-plugin/plugin.json > /dev/null && echo "✓ vault-bridge plugin.json" || echo "✗ vault-bridge plugin.json"
python3 -m json.tool obsidian-vault-manager/.claude-plugin/plugin.json > /dev/null && echo "✓ ovm plugin.json" || echo "✗ ovm plugin.json"

# 5. 현재 디렉토리 구조 확인
echo "=== Directory Structure ==="
echo "vault-bridge/commands: $(ls vault-bridge/commands/ | wc -l) items"
echo "thinking-tools/skills: $(ls thinking-tools/skills/ | wc -l) items"
echo "docs/design/setup-wizard.md exists: $(test -f docs/design/setup-wizard.md && echo 'yes' || echo 'no')"
```

**통과 기준**:
- 모든 이슈가 OPEN 상태 유지
- 모든 기존 테스트 통과 (게이트 해제 조건 아님, 현재 상태 건강성만 확인)
- JSON 매니페스트 모두 유효
- 디렉토리 구조 무변화

---

## 의존성 / 순서 주의

### 크로스청크 게이트

1. **#94(commands→skills)** ← 선행: v2.0 버전 결정 (독립적, 기술 부채 아님)
2. **#113(doc-only plugin)** ← 선행: #101/#102 수렴, 그다음 자연스럽게
3. **#114(multi-model expert-panel)** ← 선행: dogfooding 데이터 필요 (6개월+ 추적)
4. **#115(adversarial D5)** ← 선행: #107 C2 통합 설계
5. **#117(setup-wizard)** ← 선행: 재설계 스파인 #99~105 완료

### 착수 금지 조건

- #94: v2.0 명시적 결정 전까지 미작업
- #113: 3번째 doc primitive 등장 전까지 미작업
- #114: MCP 비용/이득 실측 검증 전까지 미작업
- #115: #107 통합 검토 전까지 미작업
- #117: 재설계 스파인 완료 + 재평가 후에만 시작

### 문서 업데이트 시점

- 매월 첫째 주: 각 선행 조건(#99~107 resolve, 실측 데이터) 갱신
- 각 이슈 comment 추가 시: 게이트 조건 변화 있으면 이 문서에 반영
- 재설계 완료 시: #117 명시적 재평가

---

**작성 시점**: 2026-06-03  
**최종 검토**: (미완료)  
**다음 재평가**: 2026-07-03
