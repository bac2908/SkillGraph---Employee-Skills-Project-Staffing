# Tổng quan dự án SkillGraph

**Tên đầy đủ:** SkillGraph — Employee Skills & Project Staffing.

**Mô tả:** Hệ thống quản lý năng lực nhân viên và hỗ trợ phân công nhân sự cho dự án.

**Đối tượng đọc:** Người review, nhà tuyển dụng, người quản lý doanh nghiệp và lập trình viên mới tiếp nhận dự án.

**Mốc đối chiếu mã nguồn và tài liệu:** 12/09/2026.

Tài liệu này giải thích dự án làm gì, vì sao cần, ai sử dụng, cách hoạt động và
kết quả hướng tới khi hoàn thiện. Các mục tiêu chưa làm được ghi rõ là đề xuất
hoặc điều kiện nghiệm thu; không xem chúng là chức năng đang có.

Cách đọc nhanh:

- Muốn hiểu bài toán và giá trị: đọc mục 1–4, sau đó mục 9 về kết quả cuối cùng.
- Muốn review kỹ thuật: đọc thêm mục 5–8 về dữ liệu, thuật toán và kiến trúc.
- Muốn tiếp nhận dự án: đọc mục 10–12 về giới hạn, cách kiểm chứng và tài liệu liên quan.

## 1. Hiểu dự án trong một phút

Trong một doanh nghiệp có nhiều nhân viên và nhiều dự án, người quản lý cần biết:
**ai có kỹ năng phù hợp, dự án đang thiếu năng lực gì và có thể phân công thêm
cho ai mà không vượt mức phân bổ cho phép?**

SkillGraph tập trung thông tin nhân viên, kỹ năng, yêu cầu dự án và phân công
vào một ứng dụng web. Hệ thống nối các thông tin này để phân tích mức đáp ứng
kỹ năng, đưa ra danh sách ứng viên nội bộ và kiểm tra giới hạn phân bổ khi lưu.
Người quản lý vẫn là người quyết định phân công.

Đầu ra quan trọng không chỉ là danh sách nhân viên, mà là **bức tranh năng lực
của đội dự án và cơ sở để giải thích một quyết định bố trí nhân sự**.

Hiện dự án ở mức **MVP nội bộ chạy cục bộ**: đã có giao diện, API và dữ liệu
lưu thật cho các luồng chính; có kiểm thử và công cụ vận hành cơ bản. Chưa phải
dịch vụ production hoặc sản phẩm SaaS cho nhiều doanh nghiệp độc lập.

## 2. Mục đích và vấn đề doanh nghiệp cần giải quyết

Mục đích chính là hỗ trợ doanh nghiệp sử dụng năng lực sẵn có có căn cứ hơn,
giảm việc phân công dựa hoàn toàn vào trí nhớ hoặc thông tin nằm rải rác.
Những tình huống dưới đây là bài toán mục tiêu, không phải kết quả khảo sát
hay số liệu hiệu quả đã đo ở một doanh nghiệp cụ thể.

| Vấn đề | Cách SkillGraph hỗ trợ | Kết quả doanh nghiệp có thể sử dụng |
| --- | --- | --- |
| Hồ sơ kỹ năng nằm ở nhiều bảng tính hoặc chỉ người quản lý biết | Danh mục nhân viên và kỹ năng thống nhất, có cấp độ và kinh nghiệm | Tra cứu ai có kỹ năng nào thay vì hỏi lần lượt từng người |
| Dự án có người nhưng vẫn thiếu năng lực cần thiết | Đối chiếu kỹ năng yêu cầu với kỹ năng của đội đã được phân công | Phân biệt kỹ năng đã đáp ứng, có nhưng chưa đủ cấp độ và hoàn toàn chưa có |
| Khó tìm người nội bộ để bổ sung cho đội dự án | Gợi ý theo kỹ năng còn thiếu và quan hệ cộng tác trong dữ liệu | Có danh sách ứng viên và thông tin để cân nhắc, không tự động điều chuyển |
| Một người bị nhiều dự án phân công quá mức | Tổng hợp allocation và từ chối thao tác làm tổng vượt 100% | Phát hiện xung đột ngay khi lưu phân công qua ứng dụng |
| Không rõ ai đã sửa thông tin dự án hoặc phân công | Nhật ký dự án ghi người thao tác, thời điểm, dữ liệu trước/sau | Admin có căn cứ truy vết các thay đổi nằm trong phạm vi được ghi |
| Khó nhìn tổng thể nhân sự và dự án | Dashboard tổng hợp dữ liệu từ API | Có điểm bắt đầu để theo dõi và đi sâu vào từng dự án |

Thông tin thiếu hụt cũng có thể hỗ trợ thảo luận về đào tạo hoặc tuyển thêm.
Tuy nhiên, **ứng dụng chưa có quy trình đào tạo, tuyển dụng hoặc phê duyệt ngân
sách**. Chưa có số đo chứng minh tiết kiệm bao nhiêu giờ hay tăng năng suất bao
nhiêu phần trăm; cần thử nghiệm thực tế để xác nhận những lợi ích đó.

## 3. Dành cho ai và phạm vi tổ chức

Đối tượng phù hợp để thử nghiệm là nhóm phát triển phần mềm, đơn vị cung cấp
dịch vụ theo dự án hoặc bộ phận có nhu cầu ghép năng lực nhân viên với công việc.
Đây là định hướng sử dụng, không phải khẳng định đã triển khai tại khách hàng.

### Ba vai trò hiện có

Mỗi tài khoản có một role. Admin cấp tài khoản và quyền; người dùng không chọn
role để tự nâng quyền ở màn hình đăng nhập.

| Quyền | Admin — Quản trị viên | Manager — Quản lý dự án | Viewer — Chỉ xem |
| --- | --- | --- | --- |
| Xem danh mục, hồ sơ, dashboard, phân tích và gợi ý | Có | Có | Có |
| Thêm/sửa/xóa nhân viên, kỹ năng; quản lý kỹ năng của nhân viên | Có | Không | Không |
| Tạo/xóa dự án | Có | Không | Không |
| Sửa dự án, phân công, allocation và yêu cầu kỹ năng | Mọi dự án | Chỉ dự án được giao | Không |
| Xem nhật ký hoạt động dự án | Có | Không | Không |
| Tạo tài khoản, cấp quyền, khóa, đặt lại mật khẩu người khác | Có | Không | Không |
| Đổi mật khẩu cá nhân và đăng xuất | Có | Có | Có |

Các điểm cần hiểu đúng:

- Manager và Viewer hiện đọc được dữ liệu nghiệp vụ chung của không gian,
  không chỉ phòng ban hay dự án của mình. Quyền ghi của Manager mới được giới
  hạn theo dự án; nhật ký và quản trị tài khoản chỉ dành cho Admin.
- Một hồ sơ `Employee` không tự tạo tài khoản đăng nhập. Chưa có role Employee
  tự cập nhật hồ sơ/kỹ năng cá nhân hoặc trang “Công việc của tôi”.
- Không có đăng ký công khai, mật khẩu mặc định hoặc đăng nhập Google. Admin
  đầu tiên được tạo bằng công cụ cài đặt; các tài khoản sau do Admin quản lý.
- FE dùng chung trang đăng nhập và khung giao diện, hiển thị menu/nút theo
  quyền. BE kiểm tra quyền độc lập, kể cả khi gọi API trực tiếp. Chưa có ba
  dashboard chuyên biệt cho từng role.
- Phạm vi hiện tại là **một tổ chức/không gian dùng chung**, chưa có cơ chế
  tách dữ liệu giữa nhiều doanh nghiệp. Không đưa dữ liệu của nhiều khách hàng
  độc lập vào cùng không gian với kỳ vọng chúng đã được cô lập.

Chi tiết và các giới hạn quản trị Admin: [Đăng nhập và phân quyền](authentication.md).

Đã có [công cụ khôi phục Admin cục bộ](admin-recovery.md) khi quên mật khẩu:
người vận hành xác nhận đúng tài khoản, nhập ẩn mật khẩu tạm và thu hồi phiên.
Không phải API công khai, không mở khóa/nâng quyền và không thay thế email reset.

## 4. Một quy trình sử dụng từ đầu đến cuối

1. **Chuẩn bị dữ liệu:** Admin tạo danh mục kỹ năng, hồ sơ nhân viên và khai báo
   kỹ năng của từng người, gồm cấp độ và số năm kinh nghiệm.
2. **Xác định nhu cầu:** Admin tạo dự án, cấp quyền cho Manager nếu cần;
   Admin/Manager phụ trách khai báo kỹ năng yêu cầu, cấp độ tối thiểu và ưu tiên.
3. **Lập đội ban đầu:** Người có quyền phân công nhân viên, ghi vai trò công
   việc và phần trăm allocation cho từng người.
4. **Xem thiếu hụt:** Hệ thống đối chiếu yêu cầu với kỹ năng của đội hiện tại.
5. **Cân nhắc bổ sung:** Người quản lý xem gợi ý ứng viên, kỹ năng phù hợp và
   thông tin cộng tác; kiểm tra thêm khả năng nhận việc trước khi quyết định.
6. **Lưu phân công:** BE kiểm tra quyền và tổng allocation trong transaction.
   Vượt giới hạn thì trả lỗi; phân công hợp lệ được lưu và cập nhật giao diện.
7. **Theo dõi:** Xem lại phân tích/dashboard; Admin xem nhật ký để biết các
   thay đổi dự án, phân công và yêu cầu kỹ năng.

### Ví dụ minh họa

Ví dụ sau dùng tên và số liệu giả định, không phải dữ liệu thật hoặc bài test
vừa được thực thi:

- Dự án **Cổng khách hàng** yêu cầu Python cấp 3 và React cấp 3.
- Đội hiện có Python cấp 4 nhưng React cao nhất chỉ cấp 2. Kết quả là Python
  `COVERED`, React `GAP`; tỷ lệ đáp ứng là 1/2, tức 50%.
- Minh có trạng thái `AVAILABLE`, React cấp 4 và chưa thuộc dự án này, nên có
  thể xuất hiện trong gợi ý. Minh đang được phân bổ 60% ở dự án khác.
- Nếu quản lý phân công thêm 50%, tổng thành 110% và API từ chối. Nếu phân
  công 40%, tổng thành 100% và có thể được lưu khi các điều kiện khác hợp lệ.
- Sau khi lưu, React của đội đạt yêu cầu; với đúng hai yêu cầu trên, tỷ lệ
  đáp ứng tăng lên 100%. Admin đọc được sự kiện tạo phân công.

**100% ở đây chỉ là đủ các loại kỹ năng theo cách tính hiện tại**, không có
nghĩa dự án chắc chắn thành công, đủ số người, đủ ngân sách hoặc kịp tiến độ.

## 5. Các khái niệm dữ liệu cốt lõi

Graph là mô hình lưu các đối tượng và mối quan hệ giữa chúng. Trong SkillGraph,
ba đối tượng nghiệp vụ chính là nhân viên (`Employee`), kỹ năng (`Skill`) và
dự án (`Project`).

| Quan hệ | Ý nghĩa | Thuộc tính nghiệp vụ chính |
| --- | --- | --- |
| `Employee - HAS_SKILL -> Skill` | Nhân viên có kỹ năng | `level`: cấp 1–5; `years_experience`: số năm kinh nghiệm |
| `Employee - WORKS_ON -> Project` | Nhân viên được phân công vào dự án | `role`: vai trò công việc; `allocation`: phần trăm phân bổ |
| `Project - REQUIRES_SKILL -> Skill` | Dự án cần kỹ năng | `min_level`: cấp tối thiểu 1–5; `priority`: MUST/SHOULD/NICE |

`role` trên phân công, ví dụ Backend Developer, **khác** role đăng nhập
Admin/Manager/Viewer. Thông tin phân công không tự cấp quyền quản lý dự án.

Graph còn có `Team`, quan hệ `MEMBER_OF`/`OWNED_BY` và node `AuditEvent`.
Team đã nằm trong mô hình dữ liệu, nhưng chưa có module CRUD Team đầy đủ trên
API/giao diện. AuditEvent lưu lịch sử độc lập để xóa dự án không xóa lịch sử.

Graph phù hợp với cách đặt câu hỏi qua nhiều quan hệ: “ai có kỹ năng còn
thiếu và có quan hệ làm chung với đội này?”. Đây là lựa chọn mô hình hóa của
dự án, **không phải khẳng định SQL không làm được hoặc graph luôn nhanh hơn**.
Hiệu năng cần đo trên dữ liệu và truy vấn thực tế.

## 6. Phân tích và gợi ý thực sự tính như thế nào?

### 6.1. Phân tích thiếu hụt kỹ năng

Với mỗi kỹ năng dự án yêu cầu, hệ thống lấy cấp độ cao nhất của kỹ năng đó
trong những nhân viên đã được phân công vào dự án:

- `COVERED`: có kỹ năng và cấp cao nhất đạt mức yêu cầu.
- `GAP`: có kỹ năng nhưng cấp cao nhất chưa đạt.
- `MISSING`: chưa có nhân viên nào trong đội được ghi nhận có kỹ năng đó.

Tỷ lệ đáp ứng = số yêu cầu `COVERED` / tổng số yêu cầu × 100, làm tròn hai chữ
số thập phân. Chưa khai báo yêu cầu thì giá trị hiện tại là 0%, không tự coi
là đã đáp ứng đầy đủ.

Phép tính chưa cộng trọng số MUST/SHOULD/NICE, chưa yêu cầu nhiều người cùng
đạt một kỹ năng và chưa cân theo allocation. Cấp độ do người quản trị nhập,
không phải kết quả kiểm tra năng lực độc lập do hệ thống thực hiện.

### 6.2. Gợi ý ứng viên nội bộ

Đây là thuật toán **dựa trên quy tắc**, không có mô hình AI/ML tự học:

1. Lấy những yêu cầu đang `GAP` hoặc `MISSING`.
2. Xét người có trạng thái `AVAILABLE`, chưa là thành viên dự án và có ít
   nhất một kỹ năng thiếu đạt cấp độ yêu cầu.
3. Xếp theo số kỹ năng phù hợp giảm dần; tiếp theo là số thành viên hiện tại
   có quan hệ làm chung qua dự án khác; rồi tổng cấp độ kỹ năng phù hợp; cuối
   cùng dùng mã nhân viên để thứ tự ổn định.
4. Trả thông tin kỹ năng khớp và quan hệ cộng tác để quản lý xem xét.

Quan hệ cộng tác được suy ra từ các cạnh `WORKS_ON` đang lưu, không phải hồ sơ
lịch sử đầy đủ có mốc thời gian. Priority và số năm kinh nghiệm chưa trực tiếp
tham gia thứ tự xếp hạng. Nếu mọi yêu cầu đã được đáp ứng, danh sách gợi ý rỗng.

**Gợi ý chưa lọc theo allocation còn lại**. Trạng thái `AVAILABLE` không tự
được đồng bộ từ phần trăm phân bổ; quản lý cần đọc cả hai thông tin. Có tên
trong danh sách không bảo đảm người đó nhận được mức allocation mong muốn.

### 6.3. Chặn phân bổ vượt 100%

Mỗi phân công có allocation nguyên từ 1 đến 100. Khi thêm/sửa phân công, BE
khóa theo nhân viên và kiểm tra tổng ở các dự án khác cộng allocation mới
không vượt 100%, trong cùng transaction ghi dữ liệu.

Quy tắc hiện tại cộng mọi `WORKS_ON`, kể cả tới dự án đã hoàn thành. Chưa xét
ngày bắt đầu/kết thúc, lịch nghỉ phép hay hợp đồng bán thời gian; đây không
phải hệ thống lập lịch theo ngày. Không thể dùng quy tắc ứng dụng để bảo đảm
cho dữ liệu bị sửa trực tiếp ở DB ngoài các API kiểm soát.

## 7. Những phần đã triển khai và giới hạn hiện tại

| Nhóm | Đã có | Giới hạn đáng chú ý |
| --- | --- | --- |
| Danh mục | CRUD nhân viên, kỹ năng, dự án; tìm kiếm, lọc, phân trang; trang chi tiết | Chưa phải HRM đầy đủ; chưa có CRUD Team trên giao diện |
| Quan hệ và phân công | Quản lý ba quan hệ chính; vai trò dự án; allocation; kiểm tra xung đột | Chưa phân bổ theo thời gian hoặc tự tối ưu toàn bộ đội hình |
| Phân tích | Thiếu hụt kỹ năng, tỷ lệ đáp ứng và gợi ý ứng viên | Dựa trên quy tắc và chất lượng dữ liệu đầu vào |
| Dashboard | API tổng hợp có giới hạn, chọn dự án, xem phân tích | Một số selector/hộp thoại còn tải nhiều dữ liệu; chưa có benchmark tải lớn |
| Đăng nhập và quyền | Ba role, phiên đăng nhập, đổi mật khẩu, quản trị tài khoản, CSRF, giới hạn thử sai | Chưa có email tự khôi phục, MFA/SSO; chưa có quyền tự phục vụ của Employee |
| Nhật ký | Thay đổi Project, WORKS_ON và REQUIRES_SKILL; Admin xem trước/sau | Chưa ghi toàn bộ Employee/Skill/HAS_SKILL hoặc thay đổi tài khoản/quyền |
| Giao diện | Tiếng Việt, responsive, trạng thái tải/rỗng/lỗi, xác nhận xóa, hỗ trợ bàn phím | Chưa coi kiểm thử tự động là đánh giá khả năng truy cập đầy đủ |
| Vận hành cơ bản | Liveness, readiness, CLI backup/verify/restore tách biệt | Chưa hoàn tất xác nhận phục hồi graph thật; chưa có lịch backup/offsite tự động |

FE gọi API thật; dữ liệu giả được dùng trong các bài kiểm thử, không dùng để
che lỗi kết nối của ứng dụng. Xóa danh mục còn quan hệ bị từ chối để tránh
tự động xóa dây chuyền ngoài ý muốn.

## 8. Kiến trúc và nơi xử lý từng phần

Luồng thông thường: trình duyệt gọi API FastAPI; backend xác thực, kiểm tra
quyền/nghiệp vụ và truy vấn kho dữ liệu tương ứng. Trình duyệt không kết nối
trực tiếp CognoDB và không giữ mật khẩu DB.

| Thành phần | Trách nhiệm | File/thư mục bắt đầu đọc |
| --- | --- | --- |
| Frontend: React, TypeScript, Vite, TanStack Query | Màn hình, điều hướng, biểu mẫu, gọi API và cache giao diện | [App.tsx](../frontend/src/App.tsx), [pages](../frontend/src/pages), [api.ts](../frontend/src/api.ts), [auth.tsx](../frontend/src/auth.tsx) |
| FastAPI và schema | Tiếp nhận request, validation, response và bảo vệ route | [main.py](../backend/app/main.py), [api](../backend/app/api), [schemas](../backend/app/schemas) |
| Service | Điều phối các quy tắc và tính toán nghiệp vụ | [services](../backend/app/services), [skill_gap_service.py](../backend/app/services/skill_gap_service.py), [candidate_recommendation_service.py](../backend/app/services/candidate_recommendation_service.py) |
| Repository và graph | Truy vấn Cypher, transaction, lưu quan hệ và audit | [repositories](../backend/app/repositories), [graph.py](../backend/app/db/graph.py) |
| SQLite auth | Tài khoản, mật khẩu băm, quyền dự án, phiên và giới hạn đăng nhập | [auth_store.py](../backend/app/repositories/auth_store.py); DB mặc định `backend/data/auth.sqlite3` |
| Cấu hình và công cụ | Đọc environment, tạo schema/Admin, readiness, backup/restore | [config.py](../backend/app/core/config.py), [scripts](../backend/scripts) |

Dữ liệu nghiệp vụ dùng **CognoDB qua Neo4j Python driver/Bolt**. Không suy ra
mọi khả năng hoặc lệnh quản trị của Neo4j đều chạy được trên CognoDB; xem giới
hạn engine đã ghi trong [tài liệu nhật ký](project-activity.md).

SQLite auth và graph là hai kho riêng, không có transaction chung. Vì vậy
backup cần giữ đúng cặp; sao lưu Git hoặc chỉ giữ graph là chưa đủ. Nhật ký
dự án được ghi cùng transaction với thay đổi graph, không ghi hậu kỳ vào SQLite.

Mật khẩu đăng nhập được băm Argon2id; phiên dùng cookie HttpOnly và bảo vệ
CSRF cho thao tác ghi. URI/tài khoản/mật khẩu kết nối đọc qua cấu hình môi
trường ở backend. Không đưa secrets, `.env`, DB auth hoặc backup vào Git/docs.

### Các nhóm API để reviewer tra cứu

| Nhóm | Điểm vào chính |
| --- | --- |
| Danh mục | `/api/employees`, `/api/skills`, `/api/projects` và các route theo ID |
| Quan hệ | `/api/employees/{employee_id}/skills`, `/api/projects/{project_id}/assignments`, `/api/projects/{project_id}/requirements` |
| Phân tích | `GET /api/projects/{project_id}/skill-gap`, `GET /api/projects/{project_id}/recommendations` |
| Tổng quan và lịch sử | `GET /api/dashboard`, `GET /api/activity` |
| Tài khoản | `/api/auth/login`, `/api/auth/me`, `/api/auth/password`, `/api/auth/users` |
| Tình trạng hệ thống | `GET /health`, `GET /health/ready` |

Phương thức HTTP và hợp đồng chi tiết có trong [README dự án](../README.md)
và Swagger `/docs` khi BE chạy. Các API nghiệp vụ yêu cầu đăng nhập; xem được
Swagger không đồng nghĩa được quyền đọc/ghi dữ liệu.

## 9. Khi hoàn thiện, dự án sẽ đạt kết quả gì?

### 9.1. Đích sản phẩm

Đích phù hợp của phiên bản này là **một ứng dụng nội bộ cho một tổ chức, giúp
quản lý năng lực và phân công nhân sự có kiểm soát, có thể bàn giao để người
khác cài đặt, sử dụng và tiếp tục phát triển**.

Khi nghiệm thu phạm vi đó, người sử dụng cần nhận được:

1. **Kho dữ liệu thống nhất:** biết nhân viên nào có kỹ năng gì và đang được
   phân công ở đâu; có người chịu trách nhiệm cập nhật dữ liệu.
2. **Quy trình bố trí nhân sự trọn luồng:** từ khai báo nhu cầu, xem thiếu hụt,
   cân nhắc ứng viên đến lưu phân công và xem lại kết quả.
3. **Phân quyền rõ ràng:** người dùng chỉ thực hiện được các thay đổi hợp lệ
   với role và dự án được giao, không phụ thuộc vào nút trên FE.
4. **Khả năng giải thích và truy vết:** chỉ ra vì sao một ứng viên được gợi ý,
   cùng lịch sử trước/sau cho các thay đổi dự án thuộc phạm vi audit.
5. **Bộ bàn giao kỹ thuật:** mã nguồn BE/FE, cấu hình mẫu không chứa secrets,
   script schema, tài liệu, hướng dẫn chạy và bằng chứng kiểm thử có phạm vi rõ.
6. **Quy trình vận hành có thể kiểm chứng:** biết kiểm tra dependency, sao lưu
   hai kho và phục hồi ở nơi riêng trước khi sử dụng dữ liệu quan trọng.

Đây là kết quả hướng tới, không phải tuyên bố mọi điều kiện vận hành đã đạt.
Các chức năng nghiệp vụ cốt lõi phần lớn đã có; phần còn thiếu phải được nghiệm
thu bằng bằng chứng, không chỉ bằng việc có file mã nguồn.

### 9.2. Tiêu chí kết thúc bản demo/bàn giao kỹ thuật — đề xuất

- [ ] Chạy được từ tài liệu trên môi trường người nhận bàn giao; đăng nhập bằng
  tài khoản test và thực hiện được kịch bản ở mục 4.
- [ ] Kiểm chứng Admin/Manager/Viewer, bao gồm Manager không sửa được dự án
  ngoài quyền và Viewer bị từ chối khi cố gọi API ghi trực tiếp.
- [ ] Kiểm chứng các ca skill-gap, xếp hạng gợi ý và biên allocation 100%/vượt
  100%, kể cả trường hợp ghi đồng thời trong phạm vi test đã chọn.
- [ ] Kiểm chứng lịch sử đúng actor và trước/sau; thao tác bị từ chối không
  trở thành sự kiện thay đổi thành công.
- [ ] Chạy lại bộ kiểm thử phù hợp với phiên bản bàn giao, ghi ngày, môi trường
  và kết quả; FE build được, các đường dẫn tài liệu còn đúng.
- [ ] Hoàn tất phục hồi thử graph + auth ở đích riêng, đối chiếu dữ liệu/quyền
  và giữ báo cáo; nguồn không bị ghi đè.
- [ ] Bàn giao cả giới hạn, việc còn lại và cách xử lý mất quyền Admin; không
  bàn giao mật khẩu hoặc dữ liệu nhạy cảm trong repository.

Các ô trên là **checklist nghiệm thu cho lần bàn giao cuối**, chưa được tự đánh
dấu chỉ dựa vào kết quả kiểm thử lịch sử. Chưa đặt lịch hoặc cam kết thời điểm
hoàn tất trong tài liệu này.

### 9.3. Nếu đưa vào doanh nghiệp dùng thật — điều kiện bổ sung

Đây là giai đoạn tiếp theo cần chốt phạm vi, ngân sách và người vận hành; việc
viết tài liệu này không đồng nghĩa triển khai hoặc đăng ký dịch vụ:

- Môi trường staging có HTTPS để thử nghiệm; cấu hình cookie, origin, proxy
  và secrets đúng trước khi mở môi trường sử dụng thật.
- Quyết định rõ ai được đọc dữ liệu nhân sự. Chính sách đọc chung hiện tại
  phải được tổ chức chấp thuận hoặc thu hẹp bằng tính năng đã kiểm thử.
- Chốt quy trình khôi phục tài khoản quản trị; bổ sung audit tài khoản/quyền
  theo yêu cầu. Email reset, MFA/SSO là lựa chọn cần đánh giá, chưa có sẵn.
- Hoàn tất backup/restore thực tế, nơi lưu tách biệt được bảo vệ, lịch sao lưu,
  giới hạn dung lượng và diễn tập định kỳ. Chốt RPO (mức mất dữ liệu chấp nhận)
  và RTO (thời gian phục hồi mục tiêu), rồi đo thay vì tự cam kết.
- Có giám sát, cảnh báo, kiểm thử tải trên dữ liệu đại diện, đánh giá bảo mật
  và quy trình xử lý sự cố. Chưa có cam kết số người dùng đồng thời hay SLA.

Chỉ coi ứng dụng sẵn sàng vận hành chính thức sau khi đạt các điều kiện đã
thống nhất. Không dùng việc Vite chạy được trên localhost làm bằng chứng production.

## 10. Những gì không nằm trong bản hiện tại

- Không thay thế toàn bộ phần mềm nhân sự: chưa có chấm công, tính lương,
  nghỉ phép theo quy trình, tuyển dụng hoặc đánh giá hiệu suất.
- Không thay thế công cụ quản lý công việc chi tiết: chưa có task/sprint,
  timesheet, lịch làm việc hoặc theo dõi ngân sách dự án.
- Không phải bộ tối ưu đội hình tự động; không tự chuyển nhân viên, tự lập
  kế hoạch đào tạo hoặc bảo đảm đề xuất là phương án tốt nhất.
- Chưa có tự phục vụ cho nhân viên, liên kết tài khoản–Employee, dashboard
  riêng cho từng role hoặc cô lập đa doanh nghiệp.
- Chưa có nhập/xuất Excel trên giao diện, tích hợp HRM/Jira hoặc thông báo email.
- Audit hiện tại không phải nhật ký toàn bộ ứng dụng, không chống sửa tuyệt
  đối ở cấp quản trị DB và không ghi mọi thay đổi do Cypher chạy trực tiếp.

Các hướng như phân bổ theo thời gian, tăng khả năng giải thích gợi ý, MFA/SSO
hay multi-tenant là mở rộng cần thiết kế riêng; không tự đưa tất cả vào điều
kiện hoàn thành của phiên bản này. Xem [Lộ trình tiếp theo](next-steps.md).

## 11. Cách reviewer chạy và đánh giá dự án

### Chuẩn bị môi trường

Đọc [README dự án](../README.md) và [hướng dẫn frontend](frontend.md) để cài
Python/dependency và Node.js theo yêu cầu của repository. Cấu hình kết nối
CognoDB ở backend bằng `.env.example` làm mẫu; người vận hành điền secrets
trực tiếp vào môi trường riêng, không gửi vào tài liệu.

Tạo schema khi cài mới hoặc chạy migration tương ứng khi nâng cấp. Script
`seed.py` chỉ dùng khi chủ động chuẩn bị dữ liệu mẫu ở môi trường test; không
chạy lại trên dữ liệu đang dùng chỉ để mở giao diện. Tạo Admin đầu tiên theo
[tài liệu xác thực](authentication.md); script bootstrap không đặt lại mật
khẩu cho tài khoản đã tồn tại.

Nếu dự án đã cài và cấu hình, mở **hai terminal từ thư mục gốc repository**:

```powershell
# Terminal 1: backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers --reload
```

```powershell
# Terminal 2: frontend
cd frontend
npm.cmd run dev
```

Giữ cả hai terminal chạy. FE: <http://127.0.0.1:5173/>; Swagger BE:
<http://127.0.0.1:8000/docs>. Địa chỉ `127.0.0.1` chỉ máy đang chạy truy cập
trực tiếp được. Instance CognoDB được cấu hình phải hoạt động; SQLite auth
là file do backend sử dụng, không cần khởi động thêm server SQLite.

### Kiểm chứng chức năng và chất lượng

Thực hiện ví dụ mục 4 trên **dữ liệu tổng hợp và môi trường test riêng**, thử
các quyền ở mục 3, sau đó kiểm tra trạng thái rỗng, lỗi kết nối và vượt allocation.
Không chạy kịch bản thêm/sửa/xóa trên dữ liệu thật chỉ để trình diễn.

Các lệnh sau là hướng dẫn kiểm tra, không phải tuyên bố đã chạy trong lần viết
tài liệu này. Cần cài dependency kiểm thử theo hướng dẫn hiện có:

```powershell
# Tại backend: kiểm thử cô lập, không truy cập graph thật
.\.venv\Scripts\python.exe -B -m pytest -m "not integration" -q
.\.venv\Scripts\python.exe -B -m ruff check app tests scripts
```

```powershell
# Tại frontend
npm.cmd run typecheck
npm.cmd run build
npm.cmd test
npm.cmd run test:auth-stack
```

Test FE thông thường dùng API giả lập; `test:auth-stack` dùng FastAPI và SQLite
tạm thật nhưng graph được stub. Không gọi đó là E2E đầy đủ với graph thật.
Các integration test có thể tạo/xóa dữ liệu; đọc tài liệu từng nhóm trước khi
chạy, không chạy toàn bộ `-m integration` trên DB production.

**Bằng chứng đã ghi nhận:** tài liệu readiness/backup ngày 11/09/2026 ghi 170
test backend không integration đạt, 2 integration chỉ đọc đạt và 1 test
FE–FastAPI auth cô lập đạt. Tài liệu nhật ký ghi kết quả API, giao diện và
graph của đợt 10/09/2026. Đây là kết quả theo từng mốc, không cộng dồn thành
một lần chạy mới và không chứng minh bản hiện tại đã qua kiểm thử production.

Trong lần bổ sung tổng quan ngày 12/09/2026 chỉ đối chiếu mã nguồn/tài liệu và
kiểm tra phần tài liệu thay đổi: 52 liên kết file/thư mục nội bộ hợp lệ, kiểm
tra diff không lỗi whitespace, Markdown qua Prettier `--debug-check`. Không
chạy lại ứng dụng/test suite, không migration, không tạo tài khoản hay sửa dữ liệu.

### Đánh giá giá trị doanh nghiệp — đề xuất, chưa đo

Khi thử nghiệm với tổ chức thực tế, nên đo thời gian tìm ứng viên trước/sau,
số xung đột phân công phát hiện được, tỷ lệ hồ sơ kỹ năng được cập nhật và mức
hữu ích của gợi ý theo phản hồi quản lý. Chốt cách đo và tập dữ liệu trước;
không dùng tỷ lệ coverage thay cho KPI năng suất hoặc chất lượng nhân viên.

## 12. Tài liệu đọc tiếp

| Nhu cầu | Tài liệu |
| --- | --- |
| Tìm toàn bộ tài liệu | [Mục lục docs](README.md) |
| Cài đặt và danh sách API | [README dự án](../README.md) |
| Giao diện, cách chạy và test trình duyệt | [Frontend](frontend.md), [UI/UX](ui-redesign.md) |
| Tài khoản, role, session và giới hạn bảo mật | [Đăng nhập và phân quyền](authentication.md) |
| Quên mật khẩu Admin duy nhất | [Công cụ khôi phục Admin cục bộ](admin-recovery.md) |
| API tổng quan và giới hạn hiệu năng | [Dashboard](dashboard.md) |
| Truy vết thay đổi, transaction và giới hạn engine | [Nhật ký dự án](project-activity.md) |
| Kiểm tra ứng dụng/DB sẵn sàng | [Readiness](readiness.md) |
| Bảo vệ dữ liệu và trạng thái phục hồi thử | [Sao lưu/phục hồi](backup-restore.md) |
| Phần đã hoàn thành và các ưu tiên tiếp theo | [Lộ trình](next-steps.md) |

**Thông điệp kết luận:** SkillGraph giúp doanh nghiệp kết nối **con người —
kỹ năng — nhu cầu dự án** để phân công có căn cứ và có kiểm soát. Giá trị của
dự án nằm ở luồng nghiệp vụ, quy tắc và khả năng giải thích; không chỉ ở việc
có một dashboard đẹp hoặc sử dụng graph database.
