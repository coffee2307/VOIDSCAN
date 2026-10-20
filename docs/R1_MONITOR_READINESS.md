# VOIDSCAN R1.6 — Monitoring readiness

Trạng thái: Đã phát triển chức năng kiểm tra khả năng giám sát và chất lượng dữ liệu cục bộ; chưa có mô hình nhận diện tài khoản bot được kiểm định ngoài thực tế.

## Baseline trước triển khai

Ngày 20/10/2026: cơ sở dữ liệu có 1 snapshot trên 1 đối tượng, 0 ảnh đang theo dõi. Meta Graph API trả lỗi 190/463: user token hết hạn. Không có đủ thời gian quan sát để ước tính tương tác ảo hay tỷ lệ chính xác.

## Giao diện và lệnh

Vào Theo dõi & lịch sử → Tình trạng nghiên cứu & thu thập để xem tổng snapshot, số ảnh đang theo dõi, số ảnh có chuỗi hợp lệ và số ảnh lỗi. Kết quả được đọc từ SQLite nội bộ, không gửi request đến Meta và không tiết lộ danh tính tài khoản phản ứng.

Lệnh cục bộ:

    cd F:\VOIDSCAN
    python research_cli.py readiness
    python research_cli.py audit

API nội bộ GET /api/research/readiness sử dụng SQLite read-only (mode=ro), không ghi dữ liệu, không gọi mạng.

**Cập nhật bộ lập lịch:** server kiểm tra ảnh đang giám sát sau khi khởi động và mỗi khoảng 30 giây, nhưng chỉ gọi Meta khi ảnh đã đến hạn (mặc định 600 giây kể từ lượt quét thành công hoặc lần thử giám sát gần nhất). Một ảnh vừa quét thủ công sẽ không được đo lại quá sớm. Sau khi khởi động lại server, lịch được xác định từ timestamp SQLite, không phải chờ nguyên một chu kỳ mới. Nếu token hết hạn, các lần thử sau đó chỉ thực hiện khi đến hạn; không truy cập Meta liên tục. Máy và server vẫn phải chạy để thu thập dữ liệu.

Các lỗi từ lần giám sát được phân loại theo kind, ví dụ expired, rate_limit, permission, network, not_found, error. Không lưu token hoặc thông báo lỗi Graph thô.

Hệ thống chỉ coi chuỗi đủ để áp dụng thuật toán thống kê khi đạt ít nhất 7 mốc/6 khoảng liền kề hợp lệ trên cùng ảnh và cùng reaction. Điều kiện này KHÔNG xác nhận rằng chỉ báo bất thường là gian lận.

## Hướng dẫn dùng sau khi Meta token được cập nhật

1. Chạy F:\VOIDSCAN\setup-voidscan-token.bat, lưu token mới qua hộp thoại bảo mật. Không gửi token vào chat hoặc Git.
2. Tải lại http://localhost:3000 (Ctrl+F5) và xác nhận Meta hiển thị có Page.
3. Chọn Page và đúng ảnh dự thi, nhấn Quét, rồi bật Theo dõi định kỳ.
4. Giữ server hoạt động, xem tình trạng trong trang Theo dõi & lịch sử. Chu kỳ mặc định là khoảng 10 phút; Meta có thể giới hạn truy cập và tạo khoảng dữ liệu thiếu.
5. Nếu lỗi giám sát, kiểm tra trạng thái rồi xử lý token/quyền Page, không suy diễn giá trị thiếu thành 0.

## Bảo đảm

- Không tự động bật giám sát cho bất kỳ Page hoặc ảnh nào.
- Không thay đổi hay xóa dữ liệu CSV hoặc SQLite hiện hữu, không tiết lộ token.
- Các chỉ số chất lượng không phải xác suất gian lận. bot_probability_validated=false, automatic_deduction=0.
- Bộ kiểm thử dùng DB riêng và phản hồi Meta giả lập; không chứng minh precision/recall trên cuộc thi thực.

Kiểm thử:

    python -m unittest discover -s tests -q
    python tests\smoke_http.py
    node --check web\app.js

R2 chỉ được khởi động sau khi thu thập nhiều cuộc thi với Ground Truth độc lập và đánh giá tỷ lệ báo động sai.
