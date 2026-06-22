# Project Architecture

> Tài liệu mô tả kiến trúc hệ thống, sơ đồ dữ liệu và các thành phần cốt lõi của dự án hiện tại.

## Tech Stack Core

- **Backend:** Node.js với TypeScript / Python CLI Tools.
- **Frontend:** React / Vanilla JS tùy môi trường.
- **Đóng gói Harness:** Tự động sinh (generate) cấu hình từ `source/plugins/` sang các thư mục phân phối ẩn (`.gemini/`, `.kilo/`, `.github/`, `.claude/`).

## Luồng Hoạt động (Data Flow)

```
[Developer edits source/plugins]
              │
              ▼
[python tools/generate_harness.py]
              │
     ┌────────┼────────┬────────┐
     ▼        ▼        ▼        ▼
  [.gemini] [.kilo] [.claude] [.github]
```

## Các điểm cần lưu ý (Gotchas)

- **Tránh sửa trực tiếp các file ẩn:** Mọi sửa đổi trực tiếp vào `.gemini/antigravity/skills` hay `.github/` sẽ bị ghi đè khi chạy lại `generate_harness.py`. Mọi thay đổi về code và quy tắc phải xuất phát từ thư mục `source/`.
- **Ngoại lệ:** Thư mục `.gemini/antigravity/knowledge/` được giữ nguyên vì đây là tài liệu tĩnh phục vụ riêng cho cơ chế KI của Antigravity.
