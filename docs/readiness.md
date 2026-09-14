# Kiểm tra sẵn sàng của hệ thống

Triển khai ngày 11/09/2026. Mục tiêu: phân biệt **tiến trình API còn chạy** với
**các dependency tối thiểu dùng được**. Không coi một health check xanh là bằng
chứng ứng dụng đủ an toàn để triển khai production.

## API và cách dùng

| Endpoint | 200 | 503 | Chạm database? |
| --- | --- | --- | --- |
| `GET /health` | `{"status":"ok"}` | Không phụ thuộc DB | Không |
| `GET /health/ready` | `{"status":"ready"}` | `{"status":"not_ready"}` | Có, probe nhẹ và có cache |

Hai endpoint không cần đăng nhập để công cụ vận hành kiểm tra được cả khi auth
bị lỗi. Response không chứa URI, tài khoản, đường dẫn, schema cụ thể hoặc
exception. Đều gửi `Cache-Control: no-store`. Readiness lỗi có `Retry-After: 5`.
Vite đã proxy `/health`, nên `/health/ready` cũng hoạt động qua frontend proxy.

Với BE đang chạy ở localhost:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

PowerShell báo lỗi HTTP khi nhận 503 là đúng; không đổi thành 200 để che lỗi.
Để người vận hành biết dependency nào lỗi mà không công khai chi tiết, chạy
từ thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_readiness
```

Ví dụ thành công: `{"graph":"ok","auth":"ok"}`. Exit code 0 là đạt, 1 là
chưa sẵn sàng. Các mã nội bộ: `unavailable`, `timeout`, `schema_missing` (graph),
`admin_missing` (auth). CLI không in credentials hoặc exception gốc.

## Đã kiểm tra gì?

Graph:

- Dùng async driver riêng với pool tối đa 1 kết nối; không chiếm pool nghiệp vụ.
- `RETURN 1` kiểm tra thực sự chạy truy vấn được, không chỉ mở TCP.
- Kiểm tra tên các unique constraint của Employee, Skill, Project, Team và
  AuditEvent đã được tạo. Không chạy migration hoặc ghi node khi probe.
- Có timeout phía driver/server và deadline async cho toàn bộ probe graph.
  Khi hết hạn, hủy session để đóng kết nối đang chờ; không dùng thread bị bỏ
  mặc cho thao tác mạng. Đã có test với TCP peer local nhận kết nối nhưng không
  trả lời Bolt handshake.

Auth SQLite:

- Mở file **đã tồn tại** ở chế độ `mode=rw`, không gọi constructor `AuthStore`.
  File bị mất không bị tạo lại thành một DB rỗng rồi báo xanh.
- Kiểm tra các cột cần thiết của users/sessions/login_limits và có Admin đang
  hoạt động. Không đọc mật khẩu vào response.
- Lấy write lock ngắn bằng `BEGIN IMMEDIATE` rồi rollback, vì xác thực có ghi
  session. Không sửa row, tạo bảng hoặc chạy integrity scan lớn trên mỗi probe.
- SQLite busy timeout 0,2 giây; progress deadline 0,5 giây; phần chờ async 0,75
  giây. Probe SQLite chạy ngoài event loop. OS/filesystem bị treo ở mức kernel
  không thể bị Python cưỡng chế dừng bằng cách hủy thread; đây không phải cam
  kết deadline vật lý cho mọi lỗi lưu trữ.

Hai probe chạy đồng thời. Trong mỗi process, lock gộp các yêu cầu đồng thời
thành một lần kiểm tra, cache kết quả trong vài giây. Kết quả có thể chậm phản
ánh sự cố hoặc phục hồi bằng khoảng cache; nhiều worker có cache riêng.

## Cấu hình và file liên quan

| Biến môi trường | Mặc định | Giới hạn |
| --- | --- | --- |
| `READINESS_TIMEOUT_SECONDS` | 4 | 1–10 giây, deadline graph |
| `READINESS_CACHE_SECONDS` | 5 | 1–30 giây, cache mỗi process |

Các biến mẫu ở `backend/.env.example`. Sau khi thay cấu hình, khởi động lại BE.
Không thay đổi các timeout/truy vấn của API nghiệp vụ trong đợt này.

| File | Trách nhiệm |
| --- | --- |
| `backend/app/main.py` | Endpoint, lifecycle driver, cache-control |
| `backend/app/services/readiness_service.py` | Probe, timeout, cache, single flight |
| `backend/app/db/auth_schema.py` | Danh sách cột auth dùng chung khi kiểm tra |
| `backend/app/core/config.py` | Cấu hình đã validation |
| `backend/scripts/check_readiness.py` | CLI dành cho người vận hành |
| `backend/tests/test_readiness.py` | Test cô lập và TCP peer không phản hồi |
| `backend/tests/test_readiness_integration.py` | Test rõ ràng trên cấu hình thật |

## Xử lý khi chưa sẵn sàng

1. `graph=unavailable/timeout`: kiểm tra instance đang chạy, kết nối mạng và
   credentials trong environment; không đưa chúng vào chat/log/Git.
2. `schema_missing`: xem migration đã chạy chưa. `python -m scripts.setup_schema`
   chỉ dùng sau khi xác nhận đúng instance; không gọi seed để chữa health check.
3. `auth=unavailable`: kiểm tra file, quyền đọc/ghi và tiến trình đang giữ khóa.
   Không xóa `auth.sqlite3` hoặc `.venv` để thử sửa. Nếu file mất, xem
   [quy trình sao lưu/phục hồi](backup-restore.md).
4. `admin_missing`: xác minh đang trỏ đúng kho auth. Chỉ bootstrap Admin cho
   cài đặt mới thực sự; không tạo tài khoản thay cho việc khôi phục DB bị mất.

Trước production, chỉ cho hệ thống giám sát cần thiết gọi probe hoặc đặt giới
hạn ở reverse proxy. Không dùng readiness lỗi để tự restart vô hạn: khi DB
đang bảo trì, restart API không sửa DB. Liveness và readiness phục vụ hai mục
đích khác nhau.

## Kiểm thử và giới hạn

```powershell
# Tại backend, không dùng graph thật
.\.venv\Scripts\python.exe -m pytest tests/test_readiness.py -q

# Chủ động kiểm tra cấu hình đang dùng; không tạo dữ liệu
.\.venv\Scripts\python.exe -m scripts.check_readiness
.\.venv\Scripts\python.exe -m pytest tests/test_readiness_integration.py -q
```

Đã kiểm tra cache/đồng thời, timeout và hủy kết nối, file thiếu không tự tạo,
SQLite bị khóa/thiếu bảng/thiếu Admin, response tối thiểu, liveness độc lập và
đóng driver. Kết quả CLI trên máy hiện tại: graph và auth đều `ok`.
Test readiness qua HTTP trên cấu hình thật và test hồi quy dashboard chỉ đọc
đều đạt; test FE–FastAPI auth cô lập cũng đạt. Tổng backend không integration
cùng bộ backup/restore: 170 passed, gồm 48 test mới của đợt này.

Trong đợt [nghiệm thu RBAC ngày 14/09/2026](rbac-acceptance.md), test cache bị
thất bại do TTL 10 ms hết hạn khi máy bận lên lịch tác vụ. Đã sửa riêng
`test_single_flight_cache_and_expiry` dùng đồng hồ cache giả lập, kiểm tra
20 yêu cầu đồng thời, bản sao kết quả, trước/đúng ranh giới hết hạn và cleanup
driver. Không thay logic readiness hoặc timeout production; không tăng sleep
hay bỏ assertion để né lỗi. Các kết quả 170 test phía trên là mốc cũ, không
phải số lượng kiểm thử hiện tại; kết quả chạy lại ghi trong báo cáo RBAC.

Không kiểm tra khả năng ghi mọi loại dữ liệu graph, toàn bộ hình dạng constraint,
trạng thái index, mọi API nghiệp vụ, chất lượng backup, hiệu năng tải lớn hoặc
khả năng chống mất điện. Các kiểm tra sâu được tách khỏi hot health endpoint.

Tham khảo: [Neo4j Python driver timeout/configuration](https://neo4j.com/docs/api/python-driver/current/api.html),
[transaction options](https://neo4j.com/docs/python-manual/current/query-advanced/).
