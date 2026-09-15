# Bước 5: rà soát lỗi và thông báo giao diện

## Mục đích và phạm vi

Đợt rà soát ngày 14–15/09/2026 hoàn thiện các điểm dễ gây hiểu nhầm trong bản
local SkillGraph: đăng nhập, lỗi kết nối, giữ dữ liệu biểu mẫu, thao tác lưu/xóa,
bàn phím, màn hình nhỏ và cách hiểu phân bổ nhân sự. Không thiết kế lại FE,
không thay thuật toán gợi ý, không mở rộng thành tối ưu toàn hệ thống.

Tài liệu này ghi phần đã triển khai trong mã nguồn và kết quả kiểm tra tương
ứng. **Không thay thế nghiệm thu graph thật, sao lưu/phục hồi thật hoặc đánh
giá production.** Xem [graph E2E](graph-e2e-acceptance.md) và
[backup/restore](backup-restore.md) để biết trạng thái riêng của hai mục đó.

## Những điểm đã sửa

### 1. Đăng nhập và tình trạng phiên

- Trang đăng nhập chỉ hướng dẫn người dùng liên hệ quản trị viên khi chưa có
  tài khoản hoặc quên mật khẩu. Bỏ câu lệnh tạo Admin khỏi lời nhắc này.
  Hướng dẫn vận hành vẫn ở [đăng nhập và phân quyền](authentication.md) và
  [khôi phục Admin](admin-recovery.md); không có tài khoản/mật khẩu mặc định.
- Sai thông tin đăng nhập giữ thông báo chung, không tiết lộ email có tồn tại,
  bị khóa hay không. Không đổi lỗi mạng/HTTP 503 thành lỗi sai mật khẩu.
- Khi phiên đã xác thực nhận HTTP 401, FE xóa cache, đóng nội dung nghiệp vụ
  và yêu cầu đăng nhập lại với thông báo hết hạn hoặc bị thu hồi. Đây là thông
  báo thông tin, không phải thông báo thành công. Lần vào trang đầu tiên khi
  chưa đăng nhập không tự gán thành hết phiên.
- Lỗi mạng/5xx lúc kiểm tra lại `/api/auth/me` không chứng minh phiên vô hiệu.
  Nếu đã có người dùng xác thực, FE giữ workspace và biểu mẫu đang nhập, hiện
  lỗi có nút thử lại. Lần khởi động chưa xác thực vẫn chặn workspace cho đến
  khi kiểm tra được phiên. Mọi request nghiệp vụ tiếp tục chịu kiểm tra BE;
  thay đổi này không cho phép sử dụng API khi thiếu quyền.

### 2. Thông báo lỗi rõ nghĩa

| Tình huống | Cách FE xử lý |
| --- | --- |
| Sai mật khẩu/tài khoản không dùng được | Thông báo chung về email hoặc mật khẩu; giữ các ô nhập để sửa |
| Hết hạn/thu hồi phiên | Yêu cầu đăng nhập lại, không tiếp tục hiển thị workspace cũ |
| Không kết nối được máy chủ | Hướng dẫn kiểm tra mạng hoặc liên hệ quản trị viên |
| Quá 30 giây chờ response | Báo quá thời gian chờ, không tự gửi lại thao tác ghi |
| HTTP 503 | Báo dịch vụ dữ liệu tạm thời chưa sẵn sàng; không khẳng định riêng graph bị hỏng |
| HTTP 5xx khác | Thông báo lỗi hệ thống chung; không đưa chi tiết lỗi nội bộ BE lên giao diện |
| Xóa bản ghi còn quan hệ, HTTP 409 | Dịch định dạng lỗi BE hiện tại sang tiếng Việt, nêu số liên kết cần gỡ |
| Tổng allocation vượt 100%, HTTP 409 | Nêu tổng dự kiến, phần ở dự án khác, phần yêu cầu và giới hạn 100% |

Với thao tác ghi nghiệp vụ/quản trị tài khoản bị lỗi mạng, timeout hoặc 5xx,
FE còn nhắc **chưa xác nhận được kết quả ghi**. Người dùng phải kiểm tra dữ
liệu trước khi gửi lại; mất response không đồng nghĩa server chưa lưu. Tiêu
đề lỗi dùng cách diễn đạt trung tính, không khẳng định thao tác chắc chắn chưa
thực hiện. Các request đăng nhập/đăng xuất/đổi mật khẩu cá nhân không dùng
lời nhắc ghi nghiệp vụ này.

Các thông báo 409 trên được nhận diện theo định dạng cụ thể đang có trong BE;
không phải hệ thống dịch mọi lỗi. Validation và lỗi nghiệp vụ khác vẫn dùng
chi tiết API phù hợp. Khi BE thay đổi định dạng lỗi, cần cập nhật bộ nhận diện
và test tương ứng.

### 3. Biểu mẫu và thao tác an toàn

- `FormDialog` giữ các ô nhập khi lưu bị từ chối hoặc chưa nhận được kết quả;
  đưa focus đến thông báo lỗi. Không tự đóng rồi mở lại form khi lưu thất bại.
- Chốt đồng bộ bằng ref ngăn hai submit liên tiếp trước khi React cập nhật
  trạng thái. Trong lúc chờ, vô hiệu hóa trường nhập, nút lưu/đóng/hủy và
  Escape. Áp dụng cả form đăng nhập và đổi mật khẩu cá nhân.
- Nút xóa/gỡ tiếp tục mở hộp thoại xác nhận; mở hộp thoại, Hủy hoặc Escape
  không phát request xóa. Không tự gỡ quan hệ để cưỡng ép xóa bản ghi.
- Sửa lỗi focus khi đóng dialog: đóng trước khi React gỡ DOM và trả focus
  về nút mở nếu nút còn tồn tại. Áp dụng với Escape, Hủy, nút đóng và đóng sau
  thành công; nếu bản ghi/nút bị xóa thì không cố focus phần tử đã mất.
- Trong form phân công, chọn nhân viên cập nhật giới hạn allocation ngay,
  vẫn chọn được người khác và không làm mất vai trò đã nhập. Người đã hết
  dung lượng không thể lưu phân công mới qua form.
- Nếu đã tải được dữ liệu phụ thuộc rồi nhưng lần tải lại danh mục kỹ năng
  hoặc allocation bị lỗi, giữ form và bản nháp, hiện nút thử lại và khóa lưu
  cho đến khi lỗi được xử lý. Chưa tải được lần đầu thì không giả định là 0
  allocation hoặc danh mục rỗng.

Bản nháp chỉ tồn tại trong bộ nhớ của trang đang mở, **không phải tính năng
tự lưu**. Đóng form, đổi trang/tài khoản, tải lại trang hoặc hết phiên có thể
mất bản nháp; không lưu mật khẩu hay bản nháp vào localStorage/sessionStorage.
Chặn submit liên tiếp phía FE không phải idempotency phía BE và không thay
thế kiểm soát giao dịch/allocation tại database.

### 4. Giải thích trạng thái, allocation và gợi ý

- `AVAILABLE` / “Sẵn sàng” là trạng thái hồ sơ do **Admin** cập nhật theo quyền
  hiện tại. Phân công không tự đổi trạng thái này.
- Allocation còn lại = `100% − tổng allocation trên tất cả dự án` theo mô
  hình hiện tại; không có lịch phân bổ theo ngày trong đợt này.
- Dashboard ghi rõ chỉ số trạng thái không đồng nghĩa còn dung lượng; phần
  phân bổ hiển thị tỷ lệ đã dùng, không phải phần còn trống. Hồ sơ nhân viên
  hiển thị cả phần đã phân bổ và còn lại.
- Khi sửa phân công cũ, con số tối đa cho dự án này đã cộng lại phần hiện
  đang phân bổ tại đây. Không nhầm nó với dung lượng còn trống ngoài dự án.
- Khối gợi ý nói rõ chưa lọc theo allocation còn lại. Nút **Kiểm tra phân bổ**
  mở form để xem xét, không tự phân công. Một người được gợi ý vẫn có thể đã
  dùng 100%; cần kiểm tra khả năng nhận việc và xác nhận trước khi giao.
- Con số FE có thể cũ do người khác thao tác; BE vẫn kiểm tra giới hạn khi lưu.

## File, API, cấu hình và quyền

| Thành phần | File chính |
| --- | --- |
| Phiên, xử lý lỗi HTTP và mạng | `frontend/src/auth.tsx`, `frontend/src/api.ts`, `frontend/src/App.tsx` |
| Trang đăng nhập/đổi mật khẩu | `frontend/src/pages/Auth.tsx` |
| Dialog, focus, thông báo và chú thích dùng chung | `frontend/src/components/ui.tsx`, `frontend/src/styles.css` |
| Quan hệ kỹ năng/phân công, tính dung lượng | `frontend/src/components/Relations.tsx`, `frontend/src/hooks.ts` |
| Chú thích hồ sơ, danh sách, dashboard, gợi ý | `frontend/src/config.ts`, `frontend/src/pages/Directory.tsx`, `frontend/src/pages/Details.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/Analysis.tsx` |
| Kiểm thử mục 5 | `frontend/tests/usability.spec.ts`, `frontend/playwright.config.ts` |

Sử dụng các API sẵn có: `/api/auth/me`, `/api/auth/login`, `/api/auth/password`,
CRUD nhân viên/kỹ năng/dự án và quan hệ assignments/skills/requirements. Không
thêm endpoint, migration graph/SQLite, biến môi trường, dependency hoặc dịch
vụ mới. Không cần tạo lại tài khoản hay seed lại dữ liệu. Khởi động theo
[hướng dẫn FE](frontend.md); môi trường đã cài thư viện không cần cài lại.

Quyền Admin/Manager/Viewer không thay đổi. Manager chỉ sửa phần dự án được
giao; Viewer không được ghi. Không dùng việc ẩn nút để thay kiểm tra BE. Xem
[ma trận quyền](authentication.md#quyền-truy-cập) và
[nghiệm thu ba role](rbac-acceptance.md).

## Kiểm chứng

Các bài lỗi mạng/HTTP/timeout trong `usability.spec.ts` dùng dữ liệu tổng hợp
và mock API trong trình duyệt. Ứng dụng chạy bình thường vẫn gọi API thật,
không có dữ liệu giả thay thế khi server lỗi. Không dùng tài khoản hay graph
đang vận hành để gây lỗi thử nghiệm.

Chạy từ thư mục `frontend`:

```powershell
npm.cmd test -- usability.spec.ts
npm.cmd test
npm.cmd run test:auth-stack
npm.cmd run test:rbac
npm.cmd run build
npm.cmd run format:check
```

Chạy `test:auth-stack` và `test:rbac` **lần lượt**, cùng dùng cổng test
5174/18000, FastAPI thật và SQLite tạm nhưng graph mô phỏng. Không dùng các
server test này để chạy ứng dụng hằng ngày. Bộ `npm test` dùng Edge sẵn có,
không tải trình duyệt mới. Không chạy `test:live` hay runner graph trong đợt này.

Kiểm tra BE cô lập, từ `backend`:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
```

Kết quả ngày 15/09/2026:

| Lệnh/phạm vi | Kết quả thực chạy |
| --- | --- |
| `npm.cmd test` | **47 passed** (2,1 phút), gồm **20** ca trong `usability.spec.ts` và 27 ca hồi quy có sẵn |
| `npm.cmd run test:auth-stack` | **1 passed** (54,1 giây), FE–FastAPI auth/SQLite tạm, graph mô phỏng |
| `npm.cmd run test:rbac` | **10 passed** (33,9 giây), kiểm tra UI + API ba role, thu hồi phiên và buộc đổi mật khẩu; graph mô phỏng |
| `npm.cmd run build` | **PASS**, gồm TypeScript `tsc --noEmit` và Vite build |
| `npm.cmd run format:check` | **PASS** toàn bộ file được cấu hình kiểm tra |
| `pytest -m "not integration" -q` | **271 passed, 9 deselected** (131,11 giây); 9 ca graph integration không chạy |

Lần chạy rà soát trước có 9 lỗi cần xử lý: 5 ca tìm bản ghi mới ở trang đầu
trong khi danh sách phân trang, 2 ca selector khớp nhãn quá chặt và 2 ca phát
hiện lỗi trả focus thật khi đóng dialog. Đã sửa selector/tìm kiếm trong test
và sửa vòng đời dialog trong ứng dụng, không bỏ test hoặc nới điều kiện đạt.
Sau đó bổ sung 2 ca lỗi tải lại dữ liệu phụ thuộc; cả 20 ca rà soát đạt trong
bộ 47 ca cuối.

**Kết luận:** đạt phạm vi rà soát bước 5 trên môi trường kiểm thử cục bộ/cô
lập nêu trên; không còn test thất bại trong các bộ đã chạy. Không suy rộng
thành kết luận mọi luồng với graph thật hoặc production đã được nghiệm thu.

Các điểm kiểm tra giao diện gồm màn hình 320×740 và 390×844, không tràn ngang,
Enter/Tab/Escape, focus lỗi và trả focus khi đóng, khóa thao tác lúc đang lưu,
axe cho những màn hình/hộp thoại được chọn. Form dài cuộn trong hộp thoại để
xem các ô hoặc nút; focus đến lỗi có thể cuộn phần đầu form khỏi khung nhìn.
Ảnh minh chứng dùng dữ liệu test nằm trong `frontend/test-results/`, được Git
bỏ qua; không đưa ảnh tài khoản thật hoặc secrets vào tài liệu.

## Giới hạn và việc không kết luận

- Kết quả này không xác nhận luồng ghi end-to-end với CognoDB thật hoặc việc
  restore thật đã đạt. Hai hạng mục tiếp tục có điều kiện nghiệm thu riêng.
- HTTP 503 được giả lập để kiểm tra FE; không tắt DB nguồn để thử nghiệm.
  Việc xác định dependency nào lỗi thuộc [readiness](readiness.md)/vận hành.
- Kiểm tra mobile là viewport trình duyệt Edge, không phải mọi thiết bị vật
  lý, trình đọc màn hình hoặc mọi browser. Axe không thay đánh giá truy cập
  thủ công toàn bộ ứng dụng.
- Chưa có bộ dữ liệu nghiệm thu graph thật và số đo tải mới để kết luận vấn
  đề hiệu năng. Không bổ sung cache/server/thuật toán tối ưu theo suy đoán.
  `useCapacity` vẫn tổng hợp theo từng dự án; tối ưu khi có đo đạc chứng minh.
- Không mở Internet, không thay mật khẩu thật, không thay quyền thật, không
  thêm email reset/MFA/SSO hoặc audit tài khoản trong hạng mục này.
