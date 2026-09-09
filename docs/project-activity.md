# Nhật ký hoạt động dự án

Triển khai ngày 10/09/2026. Đây là nhật ký thay đổi nghiệp vụ của dự án, **không
phải nhật ký toàn bộ ứng dụng** và chưa phải chứng nhận sẵn sàng production.

## Mục đích và phạm vi

Admin có thể trả lời: ai thay đổi dự án, lúc nào, trường nào đổi từ giá trị gì
sang giá trị gì. Dữ liệu lấy từ API thật, không sinh lịch sử giả cho dữ liệu cũ.

| Tài nguyên | Sự kiện | Trường được lưu trước/sau |
| --- | --- | --- |
| Project | Tạo, cập nhật, xóa | project_id, name, description, status |
| WORKS_ON | Gán, cập nhật, gỡ phân công | project_id, employee_id, role, allocation |
| REQUIRES_SKILL | Thêm, cập nhật, gỡ yêu cầu | project_id, skill_id, min_level, priority |

PUT/PATCH không thay đổi các trường trên không tạo sự kiện mới. Yêu cầu bị từ
chối do quyền, validation, không tồn tại hoặc vượt allocation không được ghi
thành một thay đổi thành công. Mỗi thao tác thay đổi thực tế tạo một sự kiện.

Chưa bao gồm: CRUD Employee/Skill, HAS_SKILL, đăng nhập, đổi mật khẩu, cấp/thu
hồi quyền, scripts seed và Cypher chạy trực tiếp. Không có hồi tố, nút hoàn tác,
API sửa/xóa lịch sử, xuất báo cáo hoặc chính sách tự động xóa log.

## Cách sử dụng

1. Chạy backend và frontend theo [hướng dẫn FE](frontend.md), đăng nhập Admin.
2. Vào **Dự án → một dự án → Hoạt động** để xem riêng dự án đó.
3. Hoặc chọn **Hoạt động** ở thanh bên, đường dẫn `/activity`, để xem toàn bộ
   lịch sử, bao gồm dự án đã xóa.
4. Lọc theo mã dự án, tên/mã tài khoản, hành động, loại thay đổi và thời gian.
   Nhấn **Áp dụng bộ lọc**; **Xóa bộ lọc** trả về trang đầu.
5. Mở **Xem thay đổi** để xem bảng Trước/Sau, chỉ hiển thị trường khác nhau.
6. Nút mũi tên chuyển trang mới/cũ; **Mới nhất** quay về đầu hoặc tải lại.

Thời gian nhập và hiển thị theo múi giờ trình duyệt, gửi lên server dưới dạng
thời điểm có múi giờ. Khoảng thời gian bao gồm hai đầu mút. UI có trạng thái tải,
rỗng, lỗi và thử lại, hỗ trợ bàn phím và màn hình điện thoại. Nội dung được React
escape, không render mô tả thành HTML. Link mở dự án cũ có thể trả về không tìm
thấy nếu dự án đã xóa; lịch sử vẫn đọc được tại trang Hoạt động chung.

## Quyền và người thực hiện

- Chỉ **Admin** được đọc `GET /api/activity`. Manager/Viewer nhận 403 dù gọi API
  trực tiếp; FE không hiển thị mục/tab và không gửi request lịch sử cho hai role.
- Người chưa đăng nhập nhận 401; người buộc đổi mật khẩu chưa được đọc lịch sử.
- Manager vẫn sửa dự án được giao theo chính sách hiện có. Thao tác hợp lệ của
  Manager được ghi, nhưng không tự cấp cho Manager quyền đọc audit.
- `actor_id` là `user_id` của tài khoản đăng nhập, không phải `employee_id`.
  `actor_name` là snapshot tên tại thời điểm xác thực yêu cầu.
- Server tạo `AuditActor` từ phiên đã xác thực. Không lấy actor từ body/header
  do khách tự khai báo. Không dùng trạng thái actor toàn cục giữa các request.
- Session, CSRF và quyền ghi giữ nguyên; nhật ký không mở thêm quyền sửa.

## Lưu trữ và tính nguyên tử

Tài khoản/phiên vẫn ở SQLite. Nhật ký nghiệp vụ được lưu trong graph đang cấu
hình bằng node độc lập `AuditEvent`, không chuyển dữ liệu auth sang graph.

Các thuộc tính: `event_id` (UUID), `occurred_at` (chuỗi UTC độ dài cố định),
`actor_id`, `actor_name`, `project_id`, `resource_type`, `resource_id`, `action`,
`before_json`, `after_json`. Hai snapshot là JSON với danh sách trường cho phép;
`null` ở trước nghĩa là tạo, `null` ở sau nghĩa là xóa.

Luồng ghi:

1. API xác thực và lấy actor; service áp dụng quy tắc nghiệp vụ.
2. Repository tạo UUID/thời gian một lần, ngoài callback có thể được driver retry.
3. Trong một `session.execute_write`: khóa tài nguyên khi cần, lấy dữ liệu
   trước, sửa nghiệp vụ, ghi AuditEvent trên **cùng transaction**.
4. Nếu ghi audit lỗi, exception đi ra callback; transaction không commit.
   API trả lỗi thay vì báo thành công mà thiếu nhật ký.

Khóa Employee dùng chung cho upsert/delete WORKS_ON; kiểm tra allocation vẫn
nằm trong transaction. Project được khóa khi sửa/xóa thông tin và thay đổi yêu
cầu kỹ năng. Snapshot lấy sau khi khóa. Hai phép thử đồng thời không thay cho
stress test dài hạn hoặc chứng minh mọi interleaving.

AuditEvent không có quan hệ nối tới Project/Employee/Skill. Xóa dự án không xóa
nhật ký, cũng không bị node audit cản trở. Nếu tái sử dụng cùng `project_id`,
lịch sử các lần tồn tại được xem chung theo mã; hiện chưa có ID vòng đời riêng.

Driver có thể chạy lại managed transaction; cùng một lời gọi repository giữ
cùng context/UUID qua retry. Đây không phải cơ chế idempotency-key cho mọi
request HTTP hoặc bảo đảm exactly-once xuyên sự cố mạng. Xem
[Neo4j Python transaction manual](https://neo4j.com/docs/python-manual/current/transactions/).

## Schema và nâng cấp

Từ thư mục `backend`, với môi trường và thông tin graph hiện có:

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_activity_schema
```

Script chỉ thêm schema, có `IF NOT EXISTS`, không seed/sửa/xóa dữ liệu nghiệp vụ:

- Unique constraint `audit_event_id_unique` trên `AuditEvent.event_id`.
- Composite index `audit_event_time` trên `(occurred_at, event_id)`.
- Composite index `audit_event_project_time` trên `(project_id, occurred_at)`.

`scripts.setup_schema` cũng gọi phần này cho cài đặt mới. Backend không tự chạy
schema migration mỗi lần khởi động. Tài khoản migration cần quyền tạo schema;
tài khoản chạy API cần đọc/tạo AuditEvent cùng quyền nghiệp vụ hiện tại. Thiếu
quyền ghi audit làm thao tác được audit thất bại, không bỏ qua lỗi.

Ba đối tượng schema đã được tạo và kiểm tra có tên trên graph cấu hình hiện tại
trong đợt này. Không thêm dependency, Docker image hoặc bản sao database.
Index có sẵn không có nghĩa mọi tổ hợp bộ lọc luôn dùng index: cần PROFILE và
đo với dữ liệu đại diện trước khi cam kết hiệu năng ở quy mô lớn.

## API đọc

`GET /api/activity` — session Admin, response `Cache-Control: no-store`.

| Query | Ý nghĩa |
| --- | --- |
| project_id | Chính xác mã `PROJ` và ít nhất 3 chữ số; tối đa 100 ký tự |
| action | CREATED, UPDATED, DELETED |
| resource_type | PROJECT, WORKS_ON, REQUIRES_SKILL |
| actor | Tên chứa chuỗi, không phân biệt hoa/thường; hoặc mã tài khoản chính xác; tối đa 100 ký tự |
| since, until | ISO datetime có múi giờ; since không được sau until |
| limit | 1–100, mặc định 20 |
| cursor | Marker trang trước trả về; tối đa 512 ký tự |

Ví dụ: `/api/activity?project_id=PROJ001&resource_type=WORKS_ON&limit=20`.
Response gồm `items` và `next_cursor` (`null` khi hết). Mỗi item gồm metadata và
hai object `before`, `after`; không trả JSON nội bộ hoặc toàn bộ node nghiệp vụ.

Thứ tự `(occurred_at DESC, event_id DESC)`, keyset pagination, đọc tối đa
`limit + 1` bản ghi. Không tính tổng toàn bộ lịch sử. Cursor được kiểm tra cấu
trúc/thời gian/UUID, nhưng không phải token cấp quyền hay snapshot database.
Đổi bộ lọc thì bỏ cursor cũ. Dữ liệu mới commit trong khi xem không được đóng
băng; nhấn Mới nhất để tải lại. Thời gian được lấy trước khi thực thi callback,
**không phải thứ tự commit tuyệt đối** khi nhiều request đồng thời hoặc retry.

Lỗi: 401 chưa đăng nhập, 403 trái quyền/buộc đổi mật khẩu, 422 bộ lọc/cursor sai,
503 lỗi repository. Không chuyển lỗi DB thành lịch sử rỗng giả.

## File liên quan

| File | Vai trò |
| --- | --- |
| `backend/app/core/audit.py` | Actor/context bất biến, UUID, UTC |
| `backend/app/schemas/activity.py` | Kiểu sự kiện và response |
| `backend/app/repositories/activity_repository.py` | Snapshot allowlist, ghi cùng transaction, query lịch sử |
| `backend/app/repositories/project_repository.py` | Audit Project |
| `backend/app/repositories/project_assignment_repository.py` | Audit WORKS_ON và khóa Employee |
| `backend/app/repositories/project_requirement_repository.py` | Audit REQUIRES_SKILL và khóa Project |
| `backend/app/services/activity_service.py` | Chuẩn hóa bộ lọc, cursor |
| `backend/app/api/activity.py` | Endpoint chỉ Admin |
| `backend/app/api/projects.py`, `project_assignments.py`, `project_requirements.py` | Truyền actor xác thực vào service/repository |
| `backend/scripts/setup_activity_schema.py` | Migration cộng thêm |
| `frontend/src/components/Activity.tsx` | Trang/tab lịch sử, bộ lọc, bảng trước/sau |
| `frontend/src/pages/Details.tsx`, `frontend/src/App.tsx` | Tab, route, menu theo quyền |
| `backend/tests/test_activity*.py`, `frontend/tests/activity.spec.ts` | API, transaction và kiểm thử giao diện |

## Kiểm thử

Kết quả chạy ngày 10/09/2026:

| Nhóm | Kết quả |
| --- | --- |
| Backend không integration | 122 passed, gồm 37 test mới cho activity |
| Graph activity riêng | 6 passed; lifecycle, hai trường hợp đồng thời và ba trường hợp rollback |
| Dashboard đọc graph thật | 1 passed |
| Playwright UI | 27 passed, gồm 6 test activity |
| FE–FastAPI auth cô lập | 1 passed; có kiểm tra Admin đọc được và Viewer bị chặn activity |
| Ruff, Prettier, TypeScript và Vite build | Đạt |

Đã xem ảnh desktop/mobile của lịch sử và bảng trước/sau. `.env`, virtualenv,
`node_modules`, build và kết quả test vẫn được Git bỏ qua; không cài dependency
mới. Đã bổ sung cleanup audit theo đúng dự án/actor test cho CRUD integration
cũ; không chạy lại test đó trong đợt này vì có phụ thuộc giá trị cụ thể của dữ
liệu seed `PROJ001`. Chưa kiểm thử production, tải lớn, restore hoặc lỗi
commit mạng thực tế; retry hiện có test mô phỏng ở unit level.

```powershell
# Tại backend: không chạm graph thật
.\.venv\Scripts\python.exe -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts

# Chỉ chạy trên graph local/test: có ghi fixture nhỏ rồi dọn chính fixture đó
.\.venv\Scripts\python.exe -m pytest tests/test_activity_integration.py -q

# Kiểm tra dashboard chỉ đọc graph
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_integration.py -q
```

```powershell
# Tại frontend
npm.cmd run typecheck
npm.cmd run format:check
npm.cmd run build
npm.cmd test
npm.cmd run test:auth-stack
```

Test API kiểm tra Admin-only, actor không giả mạo được, allowlist, no-op, giới
hạn bộ lọc, phân trang, lỗi DB, callback truyền lỗi audit và context ổn định qua
retry mô phỏng. FE dùng mock chỉ trong test, có trước/sau allocation, lịch sử
dự án đã xóa, phân quyền, phân trang, lỗi/thử lại, thời gian, mobile và axe.
Auth-stack dùng FastAPI/SQLite tạm thật, graph stub; không phải FE–graph E2E.

Test graph chạy riêng từng mutation như các request API, kiểm tra lifecycle,
allocation đồng thời, chuỗi trước/sau khi sửa cùng phân công và rollback khi
ghi audit bị mô phỏng lỗi. Các fixture có mã riêng và marker ngẫu nhiên, cleanup
chỉ đúng ID + marker; event chỉ đúng mã dự án + actor test. Có xác nhận dữ liệu
test đã dọn. Không chạy suite này trên production.

### Giới hạn phát hiện khi kiểm tra engine

Phép thử ban đầu tạo node và WORKS_ON rồi MATCH lại quan hệ trong **cùng một
transaction chưa commit** trả về rỗng trên database đang cấu hình, dù MERGE trả
về thuộc tính và counter tạo quan hệ. Probe đã rollback. Không kết luận nguyên
nhân nội bộ chỉ từ kết quả này hoặc từ chuỗi phiên bản Bolt mà server báo.

Luồng API hiện tại thực hiện từng mutation trong transaction riêng; lifecycle
được kiểm tra theo luồng đó, và kiểm tra rollback được thực hiện riêng. Không
gom nhiều lần gọi callback nghiệp vụ thành API bulk/create–read–update trong
một transaction cho đến khi xác minh khả năng đọc lại dữ liệu vừa ghi của
engine. Đợt này không nâng cấp hoặc sửa cấu hình engine để che giới hạn đó.

## Bảo mật, dung lượng và phần tiếp theo

- Allowlist không lưu trường password/hash, session/CSRF token, cookie, email
  hoặc toàn bộ request. Tuy nhiên tên/mô tả/vai trò do người dùng nhập vẫn được
  lưu: **không phải bộ tự động phát hiện/xóa mọi secret trong văn bản tự do**.
- Không tuyên bố audit chống sửa tuyệt đối: người có quyền quản trị DB vẫn có
  thể thay đổi dữ liệu. Muốn chống can thiệp cần chính sách quyền, lưu trữ và
  kiểm chứng bổ sung. Xem [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).
- Mỗi thay đổi tạo thêm một node nhỏ; không sao chép cả graph. No-op không thêm
  node. Nhật ký vẫn tăng dung lượng theo thời gian; hiện chưa tự xóa/retention.
  Chốt thời hạn, ngân sách lưu trữ, backup và quyền xóa trước khi vận hành lâu dài.
- Cần backup cả graph (bao gồm audit) và SQLite; chưa có transaction chung giữa
  hai kho. Đổi quyền đồng thời với một request đang chạy không tạo trật tự commit
  thống nhất giữa hai DB.
- Bước vận hành nên làm tiếp: readiness, quy trình backup/restore trên môi trường
  riêng; sau đó staging HTTPS, giám sát và tải có kiểm soát. Audit tài khoản/quyền
  là phần còn thiếu riêng, cần ghi trong cùng SQLite transaction.
