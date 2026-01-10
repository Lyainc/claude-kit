---
name: docx

description: |
  Word 문서 생성, 편집, 분석. When Claude needs to work with professional documents (.docx files) for:
  (1) Creating new documents, (2) Modifying or editing content, (3) Working with tracked changes,
  (4) Adding comments, or any other document tasks.
  Use when the user mentions 문서 작성, 워드, 계약서, 리뷰, 변경 추적, 문서 편집.
---

# DOCX 생성, 편집, 분석

Word 문서 파일(.docx) 작업을 위한 종합 스킬. 변경 추적, 코멘트, 포맷 보존, 텍스트 추출 지원.

## Overview

.docx 파일은 XML 파일과 리소스를 포함하는 ZIP 아카이브입니다. 작업 유형에 따라 다른 도구와 워크플로우를 사용합니다.

## When to Use

- 새로운 문서 생성 (계약서, 보고서, 기술 문서)
- 기존 문서 수정 및 편집 (변경 추적 포함)
- 문서 리뷰 및 코멘트 작업
- 문서 내용 분석 및 텍스트 추출
- 법률/학술/비즈니스 문서 작업

## Core Workflows

### Workflow Decision Tree

**문서 읽기/분석**:

- 텍스트만 필요 → Text extraction
- 구조/포맷/코멘트 필요 → Raw XML access

**새 문서 생성**:

- docx-js 워크플로우 사용

**기존 문서 편집**:

- 본인 문서 + 간단한 수정 → Basic OOXML editing
- 타인 문서 → **Redlining workflow** (권장)
- 법률/학술/비즈니스/정부 문서 → **Redlining workflow** (필수)

### 1. 텍스트 추출 및 분석

문서의 텍스트 내용만 필요한 경우 pandoc으로 markdown 변환:

```bash
# 변경 추적이 포함된 문서를 markdown으로 변환
pandoc --track-changes=all path-to-file.docx -o output.md

# 옵션: --track-changes=accept/reject/all
```

### 2. Raw XML 접근

코멘트, 복잡한 포맷팅, 문서 구조, 임베디드 미디어, 메타데이터 작업 시 필요.

**파일 언팩**:

```bash
python ooxml/scripts/unpack.py <office_file> <output_directory>
```

**주요 파일 구조**:

- `word/document.xml` - 문서 본문
- `word/comments.xml` - document.xml에서 참조되는 코멘트
- `word/media/` - 임베디드 이미지 및 미디어 파일
- 변경 추적: `<w:ins>` (삽입), `<w:del>` (삭제) 태그

### 3. 새 Word 문서 생성

새 문서를 처음부터 작성할 때는 **docx-js** 사용 - JavaScript/TypeScript로 Word 문서 생성.

**워크플로우**:

1. **필수 - docx-js.md 전체 읽기**: [docx-js.md](docx-js.md) (~500줄) 처음부터 끝까지 완전히 읽기. **절대 range limit 설정 금지**. 상세 문법, 중요 포맷 규칙, 모범 사례 파악 후 진행.
2. JavaScript/TypeScript 파일 생성 - Document, Paragraph, TextRun 컴포넌트 사용 (의존성은 설치되어 있다고 가정, 미설치 시 Dependencies 섹션 참조)
3. `Packer.toBuffer()`로 .docx 내보내기

### 4. 기존 Word 문서 편집

기존 문서 편집 시 **Document library** (OOXML 조작용 Python 라이브러리) 사용. 라이브러리가 인프라 설정을 자동 처리하며, 문서 조작 메서드 제공. 복잡한 시나리오에서는 라이브러리를 통해 기저 DOM에 직접 접근 가능.

**워크플로우**:

1. **필수 - ooxml.md 전체 읽기**: [ooxml.md](ooxml.md) (~600줄) 처음부터 끝까지 완전히 읽기. **절대 range limit 설정 금지**. Document library API 및 문서 파일 직접 편집을 위한 XML 패턴 학습.
2. 문서 언팩: `python ooxml/scripts/unpack.py <office_file> <output_directory>`
3. Document library 사용하여 Python 스크립트 생성 및 실행 (ooxml.md "Document Library" 섹션 참조)
4. 최종 문서 팩: `python ooxml/scripts/pack.py <input_directory> <office_file>`

Document library는 일반 작업용 high-level 메서드와 복잡한 시나리오용 직접 DOM 접근 모두 제공.

### 5. 문서 리뷰용 Redlining Workflow

markdown으로 종합적 변경 계획 수립 후 OOXML에 구현하는 워크플로우. **중요**: 완전한 변경 추적을 위해 모든 변경사항을 체계적으로 구현해야 함.

**배치 전략**: 관련 변경사항을 3-10개 단위로 그룹화. 디버깅 가능하면서 효율성 유지. 각 배치 테스트 후 다음 진행.

#### 원칙: 최소, 정확 편집

변경 추적 구현 시 실제로 변경되는 텍스트만 마킹. 변경되지 않은 텍스트 반복은 리뷰를 어렵게 하고 비전문적. 교체 시: [변경 없는 텍스트] + [삭제] + [삽입] + [변경 없는 텍스트]로 분할. 원본 run의 RSID 보존 (원본에서 `<w:r>` 요소 추출 후 재사용).

예시 - 문장에서 "30 days"를 "60 days"로 변경:
```python
# 나쁨 - 전체 문장 교체
'<w:del><w:r><w:delText>The term is 30 days.</w:delText></w:r></w:del><w:ins><w:r><w:t>The term is 60 days.</w:t></w:r></w:ins>'

# 좋음 - 변경된 부분만 마킹, 변경 없는 텍스트의 원본 <w:r> 보존
'<w:r w:rsidR="00AB12CD"><w:t>The term is </w:t></w:r><w:del><w:r><w:delText>30</w:delText></w:r></w:del><w:ins><w:r><w:t>60</w:t></w:r></w:ins><w:r w:rsidR="00AB12CD"><w:t> days.</w:t></w:r>'
```

#### Tracked Changes Workflow

1. **Markdown 표현 얻기**: 변경 추적이 보존된 markdown으로 문서 변환:
   ```bash
   pandoc --track-changes=all path-to-file.docx -o current.md
   ```

2. **변경사항 식별 및 그룹화**: 문서 검토하여 필요한 모든 변경사항 식별, 논리적 배치로 구성:

   **위치 지정 방법** (XML에서 변경 위치 찾기):
   - 섹션/제목 번호 (예: "Section 3.2", "Article IV")
   - 단락 식별자 (번호가 있는 경우)
   - 고유한 주변 텍스트로 grep 패턴
   - 문서 구조 (예: "first paragraph", "signature block")
   - **Markdown 줄 번호 사용 금지** - XML 구조와 매핑되지 않음

   **배치 구성** (관련 변경사항 3-10개씩 그룹화):
   - 섹션별: "Batch 1: Section 2 amendments", "Batch 2: Section 5 updates"
   - 유형별: "Batch 1: Date corrections", "Batch 2: Party name changes"
   - 복잡도별: 간단한 텍스트 교체부터 시작, 복잡한 구조 변경은 나중에
   - 순차적: "Batch 1: Pages 1-3", "Batch 2: Pages 4-6"

3. **문서 읽기 및 언팩**:
   - **필수 - ooxml.md 전체 읽기**: [ooxml.md](ooxml.md) (~600줄) 처음부터 끝까지 완전히 읽기. **절대 range limit 설정 금지**. "Document Library" 및 "Tracked Change Patterns" 섹션에 특히 주목.
   - **문서 언팩**: `python ooxml/scripts/unpack.py <file.docx> <dir>`
   - **제안된 RSID 기록**: 언팩 스크립트가 변경 추적에 사용할 RSID를 제안. 4b 단계에서 사용할 RSID 복사.

4. **배치 단위로 변경사항 구현**: 변경사항을 논리적으로 그룹화 (섹션별, 유형별, 근접성별)하여 단일 스크립트로 함께 구현. 이 접근법:
   - 디버깅 용이 (작은 배치 = 오류 격리 쉬움)
   - 점진적 진행 가능
   - 효율성 유지 (배치 크기 3-10개가 적절)

   **권장 배치 그룹화**:
   - 문서 섹션별 (예: "Section 3 changes", "Definitions", "Termination clause")
   - 변경 유형별 (예: "Date changes", "Party name updates", "Legal term replacements")
   - 근접성별 (예: "Changes on pages 1-3", "Changes in first half of document")

   각 배치별 관련 변경사항:

   **a. 텍스트를 XML에 매핑**: `word/document.xml`에서 텍스트 grep하여 `<w:r>` 요소 간 텍스트 분할 방식 확인.

   **b. 스크립트 생성 및 실행**: `get_node`로 노드 찾기, 변경 구현, `doc.save()`. **"Document Library"** 섹션 (ooxml.md) 패턴 참조.

   **참고**: 스크립트 작성 직전 항상 `word/document.xml` grep하여 현재 줄 번호 확인 및 텍스트 내용 검증. 각 스크립트 실행 후 줄 번호 변경됨.

5. **문서 팩**: 모든 배치 완료 후 언팩 디렉토리를 .docx로 변환:
   ```bash
   python ooxml/scripts/pack.py unpacked reviewed-document.docx
   ```

6. **최종 검증**: 완성 문서 종합 확인:
   - 최종 문서를 markdown으로 변환:
     ```bash
     pandoc --track-changes=all reviewed-document.docx -o verification.md
     ```
   - 모든 변경사항 정확히 적용되었는지 검증:
     ```bash
     grep "original phrase" verification.md  # 찾으면 안 됨
     grep "replacement phrase" verification.md  # 찾아야 함
     ```
   - 의도하지 않은 변경사항 없는지 확인

## Advanced Features

### 문서를 이미지로 변환

Word 문서 시각적 분석을 위해 2단계 프로세스로 이미지 변환:

1. **DOCX를 PDF로**:
   ```bash
   soffice --headless --convert-to pdf document.docx
   ```

2. **PDF 페이지를 JPEG 이미지로**:
   ```bash
   pdftoppm -jpeg -r 150 document.pdf page
   ```
   `page-1.jpg`, `page-2.jpg` 등으로 생성됨.

**옵션**:

- `-r 150`: 해상도 150 DPI (품질/크기 균형 조정)
- `-jpeg`: JPEG 포맷 출력 (PNG 선호 시 `-png`)
- `-f N`: 변환 시작 페이지 (예: `-f 2`는 페이지 2부터)
- `-l N`: 변환 종료 페이지 (예: `-l 5`는 페이지 5까지)
- `page`: 출력 파일 접두어

특정 범위 예시:
```bash
pdftoppm -jpeg -r 150 -f 2 -l 5 document.pdf page  # 페이지 2-5만 변환
```

## Code Style Guidelines

**중요**: DOCX 작업 코드 생성 시:

- 간결한 코드 작성
- 장황한 변수명 및 불필요한 연산 지양
- 불필요한 print 문 지양

## References

- **JavaScript Document Creation**: [docx-js.md](docx-js.md) - docx-js 라이브러리 상세 가이드
- **OOXML Editing**: [ooxml.md](ooxml.md) - Office Open XML 기술 참조
- **Scripts**: [ooxml/scripts/](ooxml/scripts/) - 유틸리티 스크립트 모음

## Dependencies

필수 의존성 (설치 필요):

```bash
# System packages (Linux)
sudo apt-get install pandoc          # 텍스트 추출
sudo apt-get install libreoffice     # PDF 변환
sudo apt-get install poppler-utils   # pdftoppm (PDF to image)

# Python
pip install defusedxml               # 안전한 XML 파싱

# Node.js
npm install -g docx                  # 새 문서 생성용
```

## Quick Start

**텍스트 추출**:

```bash
pandoc --track-changes=all doc.docx -o output.md
```

**새 문서 생성**:

```text
1. docx-js.md 전체 읽기
2. JS/TS 파일 작성 (Document, Paragraph, TextRun)
3. Packer.toBuffer()로 내보내기
```

**기존 문서 편집**:

```text
1. ooxml.md 전체 읽기
2. unpack.py로 언팩
3. Document library로 Python 스크립트 작성/실행
4. pack.py로 재팩
```

**변경 추적 리뷰**:

```text
1. pandoc으로 markdown 변환
2. 변경사항 식별 및 배치 구성
3. ooxml.md 읽기 및 문서 언팩
4. 배치별 변경 구현
5. 문서 팩 및 최종 검증
```
