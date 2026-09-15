# Xử lý lỗi thường gặp khi tiếp nhận SkillGraph

Áp dụng cho bản local 0.1.0, cập nhật 16/09/2026. Trước khi sửa: xác định đúng
thư mục source, terminal BE/FE, instance graph và file auth. Không gửi `.env`,
password, cookie, token hoặc nội dung backup vào chat để nhờ kiểm tra.

## Khởi động và kết nối

| Hiện tượng | Kiểm tra và cách xử lý an toàn |
| --- | --- |
| `ERR_CONNECTION_REFUSED` ở 5173 | FE chưa chạy/đã dừng hoặc dùng cổng khác. Tại frontend chạy `npm.cmd run dev`, mở đúng URL Vite in ra; giữ terminal đó chạy |
| Prompt PowerShell xuất hiện lại sau lệnh dev | Server đã dừng hoặc lệnh lỗi. Đọc lỗi ngay phía trên, không coi có dòng “ready” cũ là server còn chạy |
| Không gọi được `/api`, Vite báo proxy error | Khởi động BE, kiểm tra `/health` trực tiếp ở 8000, đối chiếu `SKILLGRAPH_API_TARGET`; restart Vite khi đổi `.env.local` |
| Cổng đang được dùng | Xem listener/terminal hiện hữu, không kill hàng loạt git/node/python. Dùng cổng khác và cập nhật proxy + allowed origins đồng bộ |
| `Activate.ps1` bị chặn | Không cần hạ execution policy toàn máy; gọi trực tiếp `.\.venv\Scripts\python.exe` tại backend |
| `No module named scripts/app` | Chạy module BE từ thư mục `backend`, không từ root/frontend. Dùng `python -m scripts...`, không chạy file sâu bằng đường dẫn tùy ý |
| Thiếu dependency hoặc khác môi trường | Dùng đúng interpreter `.venv`, cài requirements với constraints rồi `pip check`; FE dùng `npm ci` theo lockfile |
| Cài npm lỗi với dấu `&` trong đường dẫn | Scripts npm của repo gọi file JavaScript trực tiếp. Dùng `npm.cmd`, đặt đường dẫn PowerShell trong dấu nháy; không tự đổi tên cả workspace |

Kiểm tra chỉ đọc trên PowerShell:

```powershell
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object LocalPort -in 8000,5173,5174,18000 |
  Select-Object LocalAddress,LocalPort,OwningProcess
Invoke-RestMethod http://127.0.0.1:8000/health
```

Không cần cài lại dependency mỗi lần mở dự án. Không tải Docker/Chromium chỉ
để chữa lỗi cổng; Playwright được cấu hình dùng Edge đã có.

## Database, schema và readiness

`/health` trả OK chỉ nói API đang chạy. `/health/ready` HTTP 503 có thể do graph,
schema hoặc auth chưa sẵn sàng. Sau khi thay cấu hình, restart BE; kết quả
readiness còn cache ngắn mặc định 5 giây. Tại backend:

```powershell
.\.venv\Scripts\python.exe -m scripts.check_readiness
```

CLI dành người vận hành trả trạng thái dependency, không in credentials.
Đối chiếu [mã lỗi và phạm vi](readiness.md). Kiểm tra instance Running, đúng
URI/user/password, mạng/TLS và schema. Không vô hiệu hóa TLS để “chữa” lỗi.

Timeout nghiệp vụ không cùng ngân sách readiness. Khi graph mất kết nối,
smoke test bản bàn giao ghi nhận dashboard cần khoảng 61 giây mới hiện lỗi:
FE chờ 30 giây/request đọc rồi thử lại một lần. Không bấm Làm mới liên tục;
kiểm tra readiness bằng CLI. Đây là giới hạn đã ghi nhận, chưa tối ưu retry
trong đợt bàn giao; xem [báo cáo](release-verification.md).

Nếu auth chưa có ở bản cài mới, tạo Admin theo [bàn giao](handoff.md). Nếu auth
đáng lẽ đã có nhưng nay mất/hỏng, **không bootstrap lại**: kiểm tra đường dẫn,
quyền filesystem và backup. `AUTH_DB_PATH` tương đối phụ thuộc thư mục chạy;
dùng đường dẫn tuyệt đối để giảm nhầm lẫn.

Lỗi unique constraint khi migration: dừng, tìm dữ liệu trùng bằng kiểm tra chỉ
đọc được phép. Không xóa dữ liệu/constraint hoặc seed lại để làm lỗi biến mất.
Đợt này không tự sửa dữ liệu legacy hoặc chuyển engine database.

## Đăng nhập và quyền

- **Email/mật khẩu không đúng:** không suy ra email tồn tại hay bị khóa từ
  thông báo chung. Dùng tài khoản của đúng kho auth, kiểm tra kiểu bàn phím;
  không dùng mật khẩu mẫu trong test để đăng nhập bản thật.
- **Quên Admin:** không thể lấy lại mật khẩu từ hash. Còn Admin khác thì nhờ
  đặt lại qua UI; không còn thì người vận hành được phép dùng
  [recover_admin](admin-recovery.md), nhập ẩn và xác nhận đúng DB/tài khoản.
  Không xóa `auth.sqlite3`, không sửa hash trực tiếp, không gửi password vào chat.
- **HTTP 429:** chờ cửa sổ giới hạn, mặc định 15 phút; không xóa bảng giới hạn
  hoặc thử liên tiếp. Xem thêm chính sách trong [authentication](authentication.md).
- **HTTP 403 khi ghi:** kiểm tra role, grant project, yêu cầu đổi mật khẩu,
  origin và CSRF. FE xử lý cookie/CSRF; Swagger/curl không tự có đủ header.
  Không bỏ CSRF, wildcard origin hoặc nâng quyền chỉ để vượt lỗi.
- **Hết phiên/thu hồi:** đăng nhập lại; khóa, reset password hoặc đổi quyền
  thu hồi phiên cũ. Dữ liệu form không lưu qua phiên mới vì lý do an toàn.
- **Login lặp/không giữ cookie:** dùng thống nhất `127.0.0.1`, kiểm tra Secure
  cookie không bật khi chỉ dùng HTTP local, proxy/origin đúng cổng. Không dùng
  cấu hình HTTP local khi triển khai Internet.

## Lưu, xóa và phân công

- HTTP 409 khi xóa bản ghi còn quan hệ là kiểm soát an toàn, không phải lỗi
  nút xóa. Gỡ đúng liên kết trước; không tự cascade toàn graph.
- Lỗi mạng/timeout lúc lưu có thể xảy ra **sau khi server đã ghi**. Form giữ
  dữ liệu không có nghĩa dữ liệu chưa lưu. Kiểm tra danh sách/API/nhật ký trước
  khi gửi lại; tìm theo ID vì bản ghi mới có thể ở trang khác của danh sách.
- Validation: sửa ô tương ứng. Nút lưu không phản hồi có thể do trường bắt
  buộc, min/max hoặc đang chờ request; không bấm lặp để thử “ép” lưu.
- AVAILABLE không đồng nghĩa còn dung lượng. Khi sửa phân công, max cho dự án
  hiện tại đã cộng lại phần phân bổ ở dự án đó; tổng ngoài dự án vẫn tính vào
  giới hạn. Xem [giải thích giao diện](usability-review.md).
- Có gợi ý nhưng nút lưu bị khóa ở 0%: kiểm tra/điều chỉnh phân công khác theo
  quyền, không đổi trạng thái AVAILABLE để bỏ qua giới hạn 100%.

## Sao lưu/phục hồi lỗi hoặc dung lượng tăng

- `verify` không đạt: không dùng bộ đó để restore. Giữ output cô lập, kiểm tra
  đúng cặp manifest/graph/auth, dung lượng và checksum; không sửa checksum để
  hợp thức hóa dữ liệu hỏng.
- Đích không trống/trùng nguồn: CLI cố ý từ chối. Cấp instance test khác;
  không đổi alias hoặc xóa nguồn để vượt guard.
- Restore lỗi sau khi graph đã commit: giữ output/instance cô lập, không
  trỏ app sang đó. Hai DB không rollback chung. Theo [quy trình](backup-restore.md)
  và thử vào đích mới sau khi xác minh nguyên nhân; không có cutover tự động.
- Backup chứa dữ liệu nhạy cảm kể cả khi không có `.env`; không chia sẻ như
  source. Quyết định retention/offsite trước khi xóa; DB auth không phải cache.
- Kiểm tra Git root phải là thư mục SkillGraph, không phải `D:/`. Dùng
  `git rev-parse --show-toplevel`. Gói bàn giao không copy cả ổ D hoặc `.git`.
- `node_modules`, `.venv`, kết quả test và output `.handoff` là các nhóm khác
  nhau. Có thể tái tạo dependency/build; backup/DB không được xóa theo quy tắc
  cache. Không dùng lệnh xóa đệ quy rộng hoặc glob trên ổ đĩa.

## Khi cần chuyển cho người bảo trì

Gửi: phiên bản/fingerprint nguồn, thời điểm và múi giờ, màn hình/API lỗi,
HTTP status hoặc mã lỗi đã che thông tin nhạy cảm, bước tái hiện bằng dữ liệu
tổng hợp, kết quả lệnh kiểm tra chỉ đọc. Không gửi `.env`, DB, backup, token,
password hash, screenshot có mật khẩu hoặc log chứa thông tin cá nhân.
