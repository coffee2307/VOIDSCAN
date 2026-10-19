# VOIDSCAN 3.0 — Giải thích báo cáo kiểm định

## Sử dụng

Chọn Page → Chọn ảnh hoặc bài đăng có ảnh → Chọn reaction → Quét & phân tích. Nhấn **Bật theo dõi định kỳ** để ghi thêm mốc số liệu mỗi 10 phút khi server hoạt động. Báo cáo có biểu đồ, khoảng thời gian bị gắn cờ và nút xuất CSV.

## Các chỉ số

- Reaction ghi nhận: số lượng của loại cảm xúc được chọn tại lần quan sát hợp lệ gần nhất.
- Lượt nằm trong đợt nghi vấn: số lượt tăng ròng trong các khoảng bị bộ phát hiện biến động gắn cờ. Đây KHÔNG phải số người ảo.
- Tỷ lệ trong khoảng nghi vấn: (lượt tăng trong khoảng bị gắn cờ / tổng reaction quan sát gần nhất) × 100%. KHÔNG phải xác suất bot.
- Độ chắc chắn là bot: **chưa xác định**. Không có dữ liệu định danh người reaction hoặc nhãn bot được kiểm chứng để hiệu chỉnh xác suất.
- Trừ điểm tự động: luôn bằng 0.

## Phương pháp

Cần tối thiểu 7 mốc có giá trị, so sánh tốc độ của mỗi khoảng với ít nhất 5 khoảng trước đó. Dùng median và MAD; chỉ gắn cờ nếu tăng ròng ít nhất 20 lượt, tốc độ ít nhất 4 lượt/phút và vượt ngưỡng bảo thủ so với lịch sử. Đây là thuật toán heuristic chưa được hiệu chuẩn cho từng cuộc thi; kêu gọi bình chọn hợp lệ có thể gây báo động sai.

## Facebook Photo ID

Kiểm thử hai Page do người dùng quản lý cho thấy Graph API từ chối thống kê reaction khi dùng Photo ID đơn lẻ, nhưng trả được Like, Love, Wow, Haha, Angry bằng định danh ghép PageID_PhotoID. VOIDSCAN xác minh Photo ID thuộc Page trước khi dùng cách này, lưu Photo ID riêng để tránh đếm nhầm reaction của bài mẹ. SAD/SORRY có thể bị Meta từ chối và khi đó giá trị là không có dữ liệu, không phải 0.

Tài liệu Meta:
https://developers.facebook.com/docs/graph-api/reference/v26.0/object/reactions
https://developers.facebook.com/docs/graph-api/reference/page/photos/

## Cuộc thi cũ

Một ảnh đã có 1.000 lượt tim trước ngày bắt đầu thu thập không thể được chia chắc chắn thành 200 người thật và 800 bot chỉ từ số hiện tại. Không dựng lại được lịch sử không tồn tại. Nếu thiếu mốc, báo cáo ghi “chưa đủ lịch sử” và không công bố tỷ lệ gian lận.

## Bảo mật và tính công bằng

Đây là phần mềm nghiên cứu cục bộ. Access Token lưu mã hóa DPAPI, không có danh sách người đã reaction; SQLite lưu mốc tổng hợp và nguồn. Ban tổ chức chỉ trừ phiếu dựa trên thể lệ công khai, bằng chứng độc lập, kiểm duyệt và quyền khiếu nại.
