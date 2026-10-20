# VOIDSCAN — R2 Ground Truth Review Gate

**Trạng thái:** Đã xây dựng cơ chế kiểm duyệt dữ liệu, CHƯA xác minh được tài khoản bot hoặc độ chính xác của mô hình trên cuộc thi thật.

## Vì sao cần ít nhất hai người đánh giá?

VOIDSCAN đang sử dụng các phương pháp phát hiện tốc độ tăng reaction bất thường. Một bài được người nổi tiếng chia sẻ có thể tạo tín hiệu giống dịch vụ bán tương tác. Nếu lấy cảnh báo thống kê làm nhãn "gian lận", rồi đánh giá chính mô hình bằng nhãn đó, độ chính xác sẽ bị thổi phồng.

Cổng R2 yêu cầu hai người kiểm duyệt **độc lập với quá trình xây mô hình và không được xem cờ dự đoán trước khi ghi nhãn**. Mỗi người phải ghi kết luận về **một sự kiện** dựa trên tài liệu và bằng chứng ngoài VOIDSCAN. Các nhãn hợp lệ của từng người: manipulation, legitimate, inconclusive.

Nếu cả hai thống nhất "manipulation" hoặc "legitimate", sự kiện đủ điều kiện được chuyển vào file phục vụ kiểm thử thuật toán. Nếu bất đồng hoặc chưa thể kết luận, có thể dùng người thứ ba độc lập; nếu vẫn không xác định thì loại khỏi tập kiểm định và báo lý do.

**Quan trọng:** Tool chỉ kiểm tra cấu trúc của mã người duyệt và lời tự khai rằng họ không xem dự đoán. Nó KHÔNG thể chứng minh hai người thực sự độc lập, bằng chứng là thật hay nhãn là đúng. Tổ nghiên cứu phải thực hiện kiểm duyệt và lưu bằng chứng bên ngoài repository.

## Cấu trúc JSON

File được giữ ngoài Git, ví dụ F:\PrivateResearch\blinded_reviews.json:

    {
      "schema_version": 1,
      "cases": [{
        "case_id": "CASE_001",
        "contest_id": "CONTEST_001",
        "event_time": "2026-10-20T01:10:00+00:00",
        "reaction_type": "LOVE",
        "observations": [
          {"observed_at":"2026-10-20T01:00:00+00:00","counts":{"LOVE":50}},
          {"observed_at":"2026-10-20T01:10:00+00:00","counts":{"LOVE":60}}
        ],
        "reviews": [
          {
            "reviewer_id":"REVIEWER_A",
            "verdict":"legitimate",
            "ground_truth_source":"independent_documentation",
            "evidence_ref":"INTERNAL-REF-A",
            "blinded_to_model_flag":true
          },
          {
            "reviewer_id":"REVIEWER_B",
            "verdict":"legitimate",
            "ground_truth_source":"independent_documentation",
            "evidence_ref":"INTERNAL-REF-B",
            "blinded_to_model_flag":true
          }
        ]
      }]
    }

Đây là ví dụ minh họa, không phải hồ sơ đã được kiểm định. Chỉ có hai mốc nên chưa đủ để đánh giá thuật toán R1; cần ít nhất năm khoảng hợp lệ trước khoảng cần xét. Thời điểm sự kiện phải trùng mốc cuối, không dùng mốc tương lai.

Với bất đồng, thêm trường "adjudication" tương tự một phần tử "reviews" nhưng do người thứ ba có reviewer_id khác. Người thứ ba cũng có thể kết luận inconclusive và khi đó sự kiện bị loại.

**Nguồn bằng chứng được chấp nhận về mặt định dạng:** platform_enforcement, consented_audit, independent_documentation, contest_evidence_review. Đây chỉ là trường mô tả; phần mềm không thể xác thực tên nguồn được khai báo.

## Các lệnh chạy

    cd F:\VOIDSCAN
    python research_cli.py adjudicate --input "F:\PrivateResearch\blinded_reviews.json" --output "F:\PrivateResearch\replay_cases.json"
    python research_cli.py replay --input "F:\PrivateResearch\replay_cases.json"

Cổng adjudicate sẽ ghi một file mới, KHÔNG ghi đè file cũ hoặc tự động tải lên GitHub. Đầu ra giữ case_id, contest_id, thời điểm, reaction type, counts, nhãn đã thống nhất, mã chứng cứ nội bộ và danh sách mã chứng cứ của cả hai người duyệt (cùng mã người giải quyết bất đồng nếu có); loại bỏ reviewer ID và phản hồi cá nhân. Mã hồ sơ này là các tham chiếu nội bộ, không phải bằng chứng đã được phần mềm xác minh. Hồ sơ bất đồng chưa giải quyết không được đưa vào replay.

Báo cáo review_audit thống kê số hồ sơ tiếp nhận, số được chấp nhận và số bị loại. Trình replay tiếp tục loại những sự kiện thiếu mốc quan sát hợp lệ và áp dụng kiểm định holdout theo cuộc thi, có thứ tự thời gian.

## Giới hạn và quyền riêng tư

Không nhập Page ID thật, Photo ID thật, thông tin tài khoản phản ứng, username, URL Facebook cá nhân hoặc token. Chỉ dùng mã pseudonym trong từng gói nghiên cứu được chủ sở hữu cho phép. Nguồn gốc chứng cứ, danh tính người kiểm duyệt và tài liệu kèm theo phải được bảo vệ, quản lý tách biệt ngoài Git. Dữ liệu tổng hợp có timestamp cũng có thể nhạy cảm và tái nhận diện sự kiện; không công khai bundle khi chưa đánh giá rủi ro.

Hai người đồng thuận không đồng nghĩa cả hai đúng. Một khi có đủ nhãn độc lập mới được tính Precision/Recall/FPR theo sự kiện; chưa có cơ sở xác định "số tài khoản bot" hoặc xác suất bot.

**R2 vẫn chưa đạt nghiệm thu trên dữ liệu thật:** tại thời điểm xây dựng, VOIDSCAN có 1 snapshot, 0 ảnh đang giám sát và token Meta hết hạn.
