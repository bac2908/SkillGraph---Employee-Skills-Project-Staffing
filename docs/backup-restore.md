# Sao lưu và phục hồi dữ liệu SkillGraph

Triển khai ngày 11/09/2026. Phạm vi: bộ công cụ backup logic có giới hạn cho bản
local, kiểm tra file và phục hồi vào **nơi riêng chưa có dữ liệu**. Không triển
khai production, không ghi đè DB đang dùng, không tự đăng ký dịch vụ hoặc lịch
backup, không bổ sung audit tài khoản/quyền.

## Hai kho dữ liệu cần đi cùng nhau

| Kho | Nội dung | File trong bộ backup |
| --- | --- | --- |
| CognoDB graph | Employee, Skill, Project, Team, AuditEvent và các quan hệ của ứng dụng | `graph.json` |
| SQLite auth | Tài khoản, password hash, quyền và project grants; phiên/bộ đếm hiện có | `auth.sqlite3` |
| Thông tin kiểm chứng | Phiên bản format, thời gian, checksum SHA-256, số bản ghi, fingerprint nguồn | `manifest.json` |

Git và `seed.py` không thay thế backup. Bản graph không chứa tài khoản đăng nhập;
bản SQLite không chứa kỹ năng/phân công. Cần giữ đúng cặp từ cùng một lần backup.

## Phạm vi định dạng logic v1

- Lưu toàn bộ properties của các node đơn nhãn Employee, Skill, Project, Team,
  AuditEvent, cùng HAS_SKILL, WORKS_ON, REQUIRES_SKILL, MEMBER_OF, OWNED_BY.
- Bảo toàn mã nghiệp vụ, các thuộc tính quan hệ và lịch sử; internal graph ID
  không được giữ nguyên, cũng không dùng chúng làm định danh nghiệp vụ.
- Hỗ trợ string, boolean, integer 64-bit, float hữu hạn và list giá trị đơn.
  Null/nested map/temporal/spatial hoặc schema ngoài phạm vi sẽ bị từ chối,
  **không âm thầm bỏ dữ liệu**. Cần native backup của engine nếu có các loại này.
- Khi restore, chỉ tạo constraint/index do ứng dụng sở hữu bằng mã nguồn cố
  định. Không chạy Cypher/DDL lấy từ file backup. Không sao lưu cấu hình server,
  DB user/role, chứng chỉ, custom index/schema, transaction log hay PITR.
- Đây **không phải snapshot vật lý của CognoDB**. CognoDB dùng Bolt và Neo4j
  driver, nhưng không được suy ra rằng `neo4j-admin dump/load` chạy được trên
  dịch vụ này. Native snapshot/retention của gói cloud phải xác minh riêng với
  nhà cung cấp. [CognoDB developers](https://cognodb.com/developers)

## Nhất quán: phải tạm dừng mọi bên ghi

Graph và SQLite không có transaction chung. Một read transaction graph cũng
không được coi là snapshot ổn định cho mọi engine. Quy trình hiện tại yêu cầu:

1. Dừng backend tại terminal đang chạy (`Ctrl+C`), đợi các request đang xử lý
   hoàn tất. Đóng form trình duyệt đang chuẩn bị lưu; frontend có thể để mở.
2. Tạm dừng script seed/import, worker và mọi người chạy Cypher trực tiếp.
3. Giữ trạng thái này trong suốt lệnh backup; sau khi backup được verify mới
   tiếp tục ghi. Không cần dừng chính instance CognoDB.

Cờ `--writes-paused` là **xác nhận của người vận hành**, không phải khóa toàn bộ
cloud DB. CLI không tự dừng tiến trình hoặc ngăn các máy khác ghi. Manifest ghi
`operator-confirmed-writers-paused`; không dùng nó để tuyên bố có transaction
phân tán. Nếu không kiểm soát được các bên ghi, dùng snapshot/quy trình nhất
quán được nhà cung cấp hỗ trợ và chưa coi bộ xuất này là backup đồng bộ.

SQLite được sao lưu bằng `Connection.backup`, không copy mù file đang chạy:
dữ liệu committed trong WAL cũng được lấy. Có `integrity_check`, foreign-key
check và kiểm tra schema. [Python SQLite backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup)

## Tạo và kiểm tra backup

Chạy tại thư mục `backend`, dùng đúng environment nguồn đang có. Các tên thư
mục dưới đây là **ví dụ**; chọn tên mới mỗi lần, không dùng lại thư mục đã tồn tại.

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_restore backup --output "data/backups/20260911-01" --writes-paused
.\.venv\Scripts\python.exe -m scripts.backup_restore verify --backup "data/backups/20260911-01"
```

Thành công trả `status=verified`, số node/quan hệ/tài khoản, checksum logic và
cảnh báo tổng hợp. Exit code khác 0 là chưa đạt. Không chỉ dựa vào việc thấy
file hoặc `complete=true`: phải chạy `verify` kiểm tra đủ checksum/structure.
`verify` không cần kết nối graph hoặc credentials nguồn.

Manifest được ghi sau payload. Nếu lỗi, output có thể chưa hoàn chỉnh và được
giữ nguyên để điều tra; không tự xóa dữ liệu hoặc ghi đè để chạy lại. Dùng tên
mới cho lần sau. Không sử dụng hoặc quảng bá output lỗi làm bản phục hồi.

## Phục hồi auth ở nơi riêng

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_restore restore-auth --backup "data/backups/20260911-01" --output "data/restore-drills/auth-20260911-01"
```

Tạo `auth.sqlite3` mới và `restore-report.json`. Bản mới giữ nguyên users,
password hash, trạng thái và project grants; **xóa phiên đăng nhập cũ và bộ đếm
thử đăng nhập** trong bản được phục hồi. Không tác động file nguồn hoặc backup.
Kiểm tra checksum logic users trước/sau và xác nhận sessions còn 0.

Kết quả `auth_verified_graph_not_restored` chỉ chứng minh nhánh SQLite, không
có nghĩa đã phục hồi cả hệ thống. Không tự sửa `AUTH_DB_PATH` để chuyển ứng dụng.
Lịch sử backup có thể chứa quyền/mật khẩu đã cũ; phải rà soát trước khi cho người
dùng truy cập bản phục hồi, nhất là quyền Admin và tài khoản từng bị khóa.

## Phục hồi cả graph vào instance test trống

1. Chuẩn bị instance test **riêng thật sự**, được phép chứa bản sao dữ liệu này,
   không dùng chung với người khác. User DB phải nhìn thấy đầy đủ graph và có
   quyền tạo schema/data. Không kết luận đích rỗng từ tài khoản bị hạn chế đọc.
2. Dùng `backend/.env.restore.example` làm mẫu cho `backend/.env.restore`.
   Điền COGNODB_URI, COGNODB_USER, COGNODB_PASSWORD của **đích test**, không gửi
   credentials vào chat, tham số CLI, tài liệu hoặc Git. File `.env.restore`
   được Git bỏ qua, không được app tự đọc làm cấu hình nguồn.
3. Giữ instance đích độc quyền trong lúc import, không gắn app/worker khác vào.
4. Chạy với tên output mới:

```powershell
.\.venv\Scripts\python.exe -m scripts.backup_restore restore --backup "data/backups/20260911-01" --output "data/restore-drills/full-20260911-01" --target-env ".env.restore" --confirm-empty-target
```

Các chốt an toàn:

- Từ chối file `.env` nguồn và endpoint trùng nguồn trong manifest/cấu hình
  hiện tại, chuẩn hóa hostname/port giữa các scheme. URI không nhận credentials
  nhúng. DNS alias/đổi home database không thể được chứng minh khác chỉ bằng
  hostname; người vận hành vẫn phải xác nhận đây là instance riêng.
- Query số node toàn graph phải là 0 trước khi tạo schema, kiểm tra lại trong
  transaction import. Không có lệnh xóa toàn graph, merge vào dữ liệu cũ hoặc
  `--force` ghi đè. Instance đã có dữ liệu sẽ bị từ chối.
- Output là thư mục mới, không chứa đường dẫn auth đang cấu hình. Không ghi đè
  file SQLite cũ hoặc sidecar có sẵn, kể cả trường hợp DB nguồn đang bị mất.
- Payload/manifest được kiểm tra trước; node label và relationship type dùng
  registry cố định, properties đi qua parameters. Không thực thi nội dung file.
- Dữ liệu graph được import trong một transaction; lỗi trong import sẽ rollback.
  Schema tạo trước đó có thể còn lại. Sau commit, đọc lại graph và đối chiếu
  checksum logic của **toàn bộ properties, node và quan hệ**, không chỉ count.
- Đọc lại quan hệ thực hiện sau commit vì engine hiện tại đã có giới hạn với
  quan hệ mới trong cùng transaction; xem [ghi chú audit](project-activity.md).

Thành công trả `restore_verified` và lưu `restore-report.json`. CLI không đổi
`.env`, không đăng nhập bằng tài khoản thật, không khởi động app trên bản phục
hồi và không publish. Instance test sau thành công **có bản sao graph**, không
còn trống. Không chạy lại vào đó; không tự xóa nó để thử tiếp.

Nếu lỗi sau graph commit hoặc giữa hai kho, giữ instance/output cô lập, không
chuyển app sang đó. Hai kho không rollback chung được. Bản nguồn và backup vẫn
được giữ; xác minh nguyên nhân trước khi thử ở một đích mới. Không suy ra thành
công chỉ từ số file đã được tạo.

## Kiểm chứng nghiệp vụ trước khi chuyển ứng dụng

- Số node/quan hệ, checksum logic graph và users phải khớp backup; sessions=0.
- `missing_manager_project_grants=0` là không phát hiện grant trỏ tới project
  vắng mặt. Nếu khác 0, cần rà soát thủ công; không tự bỏ/cấp lại quyền. Grant
  cũ có thể tồn tại do dự án đã xóa. Actor/dự án lịch sử trong audit không bắt
  buộc còn sống, nên không dùng chúng để báo mất dữ liệu.
- Trên một bản app test riêng, kiểm tra readiness, đăng nhập lại, quyền
  Admin/Manager/Viewer, danh sách và dashboard, phân tích/phân công với dữ liệu
  test. Không chạy kịch bản ghi vào nguồn chỉ để kiểm tra backup.
- Chỉ chuyển cấu hình app sau khi người vận hành chốt thời điểm phục hồi,
  mức mất dữ liệu chấp nhận được và rà soát quyền. Công cụ này không tự cutover.

## Bảo mật và dung lượng

- Backup chứa dữ liệu cá nhân, password hash và quyền. Đây là dữ liệu nhạy cảm,
  dù không copy `.env` hoặc mật khẩu DB. Không đăng lên Git hoặc gửi công khai.
- Giữ mã nguồn đúng phiên bản và secrets ở kho riêng an toàn. Full restore hiện
  cần cấu hình nguồn hợp lệ để kiểm tra chống trỏ nhầm (không kết nối nguồn khi
  restore); verify và restore-auth dùng được không cần credentials graph.
- Thư mục output mới trên Windows được đặt ACL chỉ tài khoản đang chạy và
  SYSTEM; trên POSIX là mode 0700. Không sửa ACL thư mục dữ liệu cũ. ACL không
  thay mã hóa: trước khi chép ra USB/offsite cần phương án lưu trữ mã hóa riêng.
- SHA-256 phát hiện hỏng/thay đổi file, **không chứng thực nguồn gốc** nếu kẻ
  xấu sửa cả manifest. Chỉ phục hồi từ bản backup đáng tin cậy và kho được bảo vệ.
- Giới hạn v1: 100.000 node, 250.000 quan hệ, tối đa 64 MiB mỗi payload, yêu cầu
  còn khoảng 193 MiB trống trước khi bắt đầu. Không cài dependency mới, không
  tải Docker image, không sao chép `.venv`/`node_modules` hoặc cả ổ D.
- CLI có timeout kết nối/transaction và giới hạn sao lưu SQLite. Đây không phải
  deadline cứng cho mọi I/O của hệ điều hành/mạng; không chạy tùy tiện như job
  production. Dữ liệu lớn hơn giới hạn cần công cụ native/streaming đã kiểm thử.
- Không có tự động xóa/retention hoặc Scheduled Task. Có thể đề xuất lịch hằng
  ngày và trước migration, giữ một số bản theo ngân sách đã chốt; **chưa áp dụng**.
  Chỉ giữ backup trên cùng ổ đĩa không bảo vệ khi ổ hỏng. Cần chọn nơi offsite
  và thử phục hồi định kỳ trước khi gọi đây là kế hoạch disaster recovery hoàn chỉnh.
  RPO (mức dữ liệu có thể mất) và RTO (thời gian phục hồi) chưa được chốt/đo;
  không coi đề xuất lịch hằng ngày là cam kết dịch vụ đang có.

## File mã nguồn và kiểm thử

| File | Vai trò |
| --- | --- |
| `backend/scripts/backup_restore.py` | CLI backup/verify/restore-auth/restore, manifest và guard |
| `backend/scripts/backup_support/files.py` | File mới, ACL, checksum và giới hạn dung lượng |
| `backend/scripts/backup_support/auth.py` | SQLite online backup, integrity, schema, thu hồi phiên |
| `backend/scripts/backup_support/graph.py` | Export/validate/import và checksum logic graph |
| `backend/.env.restore.example` | Mẫu cấu hình instance test, không chứa secret |
| `backend/tests/test_backup_restore.py` | Test cô lập cho backup, corruption, WAL và từ chối đích nguy hiểm |

```powershell
# Tại backend: dữ liệu tổng hợp/temp, không import vào graph thật
.\.venv\Scripts\python.exe -m pytest tests/test_backup_restore.py tests/test_readiness.py -q
.\.venv\Scripts\python.exe -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -m ruff check app tests scripts
```

Kết quả đợt này: 48 test mới cho readiness/recovery; toàn bộ backend không
integration đạt 170 test. Đã thử đọc/export logic nguồn thật (26 node, 65 quan
hệ) và CLI readiness trả graph/auth `ok`. Unit tests kiểm tra backup/restore
SQLite thật ở file tạm, WAL committed, checksum sai, schema sai, đích tồn tại,
đích trùng nguồn, đích graph không trống, giới hạn dung lượng và lỗi không lộ secret.
Hai test integration chỉ đọc (readiness và dashboard) đạt; 1 test FE–FastAPI
auth cô lập đạt. Đã kiểm tra Ruff, compile và `git diff --check`. File môi trường
thật và các thư mục backup/restore vẫn được Git bỏ qua.

Phục hồi graph thật vào instance test và bộ backup dữ liệu thật chỉ được chốt
sau khi có cấu hình `.env.restore` và xác nhận tạm dừng ghi. **Chưa coi kết quả
mock là restore drill trên CognoDB đã đạt.** Kết quả thực tế sẽ được cập nhật
tại đây khi thực hiện xong; không có báo cáo production/load test trong đợt này.
