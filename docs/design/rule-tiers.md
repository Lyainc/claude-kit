# Rule Management: 3-Tier Architecture & Safety Guards

이 문서는 시스템 전반에 적용되는 규칙(Rule)의 관리 아키텍처와 계층적 적용 우선순위, 그리고 안전한 실행을 위한 안전판(Safety Guards)을 정의합니다.

> **주의:** 헌법(Constitution) 및 기본 정책(Policy) 목록 자체는 **Issue #99 Boundary 단일 출처** 문서를 참조하십시오. 본 문서에서는 규칙의 적용 및 관리 방식만 다루며, 구체적인 규칙을 절대 재정의하지 않습니다.

## 1. 3-Tier Rule Architecture (규칙 계층 구조)

규칙은 다음과 같이 3개의 계층(Tier)으로 관리되며, 구체적인 범위가 설정된 규칙일수록 상위 우선순위를 갖습니다.

> **번호 표기 주의:** Tier 번호는 *우선순위 순위*가 아니라 *적용 범위(specificity/scope)* 를 나타냅니다 — Tier 1(Default)이 가장 넓은 기본 범위, Tier 3(Project-local)이 가장 좁은 범위예요. 우선순위는 그 반대로, 범위가 좁을수록(번호가 클수록) 높습니다(아래 병합 우선순위 참조). 따라서 "Tier 1 = 최우선"이라는 일반 관례와 반대 방향이라는 점에 주의하세요.

### 병합 우선순위 (Merge Priority)
**Project-local > User-global > Default**

1. **Tier 3: Project-local (`.claude/*.local.md`)**
   - **우선순위:** 1 (최상위)
   - 특정 프로젝트나 워크스페이스에만 적용되는 규칙입니다.
   - 프로젝트별 컨텍스트와 도메인 지식, 코딩 컨벤션, 제한 사항 등이 포함됩니다.
   - 위치: 프로젝트 최상단 디렉토리 내 `.claude` 폴더 아래 위치.

2. **Tier 2: User-global (`Vault type:rule`)**
   - **우선순위:** 2 (중간)
   - 사용자의 Obsidian Vault(또는 통합 Vault)에서 `type:rule` 프론트매터(Frontmatter)로 선언된 규칙 노트입니다.
   - 사용자의 개인적인 작업 방식, 범용적인 선호 스타일, 여러 프로젝트에 걸쳐 공통적으로 적용해야 하는 규칙 등을 포함합니다.
   - 시스템 전반에 걸쳐 사용자의 글로벌 환경설정 역할을 합니다.

3. **Tier 1: Default**
   - **우선순위:** 3 (최하위 - 기본값)
   - 시스템에 기본으로 내장된 기본 가이드라인 및 헌법입니다.
   - `AGENTS.md`나 시스템 기본 프롬프트(System Prompt) 등에 포함된 일반적인 에이전트 동작 원칙.

## 2. 안전판 (Safety Guards)

여러 계층의 규칙이 병합되어 실행될 때 발생할 수 있는 충돌이나 예상치 못한 동작을 방지하기 위해 다음 4가지 안전판을 적용합니다.

1. **확인게이트 (Confirmation Gate)**
   - 파괴적인 작업(삭제, 덮어쓰기)이나 외부 시스템/네트워크와 강하게 상호작용하는 경우, 상위 계층의 규칙에 자동 실행(Auto-continue)이 명시되어 있더라도 자동으로 넘어가기 전 사용자에게 확인을 요청하는 명시적 승인 단계입니다.
   
2. **근거첨부 (Evidence Attachment)**
   - 시스템이 특정 동작을 수행할 때, 어떤 계층의 규칙(예: Project-local의 특정 규칙 파일)에 의해 해당 판단을 내렸는지 근거(Citation/Trace)를 명시해야 합니다.
   - 툴 사용 전/후 로그나 커밋 메시지 트레일러에 병합 우선순위에 따른 결정 근거를 남깁니다.

3. **stale재검토 (Stale Review)**
   - User-global이나 Project-local에 선언된 규칙 파일 중 장기간 업데이트되지 않은 규칙(예: 수개월 이상 방치)에 대해 적용 전 유효성을 재확인(Review)하거나, 사용자에게 알림을 주어 시대에 뒤떨어진 규칙이 시스템 동작을 방해하거나 현재 시스템 상태와 충돌하지 않도록 방지합니다.

4. **끄기스위치 (Kill Switch)**
   - 특정 상위 계층의 규칙이 시스템의 정상적인 동작을 심각하게 저해하거나 무한루프 등을 발생시킬 때, 즉시 해당 규칙(User-global 또는 Project-local)의 적용을 우회(Bypass)하거나 비활성화할 수 있는 비상 탈출구입니다. 시스템 동작의 복원력을 보장합니다.
   - **헌법은 끌 수 없음(immutable):** 끄기스위치는 **정책(policy) 규칙에만** 적용됩니다. 헌법(constitutional) 규칙(CON-1~5, `claude-kit-boundary.md` §5)은 어느 Tier·끄기스위치로도 우회·비활성화할 수 없습니다. 헌법 규칙이 동작을 막는 것처럼 보이면 끄는 게 아니라 설계를 재검토해야 합니다.

## 3. Integration: Goal-Doc (#100) 연동

Goal 문서(Issue #100)에서 각 목표 실행 시 어떤 규칙 계층(Tier)을 어느 수준까지 반영할지 명시적으로 선언할 수 있도록 연결 필드를 제공합니다.

- **`rule_tiers` 필드 연결 지점:**
  Goal-Doc 프론트매터나 설정 블록 내에서 다음과 같이 사용할 Tier를 선언하여 정책을 주입할 수 있습니다.

  ```yaml
  goal_metadata:
    enforce_rules:
      - project-local
      - user-global
      - default
    safety_guards:
      ignore_stale: false  # stale 규칙 자동 무시 여부 (stale재검토 연동)
      strict_confirmation: true # 확인게이트 강화 여부
  ```

- **동작 방식:**
  에이전트는 목표(Goal) 실행 전에 이 필드를 참조하여, 어떤 계층의 규칙 스택을 병합(Merge)하여 프롬프트 컨텍스트에 로드할지 결정합니다. 이를 통해 각 Issue/Goal의 성격에 따라 유연하게 규칙의 강도를 조절하고 안전판 적용 수준을 제어할 수 있습니다.
