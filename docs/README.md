# Tài liệu SkillGraph

**Mới tìm hiểu dự án?** Đọc [Tổng quan dự án](tong-quan-du-an.md) trước để hiểu
mục đích, bài toán doanh nghiệp, người dùng, luồng nghiệp vụ và kết quả hướng
tới khi hoàn thiện; tài liệu phân biệt rõ phần đã có với mục tiêu còn lại.

Tài liệu được lưu cùng mã nguồn. Mỗi tính năng mới hoặc thay đổi hành vi đáng kể
phải có tài liệu tiếng Việt trong `docs/`; cập nhật tài liệu tương ứng khi mở rộng
tính năng. Quy ước này được lưu ở [AGENTS.md](../AGENTS.md).

| Tài liệu | Nội dung |
| --- | --- |
| [Tổng quan dự án — đọc trước](tong-quan-du-an.md) | Mục đích, giá trị doanh nghiệp, role, quy trình, kiến trúc, trạng thái và tiêu chí hoàn thành |
| [Giao diện](frontend.md) | Chạy FE, chức năng, cấu hình API và kiểm thử trình duyệt |
| [Nâng cấp giao diện UI/UX](ui-redesign.md) | Thiết kế mới Emerald Glassmorphic, typography, màu sắc và E2E |
| [Đăng nhập và phân quyền](authentication.md) | Admin/Manager/Viewer, session, CSRF, SQLite và giới hạn triển khai |
| [Nghiệm thu ba role](rbac-acceptance.md) | Kết quả UI + API Admin/Manager/Viewer, thu hồi phiên, buộc đổi mật khẩu; phạm vi cô lập và giới hạn graph thật |
| [Nghiệm thu FE–BE–graph thật](graph-e2e-acceptance.md) | Bộ test 13 bước, đích riêng, dữ liệu kỳ vọng và cleanup; đang chờ cấu hình/chạy thật |
| [Khôi phục Admin](admin-recovery.md) | CLI cục bộ, xác nhận tài khoản, mật khẩu tạm nhập ẩn, thu hồi phiên và giới hạn an toàn |
| [Dashboard tổng hợp](dashboard.md) | API tổng hợp, dữ liệu có giới hạn, cách tải và kiểm thử |
| [Nhật ký hoạt động dự án](project-activity.md) | Actor, dữ liệu trước/sau, transaction, API, giao diện và migration |
| [Kiểm tra sẵn sàng](readiness.md) | Liveness/readiness, timeout, cache và xử lý dependency lỗi |
| [Sao lưu và phục hồi](backup-restore.md) | Backup graph + SQLite, checksum, phục hồi vào nơi riêng và giới hạn |
| [Lộ trình tiếp theo](next-steps.md) | Việc đã làm, phần còn thiếu và ưu tiên vận hành |

## Quy ước đặt tên và nội dung

- Tên file chữ thường, dùng dấu gạch ngang: `project-activity.md`,
  `backup-restore.md`.
- Ghi rõ mục đích, phạm vi đã làm/chưa làm, file mã nguồn và API liên quan.
- Có hướng dẫn cấu hình/migration, phân quyền, cách sử dụng, lệnh kiểm thử và
  kết quả thực tế; không dùng kết quả mock để tuyên bố production đã sẵn sàng.
- Ghi giới hạn, rủi ro và các lựa chọn còn phải chốt.
- Không đưa mật khẩu, URI chứa credentials, cookie, token hoặc dữ liệu thật nhạy
  cảm vào tài liệu. Ví dụ phải dùng giá trị tổng hợp.
- Thêm liên kết vào mục lục này và dẫn tài liệu khi bàn giao tính năng.
