# VOIDSCAN — R0: Quy trình nghiên cứu và kiểm định

**Trạng thái:** Hạ tầng nghiên cứu được thiết lập; CHƯA có mô hình bot được kiểm định.
**Mục tiêu:** Đo chất lượng thống kê Like/Love/Haha/... ở từng ảnh/bài của Page có quyền, đánh giá những khoảng tăng bất thường và không nhầm tín hiệu với gian lận đã chứng minh.

## 1. Phân biệt chính xác các mục tiêu

- Reaction count: số đếm tổng hợp từ Meta ở một Photo ID/bài. Null là KHÔNG CÓ DỮ LIỆU, không phải 0.
- Statistical anomaly: khoảng tăng ròng vượt một ngưỡng lịch sử; không phải tài khoản bot hay phiếu buộc phải loại.
- Manipulation event: sự kiện thao túng có bằng chứng độc lập (ngoài chính mô hình).
- Fake/bot actor: cần quan sát và kiểm định ở cấp tài khoản; không thể suy ra mỗi tài khoản từ số đếm tổng hợp.

## 2. Kiểm toán chất lượng R0

Định dạng quan sát: Page ID, Object ID, source, UTC timestamp có timezone, reaction type và nullable count. Không lưu danh tính người thả reaction hoặc token.

Không nối số đếm qua một lần đo lỗi hoặc thiếu. Chỉ so sánh hai mốc LIỀN KỀ của cùng đối tượng, cùng loại reaction; từ 12 giây tới 15 phút ở chu kỳ 10 phút. Snapshot trùng thời điểm, sai timestamp, ngắt lâu, hoặc thiếu count đều không được tạo ra một khoảng tăng hợp lệ.

Cần tối thiểu 7 mốc hợp lệ và 6 khoảng liền kề đủ điều kiện trước khi đánh giá quy tắc bất thường hiện tại. Chất lượng, khoảng nghỉ, phần trăm thiếu và độ mới của nguồn dữ liệu được báo riêng; KHÔNG chuyển thành điểm chắc chắn bot.

Ngưỡng 20 lượt tăng, 4 lượt/phút và median/MAD hiện là heuristic nghiên cứu chưa hiệu chỉnh trên bộ nhãn Facebook thật.

## 3. Ground Truth và nhãn độc lập

Đơn vị gán nhãn là **sự kiện trên một ảnh trong một khung thời gian**; không phải tài khoản cá nhân. Chỉ tiếp nhận hai nhãn được rà soát độc lập: verified_manipulation hoặc verified_legitimate, với mã hồ sơ chứng cứ nội bộ (evidence_ref) cùng nguồn rõ ràng.

Phiếu kiểm định nội bộ cần: case_id, contest_id, event_time UTC, phạm vi sự kiện, chứng cứ có thể đối chiếu, hai người rà soát độc lập với người phát triển mô hình, cách giải quyết bất đồng và ghi nhận hoàn cảnh vận động bình chọn hợp lệ.

KHÔNG lấy cảnh báo của VOIDSCAN làm nhãn đúng; không gán nhãn chỉ vì nhiều reaction cùng lúc; không lưu URL tài khoản cá nhân hoặc dữ liệu riêng tư vào repository. Không tổ chức mua bot để tạo dữ liệu.

## 4. Phương pháp đánh giá độc lập

- Preregister phiên bản thuật toán, ngưỡng, định nghĩa nhãn và chỉ số đánh giá trước khi mở holdout.
- Holdout tách theo cuộc thi, có thứ tự thời gian; không trộn một cuộc thi giữa tập phát triển và kiểm định. Nếu khoảng thời gian hai nhóm chồng nhau, báo không đủ điều kiện.
- Trình bày confusion matrix TP/FP/FN/TN; Precision, Recall, False Positive Rate và khoảng Wilson 95% cho nhãn sự kiện.
- Chỉ hiển thị số liệu mô tả với tối thiểu 5 cuộc thi tổng, 2 cuộc thi holdout, 40 sự kiện holdout, ít nhất 10 sự kiện đã xác minh gian lận và 10 sự kiện hợp lệ. Đây chỉ là ngưỡng tối thiểu để MÔ TẢ, chưa đủ để chứng minh sẵn sàng trừ điểm.
- PR-AUC cần điểm liên tục; calibration/Brier score cần xác suất thực sự và nhãn test độc lập: không báo khi mới chỉ có cờ nhị phân.
- Đánh giá cảnh báo sai trên viral hợp lệ, sự kiện sau lời kêu gọi bình chọn, quảng cáo và nhóm người thật hành động đồng thời.

## 5. Cổng chuyển Phase

**Gate R0:** xác minh quyền API, khả năng đọc ảnh riêng, timestamp và tỷ lệ dữ liệu bị thiếu; không có chỉ số xác suất bot.
**Gate R1:** thu thập dữ liệu đủ lâu trên nhiều ảnh/cuộc thi, kiểm tra false-positive trên hoạt động hợp lệ; thử robust median/MAD và các baseline thống kê khác.
**Gate R2:** bắt buộc có nhãn độc lập, đánh giá tách theo cuộc thi/thời gian và khoảng bất định.
**Gate R3:** kiểm nghiệm tiến cứu trên cuộc thi mới, kiểm tra drift và hiệu chỉnh xác suất, review và quyền khiếu nại.

Không tự động trừ bất kỳ reaction nào dựa trên heuristic.

## 6. Lệnh kiểm tra và tái lập

Dùng trong PowerShell, không cần token:

    cd F:\VOIDSCAN
    python research_cli.py audit
    python -m unittest discover -s tests -v
    python tests\smoke_http.py

Khi đã có file nhãn độc lập bên ngoài Git (JSON schema_version=1, cases[]), chạy:

    python research_cli.py evaluate --input F:\PrivateResearch\verified_events.json

Mỗi case cần case_id, contest_id, event_time, verified_label, ground_truth_source, evidence_ref, flagged_by_frozen_rule. CLI chỉ đánh giá dữ liệu được người kiểm duyệt cung cấp; KHÔNG có khả năng chứng thực nhãn độc lập thay cho hội đồng.

## 7. Nguồn khoa học

- Ikram et al. (2017), Facebook Like Farms: https://arxiv.org/abs/1707.00190 — cần dữ liệu tài khoản; precision nghiên cứu không áp dụng mặc định cho VOIDSCAN.
- Jahn et al. (2023), Coordinated Inauthentic Behavior in Likes (proof of concept): https://arxiv.org/abs/2305.07350 — dữ liệu votes cấp tác nhân và mô phỏng, không phải số tổng hợp Graph API.
- Rogers & Righetti (2025): https://doi.org/10.1177/29768624251369784 — cùng hành động không tự chứng minh lừa dối.
- NIST AI RMF Measure: https://airc.nist.gov/airmf-resources/airmf/5-sec-core/ — kiểm định độc lập, sai số, generalization.

Mọi dữ liệu đầu vào chỉ lấy từ Page người dùng có quyền và nguồn được phép. Chưa có Ground Truth thì không huấn luyện mô hình bot hoặc hiển thị % chắc chắn gian lận.
