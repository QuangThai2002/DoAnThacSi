# Nguồn phương pháp và an toàn cho AI chiến lược gia

## Nguyên tắc tuyên bố kết quả

- Số học như tổng doanh thu, chênh lệch giá và tỷ lệ thay đổi chỉ chính xác theo dữ liệu đầu vào và công thức đã công bố.
- Không gán phần trăm “độ chính xác dự báo” cho kết quả kinh doanh khi chưa có dữ liệu lịch sử, tập kiểm thử độc lập và hiệu chuẩn.
- Khi mức bằng chứng dưới 90%, hệ thống không dùng ngôn ngữ chắc chắn như “sẽ thành công”, “bảo đảm tăng doanh thu” hoặc “nên làm ngay”. Hệ thống chỉ tạo giả thuyết thử nghiệm nhỏ, chỉ số cần đo và điều kiện dừng.
- AI không tự thay đổi giá, ngân sách quảng cáo, tồn kho hay gửi dữ liệu sang Shopee. Người dùng chịu trách nhiệm phê duyệt và thực hiện.

## Nguồn được hiển thị trong ứng dụng

1. National Institute of Standards and Technology (NIST), 2023, *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. DOI: https://doi.org/10.6028/NIST.AI.100-1
2. Kohavi, R. và cộng sự, 2009, *Online Experimentation at Microsoft*. Microsoft Research. https://www.microsoft.com/en-us/research/publication/online-experimentation-at-microsoft/
3. Netflix Technology Blog, 2016, *It’s All A/Bout Testing: The Netflix Experimentation Platform*. https://medium.com/netflix-techblog/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15

Các nguồn Microsoft và Netflix minh họa phương pháp thử nghiệm có kiểm soát; chúng không chứng minh mô hình của dự án sẽ tạo ra kết quả tương tự cho một shop cụ thể.
