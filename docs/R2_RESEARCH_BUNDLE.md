# VOIDSCAN — R2 data readiness: Aggregate Evidence Bundle

**Trạng thái:** Bộ xuất dữ liệu nghiên cứu, chưa có mô hình bot đã được kiểm định trên cuộc thi thật.

## Xuất thủ công

Trong VOIDSCAN, vào Theo dõi & lịch sử → Xuất gói dữ liệu nghiên cứu R2. Tệp JSON chỉ được tạo từ các snapshot đã lưu trên máy, trả cho trình duyệt, không được tự động tải lên GitHub hay máy chủ khác.

Nội dung: mã Page/đối tượng ẩn danh bằng HMAC-SHA256 với khóa ngẫu nhiên mới cho mỗi lần xuất; các mốc UTC; số reaction Like, Love, Wow, Haha, Sad, Angry; nguồn số liệu và bản kiểm toán chất lượng.

Không xuất Page ID/Photo ID gốc, tên, URL, token, người phản ứng, ghi chú chiến dịch hay nhãn bot. Mã ẩn danh KHÔNG ổn định qua các lần xuất. Giữ file riêng tư vì lịch sử hoạt động của cuộc thi vẫn có thể nhạy cảm.

## Tính toàn vẹn và giới hạn

SHA-256 trên JSON chuẩn hóa giúp kiểm tra một payload có bị sửa hay không. Đây không phải chữ ký số và KHÔNG chứng minh dữ liệu thực sự xuất phát từ Meta. Người thay đổi payload cũng có thể tạo checksum mới.

Tối đa 25 đối tượng có mốc gần đây nhất, 3.000 snapshot gần nhất theo thời gian cho mỗi đối tượng. Các trường null là thiếu dữ liệu chứ không phải 0. Mốc bị hỏng không được xuất và được đếm riêng; đối tượng hoặc bản ghi vượt giới hạn cũng được đếm. Không có nhãn thao túng hoặc xác suất bot đã được kiểm định.

## Lệnh dòng lệnh (không cần token)

    cd F:\VOIDSCAN
    python research_cli.py bundle --output "F:\PrivateResearch\new-bundle.json"
    python research_cli.py verify-bundle --input "F:\PrivateResearch\new-bundle.json"

Thư mục PrivateResearch phải tồn tại trước. Tool không ghi đè file có sẵn và không xuất vào thư mục mã nguồn có thể bị Git theo dõi. Có thể xuất vào thư mục data được Git ignore hoặc đường dẫn khác ngoài repository.

## Cổng R2

Chỉ có thể đánh giá Precision, Recall, False Positive Rate và calibration khi có đủ lịch sử nhiều cuộc thi và nhãn sự kiện được kiểm chứng độc lập. Gói JSON là dữ liệu quan sát, chưa phải bằng chứng gian lận và không được dùng để trừ điểm tự động.

Mã nguồn: research_bundle.py. Kiểm thử: tests/test_research_bundle.py.
