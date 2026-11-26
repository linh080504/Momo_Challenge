// Tin nhắn mẫu cho nút "Dùng mẫu".
//
// QUAN TRỌNG: mẫu chỉ là ĐẦU VÀO điền sẵn vào ô nhập. Kết quả vẫn do API phân tích thật.
// Tuyệt đối không đặt kết quả dựng sẵn ở đây (brief mục 4 "Won't": demo kịch bản cứng).
//
// Mẫu đã ẩn danh: số tài khoản 0123456789 là số giả dùng chung trong eval/dataset.example.jsonl,
// tên người là tên giả phổ biến.

export interface Sample {
  id: string;
  /** Tên ngắn hiện cạnh nút để người dùng biết đang xem mẫu gì. */
  title: string;
  text: string;
}

export const SAMPLES: readonly Sample[] = [
  {
    id: "bank-brandname",
    title: "Tin nhắn giả mạo ngân hàng",
    text: "[Vietcombank] Tài khoản của Quý khách bị tạm khóa do đăng nhập bất thường. Xác thực ngay tại http://vcb-xacthuc.top/login trong 30 phút để tránh bị khóa vĩnh viễn.",
  },
  {
    id: "borrow-new-number",
    title: "Người quen nhắn mượn tiền, nói đã đổi số",
    text: "Anh ơi em Hùng đây, em đổi số mới rồi. Anh cho em mượn tạm 15 triệu đến thứ 6 em trả. Chuyển vào tài khoản vợ em nhé: 0123456789 - MB Bank - NGUYEN THI LAN. Gấp lắm anh, đừng gọi em vì em đang họp.",
  },
  {
    id: "deposit-homestay",
    title: "Đặt cọc giữ phòng",
    text: "Bạn đặt cọc 500k giữ phòng homestay dịp lễ nhé. Chuyển vào STK cá nhân chủ nhà 0123456789 (Vietcombank). Sau 2 tiếng không cọc sẽ hủy phòng. Chủ nhà đang ở nước ngoài nên không gặp trực tiếp được.",
  },
  {
    id: "friends-fund",
    title: "Tin nhắn bình thường giữa bạn bè",
    text: "Tối nay 7h họp lớp ở quán cũ nhé, mỗi người góp 200k, chuyển cho Lan giữ quỹ.",
  },
];
