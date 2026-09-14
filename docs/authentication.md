# Đăng nhập và phân quyền SkillGraph

## Bắt đầu: tạo Admin của bạn

Không có tài khoản hay mật khẩu mặc định. Không có API đăng ký công khai.
Mở PowerShell tại thư mục dự án:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.create_admin
```

Nhập email, tên hiển thị và mật khẩu 15–128 ký tự. Mật khẩu được nhập ẩn, không
đưa vào lệnh shell, mã nguồn hoặc `.env`. Script chỉ tạo tài khoản khi kho tài
khoản còn trống; hai lần chạy đồng thời cũng không tạo được hai Admin đầu tiên.
Script không cần ghi CognoDB. Nếu đã có tài khoản, dùng trang quản trị.

Sau đó mở hai terminal:

```powershell
# Terminal 1, tại backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

```powershell
# Terminal 2, tại frontend
npm.cmd run dev
```

Mở <http://127.0.0.1:5173>. Dùng email và mật khẩu vừa tạo. Không cần cài lại
`node_modules` nếu đã có. Vào **Tài khoản** trên thanh bên để tạo thêm người dùng.

## Quyền truy cập

Mọi vai trò đều xem dữ liệu chung của không gian. Đây chưa phải mô hình nhiều
doanh nghiệp/tenant tách biệt hoặc giới hạn hồ sơ nhân viên theo phòng ban.

| Thao tác | Admin | Manager | Viewer |
| --- | --- | --- | --- |
| Xem nhân viên, kỹ năng, dự án, phân tích và gợi ý | Có | Có | Có |
| Tạo/sửa/xóa nhân viên và danh mục kỹ năng | Có | Không | Không |
| Gán/sửa/gỡ kỹ năng của nhân viên | Có | Không | Không |
| Tạo/xóa dự án | Có | Không | Không |
| Sửa thông tin dự án, phân công và yêu cầu kỹ năng | Mọi dự án | Chỉ dự án được giao | Không |
| Tạo tài khoản, phân quyền, khóa, đặt lại mật khẩu | Có | Không | Không |
| Đổi mật khẩu cá nhân, đăng xuất | Có | Có | Có |
| Xem nhật ký hoạt động dự án | Có | Không | Không |

Admin chọn các dự án được giao khi cấp quyền Manager. Manager không có dự án
được giao vẫn đọc được dữ liệu nhưng không có quyền ghi. Tài khoản đăng nhập
không tự đồng nhất với một Employee; đây là hai khái niệm riêng.

Nhật ký dự án là ngoại lệ đối với dữ liệu chung: chỉ Admin đọc được, kể cả lịch
sử thao tác của Manager. Xem [phạm vi và cách lưu audit](project-activity.md).
Audit đăng nhập/đổi quyền/tài khoản chưa được triển khai trong đợt này.

Backend xác thực mọi route nghiệp vụ, kiểm tra CSRF với phương thức ghi và mặc
định từ chối quyền ghi nếu không nằm trong chính sách. Manager được cho phép
theo từng hàm endpoint cụ thể và `project_id` được giao, không dựa vào role do
trình duyệt gửi lên. Giới hạn allocation 100% tại database vẫn giữ nguyên.

## Tài khoản và mật khẩu

- Tài khoản mới hoặc được Admin đặt lại mật khẩu phải đổi mật khẩu tạm trước
  khi đọc/ghi dữ liệu nghiệp vụ. Gửi mật khẩu tạm qua kênh riêng an toàn.
- Bấm ảnh đại diện trên cùng để mở tài khoản cá nhân và đổi mật khẩu.
- Đổi mật khẩu, khóa tài khoản hoặc thay đổi quyền thu hồi phiên đăng nhập.
  Người dùng phải đăng nhập lại; quyền không được giữ trong token cũ.
- Không cho phép tự khóa/hạ quyền Admin đang thao tác hoặc bỏ Admin hoạt động
  cuối cùng. Không xóa vật lý tài khoản; dùng khóa tài khoản.
- Quên mật khẩu: liên hệ một Admin khác để đặt lại. Chưa có email tự khôi phục,
  MFA hoặc SSO. Nếu mất quyền truy cập Admin duy nhất, đã có
  [CLI khôi phục cục bộ](admin-recovery.md) cho người vận hành được phép ghi
  DB: chỉ xử lý Admin đang hoạt động, nhập ẩn mật khẩu tạm, thu hồi phiên và
  buộc đổi mật khẩu sau đăng nhập. **Không xóa file auth.sqlite3 để tạo lại**.
  Nếu vẫn nhớ mật khẩu, không cần chạy CLI khôi phục.

## Phiên đăng nhập và lưu trữ

- Mật khẩu băm bằng Argon2id qua `pwdlib`. Mật khẩu không bị trim và không được
  trả lại trong response; lỗi validation không phản chiếu giá trị đầu vào.
- Token phiên ngẫu nhiên 256 bit nằm trong cookie HttpOnly, SameSite=Lax,
  Path=/, không có Domain. SQLite chỉ lưu SHA-256 của token.
- CSRF token gắn với từng phiên, được gửi trong header `X-CSRF-Token` khi ghi.
  Đồng thời yêu cầu `Origin` thuộc danh sách cho phép. POST login cũng kiểm tra
  Origin. Không chấp nhận Origin thiếu, `null`, hoặc wildcard.
- Phiên hết hạn tuyệt đối sau 8 giờ và sau 30 phút không có request xác thực.
  Mỗi tài khoản tối đa 5 phiên. Đăng nhập tạo token mới; đăng xuất thu hồi phiên
  hiện tại phía server. Session và dữ liệu API gửi `Cache-Control: no-store`.
- FE giữ CSRF token trong bộ nhớ, không lưu token hoặc mật khẩu trong
  localStorage/sessionStorage. Khi đăng xuất/hết phiên/đổi người dùng, cache
  dữ liệu bị hủy; các tab cùng trình duyệt được báo khi phiên thay đổi.
- Giới hạn mặc định: 5 lần thử cho mỗi email và 30 lần cho mỗi IP trong cửa sổ
  15 phút. Lỗi tài khoản không tồn tại, sai mật khẩu hoặc đã khóa có cùng thông
  báo. Bộ đếm được lưu trong SQLite, không mất khi khởi động lại backend.

Dữ liệu tài khoản nằm ở `backend/data/auth.sqlite3`, đã được `.gitignore` bỏ qua.
Graph nghiệp vụ vẫn nằm ở CognoDB, không chuyển dữ liệu sang SQLite. Không
phục vụ thư mục `backend/data/` dưới dạng static; chỉ cấp quyền filesystem cho
tài khoản chạy backend và người quản trị. Sao lưu file này như dữ liệu nhạy cảm,
ở ngoài Git, bằng SQLite backup hoặc khi backend đã dừng. Không xóa cùng cache.

Đã có [công cụ sao lưu/phục hồi](backup-restore.md) tạo cặp graph + SQLite và
kiểm tra checksum. Phục hồi chỉ vào nơi riêng, thu hồi phiên trong bản được
phục hồi, không ghi đè kho đang dùng. Xem [readiness](readiness.md) để phát hiện
DB bị mất/khóa hoặc thiếu schema mà không tự tạo DB mới.

## Cấu hình

Các giá trị có thể đặt qua environment variables hoặc `backend/.env`:

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `AUTH_DB_PATH` | `backend/data/auth.sqlite3` (đường dẫn tuyệt đối tính từ mã nguồn) | Kho tài khoản/phiên |
| `AUTH_COOKIE_SECURE` | `false` | Chỉ dùng false với HTTP localhost |
| `AUTH_SESSION_HOURS` | `8` | Thời hạn tuyệt đối, 1–24 giờ |
| `AUTH_IDLE_MINUTES` | `30` | Hết phiên khi không hoạt động, 5–120 phút |
| `AUTH_ALLOWED_ORIGINS` | localhost/127.0.0.1, cổng 5173/4173/8000 | Mảng JSON các origin chính xác |

Trước khi triển khai Internet, cần HTTPS, `AUTH_COOKIE_SECURE=true`, danh sách
origin chỉ chứa domain thật, reverse proxy cùng origin cho FE/API, giới hạn
body/rate ở proxy, sao lưu và giám sát. Không bật CORS wildcard có credentials.
`--no-proxy-headers` trong lệnh local tránh tin IP giả từ header. Khi dùng reverse
proxy thật, chỉ tin proxy được cấu hình để xóa/ghi lại forwarded headers; nếu
không, mọi người dùng có thể chung bộ đếm IP hoặc IP bị giả mạo.

SQLite phù hợp với phiên bản chạy một máy chủ và lượng ghi nhỏ hiện tại. Chưa
được kiểm thử tải lớn/nhiều replica. Khi mở rộng cần kho tài khoản/phiên tập
trung, MFA/SSO nếu cần, nhật ký kiểm toán và đánh giá bảo mật trước production.

## Kiểm thử

```powershell
# backend: không truy cập CognoDB
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q

# frontend: API giả lập, chỉ trong test
npm.cmd test

# frontend + FastAPI auth thật; SQLite tạm, graph được stub, không dùng DB của bạn
npm.cmd run test:auth-stack

# frontend + FastAPI: ma trận đủ ba role, dữ liệu tổng hợp, không dùng graph thật
npm.cmd run test:rbac
```

`test:auth-stack` dùng cổng 5174 và 18000, tạo tài khoản **chỉ trong database
tạm của bài test**. Các mật khẩu mẫu trong test không phải tài khoản ứng dụng.
Không dùng `tests.auth_browser_server` làm server chạy dự án.

`test:rbac` dùng cùng hai cổng test; chạy lần lượt với `test:auth-stack`, không
chạy đồng thời. Kết quả 14/09/2026: 10 test trình duyệt đạt, bao phủ 9 trường
hợp nghiệm thu, có API ghi trực tiếp và thu hồi phiên. Xem
[báo cáo nghiệm thu ba role](rbac-acceptance.md) để phân biệt phần đã kiểm chứng
với các giới hạn: auth/SQLite thật trong test, graph mô phỏng, chưa phải E2E
với CognoDB thật hoặc production.

`npm.cmd run test:live` cần backend thật, dữ liệu có sẵn và tài khoản đã đổi mật
khẩu. Cấp email/mật khẩu qua `SKILLGRAPH_TEST_EMAIL` và
`SKILLGRAPH_TEST_PASSWORD` trong môi trường process; không viết mật khẩu trực
tiếp vào lịch sử lệnh. Khi thiếu biến, bài test được skip có giải thích. Test
login/logout để mở/thu hồi phiên nhưng chỉ đọc graph. Trace/video và ảnh tự
động khi lỗi đã tắt để tránh ghi lại thông tin đăng nhập; ảnh dashboard vẫn
chứa dữ liệu nội bộ và nằm trong thư mục bị Git bỏ qua.

Kiểm thử CRUD tích hợp backend vẫn dùng CognoDB và tạo/xóa bản ghi test; kho tài
khoản của bài này đã tách riêng. Không chạy trên database production.

Thiết kế tham khảo hướng dẫn [băm mật khẩu của FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[quản lý phiên của OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
và [chống CSRF của OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
Ứng dụng này dùng server-side session, không dùng JWT/localStorage.
