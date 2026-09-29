# Đưa Eslabong lên Internet miễn phí

Tài liệu này dùng Streamlit Community Cloud cho **bản demo công khai**. Nền tảng này cung cấp URL dạng `https://eslabong.streamlit.app` nếu tên còn trống. Không mua tên miền, không dùng thẻ và không triển khai dữ liệu thật.

## Chuẩn bị

- Mã nguồn đã ở nhánh `main` của repository GitHub `QuangThai2002/DoAnThacSi`.
- File chạy chính là `src/shopee_seller_ai.py`.
- Python cần chọn là `3.14` vì dự án dùng NumPy 2.5.x.
- Không cần nhập secrets cho bản demo. Bản này không kết nối tài khoản Shopee và không cần Ollama chạy trên cloud.

## Các bước bạn tự thực hiện

1. Mở [share.streamlit.io](https://share.streamlit.io/) và đăng nhập bằng GitHub.
2. Kết nối GitHub khi Streamlit Community Cloud yêu cầu. Chỉ tiếp tục nếu không có màn hình yêu cầu thanh toán hay thẻ.
3. Bấm **Create app** và điền:
   - Repository: `QuangThai2002/DoAnThacSi`
   - Branch: `main`
   - File path: `src/shopee_seller_ai.py`
   - Custom subdomain: `eslabong` (nếu còn trống)
4. Trong **Advanced settings**, chọn Python `3.14`; để trống phần Secrets.
5. Bấm **Deploy** và chờ log hoàn tất.

Nếu `eslabong` đã được dùng, hãy chọn một tên phụ như `eslabong-vn`. Streamlit sẽ cung cấp URL công khai có đuôi `.streamlit.app`.

## Kiểm tra sau khi public

- Mở URL bằng cửa sổ ẩn danh.
- Tạo chat **Người mới** và thử một câu hỏi về chính sách.
- Tạo chat **Chủ shop**, mở dữ liệu demo và thử xem thị trường/chiến lược.
- Không tải CSV thật hay thông tin khách hàng lên bản demo công khai.

## Giới hạn rõ ràng

- Đây là bản trình diễn: dữ liệu shop/thị trường là mô phỏng, không kết nối Shopee. Khi không có chỉ mục vector cục bộ trên cloud, Eslabong tự tìm theo từ khóa trong nguồn đã công bố thay vì báo lỗi kỹ thuật.
- Lịch sử chat chỉ thuộc phiên trình duyệt, không phải tài khoản người dùng.
- Không dùng URL này để xử lý dữ liệu kinh doanh thật, API key hoặc thông tin cá nhân.
- Nếu nền tảng yêu cầu trả phí, thẻ thanh toán hoặc nâng cấp gói, hãy dừng lại.
