# VOIDSCAN Reaction Audit — Chrome Extension 0.1.0

## Tại sao là extension mới?

Đã kiểm tra gói người dùng cung cấp: Reaction Exporter 1.3.0, Chrome Manifest V3. Extension đó có quyền cookies, identity, host permission Facebook trên mọi tab và nhiều đoạn mã minified kết nối tới máy chủ bên thứ ba. VOIDSCAN **không chép lại mã hay cài bản đó**; đây là tiện ích độc lập, viết mới, không đăng ký dịch vụ ConvLead, không token Meta và không phụ thuộc quyền quản trị Page.

Bản đầu chỉ cần: activeTab, scripting, storage và downloads. Không yêu cầu cookies, identity, debugger, webRequest hay host_permissions toàn Facebook. Mã chạy trên trang Facebook **chỉ sau khi người dùng chủ động bấm nút kích hoạt**. Không có request upload hoặc hệ thống máy chủ gửi dữ liệu.

## Cài đặt tại Chrome cá nhân đang đăng nhập

1. Mở Chrome đang dùng, nhập chrome://extensions vào thanh địa chỉ.
2. Bật Developer mode / Chế độ dành cho nhà phát triển.
3. Bấm Load unpacked / Tải tiện ích đã giải nén.
4. Chọn đúng thư mục F:\VOIDSCAN\chrome-extension (thư mục chứa manifest.json).
5. Ghim biểu tượng VOIDSCAN Reaction Audit trên thanh công cụ nếu muốn.

Không cần đăng xuất Facebook, không sử dụng Chrome Playwright riêng bị kẹt Arkose.

## Cách dùng cho cuộc thi THPT Dĩ An

Mở bài đăng:
https://www.facebook.com/tuoitretruongthptdian/posts/pfbid027NL9w2QaKQ3gf7vPztXfczuaaaHi1w6PZUzbSfn8V2w27xMAi6HVJS5LtLumdNkYl

1. Nhấn icon extension > "Mở bảng thu thập trên tab Facebook".
2. Nếu đang ở bài đăng nhiều ảnh, bấm "Lưu các link ảnh đang hiển thị trong bài". Với phần album ẩn sau +33, mở rộng thêm rồi lặp lại. Extension chỉ lấy các anchor ảnh đã thực sự có trong giao diện; không tự suy đoán rằng đã lấy đủ 38.
3. Mở từng ảnh riêng từ bài đăng. Mã ảnh được nhận tự động nếu URL chứa fbid. Nếu không nhận, nhập Photo ID số từ link ảnh. **Không nhập ID bài mẹ thay cho ảnh.**
4. Nhấp vào số reaction của ảnh, trên Facebook chọn một tab loại reaction Like, Love, Care, Haha hoặc Wow.
5. Trong bảng VOIDSCAN chọn đúng loại đang xem rồi bấm "Đọc danh sách đang mở"; khi có nhiều hồ sơ và Facebook cho cuộn, bấm "Cuộn & đọc" tối đa 20 lượt (khoảng cách 1,2 giây/lượt). Có nút dừng. Với hộp thoại bị Facebook giới hạn, việc cuộn không bảo đảm đủ danh sách.
6. Lặp lại cho các tab phản ứng và từng ảnh được phép xem. Dữ liệu được lưu trong chrome.storage.local; cùng một URL trên cùng một ảnh chỉ giữ một bản ghi, nhưng có thể xuất hiện ở nhiều ảnh.
7. Từ popup, bấm "Xuất danh sách CSV", "Xuất tổng hợp CSV", "Xuất JSON", hoặc "Xuất link ảnh CSV". CSV có BOM UTF-8 và mở được bằng Excel. Mỗi file được tạo tại thời điểm bạn chủ động xuất.

Các cột CSV tài khoản: photoId, photoUrl, profileUrl, reaction, capturedAt. Không thu thập tên hiển thị, bạn bè, số điện thoại, email, nội dung trang cá nhân, hồ sơ bị ẩn hoặc danh sách không được phép truy cập.

## Không phải bộ phát hiện bot

- Đây là công cụ ghi nhận URL hồ sơ từ danh sách reaction **đã được Facebook cho hiển thị trong phiên đang đăng nhập**, không phải nguồn dữ liệu chính thức của Facebook.
- Nếu giao diện chỉ tải 120 hồ sơ trong số 800 reaction, kết quả là 120 hồ sơ quan sát được; không được tuyên bố đủ 800.
- Tính điểm Like/Love/Care/Haha/Wow = 1 cho mỗi reaction được quan sát. Không tự thêm điểm chia sẻ, không tính Sad/Angry.
- Không tự kết luận người tham gia là bot từ URL hoặc trang cá nhân trống; muốn xử lý gian lận cần bằng chứng độc lập và Ban tổ chức xác minh.
- Thu thập có giới hạn, không sử dụng API ẩn, không tìm cách vượt CAPTCHA, login wall, giới hạn tải hoặc truy cập riêng tư.
- Các selector có thể thay đổi khi Facebook cập nhật. Nếu hộp thoại reaction không được tìm thấy, cần chỉnh code dựa trên giao diện hiện hành.
- Không tự quét đầy đủ 38 ảnh khi bạn chưa mở và xem từng ảnh. Chức năng chạy thu thập chỉ bắt đầu theo thao tác của bạn.

## Quyền riêng tư và xóa dữ liệu

URL hồ sơ là dữ liệu cá nhân dù hiển thị công khai; phải dùng đúng mục đích kiểm toán đã được cho phép, hạn chế chia sẻ và xóa khi không còn cần thiết. Nút "Xóa dữ liệu trên Chrome" trong popup xóa cả danh sách reaction lẫn danh sách link ảnh đã lưu. Cài lại Chrome/extension có thể làm mất dữ liệu chưa xuất. Tuyệt đối không đăng dữ liệu tài khoản lên GitHub.

Không gửi cookie, token Facebook, mã OTP, credential, nội dung các trang cá nhân hay kết quả bí mật đến dịch vụ bên ngoài.

## Kiểm thử và nguồn mã

Mã viết mới nằm trong chrome-extension/, không dùng file JS/CSS/font của Reaction Exporter 1.3.0.

    node --check chrome-extension/lib.js
    node --check chrome-extension/content.js
    node --check chrome-extension/popup.js
    node chrome-extension/test-lib.cjs

Các bài test chứng minh cú pháp, lọc URL, tránh công thức CSV và quyền extension. Chúng không chứng minh khả năng lấy đủ hồ sơ trên giao diện Facebook thật.
