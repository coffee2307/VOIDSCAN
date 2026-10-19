# VOIDSCAN — Lưu Access Token một lần trên Windows

VOIDSCAN sử dụng Windows Data Protection API (DPAPI) thay vì lưu token thô vào .env, setx hoặc GitHub.

## Thiết lập lần đầu (một lần cho tài khoản Windows này)

1. Mở F:\VOIDSCAN bằng File Explorer.
2. Nhấp đúp **setup-voidscan-token.bat**.
3. Một **cửa sổ nhập token riêng của Windows** sẽ xuất hiện. Sao chép Meta **User Access Token**, nhấn `Ctrl + V` trong ô nhập hoặc nhấn nút **Dán từ clipboard**. Có thể nhấp chuột phải vào ô nhập → **Dán**. Nội dung được che bằng dấu chấm, không cần dán vào cửa sổ CMD màu đen.
4. Nhấn **Lưu token**. Chỉ sau khi có thông báo thành công thì token mới được lưu mã hóa. Nếu bạn nhấn Hủy, token cũ sẽ giữ nguyên.
5. Dừng server VOIDSCAN cũ một lần nếu nó còn hoạt động, sau đó nhấp đúp **start-voidscan.bat**. Nếu clipboard vẫn giữ đúng token vừa lưu, hộp thoại sẽ xóa nội dung clipboard để giảm nguy cơ vô tình dán lộ token.

Cách khác: PowerShell trong thư mục dự án:

    cd F:\VOIDSCAN
    python manage_token.py set
    python manage_token.py status
    python server.py

Sau khi thiết lập, **không cần nhập lại token** mỗi lần chạy Python. start-voidscan.bat tự kiểm tra server, khởi động server nếu cần và mở http://127.0.0.1:3000.

Nếu chưa có token lưu, start-voidscan.bat sẽ hỏi một lần để lưu ngay trong quá trình khởi động.

## Cơ chế và vị trí lưu

- Mã hóa bằng Windows DPAPI theo **Current User**.
- File được mã hóa tại **%LOCALAPPDATA%\VOIDSCAN\secrets\meta-user-token.dpapi**.
- File nằm ngoài F:\VOIDSCAN và ngoài Git repository; không sử dụng .env plaintext.
- Khi chạy python server.py, mã tự giải mã vào bộ nhớ và thiết lập META_USER_ACCESS_TOKEN chỉ cho tiến trình này.
- Nếu người dùng cố ý đặt META_USER_ACCESS_TOKEN hoặc META_PAGE_ACCESS_TOKEN trong môi trường tiến trình, biến đó được ưu tiên.
- Token không được in ra console, không lưu trong database, và không gửi về trình duyệt qua API.
- DPAPI không ngăn mã độc chạy dưới cùng tài khoản Windows. Không chia sẻ quyền đăng nhập Windows.

## Token không tồn tại vĩnh viễn

Meta có thể thu hồi hoặc token có thể hết hạn. Lưu mã hóa chỉ giúp không phải nhập lại mỗi lần, KHÔNG tự gia hạn token. Nếu danh sách Page trống và VOIDSCAN báo lỗi Meta `190`, subcode `463`, nghĩa là **token đã hết hạn**, không phải server cục bộ bị ngắt kết nối. Khi Meta báo token hết hạn, tạo User Access Token mới cho ứng dụng VOIDSCAN với các quyền Page trước đó rồi chạy:

    python manage_token.py set

Dán token mới, khởi động lại server. Không gửi mã token vào cuộc trò chuyện hoặc lên GitHub.

## Kiểm tra, thay thế và xóa

    python manage_token.py status
    python manage_token.py set
    python manage_token.py delete

Hoặc nhấp đúp remove-voidscan-token.bat để xóa file mã hóa. Xóa cục bộ không tự thu hồi token ở phía Meta.

## Không khuyến nghị

- Không dùng setx META_USER_ACCESS_TOKEN để lưu token dạng văn bản trong Windows Registry.
- Không gửi token trong issue, email, ảnh, ảnh chụp màn hình hoặc .env.example.
- Không mở cổng VOIDSCAN trực tiếp ra Internet khi hệ thống chưa có xác thực.

## Đổi Windows User hoặc đổi máy

File mã hóa gắn với tài khoản Windows hiện tại, không thể mặc nhiên sao chép sang tài khoản hoặc thiết bị khác để giải mã.

## Kiểm thử

    python -m unittest discover -s tests -v
    python tests\smoke_http.py

Unit tests sử dụng token giả trong thư mục tạm, không đọc token Meta thật.
