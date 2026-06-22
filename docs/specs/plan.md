NHIỆM VỤ: Viết plugin guard cho OpenCode — Port từ hook Kilo hiện có
Mục tiêu
Tạo file .opencode/plugins/solocode-guard.js — một plugin OpenCode gộp ba cơ chế chặn cứng (gate-guard, secret-scan, config-protection) bằng cách port logic từ các hook Kilo đã có sẵn trong repo, KHÔNG viết mới từ đầu.

Giai đoạn 1 — Đọc (read-only, chưa viết code)
Đọc kỹ ba file sau. Mỗi khi tham chiếu tới logic nào, ghi rõ đường dẫn kèm số dòng dạng (file:dòng):

.kilo/hooks/pre-tool-use/gate-guard.js
.kilo/hooks/pre-tool-use/secret-scan.js
.kilo/hooks/pre-tool-use/config-protection.js
Đồng thời đọc docs/specs/opencode-mechanisms.md mục B để lấy đúng signature của hook tool.execute.before và cách throw error để chặn.

Sau khi đọc, viết một đoạn tóm tắt ngắn vào docs/specs/guard-port-plan.md liệt kê:

Các regex/pattern destructive command có trong gate-guard.js (kèm dòng).
Các regex/pattern phát hiện secret có trong secret-scan.js (kèm dòng).
Logic phát hiện làm-yếu-config trong config-protection.js (kèm dòng).
Logic normalize lệnh (gỡ sudo, gộp khoảng trắng, xử lý đường dẫn) nếu có trong gate-guard.js.
DỪNG LẠI sau giai đoạn 1 để người dùng kiểm tra guard-port-plan.md trước khi viết code.

Giai đoạn 2 — Viết plugin (sau khi plan được duyệt)
Tạo .opencode/plugins/solocode-guard.js với cấu trúc:

Phần core logic — các hàm thuần, độc lập, không phụ thuộc cơ chế JSON-stdin của Kilo:

isDestructiveCommand(command) — port pattern từ gate-guard.js
containsSecret(content) — port regex từ secret-scan.js
weakensConfig(filePath, content) — port logic từ config-protection.js
normalizeCommand(command) — port logic normalize nếu có; nếu file gốc chưa có thì BỎ QUA, không tự nghĩ ra.
Phần wrapper OpenCode — export plugin dùng hook tool.execute.before:

Nếu tool là bash và isDestructiveCommand trả về true → throw new Error("[SoloCode] Blocked destructive command: ...")
Nếu tool là write/edit/apply_patch và containsSecret(content) true → throw new Error("[SoloCode] Secret detected, write blocked")
Nếu tool là write/edit/apply_patch và weakensConfig true → throw new Error("[SoloCode] Config weakening blocked")
RÀNG BUỘC CỨNG (không được vi phạm)
KHÔNG bịa pattern mới. Mọi regex/danh sách lệnh nguy hiểm/regex secret PHẢI lấy từ ba file gốc. Cấm tự sáng tạo pattern bảo mật.
Mỗi pattern phải truy nguyên được. Cuối file plugin, thêm một comment block dạng bảng: mỗi pattern trong plugin mới ↔ đến từ file:dòng nào của bản gốc.
Chỉ tạo đúng một file .opencode/plugins/solocode-guard.js (và docs/specs/guard-port-plan.md ở giai đoạn 1). Không sửa file khác, không thêm tính năng ngoài phạm vi.
Không sửa opencode.json trong nhiệm vụ này.
Nếu không tìm thấy logic nào trong file gốc (ví dụ normalize), ghi rõ "KHÔNG TÌM THẤY TRONG BẢN GỐC" thay vì tự viết.
Đầu ra cuối cùng
docs/specs/guard-port-plan.md (giai đoạn 1)
.opencode/plugins/solocode-guard.js (giai đoạn 2)
Bảng truy nguyên pattern (trong comment cuối file plugin)
KHÔNG tự chạy test và tự kết luận "đã hoạt động". Việc xác minh do người dùng làm trên OpenCode thật.