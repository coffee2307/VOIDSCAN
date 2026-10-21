# VOIDSCAN Reaction Audit — Chrome Extension 0.6.1

## 0.6.1 — Sửa kết quả 0 nghi vấn khi dữ liệu hồ sơ chưa được thu thập

- Khi chỉ nhập CSV reaction 369 URL của một ảnh, 369 hồ sơ vẫn là CHƯA ĐỦ DỮ LIỆU. Không ép phân loại nghi vấn chỉ vì URL, ID số, trùng tên hoặc reaction UNKNOWN.
- Hiện rõ độ bao phủ có dữ liệu bổ sung (x/369), cảnh báo 0% và giải thích rằng đọc CSV không phải kiểm tra trực tiếp tài khoản Facebook.
- Bảng Auto Audit phân biệt URL chưa thử, HTTP không có metadata, HTML thiếu thông tin, lỗi mạng, bị từ chối/rate limit và URL đã có dữ liệu sử dụng được.
- Nút Xuất nhật ký Auto Audit tạo CSV theo URL gồm trạng thái truy xuất và thời điểm thử, phục vụ chẩn đoán tại sao chưa có hồ sơ nào được phân loại. Không lấy thêm dữ liệu cá nhân.
- Tự cập nhật chẩn đoán sau khi nhập CSV, sau các nhóm truy xuất và sau khi tải lại trang.
- Không gán nhãn bot khi nguồn dữ liệu không có tín hiệu cần thiết; độ bao phủ cần được cải thiện bằng nguồn dữ liệu có quyền truy cập hợp lệ, không phải hạ ngưỡng tùy tiện.
- Kiểm thử: node chrome-extension/test-auto-coverage.cjs, python tests/auto_audit_browser_smoke.py.



## 0.6.0 — Auto Audit một lần bấm cho toàn bộ danh sách CSV

- Nhập CSV reaction, bấm **Bắt đầu Auto Audit toàn bộ** một lần và cấp quyền Facebook cho trình duyệt. VOIDSCAN tự thử các URL lần lượt (một luồng, nghỉ 3,5 giây giữa các yêu cầu) bằng HTML metadata công khai không dùng cookie. Không mở hàng trăm tab hoặc yêu cầu bấm từng hồ sơ.
- Ghi tiến độ từng URL vào Chrome storage và hiện tổng số đã thử, metadata dùng được, chưa đủ dữ liệu, đã bỏ qua. **Tạm dừng** có thể hủy yêu cầu đang tải; bấm Bắt đầu để tiếp tục từ vị trí được lưu. Khi tab bị đóng, mở lại sẽ báo tạm dừng; cần nhấn Bắt đầu để tiếp tục.
- Khi có rate_limited, restricted, checkpoint/login hoặc ba lỗi mạng liên tiếp, **dừng**. Không vượt CAPTCHA, không dùng cookie phiên hoặc API nội bộ. Những hồ sơ không trả metadata sẽ giữ nhóm **chưa đủ dữ liệu**, không tự gắn nhãn bot.
- Mặc định chạy tối đa 2.000 URL duy nhất từ CSV; có cơ chế tránh thử lại URL mới thất bại trong vòng 24 giờ, không mất công quét trùng. Kết quả có thể ghép với dữ liệu từ FBFriends hoặc quan sát thủ công trước đây.
- Trang kiểm toán cần được **giữ mở** trong khi Auto Audit chạy; cơ chế này chạy trong trang extension chứ không phải dịch vụ nền vĩnh viễn.
- Không tự động thu gom ngày sinh, giới tính, email, số điện thoại, danh sách bạn bè hoặc nội dung bài đăng của người khác. **Metadata công khai có thể rất hạn chế**, tùy quyền Facebook; tỷ lệ truy xuất không phải tỷ lệ phát hiện bot.
- Kiểm thử: node chrome-extension/test-auto-audit.cjs và python tests/auto_audit_browser_smoke.py.

**Cài bản mới:** chrome://extensions → Reload VOIDSCAN → mở trang kiểm toán → chọn CSV reaction → Bắt đầu Auto Audit toàn bộ.



## 0.5.2 — Rà soát lần lượt trong tab Chrome

- Sau khi nhập CSV reaction: chọn một URL trong bảng kiểm toán → Mở trong tab Chrome → tự xem trang → quay lại VOIDSCAN nhấn Ghi nhận trang đã mở → Hồ sơ tiếp theo. Sử dụng lại một tab để không tạo hàng trăm tab, cho phép dừng tùy ý.
- Chỉ ghi nhận dữ liệu thực sự hiển thị trên trang: avatar, địa điểm tự khai, số bạn chung và ngày bài đăng khi các phần tử bài viết công khai chứa timestamp. Khi không thấy dữ liệu thì để trống; không quét lịch sử bài viết ẩn.
- Số lượng bạn chung và ngày bài đăng gần nhất đã quan sát được đưa vào bảng kiểm toán CSV/Excel. Chỉ khi có nhiều tín hiệu kết hợp (vd. nhiều bạn bè, nhiều mốc bài đăng nhìn thấy đều cũ), mới chuyển nhóm cần rà soát; không xác nhận bot.
- Không tự động thu thập hàng loạt nội dung hồ sơ, ngày sinh, giới tính, địa chỉ liên hệ, email hoặc số điện thoại; đặc biệt vì đối tượng có thể là học sinh.
- Thao tác đọc trang yêu cầu quyền Facebook và một lần nhấn ghi nhận từ người dùng; không vượt chặn đăng nhập hay bảo mật.



## 0.5.1 — Tương thích CSV của FBFriends 1.3.1

- Xác nhận từ mã nguồn FBFriends 1.3.1: đầu ra CSV chứa ID, Name, Profile URL, Avatar URL; các cột mở rộng có Location, Bio, Category (ngoài những trường cá nhân khác).
- VOIDSCAN nhận trực tiếp CSV đúng định dạng đó trong mục **Ghép CSV thông tin hồ sơ**, tự ghép theo Profile URL hoặc ID nếu URL thuộc Facebook và điền tên hiển thị khi reaction thiếu tên.
- Avatar URL trống luôn là "chưa thu thập"; không coi là tài khoản không có avatar. Location chỉ là nơi ở tự khai. Bio/Category chỉ lưu sự hiện diện; không lưu nguyên nội dung và không lưu ngày sinh, giới tính, số điện thoại, email, website.
- Không sao chép, cài đặt hay kích hoạt GraphQL/cookie scraper của extension bên thứ ba. Dữ liệu nằm trong phiên Chrome và chỉ xuất khi người dùng yêu cầu.
- Bản CSV xuất từ danh sách bạn bè của người khác không tự chứng minh "bạn chung" với tài khoản đang đánh giá.
- Test: `node chrome-extension/test-fbfriends-compat.cjs` và regression browser tests.

**Cập nhật:** mở chrome://extensions, bấm Reload tại VOIDSCAN rồi chọn CSV reaction và CSV FBFriends 1.3.1.



## 0.5.0 — Không còn coi dữ liệu chưa thu thập là tài khoản sạch

- **Ba trạng thái:** nghi vấn (có bằng chứng quan sát được), chưa thấy dấu hiệu (đã có dữ liệu để xem xét), chưa đủ dữ liệu (CSV chỉ có URL/reaction).
- **Nhóm kiểm tra dữ liệu độc lập:** reaction UNKNOWN được tính vào "Cần kiểm tra reaction" nhưng không biến thành nhãn bot. Bộ lọc mặc định "Ưu tiên cần xử lý" hiển thị cả nghi vấn thực và lỗi reaction.
- **Đúng ví dụ 190 URL / 1 ảnh / không avatar/địa điểm:** 190 chưa đủ dữ liệu và 12 cần kiểm tra reaction. Đó là 12 lỗi dữ liệu, KHÔNG phải 12 bot. Không gán 190 tài khoản là "không có dấu hiệu".
- **Phân tích hành vi nhiều ảnh:** so sánh tỷ lệ ảnh có tương tác khi đã có ít nhất 4 ảnh trong cùng nhóm; chỉ là cơ sở rà soát, không tự loại phiếu.
- **Metadata công khai tùy chọn:** nút thử 10 URL/lượt chỉ GET HTML công khai và bỏ cookie; cần cấp quyền Facebook bằng thao tác người dùng. Dừng nếu login, rate limit hay checkpoint; chỉ lưu trường xuất hiện rõ ràng, không bảo đảm Facebook sẽ cho phép đọc.
- **Ghi nhận trang người dùng chủ động mở:** tại popup bấm "Ghi nhận hồ sơ Facebook đang mở". Chỉ lấy avatar hoặc thành phố tự khai khi thực sự hiển thị. Dữ liệu lưu tại Chrome, không chụp toàn bộ trang, không lấy danh sách bạn bè, email, số điện thoại hay cookies. Không tự chạy hàng loạt URL Facebook.
- **Đồng bộ kết quả:** tab Kiểm toán đọc những quan sát đã lưu trong Chrome và kết hợp CSV bổ sung; có thể phân loại lại khi nhập thêm bằng chứng. Dĩ An, TP.HCM, Bình Dương áp dụng quy tắc ưu tiên địa phương của người dùng nhưng không xác minh danh tính.
- Chế độ này không bảo đảm xác định bot: việc huấn luyện kiểm định khả năng phát hiện cần dữ liệu ground truth đáng tin cậy. Không suy ra bot chỉ từ reaction UNKNOWN, trùng tên, ID số, hay cột avatar trống.

**Cách nâng cấp:** chrome://extensions → Reload VOIDSCAN → mở lại Facebook và tab Kiểm toán.


## 0.4.4 — Sửa quy tắc dựa trên dữ liệu thật

- Sửa sai phiên 0.4.3: **reaction UNKNOWN** là thiếu nhãn thu thập và **trùng tên hiển thị** là thông tin cần đối chiếu, KHÔNG tự đánh dấu tài khoản nghi vấn/bot.
- Có thể chọn **nhiều CSV reaction** cùng lúc để tổng hợp số Photo ID độc lập và kiểm tra lịch sử tương tác nhiều ảnh. Khi có nhiều ảnh, mặc định phân tích TẤT CẢ ẢNH; vẫn có thể chọn từng ảnh.
- Nút **Chọn CSV hồ sơ** nhận một tệp bổ sung hợp lệ có profileUrl và các cột avatarUrl/hasAvatar, currentCity/location, bio/hasBio, education/hasEducation, work/hasWork, friendsCount, followingCount. Ghép theo URL chuẩn hoặc numeric ID khi có.
- **Ô trống = chưa thu thập**. Chỉ hasAvatar=0 từ nguồn quan sát rõ ràng mới được xem là không thấy avatar. avatarUrl trống trong CSV reaction không phải bằng chứng tài khoản không có avatar.
- Địa điểm tự khai Dĩ An, Bình Dương, HCM được ưu tiên theo quy tắc người dùng; không có nghĩa đã xác thực danh tính, và cảnh báo xung đột reaction vẫn cần kiểm tra.
- Các cột nguồn dữ liệu, avatar, vùng địa điểm và lỗi chất lượng CSV được xuất riêng. Không thu thập cookie, tự truy cập hàng loạt profile hay suy đoán ngày đăng ký tài khoản.
- Trạng thái "nghi vấn" chỉ là tín hiệu quan sát được; KHÔNG phải xác nhận bot và không tự trừ phiếu.

**Cập nhật:** mở chrome://extensions, bấm Reload tại VOIDSCAN rồi mở lại review.html.



## 0.4.3 — Sàng lọc chỉ cần có dấu hiệu

- Khi CSV chứa reaction **UNKNOWN**, đưa hồ sơ vào nhóm **nghi vấn / cần rà soát**, nêu rõ cần xác minh loại reaction trước khi tính điểm. Đây là tín hiệu thiếu dữ liệu, không phải chứng cứ bot.
- Khi nhiều URL khác nhau có **cùng tên hiển thị trong cùng Photo ID**, đánh dấu nghi vấn yếu để người kiểm duyệt đối chiếu. Không gắn cờ chỉ vì một tên xuất hiện ở các Photo ID khác nhau; trùng tên không đồng nghĩa một người điều khiển nhiều tài khoản.
- Bổ sung Tên hiển thị và số ảnh có tên trùng vào CSV/XLSX kiểm toán, kèm lý do rõ ràng trên bảng điều khiển.
- Ngưỡng sàng lọc được mở rộng để ưu tiên rà soát, **không tự loại reaction hay tự xác nhận bot**. Các trường chưa từng thu thập không được coi là thiếu trên hồ sơ Facebook.
- Kiểm thử hồi quy: `node chrome-extension/test-file-audit.cjs`, `python tests/review_browser_smoke.py`.
- Bản Excel được lập từ CSV 190 tài khoản có 17 hồ sơ thuộc diện cần rà soát theo ngưỡng này, không phải 17 bot.

**Cập nhật:** mở `chrome://extensions`, bấm Reload tại VOIDSCAN; sau đó mở lại trang kiểm toán và chọn CSV để sàng lọc với quy tắc mới. Không xóa dữ liệu đã thu thập.

## 0.4.2 — Kiểm toán số phản ứng theo ảnh (offline)

- Bảng **Đối soát số lượng tương tác theo ảnh**: Like, Love, Care, Haha, Wow theo từng Photo ID; mỗi URL tài khoản chỉ được cộng một lần trên mỗi ảnh.
- Báo rõ dòng lặp, xung đột loại reaction và reaction chưa rõ loại. Khi cùng một URL có các bản ghi ở thời điểm khác nhau, ưu tiên bản ghi mới hơn nếu thời điểm hợp lệ; không cộng hai lần.
- Nếu dữ liệu Chrome có số reaction hiển thị từ tab Facebook, đối chiếu số thu thập/số hiển thị. Tỷ lệ này là **độ bao phủ của dữ liệu đã ghi**, không phải độ chính xác phát hiện bot; dữ liệu chụp ở những thời điểm khác nhau có thể lệch.
- Có nút **Xuất CSV đối soát ảnh** để lưu bảng đếm và chất lượng dữ liệu, tách biệt báo cáo sàng lọc hồ sơ.
- Việc lưu trữ và phân loại ở máy cục bộ; không tự mở hàng loạt hồ sơ người khác, không xác nhận bot hoặc tự loại lượt bình chọn. Những tín hiệu hành vi hiện có chỉ giúp **ưu tiên kiểm tra thủ công**.
- Test: `node chrome-extension/test-reaction-integrity.cjs`, `python tests/review_browser_smoke.py`, kiểm thử extension cũ.

**Cập nhật:** Mở `chrome://extensions` và nhấn Reload ở VOIDSCAN. Mở lại tab kiểm toán. Không xóa dữ liệu đã thu thập.

## Hotfix 0.4.1 — Tách từng ảnh và làm rõ phạm vi kiểm toán

- **Nguyên nhân 190 + 110 = 300:** lưu trữ cục bộ được thiết kế lưu nhiều Photo ID (đúng cho tổng hợp toàn cuộc thi), nhưng chỉ số tổng trong bảng nổi và nút CSV mặc định dùng toàn bộ dữ liệu (không đúng với thao tác từng ảnh). Bản mới chỉ hiển thị **reaction của ảnh đang mở**; CSV trên Facebook chỉ xuất Photo ID hiện tại.
- **Popup có dropdown Photo ID:** mặc định xem ảnh cuối đang mở; chọn ảnh 1 hoặc ảnh 2 để đếm và xuất riêng. Chỉ khi tự chọn **Tất cả ảnh** mới cộng dữ liệu toàn cuộc thi. Không xóa lịch sử ảnh cũ.
- **Tab review có dropdown Photo ID:** khi nhập CSV nhiều ảnh hoặc đọc dữ liệu Chrome, mặc định xem riêng một ảnh. Bạn có thể chọn **Tất cả ảnh** để kiểm tra mẫu hành vi giao thoa giữa nhiều ảnh. Xuất CSV/Excel theo phạm vi đang chọn.
- **Chống gán nhầm ảnh khi Facebook đổi trang:** ưu tiên Photo ID trong URL; khi SPA điều hướng, dừng tác vụ quét cũ; kiểm tra ID trước khi lưu, không giữ ID cũ khi URL đã đổi; cảnh báo nếu CSV chứa Photo ID mâu thuẫn với Photo URL.
- **Chỉ số sàng lọc minh bạch:** 0 nghi vấn không đồng nghĩa 0 bot. Phiên bản hiện tại chỉ đọc những trường đã có trong CSV, không thực sự mở URL hồ sơ Facebook. Dashboard hiển thị rõ **Hồ sơ Facebook đã mở để kiểm tra: 0**. Các URL "không có dấu hiệu" chỉ là không có tín hiệu trong dữ liệu CSV, chưa xác minh tài khoản.
- **Chấm điểm không suy đoán thiếu thông tin:** việc CSV thiếu các cột bio/học vấn/quê quán không có nghĩa tài khoản không có các thông tin này. Chỉ đưa tín hiệu "ít thông tin" ra khi CSV có các mục kiểm tra hồ sơ rõ ràng.
- Thêm kiểm thử tự động tái hiện **190 URL ảnh A + 110 URL ảnh B**, popup và CSV từng ảnh và tổng hợp; thử chuyển Facebook SPA giữa hai ảnh; kiểm thử nhập CSV/Excel cùng các kiểm thử cũ.

**Cách cập nhật:** mở `chrome://extensions`, Reload VOIDSCAN rồi tải lại Facebook và review.html. Không nhấn xóa dữ liệu. Dữ liệu cũ có thể đã bị gán sai Photo ID trong những phiên cũ nếu người dùng chuyển ảnh khi đang quét. Những dòng có Photo ID gán sai trong lịch sử mà Photo URL cũng được tạo từ ID sai không thể tự phục hồi; nếu nghi ngờ, hãy đối chiếu ảnh và quét lại.

**Không nhầm lẫn:** `Đã phân tích CSV n/n` chỉ là chạy thuật toán trên dữ liệu đã nhập. Hệ thống không tự mở từng trang cá nhân, không xác minh bio, số bạn bè, nơi ở hay độ thật/giả của tài khoản. Khi chỉ có một ảnh và file chỉ chứa reaction/URL, kết quả 0 tín hiệu nghi vấn là có thể xảy ra dù có bot thực tế.

## Phiên bản 0.4.0

## Mới ở phiên bản 0.4.0 — CSV → sàng lọc → Excel

**Trong popup**: tiếp tục dùng chức năng thu thập reaction và nút Xuất danh sách CSV. Nhấn "Xem hồ sơ cần rà soát" để mở tab `review.html`.

**Trong tab Sàng lọc tương tác**:
1. Kéo thả/chọn tệp `.csv` vừa xuất từ popup (tối đa 15 MB) hoặc nhấn "Lấy dữ liệu từ tiện ích" để đọc thẳng dữ liệu Chrome.
2. Hệ thống tự phân tích từng URL ngay từ dữ liệu đã nhập, hiển thị tiến độ **n/n**, tổng tài khoản, **nghi vấn** (đỏ) và **không có dấu hiệu** (xanh), tên tài khoản vừa xử lý, thanh tiến độ và nút dừng.
3. Danh sách mặc định chỉ hiển thị **nghi vấn**, có tìm URL và mở từng profile bằng link khi muốn kiểm tra thủ công.
4. Nhấn **Xuất CSV kết quả**: có cột chính xác **Trạng thái**, giá trị **nghi vấn** hoặc **không có dấu hiệu**, cùng lý do và số ảnh đã tương tác; giữ nguyên thứ tự xuất hiện đầu tiên trong dữ liệu.
5. Nhấn **Xuất Excel đẹp (.xlsx)**: tiêu đề nền xanh chữ trắng, các ô dữ liệu trắng chữ đen, viền, ô trạng thái đỏ/xanh, hyperlink tới profile Facebook, tự giãn độ rộng cột có giới hạn, tự xuống dòng, cố định dòng đầu và bộ lọc. Excel hoặc Google Sheets sẽ giữ định dạng khi mở/import XLSX. **CSV không thể lưu bất kỳ màu sắc/viền/độ rộng cột nào.**

Quy tắc sàng lọc từ **CSV đã nhập**: cùng một hồ sơ xuất hiện với nhiều loại reaction trên một ảnh (có thể do thay đổi cảm xúc hợp lệ); một URL xuất hiện ở phần lớn nhiều ảnh đã quan sát (có thể là vận động bình chọn hợp lệ); hoặc (chỉ khi CSV cung cấp dữ liệu thật) hồ sơ rất ít trường thông tin có sẵn kèm số lượng bạn bè/theo dõi cao. Những dấu hiệu này chỉ xếp vào nhóm **nghi vấn = cần rà soát**, không kết luận bot và không tự trừ điểm. Không dùng nơi cư trú Dĩ An/TP.HCM để tự đánh giá sạch hoặc gian lận. `không có dấu hiệu` = chưa có tín hiệu trong phần CSV được đọc, KHÔNG có nghĩa đã xác minh tài khoản thật.

**Lưu ý giới hạn:** đây là quy trình **quét dữ liệu tài khoản có trong file**, KHÔNG tự điều hướng qua tất cả các trang cá nhân. Extension không thu thập hàng loạt email, số điện thoại, ngày sinh, giới tính, bạn bè hoặc quê quán từ hồ sơ người dùng, không dùng API ẩn, không vượt CAPTCHA. Một tệp chỉ có reaction + profileUrl không thể kiểm tra được tính thật/giả từ trang cá nhân. CSV UNKNOWN vẫn được nhập nhưng không được tính thành reaction hợp lệ. Dữ liệu được đọc hoàn toàn trong Chrome, không upload đến máy chủ.

**Cập nhật extension:** mở `chrome://extensions`, Reload VOIDSCAN, Ctrl+R tab Facebook và tab review. Không cần gỡ/cài lại, dữ liệu đã lưu ở Chrome không bị xóa.

## Thay đổi của phiên bản 0.3.2

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
    node --check chrome-extension/file-audit.js
    node --check chrome-extension/xlsx-export.js
    node chrome-extension/test-file-audit.cjs
    .\.venv\Scripts\python.exe tests\extension_browser_smoke.py
    .\.venv\Scripts\python.exe tests\review_browser_smoke.py

Extension không có quyền cookies, identity, debugger hoặc quyền host toàn Facebook. Script chỉ hoạt động trên tab được người dùng chủ động kích hoạt; dữ liệu lưu trong chrome.storage.local, không upload tới bên thứ ba.
