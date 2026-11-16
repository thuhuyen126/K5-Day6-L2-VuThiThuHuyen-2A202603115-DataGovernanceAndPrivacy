# Báo cáo nhóm — Day 06 Data Lab (Field-to-Release PoC)

> Thử thách: **T02 — Raw QC Triage (Phân loại chất lượng dữ liệu thô)**. Trạng thái triển khai hiện tại: **PoC đã chạy; tích hợp human override/audit và chính sách quyết định phát hành vẫn chưa hoàn tất; quyết định hiện tại là HOLD.**

## 00 · Thông tin chung

| Hạng mục | Giá trị |
|---|---|
| Group ID | **G5** |
| Challenge | **T02 · Raw QC Triage** |
| Thành viên (1) | **Vũ Thị Thu Huyền - 2A202603115 - Data Processing & Algorithm (50%)**  |
| Thành viên (2) | **Trần Đức Hòa — 2A202603181 — Quality Analysis & Pipeline Governance (50%)** |
| Git URL | **https://github.com/thuhuyen126/K5-Day6-L2-VuThiThuHuyen-2A202603115-DataGovernanceAndPrivacy.git** |
| Tag `demo-180m` (commit) | **[CẦN ĐIỀN — xác minh bằng `git tag -n`]** |
| Tag `final-24h` (commit) | **[CẦN ĐIỀN — xác minh bằng `git tag -n`]** |
| Deadline (giờ Việt Nam) | **12H** |
| Git SHA của lần chạy được ghi nhận | `80ef1a9` (được ghi trong `out/poc/run_info.json`; không thay thế việc xác minh commit cuối cùng và các tag của repository) |

## 01 · Phát biểu bài toán

- **Những ai bị ảnh hưởng:** Người kiểm tra chất lượng dữ liệu và nhóm sử dụng dữ liệu ảnh ở các bước xử lý thị giác máy tính tiếp theo. Nếu ảnh chất lượng thấp vẫn được giữ lại, kết quả phát hiện hoặc phân tích ở các bước sau có thể không đáng tin cậy. Ngược lại, nếu ảnh có thể sử dụng được nhưng bị gắn cờ nhầm, người kiểm tra sẽ tốn thời gian xử lý cảnh báo sai và có thể yêu cầu chụp lại không cần thiết.
- **Điểm nghẽn cụ thể:** Tập ảnh đầu vào được chụp bằng nhiều camera và trong các điều kiện ánh sáng khác nhau. Một ngưỡng độ sắc nét toàn cục duy nhất có thể xếp hạng những đặc điểm bình thường của từng camera hoặc điều kiện ánh sáng thành ảnh đáng nghi. Việc kiểm tra thủ công toàn bộ ảnh tốn thời gian; vì vậy PoC ưu tiên một số lượng ảnh cố định để con người xem xét.
- **Đầu vào → đầu ra:** Đầu vào gồm thư mục ảnh T02, metadata trong `images.csv` và bản ghi provenance trong `manifest.csv`. Hệ thống trích xuất đặc trưng độ mờ và độ tối, tính điểm nghi ngờ, xếp hạng ảnh, tạo review queue gồm B ảnh đứng đầu và contact sheet chạy offline, sau đó ghi kết quả quyết định. Lần chạy được cung cấp đã xử lý 96 ảnh và xếp hạng 20 ảnh để xem xét.
Nhóm áp dụng cơ chế ra quyết định có sự tham gia của con người (Human-in-the-loop), trong đó kết quả chấm điểm Blur/Dark chỉ được sử dụng để ưu tiên ảnh cần kiểm tra, không được dùng làm căn cứ duy nhất để tự động phát hành dữ liệu.

- GO: Cho phép thông qua batch khi toàn bộ 20 ảnh trong review budget (B=20) đã được con người kiểm tra và chấp thuận (approve), không còn ảnh chờ xử lý hoặc cần escalation, đồng thời kiểm tra provenance và SHA256 manifest thành công. Quy ước approve tương ứng với KEEP (giữ lại ảnh).

- HOLD: Tạm dừng quyết định phát hành khi thiếu bằng chứng provenance, manifest không hợp lệ, chưa hoàn thành review đủ 20 ảnh, review record không khớp với review queue hiện tại, có ảnh được đánh dấu escalate, hoặc chưa xác định được người chịu trách nhiệm phê duyệt. Batch chỉ được tiếp tục xử lý sau khi các vấn đề này được giải quyết.

- REWORK: Yêu cầu xử lý lại hoặc chụp lại những ảnh bị reviewer đánh dấu reject (RECAPTURE). Trạng thái này được áp dụng khi quá trình review đã hoàn tất, không còn trường hợp escalation chưa được giải quyết và có ít nhất một ảnh không đáp ứng yêu cầu chất lượng.

Thứ tự ưu tiên quyết định: HOLD khi còn thiếu bằng chứng hoặc có trường hợp cần escalation; REWORK khi review đã hoàn tất và xác định có ảnh cần chụp lại; GO chỉ khi toàn bộ review queue được chấp thuận và provenance hợp lệ.

Lưu ý triển khai: Đây là chính sách quyết định do nhóm đề xuất cho T02. Phiên bản src/pipeline.py::decide() hiện tại vẫn trả về HOLD với POLICY_NOT_IMPLEMENTED; do đó, các tiêu chí trên chưa được thực thi và xác nhận bằng kết quả chạy pipeline. Nhóm cần hoàn thiện implementation, kiểm thử các trường hợp GO/HOLD/REWORK và xác định người chịu trách nhiệm phê duyệt trước khi tuyên bố chính sách đã hoạt động.
- **Các giả định cần chủ sở hữu xác nhận:** Điểm Blur/Dark là chỉ báo heuristic về mức độ nghi ngờ chất lượng ảnh, không phải nhãn lỗi đã được xác minh. Metadata camera/ánh sáng được giả định là chính xác. Người đánh giá được giả định có thẩm quyền xem xét khả năng quan sát và đề xuất giữ lại, chuyển cấp xử lý hoặc chụp lại. Mọi tuyên bố về tính hợp pháp của việc sử dụng dữ liệu, thời hạn lưu trữ, quyền truy cập hoặc mức độ sẵn sàng phát hành cần được DPO/pháp chế/chủ sở hữu nghiệp vụ xác nhận.

## 02 · Dữ liệu và nguồn gốc dữ liệu

| Split | N | Nguồn / liên kết | Giấy phép | Dữ liệu tổng hợp? |
|---|---:|---|---|---|
| DEV | 56 | Bộ dữ liệu fixture T02; URL nguồn chính xác **../fixtures/images/images.csv** | **../fixtures/images/manifest.csv** | Theo thông tin đã trao đổi trong quá trình làm bài là dữ liệu tổng hợp; cần xác minh bằng manifest/tài liệu nguồn |
| Tổng số ảnh được xử lý trong lần chạy PoC được ghi nhận | 96 | `out/poc/run_info.json` | Metadata lần chạy không nêu | Chỉ riêng `run_info.json` không đủ để xác định |


- **Schema mà phần triển khai yêu cầu:** `images.csv` cần có các cột `image_id`, `path`, `camera_id`, `light` và `split`. Bộ kiểm tra manifest yêu cầu các cột `file_id`, `path`, `source`, `license`, `split`, `group_id` và `sha256`.
- **Ánh xạ class:** Bằng chứng được cung cấp không có taxonomy phân loại lỗi hoặc ánh xạ class sang ID. T02 hiện sử dụng các tín hiệu nghi ngờ chất lượng (`blur` và `dark`), không phải nhãn phân lớp có giám sát. **[Bổ sung ánh xạ thực tế của dataset nếu có.]**
- **Seed và cách chia split:** Seed `42` được ghi trong `out/poc/run_info.json`. Mã sử dụng các bản ghi DEV làm tập tham chiếu cho việc tính điểm Blur. Phương pháp tạo split chính xác (theo scene/group/segment) 
- **Xác minh SHA256 của manifest:** **Chưa thể xác minh từ các tài liệu đã cung cấp.** `src/pipeline.py::load()` gọi `verify_manifest()` nếu `manifest.csv` tồn tại và, khi bật `strict_provenance`, sẽ báo lỗi nếu phát hiện vấn đề. Chưa có manifest thực tế và kết quả chạy riêng lệnh `python -m tools.verify_manifests`. Không được ghi “đã xác minh” cho đến khi chạy lệnh trên thư mục fixture thực tế.

## 03 · Nghiên cứu và thiết kế


- **Luồng dữ liệu:**

  `images.csv + tệp ảnh + manifest.csv`
  → kiểm tra provenance và metadata (`load`)
  → trích xuất đặc trưng ảnh (`process`)
  → tính điểm nghi ngờ Blur/Dark (`score_blur_dark`)
  → xếp hạng top-B và tạo contact sheet offline (`rank`)
  → đọc CSV quyết định của người đánh giá (`review`; hiện mới triển khai một phần)
  → ghi decision JSON và decision log (`decide`; hiện vẫn là HOLD placeholder)
  → tạo artifact báo cáo/đánh giá.

- **Thành phần offline:** Phần triển khai T02 được cung cấp sử dụng các đặc trưng xử lý ảnh và các phép toán dựa trên NumPy/Pandas/Pillow/SciPy, không sử dụng weights của mô hình tải xuống. `src/common/image_ops.py` tính Laplacian variance trên ảnh grayscale và các thống kê độ sáng. `out/poc/run_info.json` ghi `offline: true`. Không có checkpoint mô hình, checksum mô hình hoặc giấy phép mô hình nào được áp dụng/cung cấp cho PoC Blur/Dark này. Phiên bản dependency chính xác cần được chép từ tệp môi trường/requirements 
- **Thiết kế baseline:** Baseline Global Laplacian tính Laplacian variance cho ảnh DEV, đặt ngưỡng toàn cục tại giá trị thấp thứ B trong đó B=20, rồi xếp hạng theo negative Laplacian variance (độ sắc nét càng thấp thì mức độ nghi ngờ càng cao).
- **Thiết kế PoC:** Với mỗi ảnh, trích xuất Laplacian variance (`blur`), tỷ lệ pixel tối (`frac_dark`, pixel grayscale có giá trị < 30) và độ sáng grayscale trung bình. Điểm nghi ngờ Blur được tính bằng `1 - mean(reference_blur_values <= blur_value)`. Thứ tự ưu tiên tập tham chiếu là: cùng camera + cùng điều kiện ánh sáng nếu nhóm đó có ít nhất 10 mẫu; nếu không, dùng cùng camera nếu nhóm có ít nhất 10 mẫu; nếu vẫn không đủ thì dùng toàn bộ mẫu DEV. Điểm nghi ngờ Dark được tính bằng `frac_dark × clip((80 - brightness) / 65, 0, 1)`. Điểm nghi ngờ cuối cùng là `max(blur_score, dark_score)`. Điểm càng cao thì ưu tiên xem xét càng cao; đây không phải xác suất lỗi đã được hiệu chuẩn.
- **Các đánh đổi đã cân nhắc:** PoC bổ sung tập tham chiếu theo camera/ánh sáng và heuristic độ tối cho baseline độ sắc nét toàn cục đơn giản. Cách này có thể giảm ảnh hưởng của khác biệt quang học giữa các camera, nhưng heuristic có thể gắn cờ nhầm các cảnh ban đêm hợp lệ hoặc vùng tiền cảnh tối. PoC chưa triển khai bộ phát hiện glare (lóa) hoặc compression (nén ảnh) chuyên biệt. Phép lấy giá trị lớn nhất đơn giản và dễ giải thích, nhưng không học được tương tác giữa blur và darkness, đồng thời cho phép một đặc trưng chi phối điểm cuối.

## 04 · Baseline so với PoC

- **Baseline:** `src/t02_baseline.py`, xếp hạng bằng Global Laplacian. Bảng so sánh DEV được cung cấp ghi nhận ngưỡng toàn cục `326.281647`; điểm xếp hạng là negative Laplacian variance. 
- **PoC:** `src/t02_blur_dark.py` và `src/t02_scoring.py`, được tích hợp vào `src/pipeline.py`; phương pháp scoring được ghi là `max_blur_dark_v1`. Lần chạy được ghi nhận có Git SHA `80ef1a9` và config hash `c6f7c19c071f`. .
- **Quy trình so sánh:** `reports/table_dev_baseline_vs_poc.md` được cung cấp so sánh hai danh sách top-20 trên DEV, với B=20 và không có nhãn ground truth. Đây không phải phép so sánh độ chính xác trên heldout. Riêng lần chạy end-to-end PoC trong các artifact được cung cấp đã xử lý cả 96 bản ghi; review queue top-20 có 12 bản ghi DEV và 8 bản ghi EVAL. Không được đánh đồng hai phạm vi xếp hạng này.

**Bảng 1 · Baseline so với PoC và bằng chứng hard-slice hiện có**

| Metric (đơn vị) | Baseline | PoC | Chênh lệch / diễn giải |
|---|---:|---:|---|
| Số ảnh trùng trong top-20 DEV (ảnh) | 16 ảnh trùng | 16 ảnh trùng | `16/20`; Jaccard similarity `0.6667` (so sánh mức độ trùng của tập, không phải độ chính xác) |
| Global Laplacian threshold (đơn vị Laplacian variance) | `326.281647` | Không dùng một ngưỡng toàn cục duy nhất | PoC dùng percentile tham chiếu tính từ DEV theo camera/ánh sáng |
| Thành phần cam_A trong top-20 DEV (ảnh) | 8 | 12 | PoC chọn nhiều hơn 4 ảnh cam_A |
| Thành phần cam_B trong top-20 DEV (ảnh) | 12 | 8 | PoC chọn ít hơn 4 ảnh cam_B |
| Tỷ lệ cam_A trong top-20 DEV (%) | 40% | 60% | Tăng 20 điểm phần trăm |
| Tỷ lệ cam_B trong top-20 DEV (%) | 60% | 40% | Giảm 20 điểm phần trăm |
| Defect Recall@20 / Precision@20 | Chưa có | Chưa có | Không có GT hoặc metrics JSON chính thức được cung cấp |
| Số miss / false positive | Chưa có | Chưa có | Không thể tính nếu thiếu GT đáng tin cậy |
| Runtime (giây / 100 ảnh) | Chưa có | `0.774375`* | Lần chạy PoC: `0.7434` giây cho `96` ảnh; chưa có runtime baseline |

\* Phép tính suy ra từ run record được tạo ra: `0.7434 / 96 × 100 = 0.774375` giây trên 100 ảnh. Đây là kết quả quan sát của một lần chạy, không phải benchmark lặp lại hoặc ước lượng latency ổn định về mặt thống kê.

**Thành phần camera/ánh sáng trong top-20 DEV (số lượng lấy từ `reports/table_dev_baseline_vs_poc.md`):**

| Nhóm camera / ánh sáng | Baseline top-20 | PoC top-20 |
|---|---:|---:|
| cam_A / day | 6 | 8 |
| cam_A / dusk | 2 | 4 |
| cam_A / night | 0 | 0 |
| cam_B / day | 8 | 4 |
| cam_B / dusk | 3 | 3 |
| cam_B / night | 1 | 1 |
| **Tổng** | **20** | **20** |

**Diễn giải:** Hai danh sách DEV có 16/20 ảnh trùng nhau, Jaccard similarity là `0.6667`. Thành phần camera khác nhau: baseline chọn 12 ảnh cam_B và 8 ảnh cam_A, trong khi PoC chọn 8 ảnh cam_B và 12 ảnh cam_A. Đây là bằng chứng cho thấy thành phần ranking đã thay đổi, không phải bằng chứng PoC phát hiện được nhiều lỗi hơn. Bảng so sánh DEV ghi rõ không sử dụng ground-truth labels.

## 05 · Quy trình đánh giá

- **Metric chính:** Chưa được khai báo trong `reports/metric_contract.md`; tệp này vẫn là template chưa điền. Evaluator T02 được thiết kế để tính ranking metrics khi có GT, nhưng không có `reports/metrics_baseline.json` hoặc `reports/metrics_poc.json` được tạo ra trong các tệp đã cung cấp. Vì vậy, báo cáo không đưa ra giá trị metric chính thức, TP/FP/FN, tử số, mẫu số hoặc điểm heldout chính thức.
- **Giới hạn về GT/đánh giá:** `src/evaluate.py` dừng và báo lỗi nếu không có tệp GT, đồng thời nêu GT không được phân phối trong repository sinh viên. Điểm chính thức dự kiến được giảng viên chạy bằng private overlay. Artifact phía sinh viên không đủ để đưa ra tuyên bố về độ chính xác trên EVAL.
- **Ngưỡng và budget:** Budget xếp hạng được ghi nhận là B=20. Tham số `min_group_size` của Blur reference mặc định là 10 trong `src/t02_scoring.py`; không thể kiểm tra cấu hình override thực tế vì chưa có `configs/lab.yaml`. Ngưỡng baseline DEV là `326.281647`. Thời điểm chốt metric contract và người chịu trách nhiệm **[CẦN ĐIỀN]**.
- **Độ bất định:** Không có khoảng tin cậy, bootstrap hoặc ước lượng phương sai nào được cung cấp. Vì dataset nhỏ, chỉ báo cáo độ bất định nếu được tính từ output đánh giá chính thức; không tự tạo khoảng tin cậy.
- **Lệnh đánh giá:** Source mô tả giao diện evaluator. Lệnh chính thức cần đường dẫn GT do giảng viên cung cấp. Mẫu lệnh:

  `python -m src.evaluate --track t02 --gt <INSTRUCTOR_GT_PATH> --pred <PREDICTION_CSV> --run-name <baseline_or_poc> --out reports/metrics_<run>.json`

  Không chạy với nhãn tự đoán hoặc nhãn giả.
- **Vấn đề quan trọng của protocol:** Review queue `out/poc/review_queue.csv` trong lần chạy end-to-end được ghi nhận tạo từ toàn bộ 96 ảnh. Khi ghép với `out/poc/ranked_review.csv`, top-20 có 12 bản ghi DEV và 8 bản ghi EVAL. Vì vậy queue được ghi nhận không phải ranking heldout chỉ gồm EVAL. Bảng so sánh DEV riêng trong `table_dev_baseline_vs_poc.md` chỉ dùng DEV. Một phép đánh giá heldout hợp lệ cần xếp hạng/đánh giá tập ứng viên heldout theo protocol của giảng viên và không được tinh chỉnh trên EVAL.

## 06 · Các lát cắt kết quả

| Lát cắt / bằng chứng | N | Baseline | PoC | Ghi chú |
|---|---:|---:|---:|---|
| Tập ứng viên ranking DEV | 56 | 56 ảnh được chấm điểm | 56 ảnh được chấm điểm | Xác nhận từ ba tệp `out/dev/*.csv` |
| cam_A trong top-20 DEV | 20 ảnh trong ranking | 8 | 12 | Chỉ phản ánh thành phần, không phải defect recall |
| cam_B trong top-20 DEV | 20 ảnh trong ranking | 12 | 8 | Chỉ phản ánh thành phần, không phải defect recall |
| Số ảnh EVAL trong top-20 của pipeline được ghi nhận | Queue gồm 20 ảnh | Chưa có | 8 | Suy ra bằng cách ghép `review_queue.csv` với `ranked_review.csv`; queue chứa cả DEV/EVAL |
| cam_B / night trong top-20 DEV | 1 | 1 | 1 | `img_18_3` xuất hiện trong cả hai danh sách top-20 |

- **Failure/caution case 1 — nguy cơ cảnh báo nhầm cảnh ban đêm:** Tệp review ghi nhận `img_18_0`, `img_18_1` và `img_18_2` có quyết định `reject`, với ghi chú rằng các đối tượng quan trọng, phương tiện hoặc người đi bộ vẫn nhìn thấy được. Điều này cho thấy không nên xem riêng hình ảnh ban đêm/tối là lỗi đã được xác nhận. `img_18_3` được đánh dấu `escalate` vì ảnh mờ mạnh khiến không thể đánh giá riêng mức độ tối.
- **Failure/caution case 2 — độ tối nghiêm trọng và khả năng quan sát:** `img_08_3` (cam_A/dusk) và `img_12_3` (cam_B/dusk) được đánh dấu `approve`; ghi chú lần lượt là “Severe darkness; objects difficult to inspect” và “Very dark scene; visibility is limited.” Ngữ nghĩa của `approve` (chấp thuận nghi ngờ, chấp thuận chụp lại hay chấp thuận một hành động của reviewer) chưa được định nghĩa trong phần triển khai/báo cáo được cung cấp. **[Nhóm cần định nghĩa ý nghĩa của nhãn trước khi diễn giải thành KEEP/RECAPTURE.]**
- **Khoảng trống đã biết khác — glare:** `reports/table_dev_baseline_vs_poc.md` nêu rõ PoC Blur/Dark hiện tại không có bộ phát hiện glare cục bộ chuyên biệt. Vì vậy, hiện tượng lóa cục bộ vẫn là dạng lỗi chưa được xử lý và cần bổ sung đặc trưng hoặc kiểm tra thủ công.
- **Latency / compute:** Runtime PoC được ghi nhận là `0.7434` giây cho `96` ảnh (`0.774375` giây trên 100 ảnh, tính suy ra). Metadata máy: Python `3.14.7`; nền tảng `Windows-10-10.0.19045-SP0`; chuỗi processor `AMD64 Family 23 Model 17 Stepping 0, AuthenticAMD`. Không có tên model CPU cụ thể, benchmark bộ nhớ, thời gian chạy lặp lại hoặc runtime baseline trong tài liệu đã nhận.

## 07 · Con người và quyết định

- **Review queue:** `out/poc/review_queue.csv`; budget B=20. `src/common/review.py::make_review_queue()` sắp xếp theo score giảm dần và chọn `budget` bản ghi đầu tiên. `out/poc/contact_sheet.html` là artifact trực quan để review offline.
- **Bằng chứng review:** `out/poc/review_queue_reviewed.csv` chứa 10 bản ghi đã được reviewer điền, tất cả ghi nhận người đánh giá là `Vu Thi Thu Huyen`: 2 `approve`, 5 `escalate` và 3 `reject`. Các ghi chú cung cấp bằng chứng định tính về độ tối, khả năng quan sát trong cảnh ban đêm và sự mơ hồ giữa blur/dark.
- **Sai khác giữa queue và review — cần công khai:** `out/poc/review_queue.csv` hiện tại có timestamp 11:45 trong ZIP được cung cấp, trong khi reviewed CSV có timestamp 09:38. Chỉ 5 trong 10 `item_id` đã review trùng với top-20 queue hiện tại. Vì vậy, không thể mô tả reviewed CSV là kết quả review của chính xác queue hiện tại nếu chưa có xác nhận bổ sung. **[Giải thích tệp này thuộc lần chạy trước, là tập con được chọn thủ công hay thuộc phiên bản queue khác.]**
- **Override và audit:** `src/common/review.py` cung cấp `load_review_decisions()`, `apply_overrides()` và helper `AuditLog` dạng append-only. Tuy nhiên, `src/pipeline.py::review()` hiện đọc CSV review và ghi nhận `n_reviewed`, sau đó vẫn còn TODO; hàm không gọi `apply_overrides()` và không ghi các sự kiện reviewer override. ZIP output được cung cấp cũng không có `out/poc/audit_log.jsonl`. Vì vậy, source code có các helper audit có thể tái sử dụng, nhưng lần chạy pipeline được cung cấp chưa chứng minh được quy trình override/audit hoàn chỉnh.
- **Decision policy:** `out/poc/decision.json` ghi `status: HOLD`, `canonical: HOLD`, `reason_code: POLICY_NOT_IMPLEMENTED`, reason “Decision policy not implemented yet”, owner `TODO: tên người ký duyệt (role)`, evidence rỗng và metrics rỗng. `out/poc/decision_log.csv` chứa hai bản ghi HOLD với cùng reason code. `src/pipeline.py::decide()` trả về quyết định HOLD placeholder này một cách vô điều kiện.
- **Khi nào HOLD / REWORK:** Phần triển khai hiện tại chưa mã hóa tiêu chí vận hành. Cho đến khi nhóm xác định ngưỡng, ngữ nghĩa quyết định của reviewer, người chịu trách nhiệm, yêu cầu bằng chứng và quy tắc escalation, trạng thái an toàn được ghi nhận là HOLD. Quy tắc REWORK/chụp lại cần do chủ sở hữu nghiệp vụ xác định; không được suy ra chỉ từ điểm heuristic cao.

## 08 · Tái lập và kiểm thử

**Mẫu lệnh chạy đã được ghi nhận** (tệp cấu hình thực tế chưa có trong ZIP; cần xác nhận nội dung trước khi tuyên bố lệnh này tái lập đầy đủ):

```bash
python -m src.main --input fixtures/t02_raw_qc --config configs/lab.yaml --output out/ --offline --seed 42
```

**Mẫu lệnh đánh giá** (cần GT do giảng viên cung cấp; các artifact đã nhận không chứa GT):

```bash
python -m src.evaluate --track t02 --gt <INSTRUCTOR_GT_PATH> --pred <PREDICTION_CSV> --run-name <baseline_or_poc> --out reports/metrics_<run>.json
```

**Lệnh kiểm thử:**

```bash
pytest -q
```

- **Kết quả full test suite mới nhất:** **[CẦN ĐIỀN — không có output terminal `pytest -q` mới trong các ZIP đã cung cấp.]** Ghi chú trước đây của dự án cho biết 27 test Blur/Dark đã pass và một test pipeline-template từng lỗi do khác biệt exit code kỳ vọng. Đây là thông tin lịch sử, không phải kết quả full test suite hiện tại đã được xác minh.
- **Môi trường theo `out/poc/run_info.json`:** Python `3.14.7`; Windows 10 build `19045`; chuỗi processor `AMD64 Family 23 Model 17 Stepping 0, AuthenticAMD`; seed `42`; chế độ offline `true`.
- **Metadata lần chạy được ghi nhận:** status `0`; runtime `0.7434` giây; `n_processed=96`; `n_items=96`; `n_ranked=20`; `review_budget=20`; `n_reviewed=10`; scoring method `max_blur_dark_v1`; Git SHA `80ef1a9`; config hash `c6f7c19c071f`.
- **Hạn chế về tái lập:** `configs/lab.yaml`, các tệp dependency, fixtures và test files không nằm trong ZIP đã cung cấp. Run record chứng minh lần chạy đã hoàn tất trong môi trường ban đầu, nhưng chỉ các artifact hiện có chưa đủ để tái lập từ đầu trong một môi trường sạch.

## 09 · Hạn chế và đạo đức

- **Pháp lý / PII / giấy phép:** Bằng chứng đã cung cấp chưa xác định được giấy phép hoặc nguồn dataset. Cần xác nhận từ `manifest.csv` và tài liệu dataset. Không tuyên bố tuân thủ GDPR hoặc pháp luật Việt Nam chỉ dựa trên checklist tự động. Khi phù hợp, cần DPO/pháp chế xác nhận cơ sở pháp lý, giới hạn mục đích, thời hạn lưu trữ, kiểm soát truy cập, bảo mật và quy trình xử lý yêu cầu của chủ thể dữ liệu. Các artifact đã cung cấp không cho thấy việc sử dụng dữ liệu cá nhân thực, nhưng ảnh gốc không được gửi nên chưa thể kiểm tra độc lập.
- **Hạn chế kỹ thuật:** Blur được xấp xỉ bằng Laplacian variance trên ảnh grayscale; darkness sử dụng tỷ lệ pixel grayscale dưới 30 và độ sáng trung bình. Đây là các heuristic và có thể bị ảnh hưởng bởi nội dung cảnh, điều kiện ánh sáng, phơi sáng, đặc điểm camera và bố cục ảnh. PoC không có bộ phát hiện glare hoặc compression chuyên biệt. So sánh ranking hiện có là bằng chứng DEV không nhãn, không phải bằng chứng về độ chính xác.
- **Cảnh báo sai và lỗi bị bỏ sót:** Cảnh ban đêm và vùng tiền cảnh tối có thể bị gắn cờ dù các đối tượng quan trọng vẫn nhìn thấy được. Ngược lại, glare cục bộ, lỗi nén hoặc những dạng lỗi không được đặc trưng Blur/Dark mô tả có thể bị bỏ sót. Ghi chú reviewer hiện có minh họa một số trường hợp nhưng không định lượng tỷ lệ false positive hoặc false negative trên toàn bộ dữ liệu.
- **Khi quy mô tăng 10 lần:** Với kích thước ảnh cố định, khối lượng trích xuất đặc trưng dự kiến tăng gần tuyến tính theo số ảnh, nhưng chưa có benchmark ở quy mô 10 lần. Cần đo throughput, bộ nhớ, tính công bằng của queue giữa các nhóm camera/ánh sáng và năng lực review trước khi đưa ra kết luận về khả năng mở rộng.
- **Trạng thái governance:** Quyết định hiện tại là HOLD vì decision policy chưa được triển khai. Có bằng chứng review thủ công ở mức một phần, nhưng quyết định reviewer chưa được tích hợp thành override và chưa có audit log được cung cấp. Nhóm không được tuyên bố pipeline đã sẵn sàng phát hành.
- **Kế hoạch cải tiến:** (1) xác minh và lưu giữ bằng chứng manifest/nguồn/giấy phép; (2) tách việc tinh chỉnh trên DEV khỏi ranking/đánh giá EVAL; (3) định nghĩa và chốt metric contract; (4) bổ sung đặc trưng glare/compression hoặc quy trình kiểm tra thủ công rõ ràng; (5) định nghĩa ngữ nghĩa quyết định của reviewer; (6) triển khai áp dụng override và audit event dạng append-only; (7) triển khai tiêu chí GO/HOLD/REWORK cùng người chịu trách nhiệm và bằng chứng; (8) chạy lại toàn bộ test và đánh giá chính thức; (9) benchmark nhiều lần và báo cáo độ bất định.

## 10 · Đóng góp của thành viên

**Bảng 2 · Bằng chứng đóng góp cá nhân**

> Công việc của nhóm trước đây được chia cho hai thành viên. Hãy điền tên, Git author/email, commit SHA và trạng thái trình bày dựa trên lịch sử repository thực tế. Tệp `reports/team_contributions.csv` được cung cấp vẫn là template năm thành viên chưa điền, không cung cấp bằng chứng quy kết tác giả.

| Học viên | Git author / email | Module / vai trò | Commit SHA / bằng chứng diff | Đã trình bày? |
|---|---|---|---|---|
| Thành viên 1 — **[TÊN BẠN]** | **[CẦN ĐIỀN]** | Data loading; đặc trưng Blur/Dark; tích hợp scoring; baseline/evaluation; thuật toán và phương pháp luận báo cáo | **[CẦN ĐIỀN từ `git shortlog -sne --all` và `git log`]** | **[CẦN ĐIỀN]** |
| Thành viên 2 — **[TÊN ĐỒNG ĐỘI]** | **[CẦN ĐIỀN]** | Kiểm tra provenance; công việc Glare/Compression; human review; audit/decision policy; các phần governance/báo cáo | **[CẦN ĐIỀN từ `git shortlog -sne --all` và `git log`]** | **[CẦN ĐIỀN]** |

Công việc chung: tích hợp, tinh chỉnh trên DEV, kiểm tra các trường hợp lỗi, so sánh baseline với PoC và rà soát output cuối cùng. Cần xác minh đóng góp của từng người bằng commit và diff thực tế; không phân công module chỉ dựa trên kế hoạch ban đầu nếu Git evidence không chứng minh được.

## 11 · Tài liệu tham khảo

| URL | Ngày truy cập | Ý nghĩa đối với phần triển khai |
|---|---|---|


---

## Bảng 3 · Checklist trước khi nộp

- [ ] Thêm URL repository và các tag cuối cùng vào README; xác minh tên tag và commit mà từng tag trỏ tới.
- [ ] Xác nhận input mẫu không chứa PII thật, hoặc mô tả quy trình xử lý đã được phê duyệt.
- [ ] Cung cấp một lệnh chạy, một lệnh đánh giá chính thức và một lệnh kiểm thử đã được xác minh.
- [ ] Bổ sung `metrics_baseline.json`, `metrics_poc.json` và `table1_baseline_vs_poc.md` được sinh từ quy trình đánh giá chính thức, nếu có.
- [ ] Có ít nhất một failure case, bằng chứng reviewer và decision log; giải thích sự khác biệt/không đồng nhất của review queue.
- [ ] Xác minh nguồn, giấy phép, SHA256 manifest, data split, seed, môi trường offline và GT/evaluation N.
- [ ] Hoàn thiện và chốt `reports/metric_contract.md` với metric chính, chiều tốt hơn (higher/lower), denominator, budget, slices, phương pháp ước lượng độ bất định, timestamp và owner.
- [ ] Triển khai override/audit của reviewer hoặc ghi rõ là chưa hoàn thành; không tuyên bố tính năng đã hoạt động.
- [ ] Triển khai decision policy hoặc giữ trạng thái HOLD và ghi rõ policy/owner còn thiếu.
- [ ] Mỗi thành viên thực tế có ít nhất một commit có đóng góp thực chất và được ghi chính xác trong Bảng 2.

---

## Danh mục bằng chứng và các nội dung chưa được giải quyết

**Đã nhận và kiểm tra:** `src.zip`, `reports.zip`, `out.zip` và `out(1).zip`. Hai ZIP output chứa cùng các tệp output được liệt kê.

**Chưa được cung cấp trong các ZIP:** `fixtures/t02_raw_qc/images.csv`, `manifest.csv`, các tệp ảnh thực tế, `configs/lab.yaml`, `tools/verify_manifests.py`, thư mục tests, dependency/lock files, Git history/tags/remote, các tệp metrics `metrics_baseline.json`, `metrics_poc.json`, `table1_baseline_vs_poc.md` được sinh theo quy trình đánh giá chính thức và tệp audit JSONL.

**Các vấn đề quan trọng cần xử lý trước khi nộp:**

1. Xác nhận nguồn dataset, giấy phép, trạng thái synthetic, số lượng split, cách nhóm scene và việc xác minh SHA256 từ metadata fixture thực tế.
2. Giải thích vì sao reviewed CSV gồm 10 ảnh có timestamp sớm hơn queue 20 ảnh hiện tại và chỉ trùng 5/10 ID được review.
3. Định nghĩa ý nghĩa của `approve`, `reject` và `escalate` trong T02, cũng như chúng có tương ứng với KEEP, RECAPTURE hay escalation hay không.
4. Quyết định review queue chính thức phải được tạo từ DEV, EVAL hay một tập đánh giá riêng. Top-20 của pipeline được ghi nhận đang trộn 12 ảnh DEV và 8 ảnh EVAL.
5. Cung cấp metrics đánh giá chính thức hoặc ghi rõ nhóm sinh viên không có kết quả hiệu năng heldout chính thức.
6. Điền thông tin hai thành viên, Git attribution, tags, URL repository, tài liệu tham khảo và kết quả test mới nhất.
