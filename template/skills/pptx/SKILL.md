---
name: pptx

description: |
  Presentation creation, editing, and analysis. When Claude needs to work with presentations (.pptx files) for:
  (1) Creating new presentations, (2) Modifying or editing content, (3) Working with layouts,
  (4) Adding comments or speaker notes, or any other presentation tasks.
  Use when the user mentions 프레젠테이션, PPT, 슬라이드, 발표 자료, 파워포인트.
---

# PPTX 생성, 편집, 분석

PowerPoint 프레젠테이션 파일(.pptx) 작업을 위한 종합 스킬.

## Overview

.pptx 파일은 XML 파일과 리소스를 포함하는 ZIP 아카이브입니다. 작업 유형에 따라 다른 도구와 워크플로우를 사용합니다.

## When to Use

- 새로운 프레젠테이션 생성 (템플릿 없이 / 템플릿 기반)
- 기존 프레젠테이션 수정 및 편집
- 슬라이드 레이아웃, 코멘트, 발표자 노트 작업
- 프레젠테이션 내용 분석 및 텍스트 추출

## Core Workflows

### 1. 프레젠테이션 분석 (필수: 텍스트 + 시각적 맥락)

**중요**: 프레젠테이션 분석 시 텍스트만으로는 레이아웃/디자인 의도 파악 불가. **반드시 두 가지를 함께 확인**:

```bash
# Step 1: 텍스트 구조 추출
python -m markitdown path-to-file.pptx > content.md

# Step 2: 시각적 맥락 확보 (필수!)
python scripts/thumbnail.py path-to-file.pptx thumbnails
```

**분석 시 확인 사항**:

- 썸네일로 슬라이드 레이아웃 패턴 파악
- 텍스트와 시각적 배치 간 관계 이해
- 색상 팔레트, 폰트 스타일, 여백 패턴 관찰

### 2. Raw XML 접근

코멘트, 발표자 노트, 슬라이드 레이아웃, 애니메이션, 디자인 요소, 복잡한 포맷팅 작업 시 필요.

**파일 언팩**:
```bash
python ooxml/scripts/unpack.py <office_file> <output_dir>
```

**주요 파일 구조**:
- `ppt/presentation.xml` - 프레젠테이션 메타데이터 및 슬라이드 참조
- `ppt/slides/slide{N}.xml` - 개별 슬라이드 내용
- `ppt/notesSlides/notesSlide{N}.xml` - 발표자 노트
- `ppt/comments/modernComment_*.xml` - 슬라이드 코멘트
- `ppt/slideLayouts/` - 레이아웃 템플릿
- `ppt/slideMasters/` - 마스터 슬라이드
- `ppt/theme/` - 테마 및 스타일 정보
- `ppt/media/` - 이미지 및 미디어 파일

### 3. 새 프레젠테이션 생성 (템플릿 없이)

**html2pptx 워크플로우** 사용 - HTML 슬라이드를 정확한 위치로 PowerPoint 변환.

#### 디자인 원칙

**중요**: 프레젠테이션 생성 전 반드시 디자인 요소 분석:

1. **주제 고려**: 이 프레젠테이션의 주제는? 어떤 톤, 산업, 분위기를 제안하는가?
2. **브랜딩 확인**: 회사/조직 언급 시 브랜드 색상과 아이덴티티 고려
3. **콘텐츠에 맞는 팔레트**: 주제를 반영하는 색상 선택
4. **접근 방식 명시**: 코드 작성 전 디자인 선택 설명

**요구사항**:
- ✅ 코드 작성 전 콘텐츠 기반 디자인 접근 방식 명시
- ✅ 웹 안전 폰트만 사용: Arial, Helvetica, Times New Roman, Georgia, Courier New, Verdana, Tahoma, Trebuchet MS, Impact
- ✅ 크기, 굵기, 색상을 통한 명확한 시각적 계층 구조
- ✅ 가독성 확보: 강한 대비, 적절한 텍스트 크기, 깔끔한 정렬
- ✅ 일관성 유지: 슬라이드 전체에 걸쳐 패턴, 간격, 시각 언어 반복

**색상 팔레트 선택**:

창의적 선택 기준:
- **기본값을 넘어서기**: 이 특정 주제에 진정으로 맞는 색상은?
- **다각도 고려**: 주제, 산업, 분위기, 에너지 레벨, 타겟 청중, 브랜드 아이덴티티
- **모험적 시도**: 예상 밖 조합 (의료 = 초록, 금융 = 네이비 공식 탈피)
- **팔레트 구축**: 3-5개 색상 조합 (주색상 + 보조색 + 강조색)
- **대비 확보**: 배경 위 텍스트 명확한 가독성

**워크플로우**:

1. **필수 - html2pptx.md 전체 읽기**: 상세 문법, 포맷 규칙, 모범 사례 파악
2. HTML 파일 생성 (적절한 치수: 16:9는 720pt × 405pt)
   - 모든 텍스트 콘텐츠에 `<p>`, `<h1>`-`<h6>`, `<ul>`, `<ol>` 사용
   - 차트/테이블 영역에 `class="placeholder"` 사용 (회색 배경으로 렌더링)
   - **중요**: 그라디언트와 아이콘은 Sharp로 PNG 이미지화 후 HTML에 참조
   - **레이아웃**: 차트/테이블/이미지 슬라이드는 전체 슬라이드 또는 2단 레이아웃 사용
3. JavaScript 파일 생성 및 실행 - html2pptx.js 라이브러리 사용
   - `html2pptx()` 함수로 각 HTML 파일 처리
   - PptxGenJS API로 placeholder 영역에 차트/테이블 추가
   - `pptx.writeFile()`로 프레젠테이션 저장
4. **필수 - 시각적 검증 및 반복 수정**:
   - 썸네일 생성: `python scripts/thumbnail.py output.pptx workspace/thumbnails --cols 4`
   - **반드시 썸네일 확인 후 사용자에게 보고**
   - 확인 사항: 텍스트 잘림, 텍스트 겹침, 위치 문제, 대비 이슈
   - 문제 발견 시 HTML 수정 → 재생성 → 재검증 (문제 해결까지 반복)

### 4. 기존 프레젠테이션 편집

Office Open XML (OOXML) 포맷으로 작업. 언팩 → 편집 → 재팩 과정.

**워크플로우**:

1. **필수 - ooxml.md 전체 읽기**: OOXML 구조 및 편집 워크플로우 상세 가이드
2. 프레젠테이션 언팩: `python ooxml/scripts/unpack.py <office_file> <output_dir>`
3. XML 파일 편집 (주로 `ppt/slides/slide{N}.xml` 및 관련 파일)
4. **중요**: 편집 후 즉시 검증 및 에러 수정: `python ooxml/scripts/validate.py <dir> --original <file>`
5. 최종 프레젠테이션 팩: `python ooxml/scripts/pack.py <input_directory> <office_file>`

### 5. 템플릿 기반 프레젠테이션 생성

기존 템플릿의 디자인을 따르는 프레젠테이션 생성 시, 템플릿 슬라이드를 복제/재배열 후 placeholder 텍스트 교체.

**워크플로우**:

1. **템플릿 텍스트 추출 및 썸네일 생성**:
   - 텍스트: `python -m markitdown template.pptx > template-content.md`
   - 썸네일: `python scripts/thumbnail.py template.pptx`

2. **템플릿 분석 및 인벤토리 저장** (`template-inventory.md`):
   ```markdown
   # Template Inventory Analysis
   **Total Slides: [count]**
   **IMPORTANT: 슬라이드는 0-indexed (첫 슬라이드 = 0, 마지막 = count-1)**

   ## [Category Name]
   - Slide 0: [Layout code] - 설명/용도
   - Slide 1: [Layout code] - 설명/용도
   ...
   ```

3. **템플릿 인벤토리 기반 프레젠테이션 아웃라인 생성**:
   - **중요**: 레이아웃 구조를 실제 콘텐츠와 일치시키기
   - 실제 콘텐츠 개수를 세고 적절한 레이아웃 선택
   - `outline.md`에 콘텐츠 및 템플릿 매핑 저장

4. **rearrange.py로 슬라이드 복제/재배열/삭제**:
   ```bash
   python scripts/rearrange.py template.pptx working.pptx 0,34,34,50,52
   ```
   - 0-indexed, 동일 인덱스 반복 가능 (복제)

5. **inventory.py로 모든 텍스트 추출**:
   ```bash
   python scripts/inventory.py working.pptx text-inventory.json
   ```

6. **교체 텍스트 생성 및 JSON 저장** (`replacement-text.json`):
   - 인벤토리에 존재하는 shape만 참조
   - "paragraphs" 필드 없는 shape는 자동으로 텍스트 제거
   - bullet 사용 시 `"bullet": true, "level": 0` 필수
   - 적절한 포맷 속성 포함 (bold, alignment, font_size 등)

7. **replace.py로 교체 적용**:
   ```bash
   python scripts/replace.py working.pptx replacement-text.json output.pptx
   ```

## Advanced Features

### 썸네일 그리드 생성

슬라이드 시각적 분석을 위한 썸네일:

```bash
python scripts/thumbnail.py template.pptx [output_prefix]
```

- 기본: `thumbnails.jpg` (또는 대형 덱의 경우 `thumbnails-1.jpg`, `thumbnails-2.jpg` 등)
- 기본값: 5열, 그리드당 최대 30슬라이드 (5×6)
- 옵션: `--cols 4` (범위: 3-6)

### 슬라이드를 이미지로 변환

1. **PPTX를 PDF로**: `soffice --headless --convert-to pdf template.pptx`
2. **PDF 페이지를 JPEG로**: `pdftoppm -jpeg -r 150 template.pdf slide`

## Google Slides 호환성 가이드

Google Slides에서 열어야 하는 경우, 호환성을 위해 다음 사항 준수:

**권장 (호환성 높음)**:

- 기본 도형: 사각형, 원, 화살표
- 단순 텍스트 서식: 굵게, 기울임, 밑줄
- 기본 글머리 기호 및 번호 목록
- 표준 이미지 형식 (PNG, JPG)
- 기본 차트 유형 (막대, 선, 원형)

**주의 (호환성 낮음)**:

- 복잡한 SmartArt 또는 다이어그램
- 고급 애니메이션 및 전환 효과
- 사용자 정의 글꼴 (웹 안전 폰트 사용 권장)
- 복잡한 그라데이션 또는 패턴 채우기
- 매크로 또는 VBA 스크립트

**검증 방법**: 생성된 PPTX를 Google Drive에 업로드하여 호환성 확인

## 품질 체크리스트

생성 완료 후 반드시 확인:

- [ ] 썸네일로 모든 슬라이드 레이아웃 검증
- [ ] 텍스트 잘림 또는 오버플로우 없음
- [ ] 색상 대비 및 가독성 확인
- [ ] 차트/테이블 데이터 정확성
- [ ] (Google Slides 타겟 시) 단순 기능만 사용 확인

## Code Style Guidelines

**중요**: PPTX 작업 코드 생성 시:

- 간결한 코드 작성
- 장황한 변수명 및 불필요한 연산 지양
- 불필요한 print 문 지양

## References

- **HTML to PowerPoint**: [html2pptx.md](html2pptx.md) - html2pptx 라이브러리 상세 가이드
- **OOXML Editing**: [ooxml.md](ooxml.md) - Office Open XML 기술 참조
- **Scripts**: [scripts/](scripts/) - 유틸리티 스크립트 모음

## Dependencies

필수 의존성 (설치 필요):

```bash
# Python
pip install "markitdown[pptx]"  # 텍스트 추출
pip install defusedxml           # 안전한 XML 파싱

# Node.js
npm install -g pptxgenjs         # html2pptx용
npm install -g playwright        # HTML 렌더링
npm install -g react-icons react react-dom  # 아이콘
npm install -g sharp             # SVG 래스터화 및 이미지 처리

# System
sudo apt-get install libreoffice    # PDF 변환 (Linux)
sudo apt-get install poppler-utils  # pdftoppm (Linux)
```

## Quick Start

**새 프레젠테이션 (템플릿 없이)**:
```
1. html2pptx.md 전체 읽기
2. HTML 슬라이드 작성 (720pt × 405pt)
3. html2pptx.js로 변환
4. 썸네일 검증
```

**기존 파일 편집**:
```
1. ooxml.md 전체 읽기
2. unpack.py로 언팩
3. XML 편집
4. validate.py로 검증
5. pack.py로 재팩
```

**템플릿 기반 생성**:
```
1. 템플릿 분석 (텍스트 + 썸네일)
2. 인벤토리 작성
3. 아웃라인 생성
4. rearrange.py로 슬라이드 재배열
5. inventory.py로 텍스트 추출
6. replacement JSON 생성
7. replace.py로 적용
```
