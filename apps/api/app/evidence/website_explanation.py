PUBLISHER_REFERENCES = {
    "nhandan.vn": ("Báo Nhân Dân", "https://vanban.chinhphu.vn/he-thong-chinh-tri-68381"),
}


def public_explanation_options(facts, domain, sources_checked, evidence=()):
    options = {
        "scope": {
            "label": "Phạm vi kiểm tra",
            "finding": "Lượt kiểm tra dựa trên phần trang đọc được và các nguồn đã phản hồi. Hành vi chỉ xuất hiện sau khi tương tác vẫn chưa được kiểm tra.",
        },
    }
    if facts["article_markup"]:
        options["article_structure"] = {
            "label": "Ngữ cảnh nội dung",
            "finding": ("Trang hiển thị nhiều mục bài viết. Mỗi mục cần được đọc theo ngữ cảnh riêng."
                        if facts["homepage"] else "Trang có phần nội dung được trình bày dưới dạng bài viết."),
        }
    if facts["educational_heading"]:
        options["education"] = {
            "label": "Tiêu đề hướng dẫn",
            "finding": "Tiêu đề đề cập đến cách nhận biết hoặc phòng tránh. Cần phân biệt nội dung hướng dẫn với lời yêu cầu thực hiện giao dịch.",
        }
    if facts["sensitive_form"]:
        options["sensitive_form"] = {
            "label": "Thông tin nhạy cảm",
            "finding": "Trang có ô nhập thông tin nhạy cảm như mật khẩu, mã xác thực hoặc dữ liệu thẻ. Hãy xác minh địa chỉ và mục đích của biểu mẫu trước khi nhập.",
        }
    elif facts.get("form_count"):
        options["form_absence"] = {
            "label": "Biểu mẫu trên trang",
            "finding": "Trang có biểu mẫu. Lượt kiểm tra chưa ghi nhận ô yêu cầu mật khẩu, mã xác thực hoặc số thẻ.",
        }
    else:
        options["form_absence"] = {
            "label": "Biểu mẫu trên trang",
            "finding": "Trong phần trang đã đọc, chưa thấy biểu mẫu yêu cầu mật khẩu, mã xác thực hoặc số thẻ.",
        }
    if facts["external_form"]:
        options["routing"] = {
            "label": "Đích gửi biểu mẫu",
            "finding": "Dữ liệu nhập vào biểu mẫu được cấu hình để gửi sang tên miền khác. Hãy xác minh bên nhận trước khi nhập thông tin.",
        }
    if facts["meta_redirect"]:
        options["redirect"] = {
            "label": "Chuyển hướng",
            "finding": "Trang có khai báo tự chuyển sang địa chỉ khác. Đích cuối chưa được xác minh.",
        }
    if facts.get("account_request"):
        options["account_request"] = {
            "label": "Yêu cầu nhập thông tin",
            "finding": "Trang có trường nhạy cảm và câu chữ đề cập việc nhập hoặc gửi thông tin đăng nhập, xác thực hoặc thanh toán.",
        }
    if facts["gambling_offer"]:
        options["gambling_offer"] = {
            "label": "Trang đang quảng bá gì",
            "kind": "article",
            "finding": "Trang quảng bá cá cược trực tuyến và mời người đọc nạp tiền để tham gia.",
        }
    if facts["payment_incentive"]:
        options["payment_incentive"] = {
            "label": "Ưu đãi gắn với khoản nạp",
            "kind": "article",
            "finding": "Trang dùng tiền thưởng hoặc khuyến mãi để khuyến khích nạp tiền. Hãy xác minh bên nhận và điều kiện áp dụng trước khi quyết định.",
        }
    if facts["payment_pressure"]:
        options["payment_pressure"] = {
            "label": "Thúc giục thanh toán",
            "kind": "article",
            "finding": "Trang thúc người đọc thanh toán sớm. Hãy dừng lại để xác minh bên nhận tiền qua một kênh độc lập.",
        }
    if facts.get("withdrawal_instructions"):
        options["withdrawal"] = {
            "label": "Hướng dẫn nạp và rút tiền",
            "kind": "article",
            "finding": "Trang có phần hướng dẫn giao dịch. Nội dung này chưa xác nhận khả năng rút tiền thực tế.",
        }
    if facts.get("official_claim") or facts.get("license_claim"):
        claims = "là địa chỉ chính thức và có giấy phép" if facts["official_claim"] and facts["license_claim"] else (
            "là địa chỉ chính thức" if facts["official_claim"] else "có giấy phép")
        options["operator_claim"] = {
            "label": "Tuyên bố của trang",
            "kind": "article",
            "finding": f"Trang tự nhận {claims}. Các nguồn đã kiểm tra chưa xác minh được tuyên bố này.",
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
    registered_domain = domain.get("registered_domain")
    if facts["gambling_offer"] and host and registered_domain and host != registered_domain:
        options["subdomain"] = {
            "label": "Địa chỉ đăng nội dung",
            "finding": f"Nội dung được đăng trên một tên miền phụ của {registered_domain}. Tên miền gốc chỉ cho biết địa chỉ lưu trữ, còn danh tính bên nhận tiền cần được xác minh.",
        }
    if registered := domain.get("domain_registered_on"):
        options["registration"] = {
            "label": "Thời điểm đăng ký",
            "finding": f"RDAP ghi nhận ngày đăng ký {registered}. Hồ sơ này cho biết tuổi của tên miền chính, còn nội dung đang được đăng cần được đánh giá riêng.",
        }
    matched = {item["source"] for item in evidence if item["weight"] > 0}
    if matched & {"internal_blacklist", "external_blacklist", "safe_browsing", "url_reputation"}:
        source_names = [name for key, name in (
            ("internal_blacklist", "hồ sơ đã duyệt"),
            ("external_blacklist", "danh sách cảnh báo cộng đồng"),
            ("safe_browsing", "Google Safe Browsing"),
        ) if key in matched]
        findings = ["Địa chỉ có kết quả trùng trong " + ", ".join(source_names) + "."] if source_names else []
        findings.extend(item["finding"] for item in evidence if item["source"] == "url_reputation")
        options["alerts"] = {"label": "Cảnh báo đã đối chiếu", "finding": " ".join(findings)}
    elif sources_checked:
        options["source_result"] = {"label": "Đối chiếu bên ngoài",
                                     "finding": "Google Safe Browsing chưa ghi nhận cảnh báo trùng ở cấp tên miền trong lượt này."}
    else:
        missing = "Chưa có phản hồi Google Safe Browsing ở cấp tên miền cho lượt này."
        if "registration" not in options:
            missing += " Chưa có dữ liệu RDAP để nêu ngày đăng ký hoặc thời hạn của tên miền."
        options["source_gap"] = {"label": "Dữ kiện còn thiếu", "finding": missing}
    return options
