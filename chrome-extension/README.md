# VOIDSCAN Reaction Audit — Chrome Extension 0.3.0

## Bổ sung ở phiên bản 0.3.0

- Trang **Sàng lọc tương tác** ngay trong extension. Nhấn nút Xem hồ sơ cần rà soát trong popup: hệ thống tự nhóm URL hồ sơ, chỉ hiển thị các hồ sơ cần đối chiếu theo dữ liệu reaction đã ghi.
- Sàng lọc tự động dựa trên dấu hiệu **dữ liệu bị ghi nhiều loại reaction trên cùng ảnh** hoặc **một URL xuất hiện trên tỷ lệ rất lớn các ảnh được quan sát**. Các tín hiệu này có thể là hoạt động hợp lệ, tuyệt đối không được coi là bằng chứng bot.
- Danh sách chỉ cần rà soát mặc định; có tìm kiếm, lọc, mở một URL khi bạn thực sự cần, lưu quyết định người duyệt và ghi chú ngắn.
- CSV nghi vấn riêng và CSV đầy đủ, kèm Photo ID, các loại reaction, lý do đánh dấu, trạng thái kiểm tra. Không tự gán nhãn bot hoặc trừ điểm.
- Số hồ sơ ưu tiên rà soát và tổng URL đọc được được hiển thị ngay trong popup. Không cần xem từng profile để chạy thuật toán.
- Không thu thập ngày sinh, email, số điện thoại, giới tính, danh sách bạn bè hoặc tự động duyệt từng trang cá nhân. Nơi ở Dĩ An/HCM không được dùng để tự xác nhận tài khoản thật.

## Các thay đổi so với bản 0.1.0

- **Quét tự động 5 loại cảm xúc** trên ảnh đang mở: extension cố gắng chọn các tab Like, Love, Care, Haha, Wow và tự cuộn danh sách của từng loại. Không cần chọn loại và bấm đọc lại sau từng lần cuộn.
- **Tự dừng khi danh sách hết dữ liệu** hoặc khi đạt giới hạn 180 lượt cuộn/tab và 10 phút/lần quét. Có nút dừng bằng tay.
- **Bảng nổi kéo thả** bằng thanh tiêu đề; nút Home, CSV, thu nhỏ, đóng và thanh tiến độ. Popup Chrome gắn vào thanh công cụ không thể kéo; bảng nổi trên trang Facebook mới có thể kéo.
- Trường dữ liệu bổ sung: User ID, Username, Display Name, Reaction Type, Avatar URL, Friendship Status, Subscribe Status, Mutual Friends Number, Profile URL, Photo ID, Photo URL, thời điểm ghi nhận.
- Chỉ đọc những trường hiển thị rõ trong dòng reaction trên Facebook. Trường bị ẩn để trống, không truy cập trang cá nhân để tìm hoặc suy đoán.
- Popup có Home, xuất CSV chi tiết và tổng hợp, xuất JSON và liên kết ảnh. Giữ tương thích các bản ghi 0.1, không tự xóa dữ liệu cũ.

## Cập nhật extension đã cài

1. Trong Chrome cá nhân đã đăng nhập Facebook, mở trang chrome://extensions.
2. Bật Developer Mode nếu cần.
3. Tìm VOIDSCAN Reaction Audit và nhấn Reload. Không cần gỡ cài đặt hay đăng nhập Facebook lần nữa.
4. Tải lại tab Facebook bằng Ctrl+R, bấm icon extension rồi chọn mở bảng điều khiển.
5. Kiểm tra phiên bản hiển thị 0.3.0. Nhấn Xem hồ sơ cần rà soát để mở bảng lọc tự động.

Mã nguồn extension ở F:\VOIDSCAN\chrome-extension.

## Hướng dẫn cho cuộc thi 38 ảnh

1. Mở bài đăng và chọn ảnh riêng cần kiểm toán.
2. Nhấp vào **số reaction** của ảnh để mở danh sách người đã tương tác. Đây là thao tác chủ động, không tự bấm nút thả Like hoặc phản ứng của chính người dùng.
3. Trong bảng nổi VOIDSCAN, bấm **Quét tự động cả 5 loại cảm xúc**. Extension sẽ tự chuyển các tab mà Facebook hiển thị và tự cuộn. Có thể dừng bất kỳ lúc nào.
4. Khi hoàn thành, mở ảnh tiếp theo và quét tương tự. **Phiên bản này chưa tự điều hướng hết 38 ảnh từ bài đăng mẹ.** Nút lưu link ảnh chỉ lưu các ảnh đã hiển thị trong giao diện album.
5. Xuất CSV bằng nút CSV trên thanh tiêu đề bảng nổi hoặc Xuất danh sách CSV trong popup. Tổng hợp CSV phân biệt số hồ sơ quan sát với số reaction hiển thị (nếu đọc được).

## Giới hạn

- Không đồng nhất số hồ sơ thu được với tổng số lượt reaction. Facebook có thể chỉ hiển thị một phần danh sách, còn thiếu nhiều người.
- Không cần quyền quản trị Page hoặc token Meta. Không dùng API ẩn, không vượt CAPTCHA, tường đăng nhập hay hạn chế quyền Facebook.
- Trạng thái quan hệ, avatar, tên và số bạn chung không phải tiêu chí kết luận bot. Không tự gán nhãn bot, không trừ điểm.
- URL, tên, hình đại diện là dữ liệu cá nhân; chỉ sử dụng trong kiểm toán nội bộ phù hợp, không tải công khai lên GitHub.
- Facebook thường thay đổi cấu trúc DOM. Bộ kiểm thử là giao diện mô phỏng, không bảo đảm selector hoạt động với mọi phiên Facebook thật.

## Bài kiểm thử

    node chrome-extension/test-lib.cjs
    node --check chrome-extension/lib.js
    node --check chrome-extension/content.js
    node --check chrome-extension/popup.js
    node chrome-extension/test-review.cjs
    node --check chrome-extension/review-lib.js
    node --check chrome-extension/review.js
    .\.venv\Scripts\python.exe tests\extension_browser_smoke.py
    .\.venv\Scripts\python.exe tests\review_browser_smoke.py

Extension không có quyền cookies, identity, debugger hoặc quyền host toàn Facebook. Script chỉ hoạt động trên tab được người dùng chủ động kích hoạt; dữ liệu lưu trong chrome.storage.local, không upload tới bên thứ ba.
