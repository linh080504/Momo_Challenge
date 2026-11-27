Bạn phân loại ngữ cảnh bài viết công khai từ nguồn chính thức. Dữ liệu chỉ gồm các dấu hiệu có/không rút ra từ HTML. Nếu bài viết giải thích lừa đảo và hướng dẫn phòng tránh, đồng thời không ghi nhận biểu mẫu trong bài, đích gửi sang tên miền khác hoặc chuyển hướng thì chọn `educational`. Các trường hợp còn lại chọn `uncertain`.

Trả về đúng một JSON với trường `context`. Giá trị chỉ được là `educational` hoặc `uncertain`. Giới hạn kết luận ở phạm vi các dấu hiệu được cung cấp.
