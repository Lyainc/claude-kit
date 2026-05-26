# Vault Second Brain v4 마이그레이션 가이드

> 작성일: 2026-05-26
> 대상: 기존 OVM vault 사용자
> 관련 문서: `docs/design/vault-second-brain-v4.md`

## 1. 변경 요약

```
이전 (7 폴더):                  v4 (3 폴더):
~/vault/                         ~/vault/
├── 00_Inbox/                    ├── inbox/
├── 10_MOC/                      ├── notes/
├── 20_Projects/                 └── assets/
├── 30_Notes/
├── 40_Resources/
├── 50_Archive/
└── 90_Assets/
```

OVM 스킬: 7개 → 3개 (`capture`, `note`, `audit`).

## 2. 마이그레이션 원칙

1. **frontmatter 안 건드림** — 기존 노트의 type/status는 그대로 보존
2. **wikilink 보존** — Obsidian이 파일 이동을 추적하도록 처리 (옵션 A 권장)
3. **롤백 가능** — git 커밋 단위로 단계 진행, snapshot 커밋으로 즉시 복귀 가능
4. **type 없는 노트는 invisible** — 옵트인 원칙. type 자동 추가 금지

## 3. 마이그레이션 절차

### 3.1 사전 준비

```bash
cd ~/vault
git add -A
git commit -m "snapshot before v4 migration"
git tag v4-migration-snapshot
```

`v4-migration-snapshot` 태그는 롤백 기준점이다.

### 3.2 폴더 이동 — 옵션 A (Obsidian UI 사용, 권장)

작은 vault (<200 파일) 또는 wikilink 다수 보유 시 권장.

**옵트인 원칙** (설계 §2.2): `type:` frontmatter가 *없는* 파일은 사용자 노트일 가능성이 크다. 자동 평탄화 대신 *원위치 유지* 또는 사용자 명시 이동을 권장한다.

1. Obsidian 설정 확인: `Files & Links → Automatically update internal links: ON`
2. 단순 1:1 매핑 (Obsidian 파일 탐색기에서 우클릭 → Rename):
   - `00_Inbox` → `inbox`
   - `30_Notes` → `notes`
   - `90_Assets` → `assets`
3. `10_MOC/*` → `notes/`로 이동 (파일 단위 드래그). 이동 후 빈 `10_MOC/` 삭제.
4. `20_Projects/{name}/` 처리 (각 프로젝트별, *2단계 분리*):
   - **a. `_index.md`를 먼저 rename**: Obsidian에서 `_index.md` 우클릭 → Rename → `{name}.md` 입력 (예: `claude-kit/_index.md` → `claude-kit.md`)
   - **b. rename 완료된 파일을 `notes/`로 이동**: 드래그 또는 Move to
   - **c. 같은 폴더의 다른 `.md` 파일 처리**: `type:` 있는 파일만 `notes/`로 이동. `type:` 없는 파일은 *원위치 유지* (사용자가 나중에 처리)
   - **d. 폴더가 비면 삭제**: Obsidian이 빈 폴더는 자동 정리, 잔여물 있으면 *그대로 둠*
5. `40_Resources/*` → `notes/`로 이동 (옵트인: `type:` 있는 파일만)
6. `50_Archive/*` → `notes/`로 이동 (옵트인: `type:` 있는 파일만, status는 §3.4에서 처리)
7. 빈 폴더 정리 (Obsidian 외부, 잔여 파일 없을 때만):
   ```bash
   rmdir 20_Projects/* 2>/dev/null
   rmdir 20_Projects 10_MOC 40_Resources 50_Archive 2>/dev/null
   ```
   *비어있지 않은 폴더는 `rmdir`이 실패하므로 안전*. 실패한 폴더는 사용자가 내용 검토 후 결정.

**잔여 폴더의 의미**: 마이그레이션 후 `20_Projects/`나 `40_Resources/`가 남아있다면 *type 없는 사용자 파일이 보존된 것*이다. 사용자가 검토 후 `notes/`로 직접 이동하거나, `type: note` 추가 후 다음 마이그레이션 라운드에서 처리.

### 3.3 폴더 이동 — 옵션 B (Shell + Python 일괄, 큰 vault용)

큰 vault (>200 파일)이거나 자동화가 필요한 경우. shell은 단순 매핑, Python은 옵트인 + 충돌 처리.

**안전장치**:
- `shopt -s nullglob`: glob 미매칭 시 빈 리스트 전달 (리터럴 `*.md` 방지)
- `mv -n` (no-clobber): 충돌 시 *덮어쓰기 거부*, 수동 검토용 로그 남김
- type 옵트인: `type:` 없는 파일은 원위치 유지
- 충돌 로그: `/tmp/v4-migration-conflicts.log`

```bash
cd ~/vault
shopt -s nullglob
LOG=/tmp/v4-migration-conflicts.log
: > "$LOG"

# Step 1: 신규 폴더 생성
mkdir -p inbox notes assets

# Step 2: 단순 1:1 매핑 (충돌 시 -n으로 거부, 로그 기록)
move_safe() {
  local src="$1" dst="$2"
  for f in "$src"/*; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    if [ -e "$dst/$base" ]; then
      echo "CONFLICT: $f → $dst/$base (이미 존재, skip)" >> "$LOG"
    else
      mv -n "$f" "$dst/"
    fi
  done
}

move_safe 00_Inbox inbox && rmdir 00_Inbox 2>/dev/null
move_safe 30_Notes notes && rmdir 30_Notes 2>/dev/null
move_safe 90_Assets assets && rmdir 90_Assets 2>/dev/null

# Step 3: 10_MOC → notes (평탄화)
move_safe 10_MOC notes && rmdir 10_MOC 2>/dev/null
```

**Step 4: 20_Projects, 40_Resources, 50_Archive 처리 — Python (type 옵트인 + 충돌 처리)**

```bash
python3 << 'PYEOF'
import os, re, shutil, sys

VAULT = os.path.expanduser("~/vault")
LOG = "/tmp/v4-migration-conflicts.log"
NOTES = os.path.join(VAULT, "notes")
FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def has_type(path):
    """frontmatter에 type: 필드 존재 여부."""
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(4096)
    except (OSError, UnicodeDecodeError):
        return False
    m = FM_RE.match(head)
    if not m:
        return False
    return bool(re.search(r"^type:\s*\S+", m.group(1), re.MULTILINE))

def move_typed(src_file, dst_file, log):
    """type 있는 파일만 이동. 충돌 시 skip + 로그."""
    if os.path.exists(dst_file):
        log.write(f"CONFLICT: {src_file} → {dst_file} (이미 존재, skip)\n")
        return False
    shutil.move(src_file, dst_file)
    return True

def process_project_dir(proj_dir, log):
    """20_Projects/{name}/ 처리: _index.md rename + type 있는 파일만 이동."""
    name = os.path.basename(proj_dir.rstrip("/"))
    # a. _index.md → notes/{name}.md
    idx = os.path.join(proj_dir, "_index.md")
    if os.path.isfile(idx):
        dst = os.path.join(NOTES, f"{name}.md")
        if os.path.exists(dst):
            log.write(f"CONFLICT: {idx} → {dst} (이미 존재, skip — 수동 처리)\n")
        else:
            shutil.move(idx, dst)
    # b. type 있는 다른 .md 파일만 이동
    for f in os.listdir(proj_dir):
        full = os.path.join(proj_dir, f)
        if not os.path.isfile(full) or not f.endswith(".md"):
            continue
        if has_type(full):
            move_typed(full, os.path.join(NOTES, f), log)
        else:
            log.write(f"SKIP (no type): {full} — 원위치 유지\n")

def process_flat_dir(src_dir, log):
    """40_Resources, 50_Archive 처리: type 있는 .md만 이동."""
    if not os.path.isdir(src_dir):
        return
    for f in os.listdir(src_dir):
        full = os.path.join(src_dir, f)
        if not os.path.isfile(full) or not f.endswith(".md"):
            continue
        if has_type(full):
            move_typed(full, os.path.join(NOTES, f), log)
        else:
            log.write(f"SKIP (no type): {full} — 원위치 유지\n")

with open(LOG, "a", encoding="utf-8") as log:
    # 20_Projects
    proj_root = os.path.join(VAULT, "20_Projects")
    if os.path.isdir(proj_root):
        for d in os.listdir(proj_root):
            full = os.path.join(proj_root, d)
            if os.path.isdir(full):
                process_project_dir(full, log)
    # 40_Resources, 50_Archive
    process_flat_dir(os.path.join(VAULT, "40_Resources"), log)
    process_flat_dir(os.path.join(VAULT, "50_Archive"), log)

print(f"완료. 로그: {LOG}")
PYEOF
```

**Step 5: 빈 폴더 정리**

```bash
# 비어있는 폴더만 안전하게 제거 (rmdir은 비어있지 않으면 실패)
rmdir 20_Projects/*/ 2>/dev/null
rmdir 20_Projects 10_MOC 40_Resources 50_Archive 2>/dev/null

# 잔여 폴더 확인
for d in 20_Projects 40_Resources 50_Archive; do
  if [ -d "$d" ]; then
    echo "잔여: $d (type 없는 파일 있음 — 수동 검토)"
    ls "$d"
  fi
done
```

**Step 6: 충돌·skip 로그 검토**

```bash
cat /tmp/v4-migration-conflicts.log
```

- `CONFLICT:` 라인 → 동일 슬러그 파일이 이미 존재. 수동으로 rename 후 이동
- `SKIP (no type):` 라인 → type 없는 사용자 파일, 원위치 보존됨. 사용자가 검토 후 결정

**옵션 B 후속 작업**: shell·Python `mv`는 Obsidian wikilink를 자동 갱신하지 않는다. 이동 후 `/audit` 실행 + §4의 일괄 수정 스크립트로 처리.

### 3.4 Archive 노트에 `status: archived` 추가 (선택)

50_Archive에서 옮겨온 파일들에 archived 상태를 표시하려면:

```bash
# 마이그레이션 전에 archived 파일 목록 미리 저장 (Step 4 실행 전)
ls 50_Archive/*.md 2>/dev/null > /tmp/v4-archived-list.txt

# (Step 4·5 완료 후 실행) status: archived 부여
python3 << 'PYEOF'
import os, re, sys

LIST_FILE = "/tmp/v4-archived-list.txt"
NOTES_DIR = os.path.expanduser("~/vault/notes")
FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

if not os.path.isfile(LIST_FILE):
    print(f"archive 목록 파일 없음: {LIST_FILE}")
    sys.exit(0)

updated = skipped = errored = 0

with open(LIST_FILE, encoding="utf-8") as f:
    for line in f:
        old_path = line.strip()
        if not old_path:
            continue
        basename = os.path.basename(old_path)
        new_path = os.path.join(NOTES_DIR, basename)
        if not os.path.exists(new_path):
            skipped += 1
            continue
        try:
            with open(new_path, encoding="utf-8") as nf:
                content = nf.read()
        except UnicodeDecodeError as e:
            print(f"ERROR (인코딩): {new_path} — {e}")
            errored += 1
            continue
        m = FM_RE.match(content)
        if m:
            # 기존 frontmatter — status 필드 없으면 추가
            fm_body = m.group(1)
            if re.search(r"^status:\s*", fm_body, re.MULTILINE):
                # 이미 status 있음 — 덮어쓰지 않음 (수동 결정 영역)
                skipped += 1
                continue
            new_fm = fm_body.rstrip() + "\nstatus: archived"
            new_content = content.replace(m.group(0), f"---\n{new_fm}\n---", 1)
        else:
            # frontmatter 없음 — type도 없을 가능성 높지만 archived만 부여
            # 사용자가 type 옵트인을 안 했으므로 type은 추가하지 않음 (옵트인 원칙)
            new_content = f"---\nstatus: archived\n---\n" + content
        try:
            with open(new_path, "w", encoding="utf-8") as nf:
                nf.write(new_content)
            updated += 1
        except OSError as e:
            print(f"ERROR (쓰기): {new_path} — {e}")
            errored += 1

print(f"완료: updated={updated} skipped={skipped} errored={errored}")
PYEOF
```

이 단계는 **선택**이다. 50_Archive에 있던 노트가 *archive 상태로 분류*되어야 한다는 시멘틱 보존이 필요할 때만 실행.

**주의**:
- 인코딩 UTF-8 명시 (한국어 vault 안전)
- 이미 `status:` 있는 노트는 *덮어쓰지 않음* (사용자 의도 보존)
- frontmatter 없는 노트는 새로 생성하되 *type은 추가하지 않음* (옵트인 원칙 유지)

### 3.5 vault-bridge 매니페스트 재생성

shell `mv`는 파일 mtime을 보존하므로 `generate-manifest.py`의 incremental update가 변경 없음으로 판단할 수 있다. `--force` 필수:

```bash
python3 ~/.claude/plugins/cache/.../vault-bridge/scripts/generate-manifest.py \
  --vault-root ~/vault --force
```

플러그인 캐시 경로는 환경마다 다르다. `find ~/.claude -name "generate-manifest.py" | head -1`로 확인.

### 3.6 커밋

```bash
cd ~/vault
git add -A
git commit -m "migrate vault structure to v4 (3-folder + type marker)"
```

## 4. wikilink 호환성

| 옵션 | 적합한 경우 | 링크 처리 |
|------|------------|----------|
| **A. Obsidian UI 이동** | 작은 vault, wikilink 다수 | 자동 갱신 (Obsidian이 처리) |
| **B. Shell 일괄** | 큰 vault, 자동화 필요 | 수동 (audit + sed) |

옵션 B 사용 시 마이그레이션 후 즉시 `/audit`을 실행해 깨진 wikilink 보고를 확인하고, 발견된 깨진 링크는 다음 Python 스크립트로 일괄 수정 가능 (macOS/Linux 호환, alias 패턴 안전):

```bash
python3 << 'PYEOF'
import os, re

VAULT = os.path.expanduser("~/vault/notes")
# 처리할 경로 prefix: 마이그레이션 전 구조에서 이동된 폴더들
PREFIXES = ["20_Projects", "30_Notes", "40_Resources", "50_Archive", "10_MOC"]

# wikilink 패턴: [[path/to/file|alias]] 또는 [[path/to/file#heading]] 또는 [[path/to/file]]
# alias·heading은 보존, path만 평탄화
def rewrite(content):
    def repl(m):
        link = m.group(1)
        # alias 분리: file|alias → file, alias 보존
        if "|" in link:
            path, alias = link.split("|", 1)
        else:
            path, alias = link, None
        # heading 분리: file#heading
        if "#" in path:
            base, heading = path.split("#", 1)
        else:
            base, heading = path, None
        # 경로 prefix 제거 (마지막 segment만 남김)
        for pref in PREFIXES:
            if base.startswith(pref + "/"):
                base = base.rsplit("/", 1)[-1]
                break
        # 재조립
        out = base
        if heading:
            out += "#" + heading
        if alias:
            out += "|" + alias
        return f"[[{out}]]"
    return re.sub(r"\[\[([^\[\]]+)\]\]", repl, content)

changed = 0
for root, _, files in os.walk(VAULT):
    for fn in files:
        if not fn.endswith(".md"):
            continue
        path = os.path.join(root, fn)
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            print(f"SKIP (인코딩): {path}")
            continue
        new_content = rewrite(content)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            changed += 1
            print(f"updated: {path}")

print(f"총 {changed}개 파일 wikilink 갱신 완료")
PYEOF
```

**처리 규칙**:
- `[[20_Projects/foo/bar]]` → `[[bar]]`
- `[[20_Projects/foo/bar|별칭]]` → `[[bar|별칭]]` (alias 보존)
- `[[30_Notes/bar#섹션]]` → `[[bar#섹션]]` (heading 보존)
- 외부 URL이나 단순 `[[bar]]`는 변경 없음

**`PREFIXES` 커스터마이즈**: vault에 다른 prefix(예: `60_Personal`)가 있으면 리스트에 추가.

## 5. type 없는 노트 처리

이전 vault에서 `type:` frontmatter가 없는 노트의 처리:

- **claude-kit invisible**: `/audit`, `manifest.json`, vault-searcher의 type 필터에 안 나타남
- **Obsidian에선 정상 작동**: 그래프, 태그, 검색, wikilink 모두 OK
- **사용자가 원할 때만 type 추가**: 자동 일괄 추가 금지

이는 v4의 **옵트인 원칙**을 따른다 — vault는 사용자의 것이고 claude-kit은 *초대받은 곳*에서만 일한다.

## 6. 롤백

마이그레이션 중 문제 발생 또는 사후 결정에 따라 즉시 롤백 가능:

```bash
cd ~/vault
git reset --hard v4-migration-snapshot
```

마이그레이션 전 snapshot 커밋으로 복귀한다. 단, 마이그레이션 *이후*에 새로 작성한 노트가 있다면 별도 백업 필요.

## 7. 마이그레이션 후 검증

```bash
# Claude Code에서 실행
/audit
```

확인 항목:
- ✅ 깨진 wikilink 없음 (옵션 B 사용 시 핵심)
- ✅ 폴더 구조 v4 준수 (`inbox/`, `notes/`, `assets/`만 존재)
- ✅ type 있는 노트 카운트가 합리적인 값
- ⚠️ frontmatter 누락 노트 — 필요 시 수동 보완 (옵트인, 강제 X)

## 8. 신규 사용자 (마이그레이션 불필요)

vault가 없는 상태에서 v4를 처음 시작:

```bash
mkdir -p ~/vault/{inbox,notes,assets}
cd ~/vault
git init
git add -A
git commit --allow-empty -m "initial vault structure (v4)"
```

vault-bridge의 `/vault-link`로 현재 프로젝트와 vault 연결 후 사용 시작.

## 9. 알려진 한계

- **shell mv는 mtime 보존**: `generate-manifest.py`가 변경 없음으로 판단할 수 있어 `--force` 필수
- **Obsidian 닫힌 상태 shell 이동**: 옵션 B 사용 시 wikilink 자동 갱신 안 됨 → 수동 검증 필요
- **깊은 중첩 구조**: `20_Projects/{name}/{subdir}/*.md` 같은 2단계 이상 하위 구조는 자동 처리 안 됨. 수동 검토 후 평탄화 또는 사용자가 의도적으로 `notes/{subdir}/` 형태 유지

## 10. 마이그레이션 체크리스트

```
[ ] git snapshot 커밋 + v4-migration-snapshot 태그
[ ] (옵션 B 사전) ls 50_Archive/*.md > /tmp/v4-archived-list.txt
[ ] 옵션 A or B 선택
[ ] 폴더 이동 실행
[ ] (옵션 B) /tmp/v4-migration-conflicts.log 검토
[ ] (옵션 B) 깨진 wikilink Python 스크립트 (§4) 실행
[ ] (선택) 50_Archive 노트에 status: archived 추가 (§3.4)
[ ] manifest.json --force 재생성 (§3.5)
[ ] 마이그레이션 커밋
[ ] /audit 실행 + 결과 검토
[ ] Obsidian에서 graph view 정상 동작 확인
[ ] (선택) .gitattributes 설치 (설계 §4.3) — vault에 markdown diff 활성화
[ ] 잔여 폴더(20_Projects 등) 검토 — type 없는 파일 처리 결정
```
