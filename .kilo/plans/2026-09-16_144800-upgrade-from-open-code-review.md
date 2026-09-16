# Kế hoạch nâng cấp Solo-Code-Harness từ review `open-code-review-main`

> **Trạng thái:** Phase 1 đã hoàn tất. Task 6 đã commit (`dc1f773`); Task 1
> được thay bằng fix idempotent-write và đã commit (`37ae42c`) sau khi byte
> comparison bác bỏ chẩn đoán EOL.
> **Người soạn:** Kilo (deepseek-v4.1-flash)
> **Ngày:** 2026-09-16
> **Yêu cầu:** review bởi model cấp cao trước khi thực hiện.

**Mục tiêu:** chuyển 5 cải tiến đã xác định từ review Alibaba's `open-code-review` thành các thay đổi cụ thể, có verification, cho Solo-Code-Harness.

**Kiến trúc:** hai dự án giải bài toán khác nhau (`ocr` = CLI review code bằng Go; Solo-Code = harness kỷ luật cho agent bằng Python stdlib). Chỉ áp dụng những gì chuyển giao được, không copy cơ chế Go/Node.

**Ràng buộc bắt buộc của repo này:**
- `tools/` và `.github/scripts/` là **Python stdlib-only**, zero external deps (xem `.kilo/memory/MEMORY.md` → Tech Stack).
- Không sửa file harness để fix bug dự án, và ngược lại (`.harness.lock`).
- Mọi gate mới phải pass `python .github/scripts/checklist.py .` và không làm tăng lint budget vô cớ.

---

## 0. Bằng chứng đo được (reviewer có thể tự verify)

Mọi con số dưới đây tôi đã đo trong session này. Reviewer nên chạy lại để xác nhận.

### 0.1 Chi phí EOL hiện tại

```bash
git -C . config --get core.autocrlf          # -> true
git -C . ls-files --eol | grep -c "^i/crlf"  # -> 0    (index toàn LF)
git -C . ls-files --eol | grep -c "w/crlf"   # -> 549  (working tree CRLF)
Test-Path .gitattributes                     # -> False
```

**Hệ quả đã quan sát 2 lần trong session này:** mỗi lần `python tools/generate_harness.py --harness all` chạy, git báo 28 file `.claude/agents/*.md` + `.claude/commands/*.md` là modified, dù `git diff --numstat` trả 0/0. Nguyên nhân: generator ghi LF (`newline=""`), còn `core.autocrlf=true` khiến checkout mong đợi CRLF. Mỗi commit in warning `LF will be replaced by CRLF`.

### 0.2 Chi phí English-gate nếu port

Tôi đã mô phỏng chính xác hàm `isNonEnglish()` của họ (`scripts/verify-english-only.go:116-141`) rồi chạy trên `git ls-files` của Solo-Code:

```
scanned source files : 697
Solo-Code findings   : 45 dòng / 11 file   (phần còn lại thuộc open-code-review-main/)
```

Chi tiết 45 dòng (file → số dòng → đặc tính):

| File | Dòng | Nhóm |
|---|---|---|
| `.github/scripts/boundary_audit.py` | 3, 6, 7, 8 | C |
| `agent.yaml` | 4 | D |
| `extensions_config.json` | 4 | D |
| `tools/compaction.py` | 71, 72, 73 | B |
| `tools/compaction_pruner.py` | 122, 124 | B |
| `tools/deploy.py` | 311, 312, 314, 315, 323, 335, 336, 338 + 6 | D |
| `tools/garden.py` | 859, 860, 1031, 1049, 1459 | A ×4, C ×1 |
| `tools/shared_state.py` | 111–115, 171–173 | C |
| `tools/test_deploy.py` | 455 | A |
| `tools/test_garden.py` | 547 | A |
| `tools/test_shared_state.py` | 141–143, 153, 154 | C |

**Phân loại (quan trọng nhất của kế hoạch này):**

- **Nhóm A — dữ liệu detector, KHÔNG được dịch (6 dòng).**
  `garden.py:859-860` là `_PATH_NEGATION_MARKERS`, `garden.py:1031` là regex trong `check_enforcement_claims`. Cả hai **phải match văn bản tiếng Việt** để hoạt động. Dịch chúng sang tiếng Anh sẽ âm thầm làm yếu gate. `test_deploy.py:455` assert template chứa chuỗi `"dùng chung"`; `test_garden.py:547` là fixture tiếng Việt cho detector.
  → **Exempt bằng marker**, kèm lý do.

- **Nhóm B — fixture encoding, KHÔNG được dịch (5 dòng).**
  `"é"` trong `compaction.py` và `"éééé"` trong `compaction_pruner.py` tồn tại **chính vì** chúng là multi-byte: test byte-vs-char budget. Đổi sang ASCII là vô hiệu hoá test.
  → **Exempt bằng marker.**

- **Nhóm C — comment giải thích, NÊN dịch (18 dòng).**
  `boundary_audit.py`, `shared_state.py`, `test_shared_state.py`, `garden.py:1459`. Đây là văn xuôi giải thích "vì sao", không phải dữ liệu.
  → **Dịch sang tiếng Anh.**

- **Nhóm D — nội dung user-facing có chủ đích (16 dòng).** *(cần reviewer chốt — xem Câu hỏi mở Q1)*
  `deploy.py:311-338` là `HARNESS_LOCK_TEMPLATE` — nó **sinh ra** `.harness.lock` tiếng Việt cho project đích. `agent.yaml:4` và `extensions_config.json:4` là description hiển thị cho người dùng.
  → Đề xuất: **giữ tiếng Việt + exempt**, vì Solo-Code là dự án Việt và các chuỗi này phục vụ người đọc Việt.

### 0.3 Một phát hiện phụ

`open-code-review-main/` hiện **untracked** (`git status` → `?? open-code-review-main/`, 0 file tracked) nhưng **không có trong `.gitignore`** (chỉ có `deepseek-harness-master/` ở dòng 52). Nó sẽ bị commit nhầm nếu ai đó chạy `git add -A`.

---

## 1. Phân loại đề xuất

| # | Việc | Rủi ro | Cần thiết kế thêm? | Phase |
|---|---|---|---|---|
| 6 | `.gitignore` thêm reference dir | Rất thấp | Không | 1 |
| 1 | Idempotent write; `.gitattributes` chỉ cho repo harness | Thấp | Không | 1 |
| 2 | `tools/verify_prose.py` (port english-gate) | Thấp | Không | 1 |
| 4 | AGENTS.md "Development Assistance" (đã lọc) | Thấp | Không | 2 |
| 5 | Threat model / assurance case | Thấp | Có (nội dung) | 2 |
| 7 | Pin GitHub Action refs (`@release/v1` → SHA) | **Cao** — đụng CI/CD, cần user cho phép | Không | 2 |
| 3 | Path-scoped rules (`.solocode/rules.json`) | Trung bình | **Có** — cần chỗ tiêu thụ rule | 2 |

**Phase 1** = không đụng hành vi runtime, rủi ro thấp, làm được ngay sau khi review.
**Phase 2** = cần quyết định thiết kế hoặc cần user cấp quyền, nên review riêng.

**Thứ tự đề xuất trong Phase 2:** Task 5 (không đụng code) → Task 4 (chỉ sửa docs) → Task 7 (cần user cho phép, làm riêng) → Task 3 (cần chốt Q3, làm cuối).

---

# PHASE 1

## Task 6: Đưa `open-code-review-main/` ra khỏi tầm commit

**Mục tiêu:** reference repo không lọt vào lịch sử harness.

**File:**
- Modify: `.gitignore` (thêm 1 dòng sau `deepseek-harness-master/` ở dòng 52)

**Bước 1: Sửa `.gitignore`**

```diff
 deepseek-harness-master/
+open-code-review-main/
```

**Bước 2: Verify**

```bash
git -C . status --short
```
Expected: dòng `?? open-code-review-main/` biến mất; không còn mục nào khác.

**Bước 3: Commit**

```bash
git add .gitignore
git commit -m "chore(git): ignore open-code-review reference checkout"
```

---

## Task 1: Fix churn generate bằng idempotent write

> **Cập nhật 2026-09-16:** Không dùng quy trình bên dưới để sửa churn generate.
> Churn xuất phát từ các generator ghi lại nội dung giống hệt nhau, không phải EOL.
> Fix hiện hành là idempotent write trong `tools/claude_engine.py` và
> `tools/opencode_engine.py`, có test regression. `.gitattributes` vẫn là chính
> sách LF cho repo này, nhưng không được deploy sang project đích vì `deploy.py`
> có thể ghi đè file `.gitattributes` do project sở hữu.

**Mục tiêu:** hết warning EOL mỗi commit, hết 28 file "M" giả sau mỗi lần regenerate.

**Căn cứ:** index đã toàn LF (`i/crlf` = 0). Vấn đề nằm ở `core.autocrlf=true` biến working tree thành CRLF (549 file), lệch với generator ghi LF. Đặt `eol=lf` buộc working tree giữ LF, khớp generator, và không đổi index → **không phát sinh diff**.

**File:**
- Create: `.gitattributes`
- Modify: `.harness.lock` (thêm `.gitattributes` vào `[boundaries] files`)

**Bước 1: Tạo `.gitattributes`**

```gitattributes
# Normalise every text file to LF in the working tree and the index.
#
# Why this file exists: core.autocrlf=true turned 549 tracked files into CRLF
# in the working tree while the index held LF. The harness generators write LF
# (open(..., newline="")), so every `generate_harness.py` run left 28 generated
# files (.claude/agents/*, .claude/commands/*) reported as modified with a 0/0
# numstat — content identical, line endings not. Pinning eol=lf removes the
# mismatch at the source instead of re-running `git checkout` after each run.
* text=auto eol=lf

# Binary formats must never be line-ending converted.
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.pdf binary
*.woff binary
*.woff2 binary
*.zip binary
*.gz binary
*.exe binary
*.dll binary
*.so binary
*.dylib binary
```

**Bước 2: Renormalize**

```bash
git add --renormalize .
```
Expected: **không có file nào được stage** (index đã LF, nội dung không đổi). Nếu có file được stage, dừng lại và báo cáo — nghĩa là giả định "index toàn LF" sai ở đâu đó.

**Bước 3: Verify EOL đã hết lệch**

```bash
git -C . ls-files --eol | grep -c "w/crlf"    # expected: 0
git -C . status --short                        # expected: rỗng
```

**Bước 4: Verify bằng test thật (quan trọng nhất)**

Đây là phép thử chứng minh vấn đề đã hết, không chỉ là lý thuyết:

```bash
python tools/generate_harness.py --harness all
git -C . status --short
```
Expected: `git status` **vẫn rỗng** sau khi generator chạy. Trước thay đổi này, lệnh đó để lại 28 file `M`.

**Bước 5: Khai báo vào manifest ranh giới**

Sửa `.harness.lock`, mục `[boundaries] files`, thêm `.gitattributes` theo alphabet (sau `.env.template`):

```diff
     ".env.template",
+    ".gitattributes",
     "verify.sh",
```

**Bước 6: Thêm `.gitattributes` vào `deploy.ROOT_FILES`**

`tools/deploy.py` phải ship file này sang project đích, nếu không project đích lại gặp lại đúng vấn đề. Sửa `ROOT_FILES`:

```diff
     ".gitignore",
+    ".gitattributes",
 ]
```

Lưu ý: `tools/test_deploy.py::test_lock_template_root_files_match_root_files` yêu cầu `HARNESS_LOCK_TEMPLATE` khớp `ROOT_FILES`. Phải thêm `.gitattributes` vào **cả hai** chỗ, nếu không test fail (đây đúng là lớp bug đã xảy ra với engine codex).

**Bước 7: Chạy gate**

```bash
python -m pytest tools/ -q                     # expected: 509 passed, 3 skipped
python tools/garden.py                         # expected: 0 drift
python .github/scripts/checklist.py .          # expected: 5/5 PASSED
```

**Bước 8: Commit**

```bash
git add .gitattributes .harness.lock tools/deploy.py
git commit -m "build: pin LF line endings and stop generated-file churn"
```

**Rủi ro:**
- Nếu bước 2 stage file → dừng, báo cáo (giả định sai).
- Người dùng trên Windows có editor ghi CRLF sẽ thấy `git diff` im lặng (đúng ý muốn) nhưng file trên đĩa là LF. Đây là hành vi chuẩn của repo LF-only; họ đã chọn nó.
- `git add --renormalize .` chạm mọi file tracked. Không mất dữ liệu (index LF = working LF sau normalize), nhưng nên chạy khi repo sạch.

---

## Task 2: `tools/verify_prose.py` — gate English-only

**Mục tiêu:** biến "Prose Quality" rules 9–16 trong AGENTS.md từ **văn xuôi không ai enforce** thành **gate deterministic**. Đây chính là điểm yếu mà `open-code-review` nêu: *"a purely language-driven architecture lacks hard constraints on the review process."*

**Vì sao port được:** đã đo — chỉ 45 dòng, trong đó chỉ **18 dòng cần dịch**, 11 dòng exempt (nhóm A+B), 16 dòng là quyết định chính sách (nhóm D).

**File:**
- Create: `tools/verify_prose.py`
- Create: `tools/test_verify_prose.py`
- Modify: `tools/garden.py` (gọi check, hoặc để `.github/scripts/checklist.py` gọi — xem Q2)
- Modify: `.harness.lock` (`[shared_files] paths`: thêm cả hai file)

### Nguyên tắc port (giữ nguyên thiết kế của họ, không "cải tiến")

Đây là các quyết định thiết kế của họ mà tôi đề xuất giữ **nguyên**, vì mỗi cái đều có lý do đã kiểm chứng:

1. **Test "letter outside ASCII", không test "non-ASCII byte".** Nhờ vậy box-drawing (`─`), mũi tên (`→`), emoji đi qua. Solo-Code dùng những ký tự này rất nhiều (`# ───…` trong comment) — nếu test byte thô sẽ báo hàng nghìn dòng giả.
2. **Marker `allow-non-english:` — dấu hai chấm là phần của marker.** Nhờ vậy không thể exempt một dòng mà không nói lý do.
3. **`allowedPrefixes` cho cả cây**, mỗi entry phải có `reason`; entry tạm phải ghi rõ cái gì gỡ nó.
4. **Nguồn file: `git ls-files -z --cached --others --exclude-standard`.** Gồm file chưa commit → bắt lỗi trước khi land. `-z` tránh git quote path non-ASCII.
5. **Docstring phải nói rõ cái nó KHÔNG bắt được** (văn bản ngoại ngữ viết toàn ASCII cần dictionary → để cho review).

### Bước 1: Viết test trước (TDD)

Create `tools/test_verify_prose.py`:

```python
#!/usr/bin/env python3
"""
Prose Gate Tests
================
verify_prose.py is the enforcement arm of AGENTS.md's Prose Quality rules.
These tests pin its two failure modes in both directions: a plain Vietnamese
comment must be caught, and the symbol/emoji scaffolding this repo uses
throughout its comments must not be.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "verify_prose.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — fixed argv, no shell
        [sys.executable, str(TOOL), *args],
        cwd=ROOT, capture_output=True, text=True,
    )


def test_vietnamese_comment_is_flagged(tmp_path: Path) -> None:
    """A diacritic is a letter outside ASCII, so it must be reported."""
    f = tmp_path / "sample.py"
    f.write_text("# Kiểm tra giá trị đầu vào\nx = 1\n", encoding="utf-8")
    result = _run("--path", str(f))
    assert result.returncode == 1
    assert "sample.py" in result.stderr


def test_ascii_comment_passes(tmp_path: Path) -> None:
    f = tmp_path / "sample.py"
    f.write_text("# Check the input value\nx = 1\n", encoding="utf-8")
    assert _run("--path", str(f)).returncode == 0


def test_box_drawing_and_arrows_are_allowed(tmp_path: Path) -> None:
    """Symbols are not letters. Flagging them would drown the gate in noise."""
    f = tmp_path / "sample.py"
    f.write_text("# --- Section ---\n# a -> b >= c\n", encoding="utf-8")
    assert _run("--path", str(f)).returncode == 0


def test_emoji_is_allowed(tmp_path: Path) -> None:
    f = tmp_path / "sample.py"
    f.write_text("# done ✅\n", encoding="utf-8")
    assert _run("--path", str(f)).returncode == 0


def test_marker_exempts_a_line(tmp_path: Path) -> None:
    f = tmp_path / "sample.py"
    f.write_text(
        '# "dùng chung"  # allow-non-english: detector fixture\n',
        encoding="utf-8",
    )
    assert _run("--path", str(f)).returncode == 0


def test_bare_marker_without_reason_does_not_exempt(tmp_path: Path) -> None:
    """The colon is part of the marker so a reason cannot be omitted."""
    f = tmp_path / "sample.py"
    f.write_text("# tiếng Việt allow-non-english\n", encoding="utf-8")
    assert _run("--path", str(f)).returncode == 1


def test_nfd_decomposed_accent_is_caught(tmp_path: Path) -> None:
    """e + U+0301 spells an accented letter with an ASCII base."""
    f = tmp_path / "sample.py"
    f.write_text("# kie\u0302\u0300m tra\n", encoding="utf-8")
    assert _run("--path", str(f)).returncode == 1
```

**Bước 2: Chạy test để xác nhận fail**

```bash
python -m pytest tools/test_verify_prose.py -q
```
Expected: FAIL — `No such file or directory: .../verify_prose.py`

**Bước 3: Viết `tools/verify_prose.py`**

```python
#!/usr/bin/env python3
"""
verify_prose.py — fail when unapproved non-English text appears in source.

Ported from alibaba/open-code-review's scripts/verify-english-only.go. The
motivation is the same one that file documents: comments, identifiers and
strings are written in English so any contributor can review any file, and a
rule that lives only in prose is not enforced at all.

What it detects, and the one thing it cannot:

  - Detected: every letter outside ASCII, whichever writing system. Han, kana,
    Hangul, Cyrillic, Greek, Arabic, Hebrew, Devanagari, and equally the
    diacritics that spell German, French, Turkish or Vietnamese. Plus CJK and
    fullwidth punctuation, and combining accents.
  - Not detected: another language spelled entirely in ASCII — a romanised
    transcription, or German with umlauts written out ("Loeschen der Datei").
    Telling that from English needs a dictionary rather than a character test,
    so it stays a matter for review.

Symbols are deliberately left alone: box drawing, arrows, emoji and maths
(─ → ≥ ≈ ×) appear throughout this repo's comments on purpose. Testing for
letters rather than non-ASCII bytes is what keeps them out of scope.

Markdown is not scanned: .kilo/instruction/*.md and AGENTS.md are legitimately
Vietnamese, and they are prose for humans, not source.

Two escape hatches, narrower one preferred:

  1. Append "allow-non-english: <reason>" to the offending line. The trailing
     colon is part of the marker, so a line cannot be exempted without saying
     why. Right choice for a handful of lines.
  2. Add a prefix to ALLOWED_PREFIXES for a whole tree that is inherently
     non-English. Keep each entry narrow and justified; a temporary entry must
     say what removes it.

Usage:
    python tools/verify_prose.py              # whole repo via git ls-files
    python tools/verify_prose.py --path FILE  # a single file (tests use this)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCANNED_EXT = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".sh", ".ps1",
    ".css", ".html", ".yml", ".yaml", ".json",
}
SCANNED_NAMES = {"Makefile"}

ALLOWED_PREFIXES = [
    # (prefix, reason). Keep narrow; a temporary entry must say what removes it.
]

EXEMPT_MARKER = "allow-non-english:"

# Characters in the Common/Inherited scripts that Unicode files as letters but
# no language writes a word with: the information source, script small l, the
# maths alphabet capitals. Listed explicitly so the rule stays a character test
# rather than a script enumeration.
_LETTERLIKE_SYMBOLS = set("ℹℓℬℭ℮ℯℊℋℌℍℎℏℐℑℒℕℙℚℝℤ")


def is_non_english(ch: str) -> bool:
    """True for a letter outside ASCII, or CJK/fullwidth punctuation."""
    code = ord(ch)
    if code < 0x80:  # ASCII
        return False
    if unicodedata.category(ch).startswith("L") and ch not in _LETTERLIKE_SYMBOLS:
        return True
    if 0x0300 <= code <= 0x036F:  # combining diacritical marks (NFD spelling)
        return True
    if 0x3000 <= code <= 0x303F:  # CJK Symbols and Punctuation
        return True
    if 0xFE10 <= code <= 0xFE19:  # Vertical Forms
        return True
    if 0xFE30 <= code <= 0xFE6F:  # CJK Compatibility + Small Form Variants
        return True
    if 0xFF00 <= code <= 0xFFEF:  # Halfwidth and Fullwidth Forms
        return True
    return False


def is_scanned(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    if name in SCANNED_NAMES:
        return True
    return Path(name).suffix in SCANNED_EXT


def is_allowed(rel: str) -> bool:
    return any(rel.startswith(prefix) for prefix, _ in ALLOWED_PREFIXES)


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """Return (line_no, offending_char, stripped_line) for each bad line."""
    found: list[tuple[int, str, str]] = []
    for n, line in enumerate(text.splitlines(), 1):
        if EXEMPT_MARKER in line:
            continue
        for ch in line:
            if is_non_english(ch):
                found.append((n, ch, line.strip()))
                break
    return found


def tracked_files() -> list[str]:
    """All source files git knows, including untracked-but-not-ignored ones.

    -z separates paths with NUL and emits them verbatim; without it git quotes
    and escapes any path that is not plain ASCII. Do not trim the output: a
    path may legitimately end in a space.
    """
    proc = subprocess.run(  # noqa: S603,S607 — fixed argv, no shell
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip())
    raw = proc.stdout.decode("utf-8", "replace")
    return [f for f in raw.split("\x00") if f]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", action="append", default=[],
                        help="scan only these files (repeatable); default: whole repo")
    args = parser.parse_args()

    if args.path:
        targets = [(p, p) for p in args.path]
    else:
        targets = [
            (rel, rel) for rel in tracked_files()
            if is_scanned(rel) and not is_allowed(rel) and (ROOT / rel).is_file()
        ]

    findings: list[tuple[str, int, str, str]] = []
    for rel, path in targets:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        for line_no, ch, line in scan_text(text):
            findings.append((rel, line_no, ch, line))

    if findings:
        print(f"ERROR: unapproved non-English text in {len(findings)} line(s):",
              file=sys.stderr)
        for rel, line_no, ch, line in findings:
            print(f"  {rel}:{line_no}: {ch!r} in {line[:100]}", file=sys.stderr)
        print(
            "\nSource files are English-only: comments, identifiers and strings.\n"
            "Translated prose belongs in .kilo/instruction/*.md, AGENTS.md, or\n"
            "the README, none of which this gate scans.\n\n"
            "If the non-English text is intentional — a detector fixture, an\n"
            "encoding test, user-facing copy — append a marker with the reason:\n\n"
            f'    x = "dùng chung"  # {EXEMPT_MARKER} harness-lock template text\n\n'
            "For a whole tree that is inherently non-English, add a prefix to\n"
            "ALLOWED_PREFIXES in tools/verify_prose.py instead.\n",
            file=sys.stderr,
        )
        return 1

    print(f"No unapproved non-English text in {len(targets)} scanned source files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Bước 4: Chạy test để xác nhận pass**

```bash
python -m pytest tools/test_verify_prose.py -q
```
Expected: `8 passed`

**Bước 5: Chạy gate trên toàn repo — xác nhận đúng 45 findings**

```bash
python tools/verify_prose.py
```
Expected: exit 1, liệt kê **đúng 45 dòng** trong 11 file như bảng ở §0.2. Nếu số khác, dừng lại — nghĩa là logic port chưa khớp và phải đối chiếu lại với `isNonEnglish()` gốc.

**Bước 6: Xử lý 45 findings theo phân loại §0.2**

Dịch 18 dòng nhóm C. Ví dụ cụ thể:

`.github/scripts/boundary_audit.py` (dòng 3–8):
```diff
-"""Boundary Audit — Phát hiện file project lạc vào thư mục harness
+"""Boundary Audit — detect project files that strayed into harness directories

-Sau khi deploy harness vào project đích, script này quét các thư mục
-harness để đảm bảo không có file project (code của dự án thực) vô tình
-bị copy vào thư mục harness infrastructure.
+After the harness is deployed into a target project, this scans the harness
+directories to ensure no project file (real application code) was copied
+into harness infrastructure by accident.
```

`tools/shared_state.py` (dòng 111–115):
```diff
-# Số lần thử lại + độ trễ khi khởi tạo DB lần đầu bị "database is locked".
-# Cần thiết vì PRAGMA/executescript trong __init__ chạy TRƯỚC bất kỳ
-# transaction BEGIN IMMEDIATE nào, nên có thể va chạm khi 2 engine cùng
-# tạo file .db mới lần đầu gần như đồng thời (đã tái hiện được bug này
-# bằng test_concurrent_lock_acquire trước khi có retry).
+# Retry count and delay for "database is locked" during first-time DB init.
+# Needed because PRAGMA/executescript in __init__ run BEFORE any BEGIN
+# IMMEDIATE transaction, so two engines creating a fresh .db at nearly the
+# same moment can collide (reproduced by test_concurrent_lock_acquire before
+# the retry existed).
```

Thêm marker cho 11 dòng nhóm A + B, mỗi dòng kèm lý do:

```python
# tools/garden.py:859-860
_PATH_NEGATION_MARKERS = (
    ...
    "khong ton tai", "không tồn tại",  # allow-non-english: matches Vietnamese docs
```

```python
# tools/compaction.py:71
# "é" is 1 char but 2 UTF-8 bytes.  allow-non-english: multibyte encoding fixture
```

Nhóm D (16 dòng ở `deploy.py`, `agent.yaml`, `extensions_config.json`): **chờ Q1**.

**Bước 7: Chạy lại gate — phải sạch**

```bash
python tools/verify_prose.py
python -m pytest tools/ -q
python tools/garden.py
python .github/scripts/checklist.py .
```
Expected: gate exit 0; `509+8 passed`; 0 drift; 5/5 PASSED.

**Bước 8: Khai báo file mới**

`.harness.lock`, `[shared_files] paths`, thêm theo alphabet:
```diff
     "tools/validate_schemas.py",
+    "tools/verify_prose.py",
+    "tools/test_verify_prose.py",
```

Và nếu chọn wire qua checklist (Q2), thêm bước gọi vào `.github/scripts/checklist.py`.

**Bước 9: Commit**

```bash
git add tools/verify_prose.py tools/test_verify_prose.py \
        .github/scripts/boundary_audit.py tools/shared_state.py \
        tools/test_shared_state.py tools/garden.py \
        tools/compaction.py tools/compaction_pruner.py \
        tools/deploy.py tools/test_deploy.py tools/test_garden.py \
        agent.yaml extensions_config.json .harness.lock
git commit -m "feat(gate): enforce English-only source with verify_prose.py"
```

**Rủi ro & lưu ý:**
- **Nhóm A là rủi ro thật:** dịch `_PATH_NEGATION_MARKERS` hay regex enforcement-claim sẽ làm yếu detector mà **không test nào bắt được**. Marker exemption là bắt buộc, không phải tùy chọn.
- Gate chỉ bắt "letter ngoài ASCII". Nó không bắt văn xuôi tiếng Việt không dấu (`khong ton tai` đã nằm sẵn trong `_PATH_NEGATION_MARKERS` chính là dạng này). Phải ghi rõ giới hạn này trong docstring, như bản gốc đã làm.
- **Không scan `.md`.** Nếu scan, toàn bộ `.kilo/instruction/*.md` (tiếng Việt có chủ đích) sẽ fail. Đây là scope đúng, không phải lỗ hổng — nhưng cần reviewer xác nhận.

---

# PHASE 2

## Task 4: AGENTS.md — kỷ luật dùng AI (đã lọc bỏ rule mâu thuẫn)

**Mục tiêu:** thêm kỷ luật AI-disclosure mà Solo-Code chưa có.

**Cảnh báo quan trọng:** bản gốc có **8 rule**, nhưng **rule 6 mâu thuẫn trực tiếp với repo này**:

> *"You must not attribute commits to AI/LLM, including through 'Assisted-by', 'Co-developed-by', or similar trailers."*

Solo-Code **bắt buộc** mọi commit kết thúc bằng `Co-Authored-By: Solo-Code <admin@solo-code.com>`. Hai triết lý đối lập. **Không copy cả khối** — phải chọn.

**Đề xuất áp dụng 4 rule (bỏ rule 6):**

```markdown
### AI Assistance Discipline

Adapted from alibaba/open-code-review's AGENTS.md. This repo takes the opposite
position on commit trailers — see "Git Commit Convention" below, which requires
a Co-Authored-By trailer — so that rule is deliberately not adopted here.

1. **Disclose AI use.** State in the PR/issue that AI was used, and name the
   tool and model.
2. **Understand every line.** You must be able to explain any change yourself,
   whether you or the agent wrote it.
3. **No fix-loops.** A change should not contain repeated cycles of
   `generated -> fixed -> fixed -> fixed`. That pattern usually means the
   generated code was never reviewed, only patched.
4. **Review before requesting review.** Read all agent-produced code, text and
   config yourself before asking a human to look at it.
```

**Rule 3 có thể gate được** — đây là phần thú vị nhất. Đếm số lần cùng một file được sửa trong một nhánh:

```bash
# Number of commits touching the same file in a branch (excl. merge commits)
git log --no-merges --format= --name-only main..HEAD | sort | uniq -c | sort -rn | head
```
Nếu một file xuất hiện >3 lần trong một nhánh ngắn, đó là dấu hiệu fix-loop. **Đề xuất:** ghi lại cách đo này như một kiểm tra thủ công (advisory), **không** dựng gate cứng — ngưỡng đúng phụ thuộc ngữ cảnh và gate sai sẽ bị tắt.

**File:** Modify `AGENTS.md` (thêm section), regenerate `CLAUDE.md`/engine mirrors.

**Câu hỏi mở Q3 bên dưới.**

## Task 3: Path-scoped rules — cần quyết định thiết kế

**Giá trị:** `open-code-review` cho phép rule gắn theo đường dẫn, merge vào prompt khi review. Rule của họ cụ thể đến mức liệt kê thứ tự field và **bắt buộc sync docs sang 4 locale**.

**Vấn đề:** Solo-Code **không có chỗ tiêu thụ** loại rule này. Nó không có cơ chế "merge rule vào system prompt theo path" — agent đọc `AGENTS.md` một lần. Vậy phải thiết kế chỗ tiêu thụ trước khi tạo dữ liệu.

Ba lựa chọn, cần reviewer chọn:

| Phương án | Cách hoạt động | Rủi ro |
|---|---|---|
| **A. Gate-style** | `.solocode/rules.json` + `tools/check_path_rules.py` chạy trong checklist; rule là **assertion kiểm tra được** (vd: mọi engine trong `DEFAULT_ENGINES` phải có mặt trong `HARNESS_LOCK_TEMPLATE`) | Thấp; tự động; nhưng chỉ diễn đạt được rule kiểm tra máy được |
| **B. Prompt-style** | Rule là văn xuôi, engine generator chèn vào agent prompt theo path | Trung bình; phụ thuộc mỗi engine hỗ trợ; khó verify |
| **C. Cả hai** | `rules.json` chứa cả `check` (máy) và `guidance` (người/agent) | Cao hơn; nhiều bề mặt |

**Đề xuất của tôi: A**, vì nó phù hợp triết lý hiện có của repo (gate deterministic), và giải quyết đúng lớp bug đã xảy ra — Codex thêm engine codex nhưng quên `HARNESS_LOCK_TEMPLATE`, sinh 2 test fail mà lẽ ra một rule đã bắt sớm hơn.

Ví dụ rule cho `tools/deploy.py`:

```json
{
  "rules": [
    {
      "glob": "tools/deploy.py",
      "check": "engine_sync",
      "guidance": "When adding an engine, update ROOT_FILES, EXCLUSIVE_HARNESS_DIRS, DIRS_ALL, a DIRS_<ENGINE> list, the --engine choices, and HARNESS_LOCK_TEMPLATE. Missing HARNESS_LOCK_TEMPLATE fails test_lock_template_root_files_match_root_files."
    }
  ]
}
```

**Chưa viết task chi tiết cho Phase-2 này** — cần chốt Q3 trước, nếu không sẽ đặc tả sai.

## Task 5: Threat model / assurance case

**Giá trị:** `ocr` có `ASSURANCE_CASE.md` với system description, actors + trust level, trust boundaries. Solo-Code có `security-patterns.md` (danh sách rule) nhưng **không có threat model**. Với harness, mô hình tin cậy mới là thứ đáng viết ra, vì nó đã đổi nhiều lần và hiện mỗi engine một kiểu:

- Agent là trusted hay untrusted? (harness gate nó, nhưng nó có quyền ghi)
- Hook có bypass được không? (README từng khẳng định sai — xem decision 2026-07-25 trong `.kilo/memory/MEMORY.md`)
- `executor-mode` off nghĩa là gì về mặt tin cậy?
- Codex chạy `sandbox_mode = "danger-full-access"` + `approval_policy = "never"` — mô hình tin cậy nào? (đã ghi trong `~/.codex/config.toml`, **không** trong repo)

**File:** Create `docs/assurance-case.md` (khớp convention `docs/` hiện có — 12 file cùng loại: `audit-*.md`, `defensive-patterns.md`, `code-review-checklist.md`).

Đề xuất nội dung tối thiểu: system description → actors + trust level → trust boundaries → mỗi countermeasure ánh xạ tới file/test enforce nó → mục "cái gì KHÔNG được bảo vệ".

Việc này không có code, nhưng cần reviewer duyệt nội dung vì nó là tuyên bố về an toàn.

---

## Task 7: Pin GitHub Actions refs (từ Q4)

**Mục tiêu:** đóng rủi ro supply-chain ở `.github/workflows/`. Nghiêm trọng nhất là `pypa/gh-action-pypi-publish@release/v1` — một **branch ref**, nội dung có thể đổi bất kỳ lúc nào, và nó chạy trong job publish lên PyPI.

**Căn cứ:** `ocr` có `scripts/verify-action-pins.sh` với lý do nêu rất chính xác:

> *"A floating tag inside action.yml silently undermines consumers who SHA-pin alibaba/open-code-review itself: the outer pin freezes this repository, but a moved inner tag still changes what actually runs."*

**File:**
- Modify: `.github/workflows/ci.yml`, `.github/workflows/release.yml`
- Create: `.github/scripts/verify_action_pins.py`
- Create: `tools/test_verify_action_pins.py` *(hoặc `.github/scripts/` — xem Q2 về chỗ đặt gate)*
- Modify: `.harness.lock`, `.github/scripts/checklist.py`

**Bước 1: Xác định SHA đúng cho từng action**

Với mỗi ref đang dùng, lấy SHA của commit mà ref đó trỏ tới **tại thời điểm review**, kèm version comment:

```bash
# Ví dụ (chạy một lần, ghi lại kết quả):
git ls-remote https://github.com/actions/checkout refs/tags/v4
git ls-remote https://github.com/actions/setup-python refs/tags/v5
git ls-remote https://github.com/actions/upload-artifact refs/tags/v4
git ls-remote https://github.com/actions/download-artifact refs/tags/v4
git ls-remote https://github.com/pypa/gh-action-pypi-publish refs/heads/release/v1
```

**Lưu ý quan trọng:** đây là bước **thủ công có review** — không tự động lấy SHA rồi commit, vì một SHA lấy nhầm ref là cách tấn công chính nó. Reviewer phải xác nhận từng SHA khớp tag được nêu.

**Bước 2: Sửa workflow theo dạng `uses: owner/action@<40-hex> # vX.Y.Z`**

```diff
-      - uses: actions/checkout@v4
+      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

*(SHA trong ví dụ là minh hoạ cú pháp — phải thay bằng giá trị thật lấy ở bước 1.)*

**Bước 3: Viết gate `verify_action_pins.py`**

Port logic của họ (Python stdlib-only, không chạy bash):

```python
#!/usr/bin/env python3
"""
verify_action_pins.py — every external `uses:` must be pinned to a 40-hex SHA
with a trailing version comment.

A floating tag or branch inside a workflow silently changes what runs even when
a consumer pinned *this* repository by SHA: the outer pin freezes the repo, but
a moved inner ref still swaps the code that executes. Local refs (`./...`) are
exempt — they resolve inside the repository that is already pinned.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

# owner/repo@<40 hex> # vX...   |   local path refs are exempt
_PINNED = re.compile(r"uses:\s*[\w.-]+/[\w./-]+@[0-9a-f]{40}\s+#\s*v\d")
_LOCAL = re.compile(r"uses:\s*\./")
_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)")


def main() -> int:
    findings: list[str] = []
    for wf in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        for n, line in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            m = _USES.match(line)
            if not m:
                continue
            if _LOCAL.search(line) or _PINNED.search(line):
                continue
            findings.append(f"{wf.relative_to(ROOT).as_posix()}:{n}: unpinned -> {m.group(1)}")

    if findings:
        print(f"ERROR: {len(findings)} GitHub Action ref(s) not pinned to a SHA:", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        print("\nPin to a full 40-hex commit SHA with a `# vX.Y.Z` comment.", file=sys.stderr)
        return 1

    print("All external GitHub Action refs are SHA-pinned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Bước 4: Verify**

```bash
python .github/scripts/verify_action_pins.py   # expected: exit 1 before the fix, exit 0 after
python -m pytest tools/ -q
python .github/scripts/checklist.py .          # nếu đã wire vào checklist
```

**Bước 5: Commit**

```bash
git add .github/workflows/ci.yml .github/workflows/release.yml \
        .github/scripts/verify_action_pins.py .github/scripts/checklist.py .harness.lock
git commit -m "ci: pin GitHub Action refs to commit SHAs"
```

**Rủi ro:**
- **Đây là task duy nhất trong plan đụng vào CI/CD.** `AGENTS.md` → "Not Allowed" ghi rõ: *"Modifying `.github/workflows/` or CI/CD pipeline configuration without explicit instruction"*. **Cần user cho phép rõ ràng trước khi làm.** Đây là lý do tôi tách nó thành task riêng thay vì gộp vào Phase 1.
- Pin SHA làm việc nâng cấp action thành thủ công (phải sửa SHA + comment). Đó là đánh đổi có chủ đích, nhưng cần biết.
- `pypa/gh-action-pypi-publish` là action publish — nếu pin sai SHA, job release hỏng. Phải test bằng một lần chạy `workflow_dispatch` hoặc dry-run trước khi tin.

---

## Verification tổng thể (chạy sau mỗi task)

```bash
python -m pytest tools/ -q                    # 522 passed, 3 skipped
python tools/garden.py                        # 0 drift
python .github/scripts/checklist.py .         # 5/5 PASSED
python .github/scripts/check_skips.py tools/  # no-skips OK
python tools/check_lint_budget.py             # 74/74 (Task 2 thêm S603/S607 -> cần noqa hoặc +budget)
git -C . status --short                       # không có generated artifact mới sau mỗi lần generate
```

**Lưu ý lint budget:** `verify_prose.py` và `test_verify_prose.py` gọi `subprocess.run` → sinh S603/S607. Theo convention đã áp dụng cho `codex_guard.py`, dùng `# noqa: S603,S607 — fixed argv, no shell` **tại chỗ** thay vì raise budget. Đã đưa noqa vào code mẫu ở trên.

---

## Câu hỏi mở — cần reviewer chốt trước khi thực hiện

**Q1 (quan trọng nhất).** Nhóm D — 16 dòng user-facing (`deploy.py` template `.harness.lock` tiếng Việt, `agent.yaml` description, `extensions_config.json`) — nên **giữ tiếng Việt + marker exempt**, hay **dịch sang tiếng Anh**?
Tôi nghiêng về giữ, vì Solo-Code là dự án Việt và `.harness.lock` sinh ra để người Việt đọc. Nhưng nếu mục tiêu là contributor quốc tế, phải dịch. **Đây là quyết định chính sách, không phải kỹ thuật.**

**Q2.** Gate mới nên được gọi từ đâu — `garden.py` (như các drift check khác) hay `.github/scripts/checklist.py` (như security/lint)? `garden` là nơi check documentation/prose hiện sống; `checklist` là nơi gate CI sống. Tôi nghiêng về `checklist` vì đây là gate cứng, không phải drift advisory.

**Q3.** Path-scoped rules: chọn phương án A, B hay C? Không chốt thì không đặc tả được.

**Q4.** *(đã tự trả lời — nâng thành đề xuất, xem Task 7 bên dưới)* Có nên port `verify-action-pins.sh` không? **Có.** Kiểm tra thực tế: `.github/workflows/` đang dùng **tag và branch**, không pin SHA:

| Workflow | Ref đang dùng | Vấn đề |
|---|---|---|
| `ci.yml` | `actions/checkout@v4`, `actions/setup-python@v5` | tag có thể bị trỏ lại |
| `release.yml` | `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, `actions/download-artifact@v4` | tag |
| `release.yml` | **`pypa/gh-action-pypi-publish@release/v1`** | **branch** — nội dung có thể đổi bất kỳ lúc nào |

`@release/v1` là **branch ref**, không phải tag. Đây là rủi ro supply-chain thật và là mức yếu nhất trong ba mức (SHA > tag > branch). Đáng sửa bất kể có port gate hay không.

**Q5.** *(đã tự trả lời)* Task 5 đặt ở **`docs/assurance-case.md`**. `docs/` đã tồn tại với 12 file cùng loại (`audit-*.md`, `defensive-patterns.md`, `code-review-checklist.md`, `capability-seams.md`), nên root là sai convention.

---

## Ngoài phạm vi (không đề xuất làm)

- **CodeQL / CI mở rộng** — `ocr` có 10 workflows; Solo-Code là solo project, thêm workflow là chi phí bảo trì không tương xứng.
- **i18n docs (`docs/i18n/*`)** — `ocr` cần 5 locale vì là dự án Alibaba. Solo-Code không cần; README EN+VI trong một file là đủ.
- **Skill frontmatter `license`/`compatibility`/`metadata`** — giá trị thấp; skill của Solo-Code chạy nội bộ, không publish.
- **SPDX license headers** — Solo-Code không có LICENSE ở root cho code của chính nó theo cách `ocr` có; thêm header vào ~700 file là thay đổi lớn, lợi ích không rõ.
- **Coverage 90% như `ocr`** — Solo-Code đã có `tools/coverage_gate.py`; ngưỡng riêng của repo nó đã đặt.
