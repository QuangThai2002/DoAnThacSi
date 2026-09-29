# Đóng gói và chạy miễn phí

Tài liệu này chỉ hướng dẫn chạy trên máy cá nhân hoặc máy chủ bạn đã có. Không có bước nào tự đăng ký cloud, mua tên miền hoặc phát sinh thanh toán.

## Chạy bằng Docker

Image dùng Python 3.14 để tương thích với NumPy 2.5.x đang khóa trong dự án.
Image chỉ cài PyTorch bản CPU vì ứng dụng không dùng GPU; lần tải đầu vẫn mất thời gian do có các thư viện AI, nhưng không tải thêm bộ NVIDIA/CUDA dung lượng lớn.

Trong thư mục dự án:

```powershell
docker compose build
docker compose up -d
```

Mở `http://localhost:8501`. Nếu muốn dùng tên miễn phí dễ nhớ là `http://lockera.test:8501`, mở PowerShell **với quyền Quản trị viên** và chạy một lần:

```powershell
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "`n127.0.0.1 lockera.test"
ipconfig /flushdns
```

`lockera.test` chỉ trỏ về chính máy bạn, không cần mua tên miền và không truy cập được từ Internet. Cấu hình mặc định chỉ nhận truy cập từ chính máy này, không mở cho thiết bị khác trong mạng. Kiểm tra trạng thái container:

```powershell
docker compose ps
docker compose logs -f shopee-ai
```

Dừng ứng dụng:

```powershell
docker compose down
```

Nếu muốn dùng Ollama chạy trên máy Windows, Compose đã trỏ sẵn tới `host.docker.internal`. Ollama là tùy chọn; các đường trả lời demo và chính sách cục bộ vẫn chạy được khi không có Ollama.

## Giới hạn an toàn hiện tại

- Ứng dụng chạy dưới tài khoản không phải `root` trong container.
- File CSV bị giới hạn 10 MB và chỉ nhận đúng cấu trúc đã kiểm tra.
- Chi tiết lỗi nội bộ bị ẩn trên giao diện.
- Chỉ nên mở cổng `8501` trong mạng nội bộ khi chưa có lớp đăng nhập và HTTPS.
- Chat và dữ liệu hiện vẫn thuộc phiên trình duyệt; volume `data/local_store` chỉ là chỗ dành sẵn, chưa thay thế cơ sở dữ liệu nhiều người dùng.

## Trước khi mở ra Internet

Chưa nên public trực tiếp bản này. Cần bổ sung một lớp đăng nhập/phân quyền, cơ sở dữ liệu lâu dài, HTTPS qua reverse proxy, giới hạn tốc độ và sao lưu. Những bước đó có thể phát sinh chi phí tùy máy chủ; không thực hiện tự động trong dự án này.
