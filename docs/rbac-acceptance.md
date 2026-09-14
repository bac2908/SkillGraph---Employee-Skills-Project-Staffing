# Nghiệm thu ba role: Admin, Manager và Viewer

Ngày kiểm chứng: **14/09/2026**, trên mã nguồn hiện có của SkillGraph
(HEAD khi bắt đầu: `a353622`, kèm chỉnh sửa test readiness nêu bên dưới).

**Kết luận: đạt 9/9 trường hợp của ma trận quyền trong môi trường cô lập.**
Đã chạy cả giao diện và API trực tiếp; không chỉ kiểm tra nút bị ẩn.
Đây là nghiệm thu RBAC với **FastAPI và SQLite tài khoản thật trong môi trường
test**, còn graph nghiệp vụ được mô phỏng. **Không phải nghiệm thu end-to-end
với CognoDB thật hoặc chứng nhận sẵn sàng production.**

## 1. Mục đích và phạm vi

Kiểm chứng ba role đã triển khai, không xây lại hệ thống quyền, không tạo
trang ứng dụng riêng cho từng role. Giao diện dùng chung và giới hạn thao tác
theo quyền; backend là nơi thực thi kiểm soát truy cập.

Trong đợt công việc này đã bổ sung bộ test trình duyệt `test:rbac`, dữ liệu
test riêng và các ca API kiểm tra toàn bộ nhóm endpoint nghiệp vụ. Lần tiếp
tục ngày 14/09 hoàn tất chạy lại, kiểm tra hồi quy và lưu báo cáo này.
Không thay đổi chính sách RBAC hoặc chức năng nghiệp vụ của BE/FE.

- Admin: quản lý danh mục, dự án, quan hệ, tài khoản và xem nhật ký dự án.
- Manager: đọc dữ liệu chung; chỉ sửa thông tin, phân công và yêu cầu kỹ năng
  của dự án được cấp quyền. Không được tạo/xóa dự án hoặc quản trị tài khoản.
- Viewer: chỉ đọc dữ liệu nghiệp vụ, không ghi và không xem quản trị/nhật ký.
- Cả ba role phải đổi mật khẩu tạm trước khi vào nghiệp vụ.

Xem [ma trận quyền và chính sách xác thực](authentication.md) để biết phạm vi
chi tiết. Đây vẫn là một không gian dữ liệu dùng chung, không phải đa tenant.

## 2. Môi trường test và bảo vệ dữ liệu

- Playwright mở Microsoft Edge headless, chạy FE hiện có tại cổng `5174`.
  Vite chuyển `/api` đến FastAPI riêng tại `127.0.0.1:18000`.
- Không dùng `page.route` hoặc mock HTTP/auth trong `rbac.spec.ts`. Các request
  đi qua routing, validation, session cookie, CSRF, phân quyền và AuthStore thật.
- SQLite được tạo trong thư mục tạm, chứa tài khoản tổng hợp. Cả cấu hình
  `auth_db_path` và dependency AuthStore đều trỏ vào DB tạm.
- Dữ liệu nghiệp vụ gồm hai dự án tổng hợp `PROJ101`/`PROJ102`, một nhân viên
  và một kỹ năng trong bộ nhớ. Manager chỉ được cấp `PROJ101`.
- Các service nghiệp vụ được thay bằng fixture trong process test; graph URI
  bị thay bằng địa chỉ localhost không phục vụ DB. Trong chế độ RBAC, mở
  graph session sẽ báo lỗi test ngay. Không kết nối/seed/migrate CognoDB thật.
- Mỗi lần chạy khởi tạo dữ liệu mới; một worker, không tự retry. Các ca thu hồi
  phiên dùng tài khoản riêng; Admin và người bị thu hồi dùng browser context
  riêng để không dùng chung cookie.
- Hai test server không tái sử dụng process đang chạy. Nếu cổng bị chiếm,
  kiểm tra đúng process trước; không dừng hàng loạt tiến trình của người dùng.
- Tắt trace, screenshot và video của bộ RBAC. Output nằm trong
  `frontend/test-results/rbac/`, đã bị Git bỏ qua. Không thêm dependency hoặc
  tải thêm browser trong lần chạy này.

Không chạy công cụ đặt lại mật khẩu trên Admin thật, không sửa file môi trường,
không đọc/ghi dữ liệu tài khoản thật để phục vụ nghiệm thu. Mật khẩu tổng hợp
trong mã test **không phải thông tin đăng nhập của ứng dụng đang dùng**.
Không sử dụng `tests.auth_browser_server` làm backend thường ngày.

## 3. Ma trận kết quả

Các mã `R01`–`R06` là tiền tố tên test trong
[`frontend/tests/rbac.spec.ts`](../frontend/tests/rbac.spec.ts). `R05` và `R06`
được triển khai thành ba ca mỗi nhóm, tổng cộng **10 test trình duyệt**.

| Trường hợp cần nghiệm thu | Bằng chứng giao diện và API | Kết quả |
| --- | --- | --- |
| Admin quản lý dữ liệu và tài khoản | R02: tạo/sửa/xóa dự án bằng biểu mẫu, API trả 201/200/204, đọc lại xác nhận thay đổi; sau xóa GET trả 404. Tạo Manager, lưu grant dự án và cờ buộc đổi mật khẩu; mở trang nhật ký được | PASS |
| Manager sửa dự án được giao | R03: có nút sửa PROJ101, lưu qua UI nhận 200 và đọc lại đúng nội dung. Test backend xác nhận cả 5 API ghi được cấp quyền trả 2xx | PASS |
| Manager sửa dự án không được giao | R03: không có nút sửa/phân công PROJ102; PATCH/PUT/DELETE trực tiếp bị 403. Đọc lại dự án không thay đổi; không được tạo/xóa dự án dù có grant | PASS |
| Manager vào quản trị tài khoản hoặc nhật ký | R03: truy cập trực tiếp `/users` và `/activity` hiện trang từ chối; tab hoạt động bị ẩn; GET API tài khoản/nhật ký trả 403 | PASS |
| Viewer xem dữ liệu nghiệp vụ | R04: bảng nhân viên, kỹ năng, dự án hiển thị dữ liệu test; API danh mục, dashboard, skill-gap và recommendations trả 200 | PASS |
| Viewer gọi API ghi trực tiếp | R04: 15 thao tác POST/PATCH/PUT/DELETE trên danh mục và quan hệ đều trả 403 với lý do RBAC; không thể tự nâng role thành Admin; dự án đọc lại không thay đổi | PASS |
| Người chưa đăng nhập gọi nghiệp vụ | R01: deep link bị chuyển về đăng nhập, không có sidebar; API đọc/ghi trả 401. Backend kiểm tra toàn bộ 28 tổ hợp method/path nghiệp vụ hiện có từ OpenAPI | PASS |
| Tài khoản khóa hoặc phiên đã thu hồi | R05: khóa tài khoản, reset mật khẩu, đổi Manager thành Viewer qua API Admin; phiên cũ gọi `/me`, đọc dữ liệu và gửi lệnh ghi với CSRF cũ đều 401. UI quay về đăng nhập khi làm mới và bỏ dữ liệu hiển thị cũ | PASS |
| Buộc đổi mật khẩu trước nghiệp vụ | R06 cho cả ba role: chỉ thấy trang đổi mật khẩu, FE chưa gửi request nghiệp vụ; API trực tiếp vẫn 403. Đổi mật khẩu xong đăng xuất, phiên cũ 401; đăng nhập lại đọc được dữ liệu và giữ đúng role | PASS |

Ở ca thu hồi phiên, UI nhận biết khi có request tiếp theo; **không tuyên bố có
push tức thời xóa màn hình đang mở trên mọi thiết bị**. Tài khoản bị khóa hoặc
mật khẩu cũ sau reset không đăng nhập lại được. Người bị hạ quyền đăng nhập
lại chỉ có Viewer và vẫn bị từ chối sửa dự án trước đây được giao.

## 4. Kiểm tra API bổ sung ở backend

[`backend/tests/test_auth.py`](../backend/tests/test_auth.py) có 73 ca, gồm các
test auth hiện có và 6 ca RBAC bổ sung sau khi tham số hóa:

- `test_rbac_all_business_writes_denied_outside_role_or_grant`: Viewer và
  Manager ngoài grant bị chặn trên mọi route ghi nghiệp vụ lấy từ OpenAPI,
  cũng như API quản trị tài khoản. Có cookie/Origin/CSRF hợp lệ nên 403 không
  phải kết quả nhầm do thiếu CSRF. Graph session không được gọi.
- `test_rbac_password_gate_covers_all_business_routes`: kiểm tra cờ buộc đổi
  mật khẩu của cả ba role trên toàn bộ API nghiệp vụ, không chỉ route FE mở.
- `test_rbac_manager_positive_2xx_for_all_five_granted_write_routes`: PATCH
  thông tin dự án, PUT/DELETE phân công, PUT/DELETE yêu cầu kỹ năng. Với dự án
  được giao, service được gọi và nhận đúng actor Manager; dự án ngoài grant
  bị 403 và service không được gọi thêm.

Các test trước đó tiếp tục kiểm tra CSRF, Origin, cookie, hết hạn phiên,
giới hạn đăng nhập, quản trị tài khoản, thay grant thu hồi phiên, bảo vệ Admin
cuối cùng và dữ liệu bí mật không xuất hiện trong response. Những ca dùng
service giả chỉ chứng minh routing/quyền/actor, không chứng minh transaction
hay việc ghi audit xuống graph.

## 5. File liên quan và cách chạy lại

| File | Vai trò |
| --- | --- |
| [rbac.spec.ts](../frontend/tests/rbac.spec.ts) | Ma trận UI + HTTP thực, 10 kịch bản |
| [playwright.rbac.config.ts](../frontend/playwright.rbac.config.ts) | Hai server riêng, một worker, không retry/trace/video |
| [playwright.auth-stack.config.ts](../frontend/playwright.auth-stack.config.ts) | Cấu hình auth-stack dùng chung; thay webServer bằng cấu hình tường minh để tránh gộp/chạy trùng server |
| [package.json](../frontend/package.json) | Lệnh `npm.cmd run test:rbac` |
| [auth_browser_server.py](../backend/tests/auth_browser_server.py) | FastAPI thật với SQLite tạm; cờ test-only `--rbac` |
| [rbac_browser_data.py](../backend/tests/rbac_browser_data.py) | Catalogue bộ nhớ, tài khoản tổng hợp, chặn graph session |
| [test_auth.py](../backend/tests/test_auth.py) | API auth/RBAC với SQLite tạm và service giả |
| [test_readiness.py](../backend/tests/test_readiness.py) | Test cache dùng đồng hồ kiểm soát được, không phụ thuộc TTL 10 ms |

Không có migration, thay đổi `.env`, tạo Admin thật hoặc cấu hình production
nào cần thực hiện. Dùng môi trường Python `.venv` và dependency frontend đã
cài theo README; máy kiểm thử cần Microsoft Edge như cấu hình Playwright hiện có.
Không cần khởi động BE/FE thủ công cho hai bộ test auth-stack/RBAC.

```powershell
# Từ thư mục gốc: kiểm tra backend cô lập
cd backend
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -B -m ruff check .

# Sang frontend; chạy lần lượt, auth-stack và RBAC dùng chung cổng test
cd ..\frontend
npm.cmd run test:rbac
npm.cmd run test:auth-stack
npm.cmd test
npm.cmd run build
npm.cmd run format:check
```

Nếu chỉ kiểm tra lại auth/RBAC ở backend:

```powershell
# Tại backend
.\.venv\Scripts\python.exe -B -m pytest tests/test_auth.py -q
```

## 6. Kết quả chạy và phát hiện hồi quy

- Backend sau chỉnh sửa test readiness: **230 passed, 9 deselected**, 83,71
  giây, bằng `pytest -m "not integration" -q`. Trong đó có **73 ca auth/RBAC**;
  không cộng 73 lần nữa. Chín test integration bị loại chủ động, không phải
  chín test đã đạt hoặc đã được kiểm tra với graph thật.
- `npm.cmd run test:rbac`: **10 passed**, 49,3 giây.
- `npm.cmd run test:auth-stack`: **1 passed**, 11,2 giây.
- `npm.cmd test`: **27 passed**, khoảng 1,4 phút; nhóm này mock API.
- `npm.cmd run build`: **PASS**, gồm TypeScript kiểm tra kiểu và Vite build.
- Ruff toàn backend và kiểm tra format các file Python trong phạm vi: **PASS**.
- Prettier trên test/config RBAC, config auth-stack và `package.json`: **PASS**.
- `npm.cmd run format:check` toàn frontend: **chưa đạt**, chỉ báo định dạng
  `src/styles.css` đã có trước lần tiếp tục này. Giữ nguyên CSS vì ngoài phạm vi;
  đây không phải lỗi chức năng RBAC, không tuyên bố toàn bộ check đều xanh.

Lần chạy backend đầu tiên: **229 passed, 1 failed, 9 deselected**. Ca thất bại
`test_single_flight_cache_and_expiry` dùng cache 10 ms và sleep thực, nên cache
có thể hết hạn khi các tác vụ chờ được lên lịch trên máy đang bận. Đã thay
đồng hồ cache trong **test** bằng đồng hồ kiểm soát được: kiểm tra 20 yêu cầu
đồng thời, bản sao kết quả, trước/đúng mốc hết hạn và đóng driver trong `finally`.
Không thay logic readiness, timeout hay đồng hồ của event loop trong ứng dụng.
Sau sửa, đã chạy lại toàn bộ backend không integration và đạt số lượng nêu trên.

## 7. Giới hạn và việc chưa nghiệm thu

- Không chạy `-m integration` hoặc `test:live`, không xác nhận CRUD/quan hệ,
  allocation, query, constraint, audit transaction hoặc hiệu năng trên CognoDB
  thật trong đợt này. Dashboard/phân tích trong fixture là dữ liệu mô phỏng,
  không dùng để xác nhận công thức hoặc tính nhất quán thống kê.
- Không thử ba role trên bản build đã triển khai qua HTTPS/reverse proxy.
  Build thành công không thay thế kiểm thử staging hoặc đánh giá bảo mật.
- Kết quả gắn với phiên bản được kiểm tra; khi sửa route, quyền hoặc UI cần
  chạy lại. 9/9 trường hợp này không có nghĩa toàn bộ dự án đạt 100%.
- **Mục 2 — phục hồi thật vẫn chưa được đóng.** Báo cáo này không tạo bộ backup,
  không phục hồi vào graph test và không xác nhận bản phục hồi dùng được.
  Xem [tiền kiểm và điều kiện còn thiếu](backup-restore.md).
- Trước bàn giao môi trường thật: hoàn tất drill phục hồi riêng, sau đó dùng
  tài khoản/dataset test và đích được xác nhận để nghiệm thu cùng ma trận trên
  stack có graph thật. Không dùng tài khoản hoặc bản ghi đang vận hành để thử xóa.
