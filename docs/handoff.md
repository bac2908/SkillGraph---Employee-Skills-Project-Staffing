# Bàn giao SkillGraph — bản local 0.1.0

Ngày chốt hồ sơ: **16/09/2026**, múi giờ Asia/Saigon (UTC+7).
Đây là **ứng viên bàn giao chạy cục bộ**, không phải tuyên bố sẵn sàng production.
Không tạo Git tag, commit hoặc push tự động trong đợt bàn giao.

## 1. Người nhận cần đọc gì?

1. [Tổng quan dự án](tong-quan-du-an.md): giải quyết bài toán gì, dành cho ai,
   kiến trúc FE/FastAPI/CognoDB/SQLite và giới hạn nghiệp vụ.
2. Tài liệu này: cài đặt, khởi động, schema, tài khoản và nhận mã nguồn.
3. [Demo tổng hợp](demo-scenario.md): trình bày một luồng có dữ liệu/kết quả dự kiến.
4. [Báo cáo phiên bản](release-verification.md): ngày, môi trường, lệnh, kết quả
   thực chạy và những việc **chưa kiểm chứng**.
5. [Xử lý sự cố](troubleshooting.md), [khôi phục Admin](admin-recovery.md),
   [backup/restore](backup-restore.md): vận hành và khôi phục.
6. [Mục lục](README.md): tài liệu chi tiết theo tính năng/API/quyền.

Ứng dụng dành cho không gian nhân sự chung của một tổ chức. Tài khoản đăng nhập
không đồng nhất với hồ sơ Employee. Admin quản lý tài khoản/danh mục; Manager
ghi vào dự án được giao; Viewer chỉ xem. Không có đăng ký công khai hoặc mật
khẩu mặc định. Mọi quyền ghi phải được BE kiểm tra, không chỉ ẩn nút trên FE.

## 2. Thành phần được bàn giao và cách nhận diện phiên bản

- Mã BE, FE, bộ kiểm thử, tài liệu, cấu hình **mẫu** không có secret.
- `frontend/package-lock.json` khóa cây dependency npm; dùng `npm ci`.
- `backend/constraints-windows-py312.txt` ghi phiên bản dependency đã dùng để
  thử trên Windows x64/Python 3.12.10. Dùng cùng requirements, không thay chúng.
  Đây không phải lock đa nền tảng, kho wheel offline hoặc danh sách hash gói.
- Manifest xuất kèm có base commit, trạng thái có thay đổi worktree, danh sách
  file/kích thước/SHA-256 và fingerprint của bộ nguồn. **Base commit không bao
  gồm các thay đổi chưa commit**; nhận diện gói bằng manifest, không chỉ tên 0.1.0.

Không kèm `.git`/lịch sử Git, `.env` thật, DB auth/sidecar WAL, graph dump,
backup/restore output, `node_modules`, `.venv`, `dist`, trace hoặc ảnh test.
Secrets và dữ liệu thật phải bàn giao qua kênh riêng được tổ chức phê duyệt;
không gửi cùng source ZIP hoặc đưa vào tài liệu.

Người giữ repository xuất bộ nguồn bằng công cụ offline, tại `backend`:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.handoff check
.\.venv\Scripts\python.exe -B -m scripts.handoff export --output "../.handoff/release-20260916-01"
```

Output phải là **thư mục mới**. Công cụ không ghi đè hoặc tự dọn bản cũ; tạo
`skillgraph-source.zip` và `handoff-manifest.json`, kiểm tra lại các hash trong
ZIP. ZIP có thư mục `skillgraph/` và manifest ở ngoài thư mục đó. Không cần
Git khi cài từ ZIP; chỉ công cụ xuất bản gốc cần Git và repository đúng gốc.

Công cụ xét file tracked và untracked không bị ignore, kiểm tra allowlist,
symlink/junction, giới hạn 3 MiB/file, 20 MiB tổng và 2.000 file; từ chối payload
DB/binary, một số mẫu key/token/URI chứa mật khẩu và giá trị nhạy cảm trong
cấu hình local hiện có. Chỉ có hai ngoại lệ URI giả cụ thể trong test chặn
credentials nhúng, không miễn quét cả thư mục test. Output lỗi được giữ để
kiểm tra, không bàn giao khi exit code khác 0.

**Giới hạn:** quét này không chứng minh không có mọi loại secret/PII hoặc lỗ
hổng. Không quét lịch sử Git; credential từng commit phải được thu hồi/xử lý
lịch sử riêng. Hash phát hiện thay đổi, không thay chữ ký hoặc kênh phân phối
đáng tin. Trước khi gửi, người vận hành vẫn duyệt danh sách manifest và diff.

Người nhận có thể kiểm tra byte của nguồn sau khi nhận gói qua kênh tin cậy.
Chạy tại thư mục chứa ZIP, với tên đích mới chưa tồn tại:

```powershell
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath .\skillgraph-review) { throw 'Chọn thư mục nhận mới, không ghi đè.' }
Expand-Archive -LiteralPath .\skillgraph-source.zip -DestinationPath .\skillgraph-review
$taskPackage = (Resolve-Path -LiteralPath .\skillgraph-review).Path
$taskSource = Join-Path $taskPackage 'skillgraph'
$taskManifest = Get-Content -LiteralPath (Join-Path $taskPackage 'handoff-manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($entry in $taskManifest.files) {
    $target = [IO.Path]::GetFullPath((Join-Path $taskSource $entry.path))
    if (-not $target.StartsWith($taskSource + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Đường dẫn ngoài gói.' }
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Hash sai: $($entry.path)" }
}
'SHA-256 nguồn: PASS'
```

Thư mục `skillgraph-review/skillgraph` chính là gốc source để chạy các bước
cài đặt bên dưới. Bộ gói không chứa dependency nên vẫn cần cài từ kho gói.

## 3. Cài mới trên Windows, trong thư mục riêng

Đã thử quy trình dependency từ ZIP nguồn vào thư mục tạm riêng; xem
[phạm vi smoke test](release-verification.md). Máy sạch hoàn toàn/OS khác và
việc tạo instance graph cloud không nằm trong kết quả đó.

Yêu cầu môi trường đã kiểm chứng: Windows 11 x64, Python 3.12.10, Node.js
24.19.0, npm 12.0.2; Edge sẵn có để chạy test. FE khai báo Node >=22.12 nhưng
không coi mọi phiên bản thỏa điều kiện đã được kiểm thử. Cần mạng đến kho gói
khi cài mới và đến CognoDB khi sử dụng nghiệp vụ thật.

Giải nén nguồn vào thư mục mới, mở PowerShell ở thư mục có `backend`, `frontend`,
`docs`. Không giải nén đè lên bản đang vận hành và không chép `.venv` từ máy khác.

### Backend và cấu hình

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-dev.txt -c constraints-windows-py312.txt
.\.venv\Scripts\python.exe -m pip check
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

Nếu chỉ chạy ứng dụng, thay `requirements-dev.txt` bằng `requirements.txt`.
Không cần kích hoạt virtualenv khi gọi trực tiếp interpreter như trên; tránh
vướng execution policy. Máy dùng launcher `py` có thể dùng `py -3.12 -m venv .venv`.

Mở `backend/.env` trên máy, điền ba biến `COGNODB_URI`, `COGNODB_USER`,
`COGNODB_PASSWORD` của môi trường được cấp. URI không chứa mật khẩu; không gửi
nội dung file vào chat/log. Mẫu để URI/password trống **có chủ đích**, phải điền
trước khi import/chạy app thật. Environment của process ưu tiên hơn `.env`;
không dùng lại terminal còn biến của môi trường khác.

`AUTH_DB_PATH` mặc định là `backend/data/auth.sqlite3` tính theo vị trí source.
Cài mới ở thư mục riêng sẽ có file riêng; nếu đặt đường dẫn thủ công thì dùng
đường dẫn tuyệt đối và kiểm tra kỹ. Không trỏ bản thử vào DB auth đang dùng.
`AUTH_COOKIE_SECURE=false` chỉ phù hợp HTTP localhost. Giữ origin chính xác;
không đổi thành wildcard. Chi tiết ở [cấu hình auth](authentication.md#cấu-hình).

CognoDB trong dự án là dịch vụ/instance bên ngoài, **không được khởi động bằng
npm hoặc Uvicorn**. Người vận hành cần bật instance trên hệ thống nhà cung cấp
và cấp kết nối. Chưa có Docker Compose hoặc script tạo cloud instance trong repo.

### Schema/migration và tài khoản đầu tiên

Với **graph mới riêng được phép khởi tạo**, tại `backend`:

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_schema
.\.venv\Scripts\python.exe -m scripts.create_admin
```

`setup_schema` tạo 6 constraint nghiệp vụ và gọi migration AuditEvent (1
constraint, 2 index). Dùng `IF NOT EXISTS`, không tự sửa dữ liệu vi phạm unique
hoặc thay schema không tương thích. Không chạy seed như một migration.

Với hệ thống hiện hữu: sao lưu **graph + auth** đã verify, chốt thời điểm tạm
dừng ghi; đối chiếu phiên bản/schema trước. Nếu chỉ thiếu schema hoạt động,
dùng `python -m scripts.setup_activity_schema` theo
[hướng dẫn migration](project-activity.md). Thiếu constraint nghiệp vụ thì
đánh giá dữ liệu trước khi dùng `setup_schema`. Không tự xóa constraint/dữ liệu
để vượt lỗi. Chưa có migration runner theo version hoặc rollback tự động.

Kho SQLite mới được bootstrap bằng `AuthStore` với bảng/index hiện tại.
Không có migration SQLite phá dữ liệu trong bản này, cũng không có cơ chế
`ALTER TABLE` tự nâng mọi schema cũ. DB cũ không tương thích: giữ nguyên, dừng
và điều tra theo readiness; không xóa DB để cho ứng dụng tạo lại.

CLI tạo Admin chỉ tạo khi kho tài khoản trống. Nhập email/tên và mật khẩu
15–128 ký tự bằng prompt ẩn; không viết mật khẩu trong command line. Nếu đã
có tài khoản, đăng nhập bằng tài khoản hiện hữu; quên mật khẩu dùng
[khôi phục Admin](admin-recovery.md), không chạy bootstrap để thay tài khoản.

### Khởi động hai terminal riêng

Terminal BE, tại `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

Terminal FE, tại `frontend`:

```powershell
npm.cmd ci
npm.cmd run dev
```

Giữ cả hai terminal chạy. Mở <http://127.0.0.1:5173>; API docs ở
<http://127.0.0.1:8000/docs>. Không chạy lệnh kích hoạt BE trong terminal FE
đang chạy; Ctrl+C dừng server. Dùng cùng host 127.0.0.1 để tránh nhầm cookie.

Nếu BE đổi địa chỉ, sao chép `frontend/.env.example` thành `.env.local`, đặt
`SKILLGRAPH_API_TARGET` và restart Vite. Nếu đổi cổng FE, thêm đúng origin vào
`AUTH_ALLOWED_ORIGINS` của BE rồi restart. Không đưa secret graph vào FE.

Kiểm tra tại terminal thứ ba:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

`/health` là process còn sống; `/health/ready` phải trả `ready` khi graph/schema
và auth đều sẵn sàng. HTTP 503 không có nghĩa sai mật khẩu; xem
[readiness](readiness.md). Đăng nhập Admin, tạo Manager/Viewer và cấp dự án qua
UI; tài khoản mới phải đổi mật khẩu tạm. Không có quyền Manager tự cấp grant.

## 4. Kiểm chứng, demo và khôi phục

- Chạy các lệnh trong [báo cáo kiểm chứng](release-verification.md). Không dùng
  test mock thay graph thật và không vô tình chạy integration trên nguồn.
- Dùng [demo tổng hợp](demo-scenario.md), chỉ ở môi trường riêng. Không chạy
  `seed.py` trên dữ liệu đang dùng: seed dùng ID cố định, MERGE/SET có thể ghi
  đè properties; không đi qua toàn bộ API, audit và chốt allocation.
- Sự cố đăng nhập: xem [troubleshooting](troubleshooting.md), sau đó chỉ khôi
  phục Admin nếu cần và được phép. Không có cách đọc lại password từ hash.
- Sao lưu/khôi phục: theo [quy trình](backup-restore.md), dừng mọi writer khi
  backup cặp DB, restore vào nơi riêng, thu hồi phiên bản phục hồi và đối
  chiếu quyền Manager theo project. Không tự cutover bản đang dùng.

## 5. Checklist nhận bàn giao

- [ ] Đã nhận ZIP/manifest đúng phiên bản qua kênh tin cậy, kiểm tra SHA-256.
- [ ] Đã chỉ định người giữ source, người vận hành DB, người giữ secret và Admin.
- [ ] Đã cài dependency trong môi trường riêng, `pip check`/build/test đạt.
- [ ] Đã cấp instance, cấu hình secrets local, xác minh schema và readiness.
- [ ] Đã tạo/nhận đúng tài khoản, thử quyền Admin/Manager/Viewer.
- [ ] Đã trình bày demo và phân biệt trạng thái AVAILABLE với allocation.
- [ ] Đã thống nhất nơi lưu backup, quyền truy cập, người phục hồi, RPO/RTO.
- [ ] Đã thực hiện và ghi nhận drill restore/E2E thật trước khi dùng dữ liệu thật.
- [ ] Đã đọc giới hạn còn lại, không hiểu bản local là production hoàn chỉnh.

Checklist dành cho **người nhận** xác nhận khi thực hiện; không tự đánh dấu
thay họ. Các mục graph thật/restore thật còn chờ riêng trong báo cáo, không
được đóng chỉ vì bộ tài liệu và gói mã nguồn đã hoàn tất.
