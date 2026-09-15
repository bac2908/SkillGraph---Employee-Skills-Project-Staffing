# Kịch bản demo SkillGraph với dữ liệu tổng hợp

Mục đích: giải thích bài toán thiếu hụt kỹ năng, gợi ý và phân công trong
15–20 phút. Chuẩn bị ngày 16/09/2026, **chưa chạy demo này trên graph thật**.
Không dùng dữ liệu nhân sự, email hoặc mật khẩu thật trong buổi trình bày.

## Điều kiện và phạm vi

- Bản ứng dụng/DB riêng được phép tạo/xóa dữ liệu tổng hợp, đúng phiên bản
  [bàn giao](handoff.md), readiness đạt. Không trỏ vào instance đang dùng.
- Một Admin, một Manager được giao dự án Main và một Viewer; tạo qua UI,
  tự đặt mật khẩu qua kênh riêng, đổi mật khẩu tạm trước buổi demo.
- Các ID bên dưới chưa tồn tại. Nếu trùng thì dùng bộ ID mới đồng nhất, không
  ghi đè/xóa dữ liệu cũ để chạy kịch bản. Không dùng `seed.py` cho kịch bản này.
- Trước buổi demo kiểm tra các luồng; nếu chưa có graph riêng, trình bày bộ
  test FE mock/RBAC cô lập và nói rõ đó **không phải dữ liệu lưu graph thật**.

## Dữ liệu cần nhập qua UI

Danh mục kỹ năng: `SK91001` — Demo Covered, `SK91002` — Demo Gap,
`SK91003` — Demo Missing, cùng nhóm Demo. Tên không mô tả công nghệ thật để
dễ đối chiếu kết quả toán học.

| Nhân viên | Hồ sơ tổng hợp | Kỹ năng |
| --- | --- | --- |
| `EMP91001` | Demo Member A, `demo-member-a@example.com`, Developer, Middle, AVAILABLE, Demo Office | Covered cấp 4; Gap cấp 2; mỗi liên kết 2,5 năm |
| `EMP91002` | Demo Candidate B, `demo-candidate-b@example.com`, Developer, Middle, AVAILABLE, Demo Office | Gap cấp 4; Missing cấp 3; mỗi liên kết 2,5 năm |

Tạo `PROJ91001` — Demo Main và `PROJ91002` — Demo Shared, trạng thái ACTIVE,
mô tả “Dữ liệu tổng hợp dùng riêng cho demo”. Main yêu cầu cả ba kỹ năng cấp
3, ưu tiên Covered=MUST, Gap=SHOULD, Missing=NICE. Shared không cần yêu cầu
kỹ năng để thử allocation.

Admin phân công A vào Main 40%, vai trò Member; B vào Shared 100%, vai trò
Developer. Admin cấp Manager quyền ghi Main, **không cấp Shared**. Employee A/B
không phải tài khoản đăng nhập; không nhầm hai loại dữ liệu.

## Trình tự demo và kết quả phải thấy

| Thời lượng | Thao tác | Giải thích/kết quả kỳ vọng |
| --- | --- | --- |
| 2 phút | Mở dashboard, danh sách nhân viên/dự án | Đây là quản lý năng lực và bố trí nhân sự nội bộ, không phải hệ thống tuyển dụng công khai |
| 3 phút | Mở Main → Phân tích & gợi ý | Covered: 4/3 → COVERED; Gap: 2/3 → GAP; Missing: 0/3 → MISSING |
| 1 phút | Đọc tỷ lệ đáp ứng | `round(1/3 × 100, 2) = 33,33%`; không tính trọng số MUST/SHOULD/NICE |
| 2 phút | Xem gợi ý B rồi bấm Kiểm tra phân bổ | B khớp 2 kỹ năng thiếu, nhưng allocation đã 100%; form không cho thêm việc |
| 2 phút | Admin sửa Shared: B từ 100% xuống 80%; thêm B vào Main 20% | B đạt tổng đúng 100%; Main lên 100% coverage |
| 1 phút | Thử tăng B ở Main lên 21% | Form/BE từ chối vượt 100%; dữ liệu cũ giữ nguyên. Không lách bằng sửa DB |
| 2 phút | Manager sửa vai trò B ở Main; thử mở Shared | Main được ghi; Shared chỉ đọc. Nhật ký/tài khoản chỉ dành Admin |
| 1 phút | Viewer xem Main | Xem được nhưng không có quyền ghi. Dẫn bộ RBAC nếu cần bằng chứng API trực tiếp bị chặn |
| 2 phút | Admin gỡ B khỏi Main; xem phân tích/Hoạt động | Coverage trở lại 33,33%; nhật ký có actor, thời điểm, trước/sau của phân công |
| 1 phút | Thử xóa A hoặc kỹ năng Covered khi còn liên kết | HTTP 409 được diễn giải: phải gỡ quan hệ trước; không xóa mất dữ liệu liên quan |

Xếp hạng là **rule-based**, không phải AI/ML. Ưu tiên số kỹ năng thiếu mà ứng
viên đáp ứng, số người từng cộng tác, tổng cấp độ, rồi ID ổn định theo luật
hiện tại. AVAILABLE chỉ là trạng thái thủ công; gợi ý chưa lọc allocation.
Xem [quy tắc và kịch bản graph E2E](graph-e2e-acceptance.md) để kiểm tra thứ tự
với nhiều ứng viên, request đồng thời và audit đầy đủ.

Không dùng thao tác demo 21% bị chặn ở form làm bằng chứng BE chống race đã
đạt. Bộ graph E2E riêng mới thử HTTP trực tiếp/đồng thời trên database thật;
hiện trạng chạy thật được ghi trong tài liệu đó.

## Sau buổi demo

1. Ghi kết quả thực thấy, phiên bản, môi trường, lỗi hoặc điểm khác kỳ vọng;
   không ghi cookie/password/endpoint có secrets vào báo cáo.
2. Nếu giữ môi trường demo: đánh dấu dữ liệu tổng hợp, hạn chế truy cập; không
   nhập chung dữ liệu doanh nghiệp. Không biến tài khoản demo thành tài khoản thật.
3. Nếu cần dọn, người vận hành xác nhận đúng danh sách ID đã tạo. Gỡ các
   assignments, employee skills, project requirements qua UI trước; rồi xóa
   đúng Employee/Project/Skill của kịch bản. Bỏ grant Manager demo trước khi
   xóa project. Không dùng lệnh xóa toàn graph hoặc wildcard theo ổ đĩa.
4. Nhật ký dự án có thể còn sau xóa đúng thiết kế. Không xóa audit/DB auth
   như cache; việc hủy cả instance demo và dữ liệu auth cần quyết định riêng.
5. Đăng xuất các tài khoản; nếu không tiếp tục demo, Admin khóa tài khoản test
   theo quy trình. Không để mật khẩu trên slide, ảnh, clipboard hay source.

## Bằng chứng tối thiểu để ghi “demo đã chạy”

- Đúng ba trạng thái và coverage 33,33% → 100% → 33,33%.
- API đọc lại được dữ liệu; không chỉ thấy thành công từ state phía FE.
- Tổng allocation đạt đúng 100%, vượt giới hạn bị từ chối, audit đúng người.
- Quyền Manager/Viewer đúng; dữ liệu test được giữ/dọn theo quyết định rõ ràng.

Tài liệu này chuẩn bị kịch bản và kỳ vọng, không đánh dấu các kết quả trên đã
đạt trước khi thật sự chạy ở môi trường demo riêng.
