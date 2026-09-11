# Nâng cấp giao diện UI/UX hiện đại (Emerald & Midnight Glassmorphism)

Tài liệu này mô tả chi tiết việc nâng cấp toàn bộ hệ thống giao diện người dùng (UI/UX) của ứng dụng **SkillGraph**, chuyển đổi từ phong cách giao diện cổ điển sang phong cách làm việc số (Workspace) hiện đại chuẩn 2026.

## Mục đích

- **Nâng cao tính thẩm mỹ và chuyên nghiệp**: Mang lại cảm giác cao cấp, chỉn chu và mượt mà cho toàn bộ ứng dụng khi sử dụng.
- **Tối ưu hóa trải nghiệm người dùng (UX)**: Giúp người quản lý và nhân viên dễ dàng theo dõi thông tin kỹ năng, mức độ đáp ứng của dự án (skill gap), đề xuất nhân sự và nhật ký hoạt động.
- **Đồng bộ hóa Design System**: Xây dựng bộ quy chuẩn giao diện chung (Design Tokens) bao gồm typography, màu sắc, khoảng cách, bo góc, hiệu ứng thủy tinh mờ (Glassmorphism) và hiệu ứng chuyển động (Micro-animations).
- **Bảo tồn 100% tính tương thích E2E**: Giữ nguyên toàn bộ cấu trúc CSS selectors (`.stat-card`, `.coverage-number`, `.candidate-card`, `.capacity-person`, `.activity-item`, `tbody tr`, v.v.) giúp bộ kiểm thử Playwright tự động chạy qua 100%.

---

## Phạm vi đã triển khai

### 1. Typography & Google Fonts
- Tích hợp font chữ thế hệ mới **Plus Jakarta Sans** (cho tiêu đề, thương hiệu, thẻ chỉ số) và **Inter** (cho văn bản, bảng biểu, điều hướng) trực tiếp từ Google Fonts CDN vào `frontend/index.html`.
- Áp dụng các quy tắc render chuẩn: `-webkit-font-smoothing: antialiased`, `text-rendering: optimizeLegibility`.

### 2. Bảng màu & Design Tokens (`styles.css`)
- **Midnight Emerald Sidebar**: Tông màu tối đậm chủ đạo `#0d1f1a` -> `#081411` kết hợp viền mờ `rgba(255, 255, 255, 0.08)`, hiệu ứng active thanh menu màu Emerald `#34d399` có hiệu ứng đổ bóng mờ.
- **Glassmorphic Topbar**: Nền trắng mờ `rgba(255, 255, 255, 0.85)` với bộ lọc làm mờ hậu cảnh `backdrop-filter: blur(12px)` và thanh định hướng (Breadcrumbs) sắc nét.
- **Dải màu Emerald hiện đại**:
  - Primary Green: `#10b981` (Emerald 500), Dark Green: `#059669` (Emerald 600)
  - Surface Accent: `#ecfdf5` (Emerald 50), Background: `#f8fafc` (Slate 50)
- **Thẻ chỉ số (Stat Cards)**: Bo góc 14px, viền mờ `#e2e8f0`, dải màu rực rỡ cho icon (Green, Mint, Amber, Sky blue), hiệu ứng nhấc thẻ khi rê chuột (hover elevation: `transform: translateY(-4px)`).
- **Badge trạng thái & Progress bars**: Tự động hiển thị màu sắc tương ứng với trạng thái (Active, Gap, Missing, Assigned, On Leave) với chấm chỉ báo màu.
- **Giao diện Đăng nhập (Auth Layout)**: Thiết kế split-screen với panel câu chuyện thương hiệu hiệu ứng Midnight Glassmorphism và form đăng nhập màu sắc sang trọng.

### 3. Tương thích responsive & Hiệu ứng micro-animations
- Hỗ trợ đầy đủ hiển thị trên Desktop (1600px+), Tablet (1030px - 1250px) và Mobile (dưới 760px).
- Nút bấm (Buttons) có hiệu ứng chuyển màu gradient, shadow theo độ nổi và feedback khi nhấn (`active: translateY(1px)`).
- Modal dialogs với hiệu ứng làm mờ nền (`backdrop-filter: blur(6px)`).

---

## Các tệp liên quan

| Tệp | Thay đổi chính |
| --- | --- |
| [frontend/index.html](file:///d:/SkillGraph%20-%20Employee%20Skills%20&%20Project%20Staffing/frontend/index.html) | Nhập Google Fonts (`Plus Jakarta Sans` & `Inter`), cập nhật `theme-color` sang `#0f172a` |
| [frontend/src/styles.css](file:///d:/SkillGraph%20-%20Employee%20Skills%20&%20Project%20Staffing/frontend/src/styles.css) | Tái thiết kế toàn bộ hệ thống CSS Tokens, Sidebar, Topbar, Stat Cards, Tables, Buttons, Dialogs, Auth |
| [docs/ui-redesign.md](file:///d:/SkillGraph%20-%20Employee%20Skills%20&%20Project%20Staffing/docs/ui-redesign.md) | Tài liệu Tiếng Việt mô tả chi tiết việc nâng cấp giao diện |
| [docs/README.md](file:///d:/SkillGraph%20-%20Employee%20Skills%20&%20Project%20Staffing/docs/README.md) | Cập nhật danh mục tài liệu dự án |

---

## Hướng dẫn kiểm tra & Lệnh kiểm thử

### 1. Kiểm tra tĩnh (TypeScript Typecheck)
Từ thư mục `frontend`:
```powershell
npm.cmd run typecheck
```
*Kết quả*: Biên dịch thành công 0 lỗi.

### 2. Kiểm thử tự động E2E (Playwright Tests)
Từ thư mục `frontend`:
```powershell
npm.cmd run test
```
*Kết quả*: 27/27 test cases chạy thành công (bao gồm kiểm thử UI, Dashboard metrics, Auth flow, Activity log).

### 3. Kiểm tra trực tiếp trên trình duyệt
Khởi chạy frontend dev server:
```powershell
cd frontend
npm.cmd run dev
```
Truy cập `http://127.0.0.1:5173` để trải nghiệm giao diện mới trên các trang:
- Trang Đăng nhập & Đổi mật khẩu
- Trang Tổng quan (Dashboard)
- Trang Danh mục Nhân viên, Kỹ năng, Dự án
- Trang Nhật ký hoạt động & Quản lý tài khoản

---

## Giới hạn & Lưu ý

- **Mạng kết nối CDN Font**: Việc nạp font từ Google Fonts CDN cần kết nối Internet khi tải trang lần đầu; nếu offline, hệ thống sẽ tự động dùng font chữ dự phòng hệ thống (`-apple-system`, `Segoe UI`, `Roboto`).
- **CSS Selectors**: Tránh thay đổi hoặc xóa các class name E2E test (`.stat-card`, `.coverage-number`, v.v.) trong các phiên bản cập nhật tương lai.
