# VOIDSCAN Reaction Audit — Chrome Extension 0.3.2

## Sửa lỗi Facebook đã xác nhận ở v0.3.2

- Đã đọc cấu trúc của danh sách reaction trong phiên Facebook được người dùng kết nối: liên kết avatar có nhãn `đã thích` hoặc `đã cảm thấy Yêu thích`. Bản cũ không đọc nhãn này nên lưu 190 URL `UNKNOWN`, dù đã xuất CSV được.
- Bản 0.3.2 **đọc loại cảm xúc từ aria-label của URL hồ sơ** ngay trên tab `Tất cả`, không bắt buộc chuyển tab khi Facebook đã công khai nhãn reaction ở từng dòng. Hỗ trợ Like/Love/Care/Haha/Wow và không tính Sad/Angry.
- Facebook thường tạo hai liên kết (avatar và tên) trỏ cùng một hồ sơ. Bộ thu thập nay gộp theo URL, giữ reaction từ liên kết avatar, không để liên kết tên ghi đè thành `UNKNOWN`.
- Khi quét lại ảnh, bản ghi `UNKNOWN` cũ của cùng một URL sẽ tự chuyển thành reaction chính xác nếu nhãn có sẵn; dữ liệu đã lưu không bị xóa. Không tự đoán loại cho URL không quan sát được.
- Kiểm thử hồi quy `tests/extension_profile_aria_smoke.py` mô phỏng cấu trúc nhãn thực tế, kiểm thử `UNKNOWN` và quét 5 tab đều đạt. Tính năng vẫn có thể phụ thuộc cập nhật UI Facebook.
- **Cập nhật:** trong `chrome://extensions` nhấn Reload VOIDSCAN, tải lại tab ảnh Facebook và chạy **Quét tự động cả 5 loại cảm xúc** để nâng dữ liệu cũ. Không bấm Xóa dữ liệu.

## Sửa lỗi không nhận diện cảm xúc ở v0.3.1

- Khi Facebook mở tab **Tất cả** và không hiển thị icon reaction cho mỗi người, bản cũ có thể báo `0 hồ sơ mới; hàng nghìn chưa xác định reaction` do đếm lặp qua các lần cuộn. Bản 0.3.1 **giữ lại URL duy nhất** với giá trị `reaction=UNKNOWN`, không tính như một reaction có điểm, và có chỉ số `Chưa rõ loại` riêng.
- Khi chuyển sang tab riêng Like/Love/Care/Haha/Wow và xác minh được loại, hồ sơ `UNKNOWN` được nâng thành phản ứng tương ứng, không ghi trùng một URL trong cùng ảnh.
- Bộ nhận diện tab hỗ trợ thêm các thuộc tính `aria-pressed`, `aria-current`, `data-state`, các nút trong tablist và các nhãn có tiền tố `Reaction:`/`Cảm xúc:`. Có nút **Kiểm tra nhận diện** trong bảng nổi, chỉ hiển thị số tab và số URL, không in danh sách tài khoản.
- Nút CSV xuất cả phản ứng đã phân loại và URL chưa rõ loại, những dòng chưa rõ mang nhãn `UNKNOWN` để không nhầm với điểm đã xác minh. Bảng tổng hợp điểm chỉ tính 5 loại hợp lệ.
- Test tái hiện lỗi danh sách Tất cả đạt; test nâng 3 URL chưa phân loại lên LIKE và test tự quét 5 tab đều đạt trên Chrome mô phỏng.

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
5. Kiểm tra phiên bản hiển thị 0.3.2. Nếu Facebook chỉ hiển thị tab Tất cả, hãy ưu tiên Quét tự động cả 5 loại cảm xúc hoặc bấm Kiểm tra nhận diện. Nhấn Xem hồ sơ cần rà soát để mở bảng lọc tự động.

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
