# Kiểm thử FE → BE → graph thật từ đầu đến cuối

Ngày cập nhật: **14/09/2026**.

**Trạng thái: đã chuẩn bị bộ test và kiểm tra an toàn ngoại tuyến; chưa chạy
nghiệm thu graph thật, chưa đánh dấu bước 4 đạt.** Đích test chưa được cấu hình
đủ và chưa xác nhận quyền sử dụng độc quyền trong khoảng chạy. Không dùng kết
quả unit test hoặc build để thay cho kết quả trên CognoDB thật.

## 1. Mục đích và phạm vi

Kiểm chứng cùng một luồng từ biểu mẫu React, HTTP qua Vite, FastAPI, phân quyền,
service/repository đến graph thật; sau đó đọc lại bằng API và kết nối driver mới.
Không mock HTTP, auth hoặc service trong bộ test này. Không chạy trên dữ liệu
đang vận hành, không tự dùng `backend/.env` làm đích ghi.

Phạm vi đã viết:

- Một kịch bản Playwright gồm **13 bước** theo thứ tự, chạy bằng Microsoft Edge
  headless. Tạo dữ liệu nghiệp vụ qua giao diện, không seed bằng Cypher.
- Tài khoản Admin/Manager/Viewer tổng hợp trong SQLite riêng từng lần thử;
  xác thực, CSRF và kiểm soát quyền đều dùng implementation thật.
- So sánh kết quả nghiệp vụ với dữ liệu kỳ vọng tính trước; kiểm tra lỗi qua UI
  và API, nhật ký actor/trước/sau, xung đột và phân công đồng thời.
- Sau khi Playwright kết thúc, driver mới xuất graph và kiểm tra trạng thái
  cuối: đủ node của lần thử, đúng **18 quan hệ và thuộc tính**, có audit, không
  vượt allocation. Đây là cách phân biệt dữ liệu lưu thật với cache giao diện.
- Quy trình giữ bằng chứng và cleanup riêng, có xác nhận; không dọn dữ liệu tự
  động trong `finally` khi test lỗi.

Không sửa chính sách quyền, công thức gợi ý hoặc logic transaction của ứng dụng
trong đợt chuẩn bị này. Công cụ/test không phải chức năng production mới.

## 2. Đích test, secrets và các chốt an toàn

Đã tạo `backend/.env.e2e` trống, được Git bỏ qua. Điền trên máy:

```dotenv
COGNODB_URI=
COGNODB_USER=
COGNODB_PASSWORD=
```

Các giá trị phải thuộc **instance test trống, riêng biệt, được phép tạo/xóa dữ
liệu thử**. Không gửi mật khẩu vào chat hoặc viết vào lệnh terminal. Mẫu không
chứa secret được lưu ở [`.env.e2e.example`](../backend/.env.e2e.example).
Không ghi đè `.env.restore` của bài phục hồi hoặc `.env` của ứng dụng đang dùng.

Runner thực hiện các kiểm tra trước khi ghi:

1. File đích phải tồn tại, khác `.env`, có đủ ba trường kết nối. Không tự rơi
   về cấu hình nguồn nếu thiếu giá trị.
2. Từ chối URI chứa credentials, path hoặc query; so sánh host/port đã chuẩn
   hóa với **cả** URI nguồn trong `.env` và environment của process.
3. Đọc số node và schema đích; `run` chỉ chấp nhận graph không có node. Không
   chạy câu lệnh xóa dữ liệu có sẵn để làm trống.
4. Phải xác nhận đích dùng thử và quyền sử dụng độc quyền. Không cho ứng dụng
   khác, seed, drill phục hồi hoặc người dùng Cypher cùng ghi vào đích lúc test.
5. Thiếu constraint/index thì dừng, trừ khi người vận hành chủ động thêm cờ
   `--initialize-schema`. Cờ này chạy migration hiện có trên **đích test**, không
   chạy trên nguồn; schema được giữ lại sau cleanup.
6. SQLite riêng được tạo dưới `backend/e2e-runs/<run-id>/auth.sqlite3`; cấm tái
   sử dụng DB đã tồn tại. Không dùng tài khoản/mật khẩu Admin thật.
7. Test server chỉ nghe localhost `18001`, FE test `5175`; không tái sử dụng
   server cổng 8000/5173 hoặc server có sẵn ở cổng test.

**Giới hạn nhận diện:** host/port khác nhau không chứng minh chắc chắn là hai
database khác nhau nếu có DNS alias, proxy hoặc routing. Người vận hành vẫn
phải xác nhận instance vật lý/logical riêng. Các cờ CLI là xác nhận vận hành,
không phải cơ chế khóa các writer bên ngoài hay cơ chế phân quyền của nhà cung cấp.

## 3. Bộ dữ liệu và kết quả kỳ vọng

Mỗi lần chạy có mã ngẫu nhiên gồm 18 chữ số. ID được tạo theo dạng
`EMP<run-id>01`, `SK<run-id>01`, `PROJ<run-id>01`; tên bắt đầu bằng
`E2E <run-id> `. Không sử dụng ID của dữ liệu đang dùng.

- 3 kỹ năng: `Covered`, `Gap`, `Missing`.
- 8 nhân viên: `Member`, `Both`, `Collaborator`, `Higher`, `Tie`,
  `Unavailable`, `Low`, `Race`.
- 4 dự án: `Main`, `Shared`, `Race A`, `Race B`.

Yêu cầu của Main: cả ba kỹ năng cần cấp 3, ưu tiên lần lượt MUST/SHOULD/NICE.
Đội ban đầu chỉ có Member, sở hữu Covered cấp 4 và Gap cấp 2; chưa sở hữu
Missing. Mỗi HAS_SKILL dùng số năm kinh nghiệm 2,5 để kiểm tra số thập phân.

| Kỹ năng | Cấp đội / yêu cầu | Kết quả kỳ vọng |
| --- | --- | --- |
| Covered | 4 / 3 | COVERED — Đáp ứng |
| Gap | 2 / 3 | GAP — Cần nâng cấp |
| Missing | 0 / 3 | MISSING — Chưa có |

Tỷ lệ đáp ứng ban đầu: `round(1 / 3 × 100, 2) = 33,33%`. Phép tính hiện có
không cân trọng số ưu tiên. Khi thêm Both (Gap cấp 4, Missing cấp 3), tỷ lệ
phải lên 100%; gỡ Both khỏi Main phải trở về 33,33%.

Thứ tự gợi ý kỳ vọng:

1. Both: đáp ứng hai kỹ năng còn thiếu, đã làm cùng Member ở Shared.
2. Collaborator: đáp ứng một kỹ năng cấp 3, đã làm cùng Member.
3. Higher: một kỹ năng cấp 5, chưa cộng tác; đứng sau Collaborator theo luật
   ưu tiên số cộng tác trước tổng cấp độ.
4. Tie: giống Higher nhưng ID lớn hơn, nên xếp sau.

Member bị loại vì đang ở Main; Unavailable không ở trạng thái AVAILABLE; Low
chưa đạt cấp yêu cầu; Race không có kỹ năng phù hợp. Both ban đầu có 100%
allocation ở Shared nhưng vẫn được gợi ý: **đây là quy tắc hiện tại, gợi ý chưa
lọc dung lượng**. Test giảm Shared xuống 80% trước khi thêm 20% vào Main.

## 4. Các bước trong kịch bản và bằng chứng yêu cầu

| Bước test | Thao tác / điều kiện đạt khi chạy thật |
| --- | --- |
| 01 | Tạo 3 Skill và 8 Employee qua FE; API trả 201, đọc lại đúng tên |
| 02 | Gán 11 HAS_SKILL qua FE; đối chiếu cấp và kinh nghiệm 2,5 trên API/UI |
| 03 | Tạo 4 Project, khai báo 3 REQUIRES_SKILL; đúng min_level và priority |
| 04 | Phân công đội ban đầu và dự án chung phục vụ kiểm tra cộng tác |
| 05 | API/UI đúng COVERED/GAP/MISSING và 33,33% |
| 06 | Gợi ý đúng thứ tự, số kỹ năng khớp, cộng tác và các trường hợp bị loại |
| 07 | Manager sửa Main được giao qua UI; ngoài grant bị API từ chối; Viewer không ghi; nhật ký/quản trị chỉ Admin |
| 08 | Giữ biểu mẫu phân công đang mở, request khác tăng allocation ở Shared; gửi biểu mẫu cũ phải nhận 409 thật, UI giữ giá trị và hiển thị lỗi 100%; không thêm audit giả |
| 09 | Phân công Member 70% ở Main + 30% ở Shared = 100% thành công; thêm 1% ở Race A bị 409, không đổi graph/audit |
| 10 | Hai HTTP request từ hai context/session độc lập cùng phân công Race 60% vào hai dự án, lặp ba vòng; mỗi vòng một 201 và một 409, chỉ một quan hệ/audit mới với đúng actor |
| 11 | Sửa allocation Both, thêm vào Main rồi gỡ bằng UI; coverage và gợi ý cập nhật 100% → 33,33% |
| 12 | Đối chiếu nhật ký sửa 40 → 70 và gỡ allocation 20; đúng Admin/Manager, trước/sau; UI hiển thị tương ứng |
| 13 | Thử xóa Employee/Skill/Project vẫn còn quan hệ qua FE: 409, lỗi hiển thị và bản ghi vẫn còn |

Ba vòng request đồng thời là kiểm thử race ở mức HTTP, không phải chứng minh
mọi lịch thực thi hoặc benchmark tải. Không chèn delay/test hook vào transaction
production để ép kết quả. Nếu engine không đảm bảo khóa như dự kiến, test phải
thất bại và cần điều tra trước khi công nhận tính đúng.

## 5. Chạy kiểm thử

Điều kiện: dependency BE/FE đã cài theo README, Microsoft Edge có sẵn, đích
test trống có kết nối hợp lệ. Không cần tự mở hai terminal BE/FE test; runner
và Playwright quản lý process. Không chạy test này song song với drill phục hồi
hoặc một lần graph E2E khác trên cùng instance.

```powershell
# Tại backend: chỉ đọc thông tin đích, chưa tạo schema/node/tài khoản
.\.venv\Scripts\python.exe -B -m scripts.graph_e2e preflight
```

Preflight chỉ báo `empty` và `schema_ready`, không in URI/mật khẩu. Phải kiểm
tra giá trị; exit code 0 của lệnh đọc không thay xác nhận môi trường riêng.
Chỉ sau khi xác nhận quyền tạo/xóa dữ liệu thử và không có bên khác ghi:

```powershell
# Nếu schema test đã đầy đủ
.\.venv\Scripts\python.exe -B -m scripts.graph_e2e run --confirm-empty-test-target --exclusive-test-target

# Nếu đích test mới, được phép tạo constraint/index: dùng lệnh này thay lệnh trên
.\.venv\Scripts\python.exe -B -m scripts.graph_e2e run --confirm-empty-test-target --exclusive-test-target --initialize-schema
```

Không chạy trực tiếp `playwright.graph.config.ts` hoặc server test để bỏ qua
runner. Config Playwright này không nằm trong `npm test` mặc định; các test
mock/RBAC thường ngày không được tự chuyển sang ghi graph thật.

## 6. Bằng chứng, dọn dữ liệu và dung lượng

Runner tạo thư mục riêng với quyền truy cập hạn chế; không ghi đè lần chạy cũ:

```text
backend/e2e-runs/<run-id>/
  manifest.json       # run-id, fingerprint đích, danh sách ID được phép
  auth.sqlite3        # tài khoản/phiên test; vẫn coi là dữ liệu nhạy cảm
  report.json         # kết quả hoặc failed_or_interrupted
  graph-after.json    # chỉ có sau khi browser + đối chiếu graph đều thành công
  cleanup-report.json # chỉ có sau cleanup được xác nhận và kiểm tra lại
```

Mật khẩu test được sinh ngẫu nhiên trong process, không ghi vào manifest/report
hoặc tài liệu. Snapshot chỉ chứa dữ liệu tổng hợp của đích được xác nhận; không
commit cả thư mục này. Không bật trace/video/screenshot tự động. Output
Playwright nằm trong `frontend/test-results/graph-<run-id>/`, cũng được bỏ qua
bởi Git. Không thêm Docker, thư viện hoặc browser download cho bộ test này.

Trạng thái `passed_data_retained` nghĩa là browser đạt và driver mới đối chiếu
trạng thái lưu thật đạt, **nhưng dữ liệu thử vẫn được giữ lại để kiểm tra**.
Nếu lỗi, giữ nguyên dữ liệu và báo cáo; không đổi thành PASS hoặc xóa bằng chứng.

Khi đã xem báo cáo, dừng mọi bên ghi vào instance test và dùng đúng run-id:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.graph_e2e cleanup --run-id <run-id> --confirm-cleanup --exclusive-test-target
```

Cleanup so khớp manifest với đích, kiểm tra **mọi node** đều có ID/tên đúng
namespace hoặc là audit thuộc dự án và actor trong SQLite của lần thử. Có dữ
liệu lạ thì dừng toàn bộ. Đọc lại trong transaction trước khi xóa theo từng ID
và thuộc tính chính xác; không chạy xóa toàn graph vô điều kiện. Sau đó xác nhận
graph không còn node và lưu số lượng đã xóa. Cần môi trường độc quyền vì công
cụ không khóa được writer ngoài hệ thống.

Lệnh này **xóa dữ liệu graph thử, không qua thùng rác**; giữ schema và các file
bằng chứng/SQLite trên máy. Không coi snapshot E2E là bộ backup graph+auth có
đầy đủ quy trình verify/restore của bước 2. Không tự xóa backup, dữ liệu nguồn,
`.venv`, `node_modules` hoặc toàn bộ `e2e-runs` để giải phóng dung lượng. Nếu lần
chạy dừng trước khi tạo SQLite, hoặc engine không hỗ trợ cleanup như dự kiến,
dừng để kiểm tra thủ công, không bỏ chốt kiểm tra quyền sở hữu.

## 7. File triển khai và kiểm thử ngoại tuyến

| File | Trách nhiệm |
| --- | --- |
| [graph_e2e.py](../backend/scripts/graph_e2e.py) | Preflight, chặn nguồn, runner, đối chiếu graph mới và cleanup có xác nhận |
| [graph_browser_server.py](../backend/tests/graph_browser_server.py) | App thật, graph thật, SQLite riêng; không mock |
| [test_graph_e2e.py](../backend/tests/test_graph_e2e.py) | Unit test chốt an toàn và bộ dữ liệu kỳ vọng, không truy cập graph |
| [playwright.graph.config.ts](../frontend/playwright.graph.config.ts) | Cổng riêng, không retry/reuse, không ghi trace/ảnh/video |
| [graph.spec.ts](../frontend/tests/graph.spec.ts) | 13 bước qua UI và API trực tiếp |
| [.env.e2e.example](../backend/.env.e2e.example) | Mẫu cấu hình không có secrets |
| [.gitignore](../.gitignore) | Bỏ qua `.env.e2e` và `backend/e2e-runs/` |

```powershell
# Tại backend: ngoại tuyến, không cần kết nối đích test
.\.venv\Scripts\python.exe -B -m pytest tests/test_graph_e2e.py -q
.\.venv\Scripts\python.exe -B -m ruff check scripts/graph_e2e.py tests/graph_browser_server.py tests/test_graph_e2e.py

# Tại frontend: kiểm tra kiểu và build, không chạy graph
npm.cmd run build
```

Kết quả đã thực hiện ngày 14/09/2026: **41 test chốt an toàn đạt**, TypeScript
và build FE đạt; Ruff/Prettier các file mới đạt. Những test này kiểm tra từ chối
nhầm đích, thiếu xác nhận, graph có dữ liệu, ID/path không hợp lệ, dữ liệu lạ,
sai quan hệ/thuộc tính và không in secrets trong lỗi. **Chưa chứng minh việc
ghi/cleanup/transaction thực sự chạy được trên engine test.**

Hồi quy backend ngoại tuyến: **271 passed, 9 deselected**, 52,48 giây
(`pytest -m "not integration" -q`), đã bao gồm 41 test mới, không cộng lại.
Playwright `--list` nhận diện 1 kịch bản graph; danh sách mặc định vẫn chỉ có
27 test trong 4 file, không tự chạy bài ghi graph. Preflight với `.env.e2e`
chưa điền trả exit code 1 và thông báo thiếu cấu hình trước khi kết nối.
Không tạo schema, node, quan hệ, tài khoản thật hoặc bộ bằng chứng graph trong
lần chuẩn bị này; chưa có run-id nghiệm thu thật để ghi PASS.

## 8. Điều kiện đóng bước 4

- [ ] Xác nhận instance test riêng, được phép ghi/xóa và không dùng chung với
  dữ liệu phục hồi cần giữ; điền `.env.e2e` trên máy.
- [ ] Preflight đúng đích, trống; cấp phép schema nếu cần, xác nhận không có writer khác.
- [ ] Chạy 13 bước với FE/BE/graph thật và sửa mọi lỗi phát hiện; không bỏ assertion.
- [ ] Có `passed_data_retained` cùng kết quả đối chiếu bằng driver mới.
- [ ] Xem bằng chứng, cleanup đúng run-id theo quy trình, có kết quả graph trống.
- [ ] Cập nhật tài liệu này bằng run-id, thời điểm, kết quả thật và giới hạn còn lại;
  không đưa dữ liệu nhạy cảm vào báo cáo.

Bước 2 thử sao lưu/phục hồi thật vẫn có tiêu chí riêng trong
[backup-restore.md](backup-restore.md); kết quả E2E không tự hoàn thành bước đó.
