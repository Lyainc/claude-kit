# 미해결 이슈

## 1. 다중 vault 지원
**상황**: 한 사용자가 여러 Obsidian vault를 운영할 수 있음 (work vault, personal vault 등).
**현재 전제**: `~/vault/` 단일 경로 하드코딩.
**영향**: 포인터 파일의 `vault_path`가 상대 경로라서 vault 루트가 바뀌면 모호해짐.
**제안 방향**: `vault_root: ~/work-vault` 필드 추가 옵션화, 기본값 `~/vault/` 유지.
**보류 사유**: 현재 사용자(1인) 기준 단일 vault가 표준. 다중 vault 요구가 나왔을 때 대응.

## 2. CI / 원격 환경 동작
**상황**: vault가 없는 CI 환경에서 `.vault-link`가 있으면 vault-searcher가 어떻게 동작해야 하는가.
**후보 거동**:
- A. `.vault-link` 파싱만 시도, vault 경로 없으면 graceful no-op + 경고 로그
- B. 환경변수 `VAULT_BRIDGE_DISABLE=1` 로 완전 비활성
**영향**: CI에서 vault-searcher 호출이 실패로 판정되면 빌드 브레이크.
**보류 사유**: vault-searcher의 에러 처리 정책 전반을 건드려야 함. 별도 설계 필요.

## 3. 포인터 파일 스키마 진화
**상황**: MVP는 `vault_path:` 한 필드. 향후 `scope`, `read_only`, `auto_sync_session_notes` 등 필드 확장 요구가 생길 수 있음.
**리스크**: 스키마 breaking change 시 기존 `.vault-link` 호환성.
**제안 방향**: `version: 1` 필드 선택적 추가, 없으면 v1으로 간주. v2 도입 시 명시.
**보류 사유**: MVP 단계에서 버전 필드 강제는 오버엔지니어링. 2차 확장 시점에 판단.
