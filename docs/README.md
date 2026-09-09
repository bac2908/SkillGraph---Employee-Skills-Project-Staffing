# Tài liệu SkillGraph

Tài liệu được lưu cùng mã nguồn. Mỗi tính năng mới hoặc thay đổi hành vi đáng kể
phải có tài liệu tiếng Việt trong `docs/`; cập nhật tài liệu tương ứng khi mở rộng
tính năng. Quy ước này được lưu ở [AGENTS.md](../AGENTS.md).

| Tài liệu | Nội dung |
| --- | --- |
| [Giao diện](frontend.md) | Chạy FE, chức năng, cấu hình API và kiểm thử trình duyệt |
| [Đăng nhập và phân quyền](authentication.md) | Admin/Manager/Viewer, session, CSRF, SQLite và giới hạn triển khai |
| [Dashboard tổng hợp](dashboard.md) | API tổng hợp, dữ liệu có giới hạn, cách tải và kiểm thử |
| [Nhật ký hoạt động dự án](project-activity.md) | Actor, dữ liệu trước/sau, transaction, API, giao diện và migration |
| [Lộ trình tiếp theo](next-steps.md) | Việc đã làm, phần còn thiếu và ưu tiên vận hành |

## Quy ước đặt tên và nội dung

- Tên file chữ thường, dùng dấu gạch ngang: `project-activity.md`,
  `backup-restore.md`. Tên thứ hai là ví dụ cho tài liệu tương lai, chưa được tạo.
- Ghi rõ mục đích, phạm vi đã làm/chưa làm, file mã nguồn và API liên quan.
- Có hướng dẫn cấu hình/migration, phân quyền, cách sử dụng, lệnh kiểm thử và
  kết quả thực tế; không dùng kết quả mock để tuyên bố production đã sẵn sàng.
- Ghi giới hạn, rủi ro và các lựa chọn còn phải chốt.
- Không đưa mật khẩu, URI chứa credentials, cookie, token hoặc dữ liệu thật nhạy
  cảm vào tài liệu. Ví dụ phải dùng giá trị tổng hợp.
- Thêm liên kết vào mục lục này và dẫn tài liệu khi bàn giao tính năng.
