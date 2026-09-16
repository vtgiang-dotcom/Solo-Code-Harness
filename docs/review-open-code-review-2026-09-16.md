# Báo cáo review: `open-code-review` → khuyến nghị nâng cấp Solo-Code-Harness

| | |
|---|---|
| **Ngày** | 2026-09-16 |
| **Người thực hiện** | Kilo (deepseek-v4.1-flash) |
| **Đối tượng review** | `F:\Project\Solo-Code-CLI\open-code-review-main` (Alibaba's OpenCodeReview) |
| **Dự án nhận khuyến nghị** | Solo-Code-Harness (`F:\Project\Solo-Code-CLI`) |
| **Kế hoạch triển khai kèm theo** | `.kilo/plans/2026-09-16_144800-upgrade-from-open-code-review.md` |
| **Trạng thái** | CHỜ REVIEW CẤP CAO — chưa thực hiện thay đổi nào |

---

## 1. Mục đích và phạm vi

Câu hỏi cần trả lời: *`open-code-review` có gì mà Solo-Code-Harness nên học?*

Hai dự án **giải bài toán khác nhau**, nên phần lớn nội dung không chuyển giao được:

| | `open-code-review` | Solo-Code-Harness |
|---|---|---|
| Bản chất | CLI review code bằng AI | Harness kỷ luật cho AI agent |
| Ngôn ngữ | Go + Node/TypeScript | Python 3.10+ stdlib-only |
| Quy mô | Dự án tổ chức, OpenSSF Gold, đa contributor | Dự án solo |
| Đầu ra | Review comment theo dòng | Gate, hook, generator, mirror đa engine |

Báo cáo này **chỉ đề xuất những gì chuyển giao được**, và nêu rõ những gì tôi quyết định **không** đề xuất.

---

## 2. Đối tượng review là gì

**OpenCodeReview** (`ocr`) — công cụ AI code review CLI của **Alibaba Group**, phát triển từ công cụ nội bộ đã phục vụ hàng chục nghìn developer và tìm ra hàng triệu defect. Viết bằng Go (module `github.com/alibaba/open-code-review`).

Điểm đáng chú ý về mức độ trưởng thành:
- **OpenSSF Best Practices Gold**
- **Benchmark riêng**: AACR-Bench — 50 repo phổ biến, 200 PR thật, 10 ngôn ngữ, 1,505 issue được 80+ kỹ sư cấp cao gắn nhãn. Công bố trên HuggingFace.
- **10 CI workflows**, gồm CodeQL, contract test cho public surface, và translation-sync
- **5 locale** (en, zh-CN, ja-JP, ko-KR, ru-RU) với quy trình sync README bắt buộc
- **90% coverage gate**, SPDX license header bắt buộc, English-only enforcement

Triết lý cốt lõi họ nêu, và cũng là lý do tồn tại của nhiều thứ dưới đây:

> *"A purely language-driven architecture lacks hard constraints on the review process."*

Họ giải bài toán đó bằng **"Deterministic Engineering × Agent Hybrid"**: những bước *không được phép sai* thì giao cho logic tất định (chọn file, gộp file, match rule), còn agent chỉ lo quyết định động và truy xuất context.

---

## 3. Phương pháp review

1. Đọc `README.md`, `AGENTS.md`, `Makefile`, cấu trúc thư mục top-level.
2. Khảo sát agent assets: `skills/`, `.claude/`, `.agents/`, `.opencodereview/`.
3. Đọc `scripts/verify-english-only.go` (275 dòng) và `scripts/verify-action-pins.sh`.
4. Đọc `.gitattributes`, `.opencodereview/rule.json`, `ASSURANCE_CASE.md`.
5. **Đo lường trên Solo-Code thay vì ước lượng** — mô phỏng chính xác hàm `isNonEnglish()` của họ rồi chạy trên `git ls-files` của Solo-Code để có số thật.
6. Kiểm tra `.gitattributes`, `core.autocrlf`, và trạng thái EOL của cả index lẫn working tree.
7. Kiểm tra ref của GitHub Actions trong `.github/workflows/`.

Mọi con số trong báo cáo này đều **đo được**, không phải suy đoán. Reviewer nên chạy lại để xác nhận — lệnh nằm trong plan kèm theo.

---

## 4. Bảy phát hiện, xếp theo tỷ lệ giá trị/chi phí

### 4.1 Churn sau mỗi lần generate — fix thật là idempotent write ⭐

**Triệu chứng:** mỗi lần chạy `python tools/generate_harness.py --harness all`, `git status` báo **28–29 file** là modified (`.claude/agents/*.md`, `.claude/commands/*.md`, `opencode.json`), trong khi `git diff --numstat` trả **rỗng**.

**Chẩn đoán đầu tiên của báo cáo này — SAI.** Tôi quy cho EOL mismatch: generator ghi LF trong khi `core.autocrlf=true` khiến repo mong đợi CRLF. Số đo ban đầu có vẻ ủng hộ:

```
core.autocrlf                        -> true
tracked files with CRLF in index     -> 0     (index toàn LF)
tracked files with CRLF in worktree  -> 549
.gitattributes                       -> không tồn tại
```

**Số đo đó không chứng minh gì.** So từng byte giữa disk và index cho thấy chúng giống hệt nhau:

```
.claude/agents/architect.md   disk 2443 B, CR=0, LF=87  |  index 2443 B, CR=0, LF=87  |  identical: True
opencode.json                 disk 1353 B, CR=0, LF=50  |  index 1353 B, CR=0, LF=50  |  identical: True
.claude/commands/ship.md      disk  963 B, CR=0, LF=30  |  index  963 B, CR=0, LF=30  |  identical: True
```

EOL **đều là LF ở cả hai phía**. Không có mismatch nào. `.gitattributes` không liên quan tới triệu chứng này.

**Nguyên nhân thật:** generator ghi file **vô điều kiện**. `git status` so **stat** (mtime) trước và chỉ đọc nội dung sau; `git diff` thì đọc nội dung. Ghi vô điều kiện đẩy mtime lên kể cả khi nội dung y hệt, nên `git status` thấy stat khác → báo "M", còn `git diff` đọc nội dung → thấy giống → im lặng. Hai lệnh đúng theo cách của chúng, ghép lại thành tín hiệu gây nhầm.

Chuỗi bằng chứng dẫn tới kết luận:

| Lệnh | Kết quả | Nghĩa |
|---|---|---|
| `git diff --numstat` | rỗng | nội dung không đổi |
| byte-compare disk vs index | `identical: True` | không phải EOL, không phải BOM |
| `git update-index --refresh` | `needs update` | chỉ so stat, không đọc content |
| `git add .claude/agents` | staged rỗng, **M: 29 → 15** | `git add` refresh stat cache |
| `git add .claude/commands opencode.json` | staged rỗng, **M: 15 → 0** | xác nhận |

**Fix đúng — idempotent write:** chỉ ghi khi nội dung thật sự đổi. Vị trí: `tools/claude_engine.py` (`_write_lf`, `_copy_if_changed`, `_copy_tree_if_changed`) và `tools/opencode_engine.py` (`_write_if_changed`, `_copy_if_changed`). Khoá hành vi bằng `tools/test_generator_idempotency.py` (13 test).

**Kết quả đo sau fix:** chạy generator **2 lần liên tiếp** → `git status` chỉ còn đúng 2 file, và đó là thay đổi thật của chính việc fix. Không có file generated nào bị churn. Trước fix: 28–29 file mỗi lần chạy.

**`.gitattributes` vẫn nên thêm, nhưng vì lý do khác** — nó **không** phải fix cho churn:
- Đảm bảo mọi checkout (Linux CI, macOS) đều LF, không phụ thuộc `core.autocrlf` của từng máy
- Chặn warning `LF will be replaced by CRLF` khi commit
- `open-code-review` có file này, và nó đúng cho tính nhất quán đa nền tảng

**Bài học phương pháp:** "index LF vs worktree CRLF" **không kết luận được gì** về việc hai bên có khác nhau hay không — git normalize khi so sánh. Muốn kết luận phải so byte thô (`Path.read_bytes()` vs `git cat-file blob`). Báo cáo này từng kết luận sai vì bỏ qua bước đó.

---

### 4.2 Gate English-only — giá trị cao, chi phí trung bình

**Đây là khoảng trống rõ nhất của Solo-Code.** Solo-Code có **"Prose Quality" rules 9–16** trong `AGENTS.md` — nhưng **không có gate nào enforce chúng**. Đúng cái họ gọi là *"a purely language-driven architecture lacks hard constraints"*.

**Thiết kế của họ đáng học không chỉ vì nó chạy, mà vì cách nó tự giới hạn:**

| Khía cạnh | Cách làm | Vì sao quan trọng |
|---|---|---|
| Test cái gì | **"a letter outside ASCII"**, không phải "non-ASCII byte" | Box-drawing `─`, mũi tên `→`, emoji đi qua. Solo-Code dùng những ký tự này rất nhiều trong comment |
| Exemption tại chỗ | `allow-non-english: <reason>` — **dấu hai chấm là phần của marker** | Không thể exempt một dòng mà không nói lý do |
| Exemption cả cây | `allowedPrefixes` với `reason` cho từng entry | Entry tạm phải ghi rõ cái gì gỡ nó |
| Nguồn file | `git ls-files -z --cached --others --exclude-standard` | File mới bị check **trước khi** commit; `-z` tránh git quote path non-ASCII |
| Giới hạn | Docstring nói thẳng cái nó **không** bắt được (văn bản ngoại ngữ viết toàn ASCII cần dictionary) | Không hứa quá khả năng |

**Đo mức ảnh hưởng lên Solo-Code** bằng cách mô phỏng chính xác `isNonEnglish()` (`verify-english-only.go:116-141`):

```
scanned source files (Solo-Code) : 697
flagged lines                    : 45 dòng / 11 file
```

**Và đây là phát hiện quan trọng nhất của báo cáo này** — 45 dòng **không đồng nhất**, chia làm 4 nhóm với cách xử lý **khác nhau**:

| Nhóm | Số dòng | Bản chất | Xử lý |
|---|---|---|---|
| **A. Dữ liệu detector** | 6 | `garden.py:859` là `_PATH_NEGATION_MARKERS`, `garden.py:1031` là regex enforcement-claim. `test_deploy.py:455` assert template chứa `"dùng chung"` | **EXEMPT — tuyệt đối không dịch** |
| **B. Fixture encoding** | 5 | `"é"` trong `compaction.py`, `"éééé"` trong `compaction_pruner.py` tồn tại *chính vì* chúng multi-byte | **EXEMPT** |
| **C. Comment giải thích** | 18 | `boundary_audit.py:3-8`, `shared_state.py:111-115/171-173`, `test_shared_state.py`, `garden.py:1459` | **DỊCH** |
| **D. User-facing có chủ đích** | 16 | `deploy.py:311-338` (template `.harness.lock` tiếng Việt), `agent.yaml:4`, `extensions_config.json:4` | **Chờ quyết định — xem §6 Q1** |

**Cảnh báo nghiêm trọng về nhóm A:** dịch `_PATH_NEGATION_MARKERS` hay regex enforcement-claim sang tiếng Anh sẽ **làm yếu gate âm thầm** — chúng phải match văn bản tiếng Việt để hoạt động, và **không test nào bắt được** việc làm yếu đó. Đây chính là loại lỗi mà gate mới này tồn tại để phòng.

**Chi phí thật:** chỉ **18 dòng cần dịch** + 11 dòng thêm marker. Không phải 45 dòng như đọc số thô.

---

### 4.3 Path-scoped rules — giá trị cao, nhưng cần thiết kế trước

Họ có `.opencodereview/rule.json` — rule gắn theo **đường dẫn file**, merge vào system prompt khi review:

```json
{"rules": [{"path": "internal/llm/providers.go",
            "rule": "Field order within each entry MUST follow: Name → DisplayName →
                     Protocol → BaseURL → AuthHeader → EnvVar → AmbientAuth → Models.
                     Any addition MUST be accompanied by updates to the built-in
                     provider table in ALL of these docs: en/zh/ja/ru configuration.md",
            "merge_system_rule": true}]}
```

Rule của họ rất cụ thể: thứ tự field, naming convention, **sync docs sang 4 locale**, test coverage bắt buộc, regression guard cho misrouting.

**Vì sao điều này đáng giá với Solo-Code:** nó giải đúng một lớp bug đã xảy ra thật. Khi tích hợp engine Codex, `tools/deploy.py` được cập nhật `ROOT_FILES`, `EXCLUSIVE_HARNESS_DIRS`, `DIRS_ALL`, `DIRS_CODEX`, và `--engine choices` — nhưng **quên `HARNESS_LOCK_TEMPLATE`**, sinh ra 2 test fail. Một path-scoped rule cho `tools/deploy.py` kiểu *"khi thêm engine, phải cập nhật cả 6 chỗ này"* sẽ phát hiện ở giai đoạn review thay vì để test bắt sau.

**Nhưng Solo-Code chưa có chỗ tiêu thụ loại rule này** — agent đọc `AGENTS.md` một lần, không có cơ chế merge rule theo path. Nên phải thiết kế chỗ tiêu thụ **trước khi** tạo dữ liệu. Xem §6 Q3.

---

### 4.4 Kỷ luật dùng AI trong `AGENTS.md` — có một rule **mâu thuẫn**

Họ có 8 rule về kỷ luật dùng AI. Rule đáng chú ý nhất:

> *"Your PR should not contain repeated cycles like `AI generated -> fixed -> fixed -> fixed`. This may indicate that you did not review the AI-generated code, but instead let the AI fix issues as they arise, over and over."*

Đây là dạng lỗi **Solo-Code không có cách nào phát hiện**. Có thể đo được: đếm số lần cùng một file được sửa trong một nhánh (`git log --no-merges --format= --name-only main..HEAD | sort | uniq -c | sort -rn`). Tôi đề xuất ghi lại như **kiểm tra thủ công (advisory)**, không dựng gate cứng — ngưỡng đúng phụ thuộc ngữ cảnh, và gate sai sẽ bị tắt.

**Điểm mâu thuẫn cần biết — rule 6 của họ:**

> *"You must not attribute commits to AI/LLM, including through 'Assisted-by', 'Co-developed-by', or similar trailers."*

Solo-Code **bắt buộc** mọi commit kết thúc bằng `Co-Authored-By: Solo-Code <admin@solo-code.com>`. Hai triết lý **đối lập trực tiếp**: họ muốn sạch dấu vết AI trong lịch sử, Solo-Code muốn attribution rõ ràng.

**Không có câu trả lời đúng/sai**, nhưng đây là lựa chọn có hệ quả — nó ảnh hưởng đến cách dự án được nhìn nhận khi có contributor ngoài. **Khuyến nghị: áp dụng 4 rule, bỏ rule 6.** Không copy cả khối.

---

### 4.5 Threat model / assurance case — giá trị trung bình

`ASSURANCE_CASE.md` (9.6 KB) của họ có: system description, **actors kèm trust level**, trust boundaries diagram.

```
Actors:
  Local user          Trusted      — invokes the CLI with full control over config
  LLM provider API    Semi-trusted — responses validated before use
  Git repository      Semi-trusted — diffs may contain adversarial content
  Network             Untrusted    — TLS
  Web browser         Untrusted    — may be exploited via DNS rebinding
```

Solo-Code có `security-patterns.md` (danh sách rule) nhưng **không có threat model**. Với một harness, mô hình tin cậy mới là thứ đáng viết ra, vì nó **đã thay đổi nhiều lần và hiện mỗi engine một kiểu**:

- Agent là trusted hay untrusted? (harness gate nó, nhưng nó có quyền ghi)
- Hook có bypass được không? — README từng **khẳng định sai** điều này (xem decision 2026-07-25 trong `.kilo/memory/MEMORY.md`)
- `executor-mode` off nghĩa là gì về mặt tin cậy?
- Codex chạy `sandbox_mode = "danger-full-access"` + `approval_policy = "never"` — mô hình tin cậy nào? (setting này nằm ở `~/.codex/config.toml`, **không** trong repo)

Giá trị thật của việc viết ra: buộc trả lời nhất quán những câu này thay vì mỗi engine một kiểu.

---

### 4.6 `verify-action-pins.sh` — **phát hiện rủi ro thật** ⚠️

Kiểm tra `.github/workflows/` của Solo-Code cho kết quả:

| Workflow | Ref đang dùng | Mức |
|---|---|---|
| `ci.yml` | `actions/checkout@v4`, `actions/setup-python@v5` | tag |
| `release.yml` | `actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, `actions/download-artifact@v4` | tag |
| `release.yml` | **`pypa/gh-action-pypi-publish@release/v1`** | **BRANCH** ⚠️ |

`@release/v1` là **branch ref**, không phải tag — nội dung có thể đổi bất kỳ lúc nào, và nó chạy trong job **publish lên PyPI**. Đây là mức yếu nhất trong ba mức (SHA > tag > branch).

Lý do họ tồn tại, họ nêu rất chính xác:

> *"A floating tag inside action.yml silently undermines consumers who SHA-pin alibaba/open-code-review itself: the outer pin freezes this repository, but a moved inner tag still changes what actually runs."*

**Lưu ý:** task này cần **user cho phép rõ ràng** — `AGENTS.md` mục "Not Allowed" ghi: *"Modifying `.github/workflows/` or CI/CD pipeline configuration without explicit instruction."*

---

### 4.7 Nhỏ hơn (ghi lại, không đề xuất làm)

| Thứ | Nhận xét |
|---|---|
| Skill frontmatter | Họ có `name`, `description`, `license`, `compatibility`, `metadata`. Solo-Code chỉ có `name` + `description`. `compatibility` có thể hữu ích cho skill cần CLI ngoài (`gemini-delegation`), nhưng giá trị thấp vì skill chạy nội bộ |
| `--audience agent` | Flag cho output tối ưu máy đọc thay vì người đọc. Ý tưởng hay, nhưng Solo-Code chưa có nhu cầu này |
| Delegation skill | Họ có `open-code-review-delegate`; Solo-Code đã có `gemini-delegation` — tương đương |
| SPDX headers | ~700 file phải thêm header. Lợi ích không rõ với dự án solo |
| Coverage 90% | Solo-Code đã có `tools/coverage_gate.py` với ngưỡng riêng |
| CodeQL, 10 workflows | Solo-Code là dự án solo; chi phí bảo trì không tương xứng |

---

## 5. Khuyến nghị thứ tự

### Phase 1 — không đụng runtime, rủi ro thấp

| Thứ tự | Việc | Vì sao trước | Cách chứng minh |
|---|---|---|---|
| 1 | `.gitignore` thêm `open-code-review-main/` | 1 dòng; hiện untracked nhưng sẽ bị `git add -A` nuốt | `git status` |
| 2 | Idempotent write trong generator | Chặn ghi lại artifact không đổi | Chạy `generate_harness.py` hai lần; không có generated artifact mới trong status |
| 3 | `tools/verify_prose.py` (hiện không tồn tại — Task 2 tạo) | Biến rule văn xuôi thành gate; chỉ 18 dòng cần dịch | Gate báo đúng 45 dòng trước, 0 sau |

### Phase 2 — cần quyết định hoặc cần cấp quyền

| Thứ tự | Việc | Điều kiện |
|---|---|---|
| 4 | `docs/assurance-case.md` (hiện không tồn tại — Task 5 tạo) | Không đụng code; cần duyệt nội dung |
| 5 | `AGENTS.md` kỷ luật AI (bỏ rule 6) | Chỉ sửa docs + regenerate |
| 6 | Pin GitHub Action refs | **Cần user cho phép** — đụng CI/CD |
| 7 | Path-scoped rules | **Cần chốt Q3 trước** — chưa có chỗ tiêu thụ |

---

## 6. Câu hỏi mở cần chốt trước khi thực hiện

**Q1 — chính sách, không kỹ thuật.** Nhóm D: 16 dòng user-facing (`deploy.py` template `.harness.lock` tiếng Việt, `agent.yaml:4` description, `extensions_config.json:4`) nên **giữ tiếng Việt + marker exempt**, hay **dịch sang tiếng Anh**?

Người soạn nghiêng về **giữ** — Solo-Code là dự án Việt, và `.harness.lock` được sinh ra để người Việt đọc. Nhưng nếu mục tiêu là contributor quốc tế thì phải dịch. Đây là **quyết định chính sách, không phải kỹ thuật**, nên cần người có quyền quyết.

**Q2 — gate mới gọi từ đâu?** `garden.py` (nơi các check documentation/prose hiện sống) hay `.github/scripts/checklist.py` (nơi gate CI sống)? Người soạn nghiêng về `checklist` vì đây là gate cứng, không phải drift advisory.

**Q3 — Path-scoped rules chọn phương án nào?** Solo-Code chưa có chỗ tiêu thụ rule theo path, nên phải thiết kế trước:

| Phương án | Cách hoạt động | Rủi ro |
|---|---|---|
| **A. Gate-style** | `rules.json` + tool kiểm tra được (vd: mọi engine trong `DEFAULT_ENGINES` phải có trong `HARNESS_LOCK_TEMPLATE`) | Thấp; tự động; nhưng chỉ diễn đạt được rule kiểm tra máy được |
| **B. Prompt-style** | Rule là văn xuôi, generator chèn vào agent prompt theo path | Trung bình; phụ thuộc mỗi engine; khó verify |
| **C. Cả hai** | `rules.json` chứa cả `check` (máy) và `guidance` (người/agent) | Cao; nhiều bề mặt |

Người soạn đề xuất **A** — hợp triết lý gate-tất-định của repo, và giải đúng lớp bug đã xảy ra.

---

## 7. Điểm yếu của báo cáo này (tự đánh giá để reviewer soi)

Ghi ra để reviewer biết chỗ nào đáng nghi, thay vì phải tự đoán:

1. **Logic port chưa được chứng minh tương đương bản gốc trên mọi input.** Tôi chỉ so khớp trên 45 dòng của Solo-Code, không fuzz-test. Nếu bản Python cho kết quả khác bản Go ở ca biên mà không ai biết, đó là loại lỗi tệ nhất cho một gate. Plan có bước "expected đúng 45 dòng, nếu khác thì dừng" nhưng đó là kiểm tra một điểm, không phải chứng minh.

2. **Phân loại 4 nhóm dựa trên đọc 45 dòng thủ công**, không có tiêu chí máy kiểm được. Reviewer nên tự đọc lại danh sách nhóm A và B để xác nhận không có dòng nào bị xếp nhầm vào nhóm "được phép dịch".

3. **Chưa kiểm chứng lợi ích của `.gitattributes` trên môi trường khác.** Kết luận dựa trên máy Windows này với `core.autocrlf=true`. Trên Linux/macOS (mặc định autocrlf=false) vấn đề có thể không tồn tại — nhưng `eol=lf` vẫn vô hại và vẫn đúng cho tính nhất quán đa nền tảng.

4. **`.opencodereview/rule.json` của họ là dữ liệu sống** (được `ocr` tiêu thụ). Việc tôi đề xuất một cơ chế *tương tự* cho Solo-Code là **suy luận**, không phải sao chép — cơ chế tiêu thụ của họ không tồn tại ở Solo-Code.

5. **Báo cáo không đánh giá chất lượng code Go của họ.** Tôi đọc `verify-english-only.go` kỹ (vì cần port), nhưng không review `internal/`, `cmd/`, hay `action.yml` (50 KB). Nếu mục tiêu là học kiến trúc Go thì báo cáo này không đủ.

---

## 8. Tham chiếu

| Nội dung | Đường dẫn |
|---|---|
| Kế hoạch triển khai chi tiết (code, lệnh, verification) | `.kilo/plans/2026-09-16_144800-upgrade-from-open-code-review.md` |
| Gate English-only bản gốc | `open-code-review-main/scripts/verify-english-only.go` |
| Gate action pinning bản gốc | `open-code-review-main/scripts/verify-action-pins.sh` |
| Rule theo path bản gốc | `open-code-review-main/.opencodereview/rule.json` |
| Threat model bản gốc | `open-code-review-main/ASSURANCE_CASE.md` |
| `.gitattributes` bản gốc | `open-code-review-main/.gitattributes` |
| Quy tắc dùng AI bản gốc | `open-code-review-main/AGENTS.md` (mục Development Assistance) |
