PUBLISHER_REFERENCES = {
    "nhandan.vn": ("Báo Nhân Dân", "https://vanban.chinhphu.vn/he-thong-chinh-tri-68381"),
}


def public_explanation_options(facts, domain, sources_checked, evidence=()):
    options = {
        "scope": {
            "label": "Phạm vi kiểm tra",
            "finding": "Kết quả dựa trên HTML công khai và các nguồn đối chiếu đã phản hồi. Các hành vi cần chạy JavaScript vẫn chưa được kiểm tra.",
        },
    }
    if facts["article_markup"]:
        options["article_structure"] = {
            "label": "Ngữ cảnh nội dung",
            "finding": f"HTML có {facts['article_count']} khối được đánh dấu là bài viết. Đây là dấu hiệu về loại nội dung trang hiển thị.",
        }
    if facts["educational_heading"]:
        options["education"] = {
            "label": "Tiêu đề hướng dẫn",
            "finding": "Tiêu đề đề cập đến cách nhận biết hoặc phòng tránh. Cần phân biệt nội dung hướng dẫn với lời yêu cầu thực hiện giao dịch.",
        }
    if facts["sensitive_form"]:
        options["sensitive_form"] = {
            "label": "Thông tin nhạy cảm",
            "finding": "HTML có trường mật khẩu, mã xác thực hoặc thông tin thẻ. Cần xác minh địa chỉ và mục đích trước khi nhập dữ liệu.",
        }
    elif facts.get("form_count"):
        options["form_absence"] = {
            "label": "Biểu mẫu trên trang",
            "finding": f"HTML khai báo {facts['form_count']} biểu mẫu. "
                       "Chưa thấy trường mật khẩu, mã xác thực hoặc số thẻ thuộc các kiểu nhận diện được.",
        }
    else:
        options["form_absence"] = {
            "label": "Biểu mẫu trong HTML",
            "finding": "Trong HTML đã đọc, bộ kiểm tra chưa thấy trường mật khẩu, mã xác thực hoặc số thẻ thuộc các kiểu nhận diện được.",
        }
    if facts["external_form"] or facts["meta_redirect"]:
        options["routing"] = {
            "label": "Đích gửi hoặc chuyển hướng",
            "finding": "HTML có khai báo gửi biểu mẫu sang tên miền khác hoặc khai báo tự chuyển hướng. Đích thực tế chưa được xác minh.",
        }
    if facts["gambling_offer"] or facts["payment_incentive"] or facts["payment_pressure"]:
        options["payments"] = {
            "label": "Lời mời hoặc áp lực thanh toán",
            "finding": "HTML có tín hiệu liên quan đến nạp tiền, ưu đãi gắn với khoản nạp hoặc lời thúc giục thanh toán. Hãy tạm dừng và xác minh trước khi gửi tiền.",
        }
    host = (domain.get("host") or "").removeprefix("www.")
    if host in PUBLISHER_REFERENCES and not domain["score"]:
        publisher, source = PUBLISHER_REFERENCES[host]
        options["domain"] = {
            "label": "Tên miền",
            "finding": f"Địa chỉ {host} khớp với website {publisher} được Cổng Thông tin điện tử Chính phủ liệt kê.",
            "source_url": source,
        }
    elif domain["official_brand"] and not domain["score"]:
        options["domain"] = {"label": "Tên miền", "finding": f"Tên miền khớp danh mục địa chỉ chính thức của {domain['official_brand']}."}
    elif domain["score"]:
        options["domain"] = {"label": "Tên miền", "finding": "Cấu trúc địa chỉ có dấu hiệu bất thường được ghi trong báo cáo tên miền."}
    else:
        options["domain"] = {"label": "Tên miền", "finding": "Bộ quy tắc chưa thấy bất thường trong cấu trúc địa chỉ. Kết quả này chỉ phản ánh phần URL đã kiểm tra."}
    if registered := domain.get("domain_registered_on"):
        options["registration"] = {
            "label": "Thời điểm đăng ký",
            "finding": f"RDAP ghi nhận ngày đăng ký {registered}. Đây là thông tin về tên miền.",
        }
    matched = {item["source"] for item in evidence if item["weight"] > 0}
    if matched & {"internal_blacklist", "external_blacklist", "safe_browsing"}:
        source_names = [name for key, name in (
            ("internal_blacklist", "hồ sơ đã duyệt"),
            ("external_blacklist", "danh sách cảnh báo cộng đồng"),
            ("safe_browsing", "Google Safe Browsing"),
        ) if key in matched]
        options["alerts"] = {"label": "Cảnh báo đã đối chiếu",
                              "finding": "Địa chỉ có kết quả trùng trong " + ", ".join(source_names) + "."}
    elif sources_checked:
        options["source_result"] = {"label": "Đối chiếu bên ngoài",
                                     "finding": "Google Safe Browsing chưa ghi nhận cảnh báo trùng ở cấp tên miền trong lượt này."}
    else:
        missing = "Chưa có phản hồi Google Safe Browsing ở cấp tên miền cho lượt này."
        if "registration" not in options:
            missing += " Chưa có dữ liệu RDAP để nêu ngày đăng ký hoặc thời hạn của tên miền."
        options["source_gap"] = {"label": "Dữ kiện còn thiếu", "finding": missing}
    return options
