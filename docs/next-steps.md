# SkillGraph: phân tích lộ trình sau bản local

Đã hoàn thành [dashboard tổng hợp](dashboard.md) và bổ sung
[nhật ký hoạt động dự án](project-activity.md) trong đợt tiếp theo (10/09/2026).
Chưa triển khai toàn bộ các hạng mục vận hành. Trạng thái cụ thể ghi dưới đây;
không coi các đề xuất còn lại là tính năng đã có.

Ngày 12/09/2026 đã bổ sung [công cụ khôi phục Admin cục bộ](admin-recovery.md):
không cần mật khẩu cũ, không tạo DB/tài khoản, chỉ xử lý Admin đang hoạt động,
thu hồi phiên và buộc đổi mật khẩu tạm. Kiểm thử bằng DB tạm; không đặt lại
mật khẩu Admin thật. Phần này không bổ sung audit tài khoản/quyền hoặc triển
khai các hạng mục vận hành còn lại.

## Thứ tự ưu tiên đề xuất

| Thứ tự | Hạng mục | Lý do | Điều kiện nghiệm thu |
| --- | --- | --- | --- |
| 1 — đã làm | Dashboard tổng hợp | Loại tải cả danh mục và request theo từng dự án khi mở tổng quan | Tổng chính xác, response có giới hạn, lỗi rõ ràng, test BE/FE |
| 2 — đã làm phần dự án | Nhật ký thay đổi | Trả lời ai sửa dự án/phân công/yêu cầu kỹ năng; audit tài khoản/quyền còn thiếu | Cùng graph transaction, Admin-only, trước/sau, lọc, cursor; xem giới hạn engine trong tài liệu |
| 3 — đã có công cụ; xem trạng thái drill | Readiness, backup và phục hồi | Kiểm tra DB với timeout; backup logic graph + SQLite, verify và restore riêng | [Readiness](readiness.md), [quy trình và kết quả phục hồi](backup-restore.md); chưa có lịch tự động/offsite/production |
| 4 | Một môi trường staging HTTPS | Kiểm tra toàn bộ luồng ngoài máy cá nhân | Cookie/origin đúng; secrets tách biệt; chưa chứa dữ liệu nhạy cảm thật |
| 5 | Giám sát và kiểm thử tải | Có số đo trước khi quyết định mở rộng | Ghi nhận độ trễ p95, tỷ lệ lỗi và tài nguyên dưới tải có kiểm soát |
| Theo nhu cầu | Email reset, MFA/SSO | Phụ thuộc cách tổ chức quản lý danh tính | Chọn nhà cung cấp/chính sách trước; kiểm thử hết hạn, thu hồi và phục hồi |

Nếu mục tiêu trước mắt là phỏng vấn, ưu tiên audit và một kịch bản demo có thể
giải thích rõ trade-off. Nếu mục tiêu là dùng thật nhiều người, backup/restore và
staging an toàn phải hoàn tất trước khi mở cho người dùng thực tế.

## Lịch sử thay đổi ngay tại dự án: đã triển khai phần graph

Đã thêm tab Hoạt động cho Admin trong chi tiết dự án và trang `/activity`. Ví dụ minh họa:

> 09:30 — Manager A đổi allocation của EMP001 từ 40% thành 60%, vai trò Backend Developer.

Đây là ví dụ thiết kế, không phải sự kiện thật. Mỗi mục có người thao tác, thời
gian UTC hiển thị theo múi giờ người xem, tài nguyên và các trường trước/sau đã
được cho phép. Có bộ lọc thời gian, hành động và người thực hiện; mở chi tiết khi
cần thay vì hiển thị nguyên JSON dài.

Giai đoạn đầu trang audit chỉ dành Admin. Quyền Manager xem lịch sử dự án
cần chốt rõ; không tự suy ra từ quyền đọc dữ liệu hiện tại. Không thêm nút hoàn
tác ngay: hoàn tác là một thao tác ghi mới, cần kiểm tra trạng thái và allocation
hiện tại chứ không chép mù giá trị cũ.

### Thiết kế và các phần audit còn lại

Dữ liệu nghiệp vụ nằm ở graph, auth nằm ở SQLite. Nếu sửa graph xong mới ghi audit
vào SQLite thì có thể mất audit khi SQLite lỗi. Middleware ghi sau response cũng
không tự giải quyết tính nguyên tử.

Thiết kế cho quy mô hiện tại (mục 1/3 và context retry đã triển khai cho dự án;
mục 2 audit SQLite còn thiếu):

1. Với thao tác graph, ghi AuditEvent và thay đổi nghiệp vụ trong cùng graph
   transaction. Audit thất bại thì thay đổi không được xác nhận thành công.
2. Với thao tác tài khoản/quyền, ghi audit trong cùng SQLite transaction tương ứng.
3. Lưu mã actor ổn định và snapshot tên hiển thị tối thiểu. Không phụ thuộc vào
   việc actor hoặc tài nguyên đích còn tồn tại khi xem lịch sử.
4. Mỗi sự kiện có ID ổn định và ràng buộc chống trùng phù hợp. Kiểm thử retry để
   callback chạy lại không sinh sự kiện sai/trùng. Neo4j driver có cơ chế retry
   managed transaction; phải kiểm chứng trên engine thực tế của dự án.
   [Tài liệu transaction](https://neo4j.com/docs/python-manual/current/transactions/)
5. Không tuyên bố hai database có chung transaction hoặc chung thứ tự commit.
   Nếu gộp lịch sử lên UI, cần phân biệt nguồn và phân trang ổn định.

Không lưu password, password hash, cookie, session token, CSRF token hoặc nguyên
request body vào audit. Chỉ ghi các trường cần thiết qua danh sách cho phép;
giới hạn kích thước và bảo vệ quyền đọc. Thời hạn lưu/xóa log cần chính sách rõ
ràng, không để tăng vô hạn. [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

Test bắt buộc: rollback khi ghi audit lỗi; giữ lịch sử sau khi xóa tài nguyên;
không lộ secret; chặn truy cập trái quyền; ghi đồng thời; retry; không gán một
yêu cầu thất bại thành sự kiện thay đổi thành công. Audit ở tầng ứng dụng không
ghi được mọi thay đổi do người dùng chạy Cypher trực tiếp; phạm vi này phải nói rõ.

## Hai hướng phát triển nghiệp vụ có giá trị

### Phân công theo thời gian

Thêm ngày bắt đầu/kết thúc và chỉ cộng allocation trong khoảng thời gian giao
nhau. Phải định nghĩa dự án kết thúc, nghỉ phép, lịch toàn thời gian/bán thời gian
và cách xử lý dữ liệu cũ. Đây là thay đổi mô hình nghiệp vụ, không chỉ thêm hai ô
ngày trên FE. Cần kiểm thử giao nhau ở ranh giới ngày và phân công đồng thời.

### Giải thích đề xuất ứng viên

Hiển thị vì sao ứng viên được xếp hạng: kỹ năng nào lấp khoảng trống, cấp độ yêu
cầu/thực tế, quan hệ làm chung và dung lượng còn lại. Cho quản lý xem tác động
dự kiến lên coverage trước khi lưu. Giữ rõ đây là dự đoán; server phải kiểm tra
lại khi ghi. Hệ thống hiện tại là rule-based, chưa phải mô hình ML.

## Triển khai và tiết kiệm dung lượng

- Chưa chọn hoặc đăng ký dịch vụ hosting/email/SSO, chưa publish ứng dụng.
- Trước staging cần chốt nơi chạy, domain, ngân sách và quyền truy cập. Không mở
  Vite dev server ra Internet như một bản production.
- Duy trì cùng origin cho FE/API nếu phù hợp để giảm cấu hình cookie/proxy;
  cấu hình HTTPS, Secure cookie, allowed origins và secrets riêng cho môi trường.
- Backup graph và SQLite là hai việc riêng. Git và seed không thay backup.
  Thử restore ở nơi riêng, đối chiếu quyền theo project giữa hai kho dữ liệu.
- Đặt giới hạn dung lượng/thời hạn cho log và backup; cần thống nhất chính sách
  trước khi tự động xóa. Không coi auth.sqlite3 là cache.
- Chỉ thêm Redis, hàng đợi hoặc dịch vụ khác khi có yêu cầu/số đo chứng minh cần;
  các đợt dashboard và nhật ký dự án không thêm dependency hay image Docker.
- Không benchmark tải ghi trên dữ liệu thật. Dùng dataset tổng hợp ở môi trường
  riêng và mô tả rõ số nhân viên/dự án/quan hệ cùng mức đồng thời đã kiểm thử.
