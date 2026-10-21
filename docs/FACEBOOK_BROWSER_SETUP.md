# VOIDSCAN — Chrome + Playwright cho Facebook

Trạng thái: Đã cài Playwright 1.64 vào .venv, mở thành công Chrome thật trên máy Windows, hồ sơ trình duyệt tách biệt. TinyFish không cần thiết.

## Mở và đăng nhập
- Từ Explorer, chạy F:\VOIDSCAN\setup-voidscan-facebook.bat.
- Chrome riêng sẽ mở bài dự thi THPT Dĩ An. Bạn tự đăng nhập và xác thực hai bước nếu Facebook yêu cầu.
- Để trình duyệt mở và thông báo lại trong chat khi bạn đã hoàn tất đăng nhập. Không gửi mật khẩu, mã OTP hoặc cookie.

Profile Chrome (cookie được Chrome quản lý cục bộ): %LOCALAPPDATA%\VOIDSCAN\facebook-browser\chrome-profile.

Cảnh báo: không sao chép/chia sẻ thư mục profile, không đẩy lên GitHub, không sử dụng chung thư mục Chrome cá nhân. Nếu muốn chấm dứt phiên đăng nhập, đăng xuất Facebook trong Chrome; đóng Chrome chỉ tắt chương trình nhưng có thể giữ phiên đăng nhập cục bộ.

## Điều khiển cục bộ
Lệnh kiểm tra (chỉ xác nhận browser window đã mở, không xác minh đăng nhập Facebook):

    cd F:\VOIDSCAN
    .\.venv\Scripts\python.exe facebook_browser.py status

Chuyển trang Facebook trong Chrome đang mở:

    .\.venv\Scripts\python.exe facebook_browser.py open --url "https://www.facebook.com/"

Dừng trình duyệt riêng:

    .\.venv\Scripts\python.exe facebook_browser.py stop

Nếu chạy lại báo profile bị khóa, hãy đóng phiên VOIDSCAN Chrome trước rồi thử lại. Trong khi hoạt động, Playwright giao tiếp qua internal pipe; không mở cổng Remote Debugging 9222. Các lệnh điều hướng chỉ cho phép HTTPS Facebook, không mở URL ngoài danh sách cho phép.

## Phạm vi
Đây chỉ là thiết lập phiên trình duyệt. Chưa tự động quét đủ 38 ảnh hoặc phân loại người dùng Facebook. Sau khi đăng nhập cần thử đọc số tổng reaction và share mà Facebook thực sự cho phép xem ở từng ảnh. Không vượt CAPTCHA hay hạn chế quyền truy cập, không lấy mật khẩu, cookie, tài khoản cá nhân hoặc kết luận bot từ hồ sơ trống.

Meta Graph API và phiên Chrome đăng nhập là hai nguồn quyền truy cập khác nhau. Đăng nhập Chrome không cấp thêm quyền API đối với Page của trường.

## Kiểm định
Chạy python -m unittest tests.test_facebook_browser_setup -v. Các bài test chỉ đảm bảo whitelist URL và profile tách biệt; không đánh giá khả năng phát hiện bot.
