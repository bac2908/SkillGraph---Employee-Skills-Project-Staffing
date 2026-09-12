# Khôi phục mật khẩu Admin bằng công cụ cục bộ

Triển khai ngày 12/09/2026. Dành cho người vận hành được phép truy cập máy chủ
và ghi kho tài khoản của SkillGraph. Đây là công cụ dự phòng khi không thể
đăng nhập Admin, **không phải chức năng quên mật khẩu công khai**.

## Mục đích và khi nào sử dụng

- Còn nhớ mật khẩu và đăng nhập được: dùng trang **Tài khoản cá nhân** nếu
  muốn đổi mật khẩu; không cần chạy công cụ khôi phục.
- Quên mật khẩu nhưng còn Admin khác truy cập được: ưu tiên nhờ Admin đó đặt
  lại mật khẩu qua trang **Tài khoản**.
- Quên mật khẩu Admin duy nhất hoặc không thể nhờ Admin khác: người vận hành
  có quyền filesystem có thể dùng `python -m scripts.recover_admin`.

Mật khẩu cũ được băm nên không đọc lại được. Công cụ chỉ đặt mật khẩu khôi
phục tạm mới cho **một Admin hiện có đang hoạt động**, không tạo tài khoản,
không đổi role và không mở khóa tài khoản bị khóa. Có nhiều Admin vẫn phải
chỉ định chính xác một tài khoản; không có chế độ đặt lại hàng loạt.

Trong đợt triển khai này, chủ dự án đã nhớ mật khẩu. **Không chạy khôi phục
trên tài khoản thật**; các thao tác thay đổi tài khoản chỉ được thử với dữ liệu
tổng hợp trong database tạm.

## Phạm vi đã triển khai

1. Mở file SQLite auth **đã tồn tại**, kiểm tra schema, `quick_check` và khóa
   ngoại; không gọi constructor `AuthStore`, không bootstrap hoặc migration.
2. Nhập email; hiển thị đường dẫn DB tuyệt đối, email, mã tài khoản và trạng
   thái để người vận hành xác nhận. Không liệt kê tất cả tài khoản hoặc hash.
3. Yêu cầu gõ nguyên câu xác nhận, gồm email đúng; mặc định nhập khác là hủy.
4. Nhập mật khẩu tạm hai lần bằng `getpass`, 15–128 ký tự, giữ nguyên khoảng
   trắng; không cho dùng lại mật khẩu hiện tại.
5. Dùng Argon2id như hệ thống auth hiện có. Trong một SQLite transaction:
   - Chỉ thay `password_hash` và bật `must_change_password=1` cho tài khoản đích.
   - Xóa tất cả phiên của đúng tài khoản đó.
   - Xóa hai bộ đếm theo tài khoản: thử đăng nhập và thử đổi mật khẩu.
   - Giữ nguyên giới hạn theo IP, tài khoản khác và các phiên/quyền của họ.
6. Sau khôi phục, đăng nhập bằng mật khẩu tạm; phải đổi sang mật khẩu khác
   trên giao diện trước khi đọc/ghi nghiệp vụ. Đổi xong phải đăng nhập lại.

Không truy cập CognoDB, không cần thông tin đăng nhập graph, không thay đổi
quan hệ, phân công hoặc quyền dự án. Không thêm API, màn hình, dependency,
schema, cơ chế email, SSO/MFA hoặc audit tài khoản/quyền trong đợt này.

## Quyền và chốt an toàn

**Ranh giới quyền là quyền truy cập máy chủ và file DB**, không phải phiên
đăng nhập web. Người đọc/ghi được DB auth vốn có khả năng can thiệp tài khoản;
vì vậy cần hạn chế quyền hệ điều hành, bảo vệ máy chủ và không chia sẻ DB.
Không đưa lệnh này thành endpoint web hay nút để người chưa đăng nhập tự chạy.

- Chỉ chấp nhận terminal có stdin/stdout tương tác; từ chối pipe input hoặc
  chuyển output sang file. Nếu `getpass` không thể nhập ẩn, dừng thay vì đọc
  mật khẩu theo chế độ có thể hiện ký tự.
- Không có tham số `--password`, `--force`, `--yes` hoặc biến môi trường nhận
  mật khẩu khôi phục. Lỗi tham số không in lại giá trị đã nhập nhầm.
- Kiểm tra schema đúng phạm vi ba bảng auth và index hiện tại; từ chối
  trigger/view/cột/đối tượng không được hỗ trợ. Không tự sửa DB lạ hoặc bị hỏng.
- Giai đoạn xem thông tin dùng `mode=ro`. Giai đoạn ghi dùng `mode=rw`, không
  dùng chế độ tự tạo file; đường dẫn sai không tạo thêm kho tài khoản rỗng.
- Từ chối symlink ở file đích. Lưu định danh file và dấu vân tay trạng thái
  tài khoản để phát hiện thay thế file hoặc thay đổi tài khoản sau khi xem.
- Khi ghi, lấy `BEGIN IMMEDIATE`, kiểm tra lại trạng thái Admin và dấu vân tay
  trước khi cập nhật. Hai lần khôi phục từ cùng trạng thái xem trước không tự
  ghi đè mật khẩu của nhau: lần sau phải kiểm tra và xác nhận lại.
- Đổi mật khẩu, thu hồi phiên và xóa bộ đếm theo tài khoản nằm trong một
  transaction. Lỗi trước commit đóng connection và rollback các thay đổi.
- CLI không in exception SQLite/cấu hình/hash hoặc traceback ra terminal.
  Tên đường dẫn, email và ID được escape khi hiển thị.

CLI nhắc dừng BE và các bên ghi auth trước khi thực hiện, nhưng **không tự
dừng tiến trình hoặc khóa người vận hành khác trong suốt thời gian nhập**.
Xác nhận tại terminal là xác nhận của người vận hành, không phải cơ chế chứng
minh rằng không còn request đang chạy. Request đã xác thực và đang thực thi
trước khi thu hồi phiên không thể bị công cụ này hủy hồi tố.

## Cấu hình và cài đặt

Không cần cài thêm thư viện, migration hoặc tạo lại database. Dùng virtualenv
của backend đã cài các dependency hiện có.

Thứ tự chọn file DB:

1. `--db-path` nếu người vận hành chỉ định rõ.
2. Biến môi trường `AUTH_DB_PATH` của process.
3. `AUTH_DB_PATH` trong `backend/.env`.
4. Mặc định `backend/data/auth.sqlite3`, tính từ vị trí mã nguồn.

Giá trị đường dẫn tương đối được giải từ thư mục đang chạy, cùng cách cấu
hình auth hiện tại. Nên chạy trong `backend` hoặc dùng đường dẫn tuyệt đối.
Luôn đọc đường dẫn mà CLI hiển thị; không mặc định rằng DB được chọn chắc chắn
là DB mà process backend khác đang dùng.

CLI dùng phần cấu hình auth riêng, bỏ qua các trường graph và không import
module khởi tạo kết nối graph. `--help` không đọc `.env` hoặc mở kho tài khoản.

## Cách dùng khi thật sự cần khôi phục

### 1. Chuẩn bị

- Kiểm tra đúng môi trường, đúng file auth và quyền vận hành.
- Chuẩn bị bản sao lưu được bảo vệ theo [hướng dẫn backup/restore](backup-restore.md).
  Công cụ này không tự sao lưu. Không copy mù file SQLite đang được ghi và bỏ
  qua WAL; không đưa bản sao vào Git hoặc gửi công khai.
- Dừng BE bằng `Ctrl+C` tại terminal đang chạy, đợi request hoàn tất; tạm dừng
  script hoặc process khác ghi cùng DB auth. Không cần dừng instance CognoDB.
- Dùng terminal riêng; tránh chia sẻ màn hình hoặc thu thập bản ghi terminal.

### 2. Chạy lệnh

Từ thư mục gốc dự án:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.recover_admin
```

Muốn xem hướng dẫn mà chưa thực hiện khôi phục:

```powershell
.\.venv\Scripts\python.exe -m scripts.recover_admin --help
```

Khi thử trên bản auth test riêng đã chuẩn bị, có thể chỉ định file rõ ràng:

```powershell
.\.venv\Scripts\python.exe -m scripts.recover_admin --db-path "data/restore-drills/auth-test/auth.sqlite3"
```

Đường dẫn trên chỉ là ví dụ và phải tồn tại. Không dùng nó để suy ra rằng
công cụ đã tạo hoặc phục hồi một bản DB test cho bạn.

### 3. Xác nhận và nhập mật khẩu

1. Đối chiếu đường dẫn DB được hiển thị.
2. Nhập email Admin cần khôi phục. Email được bỏ khoảng trắng hai đầu và
   chuẩn hóa chữ thường như luồng đăng nhập.
3. Đọc email, mã tài khoản và trạng thái đích.
4. Gõ đúng câu `KHOI PHUC` kèm email theo hướng dẫn CLI. Nhập khác sẽ hủy
   trước khi ghi; không có lựa chọn xác nhận tự động.
5. Nhập mật khẩu tạm mới và nhập lại. Terminal không hiện ký tự khi nhập;
   đây là hành vi bình thường, không phải bị treo. Đừng dán mật khẩu vào lệnh shell.
6. Chỉ coi thao tác thành công khi CLI báo đã khôi phục và trả exit code 0.

### 4. Đăng nhập lại

Khởi động backend theo [hướng dẫn đăng nhập](authentication.md), mở frontend
và đăng nhập bằng mật khẩu tạm. Màn hình buộc đổi mật khẩu sẽ xuất hiện; đổi
sang một mật khẩu khác rồi đăng nhập lại. Các phiên cũ không sử dụng tiếp được.

Nếu nhận HTTP 429, giới hạn theo IP có thể vẫn còn. Chờ hết cửa sổ giới hạn
mặc định 15 phút; không đặt lại liên tục hoặc xóa toàn bộ bảng giới hạn để bỏ
qua bảo vệ này. Đừng gửi mật khẩu hoặc ảnh mật khẩu hiện rõ khi báo lỗi.

## Thông báo lỗi và cách xử lý

| Trường hợp | Cách xử lý |
| --- | --- |
| Không thấy file DB | Kiểm tra đường dẫn/cấu hình. Không chạy create_admin hoặc xóa DB để xử lý lỗi đường dẫn |
| Không tìm thấy email | Kiểm tra email và đúng môi trường; công cụ không tạo người dùng mới |
| Tài khoản không phải Admin hoặc bị khóa | Dừng; dùng quy trình quản trị quyền phù hợp, không dùng recovery để nâng quyền/mở khóa |
| Schema không hỗ trợ hoặc toàn vẹn DB lỗi | Kiểm tra phiên bản mã nguồn và bản sao lưu; không tự sửa/xóa bảng |
| Tài khoản hoặc file thay đổi sau khi xem | Kiểm tra bên ghi/thay thế DB, chạy lại để xem và xác nhận trạng thái mới |
| DB bị khóa hoặc thiếu quyền file | Tạm dừng đúng các bên ghi, kiểm tra quyền; không cấp quyền rộng cho mọi người chỉ để chạy lệnh |
| Terminal không hỗ trợ nhập ẩn/tương tác | Dùng PowerShell/Windows Terminal tương tác, không pipe hoặc redirect |
| Hai mật khẩu khác nhau, quá ngắn/dài hoặc trùng mật khẩu cũ | Nhập lại đúng quy tắc; mật khẩu không được tự trim |
| Ngắt tiến trình hoặc lỗi I/O ở thời điểm ghi/commit | Kiểm tra trạng thái và khả năng đăng nhập trước khi thử lại; không giả định thông báo bị mất đồng nghĩa chưa commit |

Exit code: `0` thành công; `1` bị từ chối/lỗi nghiệp vụ hoặc hệ thống;
`2` tham số/terminal không hợp lệ; `130` ngắt bằng Ctrl+C hoặc hết input.

## File liên quan và kiểm thử

| File | Vai trò |
| --- | --- |
| [recover_admin.py](../backend/scripts/recover_admin.py) | CLI, chọn DB, kiểm tra Admin/schema, transaction và xử lý nhập ẩn |
| [test_admin_recovery.py](../backend/tests/test_admin_recovery.py) | Test bằng SQLite tạm; không dùng tài khoản thật |
| [auth_schema.py](../backend/app/db/auth_schema.py) | Danh sách bảng/cột auth dùng chung, không migration |
| [auth_store.py](../backend/app/repositories/auth_store.py) | Bộ băm/digest hiện có và luồng đăng nhập/đổi mật khẩu để kiểm chứng |
| [auth.py](../backend/app/schemas/auth.py) | Quy tắc mật khẩu dùng chung |

Từ `backend`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_admin_recovery.py -q
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -B -m ruff check app tests scripts
```

Kết quả ngày 12/09/2026: **224 test backend không integration đạt**, gồm **54
test mới** của phần này; 9 integration test không được chạy. Ruff đạt.

Đã kiểm tra lệnh `--help`, xác nhận import CLI không tải cấu hình/kết nối
graph, Ruff format cho hai file Python mới, 72 liên kết nội bộ trong các tài
liệu thay đổi, Markdown qua Prettier `--debug-check` và diff không lỗi whitespace.

Các ca đã kiểm tra: mật khẩu cũ không dùng được; thu hồi toàn bộ phiên đích;
giữ nguyên tài khoản khác, grants và giới hạn IP; mật khẩu tạm buộc đổi trước
khi truy cập API nghiệp vụ; sai role/khóa/email; DB mất/hỏng/schema lạ/trigger;
đổi file hoặc tài khoản sau preview; rollback khi lỗi giữa transaction hoặc
Ctrl+C; DB bị khóa; hai lần khôi phục đồng thời; xác nhận sai; password bounds;
không trim mật khẩu; từ chối pipe/redirect và fallback getpass; không in secret
trong lỗi tham số hoặc exception.

Luồng đăng nhập/đổi mật khẩu dùng FastAPI thật với SQLite tạm; truy vấn graph
được thay bằng stub. CLI được kiểm tra bằng input/getpass giả lập; chưa dùng
tài khoản thật để diễn tập và chưa coi đây là kiểm thử production. FE không
thay đổi trong đợt này nên không chạy lại suite giao diện.

## Giới hạn và lưu ý bàn giao

- Đây là thao tác quản trị có quyền cao. Câu xác nhận ngăn nhầm thao tác,
  không chứng minh danh tính người đang giữ quyền hệ điều hành.
- Không chống được người có quyền quản trị máy chủ sửa trực tiếp DB/mã nguồn
  hoặc thay đổi filesystem có chủ đích. Kiểm tra định danh file không thay cho
  kiểm soát quyền OS và yêu cầu tạm dừng các bên ghi.
- Giới hạn chờ SQLite là 2 giây; kiểm tra truy vấn dùng progress handler với
  ngân sách 3 giây. Đây không phải deadline cứng cho mọi I/O hoặc lỗi hệ điều hành.
- Bản backup chứa thông tin nhạy cảm; mật khẩu cũ và dữ liệu quyền vẫn có thể
  nằm trong backup theo thời điểm. Khôi phục backup cũ có thể phục hồi trạng
  thái cũ; cần kiểm tra lại quyền và phiên theo quy trình backup/restore.
- Không tự lưu mật khẩu, tạo file log hoặc ghi audit tài khoản bền vững.
  Audit tài khoản/quyền vẫn là hạng mục riêng chưa làm; không dùng nhật ký dự
  án để suy ra đã có lịch sử thao tác khôi phục này.
- Không đảm bảo xóa sạch bản sao mật khẩu khỏi bộ nhớ process hoặc công cụ
  ghi hình/giám sát bên ngoài. Chỉ thực hiện trong môi trường vận hành tin cậy.
- Không tự triển khai, khởi động/dừng dịch vụ, tạo tài khoản phụ hoặc xử lý
  các hạng mục nghiệm thu MVP khác khi chạy công cụ.
