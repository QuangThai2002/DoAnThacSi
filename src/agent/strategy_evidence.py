"""Citable methodological sources and safety policy for strategy suggestions."""

from __future__ import annotations


STRATEGY_EVIDENCE = (
    {
        "title": "AI Risk Management Framework (AI RMF 1.0)",
        "author": "National Institute of Standards and Technology (NIST)",
        "year": "2023",
        "use": "Cơ sở cho minh bạch, giám sát của con người, quản trị rủi ro và ghi nhận giới hạn của AI.",
        "url": "https://doi.org/10.6028/NIST.AI.100-1",
        "adoption": "Khung hướng dẫn công khai; không phải bằng chứng rằng một doanh nghiệp cụ thể dùng mô hình của dự án.",
    },
    {
        "title": "Online Experimentation at Microsoft",
        "author": "Kohavi và cộng sự, Microsoft Research",
        "year": "2009",
        "use": "Cơ sở dùng thử nghiệm đối chứng để kiểm tra tác động của một thay đổi thay vì tin vào dự đoán ban đầu.",
        "url": "https://www.microsoft.com/en-us/research/publication/online-experimentation-at-microsoft/",
        "adoption": "Microsoft mô tả việc xây dựng nền tảng thí nghiệm có đối chứng cho các dịch vụ trực tuyến.",
    },
    {
        "title": "It’s All A/Bout Testing: The Netflix Experimentation Platform",
        "author": "Netflix Technology Blog",
        "year": "2016",
        "use": "Ví dụ thực tế về đưa thay đổi vào thử nghiệm nhỏ trước khi áp dụng rộng.",
        "url": "https://medium.com/netflix-techblog/its-all-a-bout-testing-the-netflix-experimentation-platform-4e1ca458c15",
        "adoption": "Netflix mô tả nền tảng A/B testing nội bộ; đây là ví dụ phương pháp, không phải lời xác nhận cho kết quả bán hàng Shopee.",
    },
)


DEMO_EVIDENCE_SCORE = 45
DEMO_EVIDENCE_LABEL = "Mô phỏng — cần kiểm chứng bằng thử nghiệm thật"


def safe_language_policy(evidence_score: int) -> str:
    """Choose language that does not overstate uncalibrated business outcomes."""
    if evidence_score >= 90:
        return "Có thể trình bày là kết quả đã được kiểm chứng trên dữ liệu và quy trình đánh giá đã ghi nhận."
    return (
        "Không đủ bằng chứng để khẳng định kết quả kinh doanh. Hệ thống chỉ nêu giả thuyết, "
        "cách thử quy mô nhỏ và điều kiện dừng; quyết định cuối cùng thuộc về người dùng."
    )
