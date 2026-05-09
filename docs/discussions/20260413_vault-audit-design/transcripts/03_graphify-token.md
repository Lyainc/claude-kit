# Transcript 03 — graphify Dependency & Token Reduction Target

## Briefing

**[Optimistic Practitioner]**: graphify `graph.json` 재활용하면 community/orphan 무료 확보.

**[Critical Practitioner]**: graphify는 외부 skill, 사용자 대부분 미설치. 필수 의존 = 설치 장벽. md-only 볼트에서 `--update`가 LLM 호출로 비용 증가 가능.

## Q&A

**[Architecture Expert]**: Soft dependency 원칙. `graph.json` 있으면 활용, 없으면 `[[link]]` 정규식 파서 폴백. 5만 노트도 수 초.

**[Performance Expert]**: 10x 감축은 조건부. 전제: (1) Pass A가 95% 필터링, (2) Pass B는 진짜 ambiguous만. 실측 없음. 보수적으로 3~5x 공약, 10x는 목표. embedding 모델(로컬 vs API) 영향 큼.

**[Data Integrity Expert]**: `graph.json` 외부 캐시로 쓸 때 stale 체크 필수. graphify `--update` 시각과 vault 변경 시각 어긋나면 오판. sidecar에 의존 시각 기록.

**[PKM Expert]**: graphify Obsidian export는 "해석된 뷰". 원본 볼트와 분리 저장 권장. 입력으로 쓰되 출력은 섞지 말 것.

## Dialectic

- Thesis: graphify 필수
- Antithesis: 완전 독립
- Synthesis: Soft dependency + `--use-graphify` 플래그. 토큰 목표 3~5x 공약, 10x 보너스.

## Conclusion

**결론**: graphify 선택적 가속기. 10x는 희망사항, 측정 인프라로 실측 재조정.
