# Dashboard tổng hợp

## Đã triển khai

`GET /api/dashboard` thay việc frontend tải toàn bộ nhân viên, kỹ năng và dự án
rồi gọi danh sách phân công của từng dự án để tính số liệu tổng quan.

API nằm trong router nghiệp vụ hiện hữu: cần đăng nhập và hoàn tất đổi mật khẩu
bắt buộc. Admin, Manager và Viewer được đọc số liệu toàn không gian, giống chính
sách đọc các danh mục hiện tại. Đây không phải cơ chế phân vùng nhiều tổ chức.
Response có `Cache-Control: no-store`.

## Hợp đồng dữ liệu

| Trường | Ý nghĩa |
| --- | --- |
| `generated_at` | Thời điểm BE tạo phản hồi, UTC; không phải thời điểm commit cuối cùng |
| `summary.employee_count` | Tổng số Employee, không bị giới hạn bởi phân trang |
| `summary.available_employee_count` | Số Employee có status AVAILABLE |
| `summary.project_count` | Tổng số Project |
| `summary.active_project_count` | Số Project có status ACTIVE |
| `summary.skill_count` | Tổng số Skill |
| `capacity` | Tối đa 5 nhân viên có tổng allocation thấp nhất |
| `default_project` | Một Project; ưu tiên ACTIVE rồi mã dự án tăng dần; null nếu không có |

Mỗi dòng capacity chỉ gồm mã, tên, chức danh, `total_allocation` và
`remaining_allocation`. Không trả email hoặc thông tin xác thực.
Sắp xếp theo allocation tăng dần, tên không phân biệt hoa thường, rồi mã nhân viên.
Nhân viên chưa có phân công được tính 0%. Không lọc theo trạng thái nhân viên:
allocation thấp không tự có nghĩa là người đó sẵn sàng nhận việc.

Tổng allocation gồm mọi `WORKS_ON` tới Project, kể cả dự án đã kết thúc, theo quy
tắc hiện hữu. Chưa xét lịch/ngày. Nếu dữ liệu cũ hoặc ghi DB trực tiếp vượt 100%,
API vẫn trả tổng thật và dung lượng âm, không âm thầm làm tròn thành 100%.

Database rỗng: HTTP 200, các tổng bằng 0, capacity rỗng, default_project null.
Lỗi truy vấn: HTTP 503 với thông báo chung; không trả số 0 hoặc dữ liệu giả.

## Thiết kế truy vấn và hiệu năng

- Một managed read transaction, 5 câu truy vấn cho mỗi lần thực thi: tổng nhân
  viên, tổng dự án, tổng kỹ năng, top 5 allocation và dự án mặc định.
- Từng loại dữ liệu được tổng hợp riêng, tránh tích Descartes làm nhân số đếm
  hoặc tổng allocation khi ghép nhiều quan hệ.
- Số câu truy vấn không tăng theo số dự án. Driver có thể retry transaction,
  nên 5 không phải giới hạn tuyệt đối khi có lỗi tạm thời.
- Payload tổng quan có giới hạn; không trả toàn bộ danh mục rồi cắt ở frontend.
- Đây không phải truy vấn O(1): tính tổng và xếp hạng allocation vẫn phải đọc
  dữ liệu liên quan. Chưa có benchmark tải lớn hoặc cam kết thời gian phản hồi.
- Nhiều truy vấn trong một read transaction không đồng nghĩa snapshot isolation.
  Số liệu có thể thay đổi khi người khác ghi đồng thời. `generated_at` không hứa
  rằng mọi panel cùng một snapshot.

Frontend mở dashboard có 3 loại request nghiệp vụ ở luồng bình thường:
overview, skill-gap và recommendations của một dự án. Không tính auth, retry,
làm mới hoặc thao tác người dùng; nếu không có dự án thì chỉ cần overview.

## Thay đổi giao diện

- Giữ bố cục, chức năng phân tích và phân công hiện hữu.
- Hiển thị các tổng từ BE và tối đa 5 dòng phân bổ.
- Bộ chọn dự án chỉ tải khi mở; tìm kiếm có debounce 250 ms, mỗi trang 10 dự án.
  Không cắt danh sách ở 100 dự án. Tìm từ khóa mới trở về trang đầu.
- Escape đóng bộ chọn; đóng/chọn xong trả focus về nút mở; hỗ trợ mobile.
- Nút Làm mới yêu cầu tải lại các query đang dùng. Ghi dữ liệu thành công cũng
  invalidates cache, bao gồm overview. Không thêm cơ chế polling liên tục.
- Nhãn Đã tải thể hiện thời gian tạo phản hồi, không quảng cáo dữ liệu real-time.

Giới hạn còn lại: `useCapacity` trong hộp thoại phân công vẫn tổng hợp từ từng dự
án; các selector khác còn dùng `useAll`. Skill-gap/recommendations vẫn là API
riêng, chưa giới hạn toàn bộ kích thước phản hồi. Đợt này tối ưu luồng mở tổng quan,
không tuyên bố mọi màn hình đã sẵn sàng với hàng triệu bản ghi.

## Kiểm thử

Trong backend:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -B -m ruff check app tests
```

Test mới kiểm tra: đăng nhập/quyền, buộc đổi mật khẩu, tổng lớn hơn một trang,
database rỗng, lỗi 503, dữ liệu allocation vượt giới hạn, số truy vấn cố định,
đóng session khi lỗi và không trả kết quả một phần.

Kiểm tra graph thật **chỉ đọc**, chạy khi cấu hình hợp lệ và không có người sửa
dữ liệu đồng thời để tránh số liệu thay đổi giữa các phép đối chiếu:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_dashboard_integration.py -q
```

Chỉ chạy đúng file trên nếu muốn chỉ đọc. `tests/test_crud_api.py` là integration
test khác, có tạo/xóa bản ghi test. Không dùng seed để kiểm tra dashboard.

Trong frontend:

```powershell
npm.cmd run format:check
npm.cmd run build
npm.cmd test
npm.cmd run test:auth-stack
```

Test browser kiểm tra số loại request khi mở trang, tìm dự án thứ 125, phân trang,
mobile, focus/Escape, dữ liệu rỗng, lỗi/retry và làm mới sau khi ghi phân công.
Test auth-stack dùng FastAPI thật, SQLite tạm và graph stub, không ghi dữ liệu thật.

## Các file chính

- `backend/app/api/dashboard.py`: endpoint và hợp đồng OpenAPI.
- `backend/app/schemas/dashboard.py`: validation phản hồi.
- `backend/app/services/dashboard_service.py`: điều phối và thời gian phản hồi.
- `backend/app/repositories/dashboard_repository.py`: truy vấn aggregate.
- `frontend/src/pages/Dashboard.tsx`: dashboard dùng API tổng hợp.
- `frontend/src/components/ProjectPicker.tsx`: bộ chọn dự án có phân trang.
