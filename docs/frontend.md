# SkillGraph frontend

Dashboard tiếng Việt sử dụng React, TypeScript, Vite và TanStack Query. Dữ liệu
hiển thị được lấy từ FastAPI; không có dữ liệu mẫu tự động thay thế khi backend lỗi.

## Chạy trên Windows

Yêu cầu Node.js >= 22.12 và backend đã được cấu hình. Mở hai terminal tại thư mục dự án.

Terminal 1:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

Terminal 2:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Mở <http://127.0.0.1:5173>. Nếu `node_modules` đã được cài, chỉ cần `npm.cmd run dev`.
Lần đầu, tạo Admin bằng `python -m scripts.create_admin` trong backend;
xem [hướng dẫn đăng nhập và phân quyền](authentication.md). Không có tài khoản mặc định.
Lệnh npm gọi trực tiếp file JavaScript của công cụ để tương thích với đường dẫn
Windows chứa dấu `&`. Không cần đổi tên thư mục dự án.

## Những việc có thể thực hiện

- Tổng quan: số nhân viên, nhân viên sẵn sàng, dự án đang chạy và kỹ năng;
  chọn dự án để xem mức đáp ứng kỹ năng và gợi ý ứng viên.
- Nhân viên: tìm kiếm, lọc trạng thái, phân trang, tạo/sửa/xóa hồ sơ;
  mở hồ sơ để gán, cập nhật và gỡ kỹ năng.
- Kỹ năng: tìm kiếm, lọc theo nhóm, tạo/sửa/xóa danh mục.
- Dự án: tạo/sửa/xóa; trang chi tiết gồm phân tích, đội ngũ và yêu cầu kỹ năng.
- Hoạt động (Admin): trang lịch sử chung và tab trong chi tiết dự án, lọc/phân
  trang và xem giá trị trước/sau. Xem [nhật ký dự án](project-activity.md).
- Phân công: xem dung lượng còn lại, đặt vai trò và allocation, chỉnh sửa hoặc gỡ
  phân công. Lỗi vượt giới hạn từ server được hiển thị trong biểu mẫu, giữ lại dữ
  liệu đã nhập để sửa và thử lại.

Các nút xóa/gỡ đều mở hộp thoại xác nhận. Không tự thay đổi trạng thái nhân viên
khi phân công: trạng thái `AVAILABLE` và allocation là hai thuộc tính nghiệp vụ
khác nhau theo API hiện tại. Candidate Recommendation gợi ý theo kỹ năng và lịch
sử cộng tác; vẫn phải kiểm tra dung lượng khi thực hiện phân công.

Đợt [rà soát giao diện bước 5](usability-review.md) bổ sung lời giải thích ngay
trên màn hình, phân biệt hết phiên với lỗi kết nối, giữ ô nhập khi lưu thất
bại, chặn submit liên tiếp và trả focus khi đóng hộp thoại. Trang đăng nhập
chỉ hướng dẫn liên hệ quản trị viên; CLI tạo Admin nằm trong tài liệu vận hành.
Lỗi mạng/timeout khi ghi chưa chứng minh server chưa lưu: kiểm tra dữ liệu
trước khi gửi lại. Đây không phải tính năng tự lưu bản nháp qua tải lại trang.

## API và cấu hình

Frontend gửi yêu cầu đến `/api/...`. Vite chuyển tiếp `/api` và `/health` đến
`http://127.0.0.1:8000`; cả `dev` và `preview` đều có proxy. Thiết kế proxy dựa trên
[tài liệu Vite](https://vite.dev/config/server-options.html#server-proxy).

Nếu backend dùng địa chỉ khác, tạo `frontend/.env.local` từ `.env.example`, đặt
`SKILLGRAPH_API_TARGET`, rồi khởi động lại Vite. Biến này chỉ được dùng trong
cấu hình proxy. Không đặt URI, tài khoản hay mật khẩu CognoDB trong frontend.

`npm.cmd run build` tạo `dist/`; có thể kiểm tra bản build bằng
`npm.cmd run preview` tại <http://127.0.0.1:4173>. Khi triển khai bản build cần
reverse proxy `/api` đến FastAPI và fallback các route giao diện về `index.html`.
Vite preview phục vụ kiểm tra cục bộ. Backend đã bảo vệ API bằng session và
phân quyền Admin/Manager/Viewer; cần cấu hình HTTPS, Secure cookie và origin
production trước khi mở Internet. Xem [các giới hạn triển khai](authentication.md).

## Kiểm tra

Để kiểm thử ghi **FE → BE → graph thật**, dùng runner có chốt an toàn trong
[hướng dẫn graph E2E](graph-e2e-acceptance.md), không dùng `test:live` chỉ đọc
hoặc `test:rbac` graph mô phỏng thay thế. Bộ mới đã được chuẩn bị nhưng chưa
chạy trên instance test thật; không tự nằm trong `npm test` bên dưới.

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run format:check
npm.cmd run build
npm.cmd test
npm.cmd run test:auth-stack
npm.cmd run test:rbac
npm.cmd run test:live
```

- `test`: chạy Microsoft Edge headless, mock API **chỉ trong test**, kiểm tra CRUD,
  quan hệ, allocation conflict, bàn phím, mobile và lỗi kết nối. Không ghi CognoDB.
  Bao gồm kiểm tra tự động bằng axe cho dashboard, biểu mẫu và bảng phân công;
  kiểm tra này không thay thế đánh giá khả năng truy cập thủ công toàn bộ ứng dụng.
  Bao gồm `usability.spec.ts` cho lỗi đăng nhập/lưu, submit liên tiếp, dữ liệu
  phụ thuộc lỗi, bàn phím và màn hình nhỏ. Xem [kết quả bước 5](usability-review.md#kiểm-chứng).
- `format`: định dạng mã nguồn bằng Prettier; `format:check`: kiểm tra định dạng.
- `test:auth-stack`: FE và FastAPI thật, SQLite tạm; graph được stub, không kết nối CognoDB.
- `test:rbac`: nghiệm thu cả ba role qua UI và API trực tiếp; FastAPI/SQLite thật
  trong test, graph mô phỏng. Kiểm tra quyền ngoài dự án, Viewer ghi trái phép,
  thu hồi phiên và buộc đổi mật khẩu. Chạy lần lượt với `test:auth-stack` vì cùng
  dùng cổng 5174/18000. Xem [kết quả và giới hạn nghiệm thu](rbac-acceptance.md).
- `test:live`: backend phải đang chạy ở cổng 8000, có dữ liệu và tài khoản hiện hữu.
  Cấp `SKILLGRAPH_TEST_EMAIL`/`SKILLGRAPH_TEST_PASSWORD` bằng environment variables.
  Thiếu tài khoản thì skip. Login/logout ghi phiên; các API nghiệp vụ chỉ được đọc.
- Playwright dùng Edge đã có trên Windows, không tải thêm một bản Chromium.
  Máy không có Edge có thể đổi `channel` trong `playwright.config.ts` hoặc cài Edge.
- Ảnh chụp và trace nằm trong `test-results/`, đã được Git bỏ qua.

## Cấu trúc mã

```text
frontend/src/
  api.ts            # fetch, timeout, xử lý lỗi HTTP, phân trang cho selectors
  types.ts          # kiểu dữ liệu tương ứng với response backend
  config.ts         # trường biểu mẫu CRUD
  hooks.ts          # tổng hợp allocation từ các dự án
  components/       # dialog, bảng quan hệ, phân tích, feedback
  pages/            # tổng quan, danh sách, chi tiết
  App.tsx           # layout và routing
  styles.css        # màu sắc, responsive, reduced motion
```

TanStack Query cache dữ liệu và cập nhật lại màn hình sau khi ghi thành công.
Các danh sách quản lý phân trang ở server (10 bản ghi/trang). Dashboard dùng
`GET /api/dashboard` lấy các tổng và tối đa 5 nhân viên; bộ chọn dự án tìm kiếm và
phân trang 10 bản ghi, chỉ tải khi mở. Xem [thiết kế và kiểm thử dashboard](dashboard.md).
Các selector khác còn đọc đủ các trang, không cắt im lặng ở giới hạn 100 bản ghi.
`useCapacity` trong hộp thoại phân công vẫn tổng hợp từ từng dự án; đây là bước
tối ưu tiếp theo, không còn nằm trên luồng tải dashboard ban đầu.

`node_modules/`, `dist/`, cache, trace và `.env.local` được bỏ qua bởi Git.
Chỉ cài thư viện một lần bằng `npm.cmd ci`; không commit `node_modules`.
