# Báo cáo chốt bản bàn giao local — 16/09/2026

## Nhận diện và phạm vi

- Phiên bản khai báo BE/FE: **0.1.0**, ứng viên bàn giao cục bộ; chưa gắn Git tag.
- Base commit đầu đợt: `133311b05f11e5db72fdefc2bf8dba44a421d443` (`update usability`).
- Gói cuối bao gồm thay đổi chưa commit của bước 6. Manifest xuất kèm có danh
  sách file/SHA-256/fingerprint của chính gói; base commit không đại diện toàn
  bộ worktree mới. Không có commit/push hoặc triển khai tự động trong đợt này.
- Ngày/múi giờ chạy: **16/09/2026, Asia/Saigon (UTC+7)**.

Môi trường thực tế: Windows 11 Home Single Language x64, build 10.0.26200;
Python 3.12.10; Node.js 24.19.0; npm 12.0.2. Trình duyệt test: Microsoft Edge
headless có sẵn. Dependency Python theo `constraints-windows-py312.txt`, FE
theo `package-lock.json`; không cập nhật framework/dependency nghiệp vụ.

## Thay đổi trong bước 6

1. Bộ hướng dẫn [bàn giao](handoff.md), [demo tổng hợp](demo-scenario.md),
   [xử lý lỗi](troubleshooting.md), liên kết tài liệu chức năng/khôi phục.
2. Constraints Python cho môi trường đã thử; giữ `requirements-dev.txt`
   dùng `httpx2` phù hợp Starlette cài trong môi trường (không đổi tùy đoán
   sang `httpx` chỉ vì tên khác các ví dụ cũ).
3. Công cụ `backend/scripts/handoff.py` và test: quét file nguồn, đối chiếu
   cấu hình nhạy cảm local, xuất source ZIP/manifest, verify byte/hash.
4. `.gitignore` bổ sung biến thể `.env.*`, SQLite/sidecar và `.handoff`;
   ngoại lệ chỉ các mẫu `.env.example`/`.env.*.example`. Ignore không tự bỏ
   tracked file, vì vậy công cụ bàn giao còn kiểm tra danh sách Git.
5. README không còn đưa seed vào quy trình cài đặt bắt buộc, làm rõ khởi tạo
   schema/Admin, constraints và test không integration; bỏ dòng liên hệ cá
   nhân không liên quan. Không thay schema/nghiệp vụ hoặc quyền người thật.

## Cài đặt thử ở môi trường riêng

Xuất source ZIP bằng công cụ bàn giao, giải nén vào thư mục tạm có prefix
`skillgraph-handoff-` trên ổ C. Không copy `.venv`, `node_modules`, `.env`, auth
DB, graph hoặc backup của ứng dụng. Tạo `.venv` mới và `npm ci` mới từ nguồn
đã xuất; không dùng `--system-site-packages` hoặc phụ thuộc vào venv cũ.

Cấu hình smoke test dùng địa chỉ graph loopback không có dịch vụ, credentials
giả và SQLite trong bản riêng; chỉ nhằm kiểm tra khởi động/đăng nhập/ứng xử
khi graph chưa sẵn sàng. **Không phải kết nối hay migration CognoDB thật.**
Không gọi `seed`, restore, hoặc schema migration lên DB nguồn.

Kết quả thực chạy khoảng **00:44–01:00 ngày 16/09/2026 (UTC+7)**:

| Kiểm tra | Kết quả |
| --- | --- |
| Tạo venv sạch + cài `requirements-dev.txt` với constraints, `--no-cache-dir` | **PASS**, không copy venv cũ; `pip check`: không có dependency lỗi |
| `npm ci --no-audit --no-fund` ở bản giải nén | **PASS**, 39 package; không copy node_modules cũ |
| TypeScript + Vite build | **PASS**, CSS 35,21 kB; JS 347,04 kB; không phải benchmark tải |
| `npm run format:check` | **PASS** |
| `pytest -m "not integration" -q`, lần cuối | **296 passed, 1 skipped, 9 deselected**, 66,69 giây |
| Ruff `app tests scripts` | **PASS** |
| `npm test`, lần cuối với cấu hình cố định | **47 passed**, 2,3 phút, API mock chỉ trong test |
| `npm run test:auth-stack` | **1 passed**, 31,4 giây, FastAPI/SQLite thật trong test, graph stub |
| `npm run test:rbac` | **10 passed**, 1,5 phút, UI và API trực tiếp, graph stub |
| Tạo Admin đầu tiên bằng CLI trong bản riêng | **PASS**, nhập bằng prompt ẩn; lần gọi thứ hai báo đã có tài khoản, không tạo thêm |
| Khởi động BE 18100 + FE 5180, proxy/origin riêng | **PASS**, không mở Internet |
| Smoke trình duyệt không mock: login → `/api/auth/me` → logout | **PASS**, Admin thật trong SQLite test; HTTP 200, đăng xuất quay lại login |
| `/health` và `/health/ready` khi graph loopback không có dịch vụ | **200** và **503** đúng kỳ vọng; không báo graph sẵn sàng giả |
| Giao diện khi graph không kết nối | **PASS việc hiển thị lỗi**, nhưng mất khoảng **61 giây** mới hiện timeout sau retry; xem giới hạn bên dưới |
| Quét nguồn và xuất ZIP thử, đọc lại SHA-256 từng file | **PASS**, 160 file nguồn; không có file cấu hình thật/DB/backup trong danh sách |
| Đối chiếu source gốc với bản riêng dùng để chạy test | **141 file mã/cấu hình/test giống byte**; báo cáo/tài liệu được hoàn thiện sau lần chạy |

296 test BE gồm 271 test có sẵn và 25 test công cụ bàn giao đạt. Một test tạo
symlink thật bị skip do tài khoản Windows không có quyền tạo symlink; không
được coi là kiểm chứng symlink/junction đầy đủ trên mọi hệ điều hành. Chín
test integration bị loại có chủ đích để không ghi hoặc kết nối graph nguồn.

Lượt FE đầu có 45 pass/2 fail do thêm `.env.local` trong lúc Vite đang chạy
làm kết nối bị gián đoạn (`ERR_SOCKET_NOT_CONNECTED` và chờ phần tử hết hạn).
Đã giữ nguyên cấu hình rồi chạy lại **toàn bộ 47**, không xóa test/nới assert.
Smoke ban đầu chờ lỗi trong 5 giây cũng chưa đủ; quan sát lần có thời gian
chờ phù hợp xác nhận dashboard mất khoảng 61 giây, không che giấu bằng mock.

Trong lần BE cuối, process test được đặt URI loopback/credentials giả và
`AUTH_ALLOWED_ORIGINS` cho 5173; terminal smoke dùng 5180. Đây là hai cấu hình
riêng; không đổi origin của hệ thống đang sử dụng. Không thay schema/người dùng
hoặc mật khẩu thật. Sau kiểm tra, dừng server test và dọn bản cài tạm (khoảng
235 MiB), giữ source ZIP/manifest cuối và báo cáo trong repository.

**Cập nhật bàn giao:** server smoke đã dừng; giải nén và chạy đoạn kiểm tra
SHA-256 dành cho người nhận đạt đủ 160 file. Lệnh dọn bản cài tạm bị cơ chế an
toàn của công cụ chặn, nên **chưa xóa thư mục tạm** có prefix
`skillgraph-handoff-` được tạo trong đợt này trên ổ C. Thư mục chứa dependency,
dữ liệu auth tổng hợp và artifact test, không nằm trong ZIP bàn giao. Người
vận hành có thể xóa đúng thư mục của đợt thử sau khi kiểm tra không còn server
sử dụng; không xóa cả Temp hoặc thư mục dự án. Gói nguồn chỉ khoảng 0,32 MiB.

## Kết luận bàn giao

Đã có bộ nguồn có manifest, hướng dẫn cài/khởi động đã thử riêng, kiểm thử hồi
quy và tài liệu demo/khôi phục/xử lý lỗi. **Đạt phạm vi bàn giao local có điều
kiện**, không coi mọi hạng mục graph thật/production đã hoàn tất. Checklist
người nhận trong [handoff](handoff.md) cần được chính người nhận thực hiện và
xác nhận. Chi tiết danh sách file cuối xem manifest đi cùng ZIP, không dùng
manifest của lần xuất thử để nhận diện gói đã cập nhật tài liệu.

## Lệnh kiểm thử để người nhận chạy lại

Tại backend sau khi cấu hình phù hợp môi trường test:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts
.\.venv\Scripts\python.exe -B -m scripts.handoff check
```

Lệnh `handoff check` chỉ chạy được trong Git repository gốc; người nhận ZIP
đối chiếu manifest, không cần tạo Git repo để chạy ứng dụng/test nghiệp vụ.
Pytest hiện import cấu hình app từ đầu; dù bỏ integration vẫn cần ba biến
COGNODB có giá trị hợp lệ về dạng. Với test cô lập, dùng URI loopback test
không có dịch vụ và credential giả trong terminal riêng, không dùng secrets
nguồn. Không dùng cấu hình này để chạy demo graph thật.

Tại frontend, chạy lần lượt:

```powershell
npm.cmd run build
npm.cmd run format:check
npm.cmd test
npm.cmd run test:auth-stack
npm.cmd run test:rbac
```

`test:auth-stack`/`test:rbac` dùng cổng riêng 5174/18000, tạo tài khoản tổng hợp
trong SQLite tạm, graph stub. `npm test` mock API chỉ trong test; không thay
dữ liệu của ứng dụng. Không chạy `test:live`, `pytest -m integration` hoặc
runner graph chỉ để tăng số test đạt nếu chưa có môi trường/quyền phù hợp.

## Chưa kiểm chứng hoặc chưa hoàn thiện

- Drill backup/restore graph thật và bản ứng dụng phục hồi đầy đủ; chưa đo
  RPO/RTO, chưa chốt offsite/retention/tự động backup. Xem [trạng thái](backup-restore.md).
- FE → BE → CognoDB thật với ghi đồng thời, đối chiếu audit và cleanup: bộ
  test đã chuẩn bị, vẫn chưa có kết quả chạy thật trong đợt này.
- Cài từ máy/OS mới hoàn toàn, Linux/macOS, các phiên bản Python/Node khác,
  môi trường không có mạng, engine/schema khác phiên bản đang dùng.
- Migration trên graph hiện hữu và chuỗi upgrade/rollback dữ liệu thật;
  đợt bàn giao kiểm tra mã/hướng dẫn, không chạy migration nguồn.
- Demo tổng hợp đã có dữ liệu và kết quả kỳ vọng, chưa trình diễn trên
  instance riêng thật. Không coi test mock như demo live đã đạt.
- Production HTTPS, Secure cookie/domain thật, giám sát, load test, đánh giá
  bảo mật độc lập, audit tài khoản/quyền, email reset/MFA/SSO, đa tenant.
- Allocation chưa theo khoảng thời gian; gợi ý chưa lọc dung lượng. SQLite
  auth hướng một máy chủ, chưa kiểm chứng nhiều replica/tải lớn.
- Khi graph mất kết nối, timeout/retry của request nghiệp vụ không dùng cùng
  ngân sách với readiness. FE chờ tối đa 30 giây/request đọc và thử lại một
  lần, nên tình huống smoke này mất khoảng 61 giây mới hiện lỗi. Chưa chỉnh
  retry/timeout toàn hệ thống trong bước chốt tài liệu; cần đo/chốt ngân sách
  tương tác trước production. Cảnh báo readiness không bảo đảm CRUD phản hồi
  lỗi trong 4 giây.
- Quét gói nguồn không quét lịch sử Git, không chứng minh mọi dạng secrets,
  PII hoặc lỗ hổng đã được phát hiện. Không dùng hash như chữ ký phát hành.

Các giới hạn trên phải được người nhận biết và chấp thuận; không tự ghi
“100% production-ready” từ kết quả build, unit test hoặc độ đầy đủ tài liệu.
