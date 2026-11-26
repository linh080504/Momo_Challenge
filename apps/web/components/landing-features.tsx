"use client";

import { useId, useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import { Camera, FileCheck, Inbox, Link2, ScanLine, UsersRound } from "lucide-react";

const collections = [
  {
    title: "Người dùng",
    features: [
      { icon: Link2, title: "Tin nhắn và đường link", text: "Kiểm tra lời thúc giục, yêu cầu cung cấp mã hoặc tên miền có dấu hiệu bất thường.", href: "#kiem-tra", link: "Kiểm tra nội dung" },
      { icon: Camera, title: "Ảnh chụp màn hình", text: "Đọc chữ từ ảnh đoạn chat, hóa đơn hoặc trang bạn nhận được.", href: "#kiem-tra", link: "Tải ảnh để kiểm tra" },
      { icon: ScanLine, title: "Mã VietQR", text: "Đối chiếu ngân hàng, tài khoản nhận và số tiền trong mã QR.", href: "/qr", link: "Mở kiểm tra VietQR" },
      { icon: UsersRound, title: "Hỏi người thân", text: "Chia sẻ tóm tắt đã che thông tin qua đường dẫn có hiệu lực 24 giờ.", href: "#kiem-tra", link: "Tạo kết quả để chia sẻ" },
    ],
  },
  {
    title: "Vận hành",
    features: [
      { icon: Inbox, title: "Báo cáo cùng chiến dịch", text: "Gom báo cáo có thông tin đối chiếu trùng và xem lại bằng chứng trong một hồ sơ.", href: "/ops", link: "Mở bàn vận hành" },
      { icon: FileCheck, title: "Duyệt có nhật ký", text: "Chuyên viên kiểm tra, phân loại và quyết định trước khi cảnh báo xuất hiện cho người dùng.", href: "/ops", link: "Xem chiến dịch" },
      { icon: UsersRound, title: "Cảnh báo đã xác nhận", text: "Dấu hiệu trùng với một chiến dịch đã duyệt có thể xuất hiện ở những lần kiểm tra sau.", href: "#kiem-tra", link: "Xem cách kiểm tra" },
    ],
  },
] as const;

export function LandingFeatures() {
  const id = useId();
  const [active, setActive] = useState(0);
  const buttons = useRef<Array<HTMLButtonElement | null>>([]);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let destination: number;
    if (event.key === "Home") destination = 0;
    else if (event.key === "End") destination = collections.length - 1;
    else if (event.key === "ArrowRight") destination = (index + 1) % collections.length;
    else if (event.key === "ArrowLeft") destination = (index + collections.length - 1) % collections.length;
    else return;
    event.preventDefault();
    setActive(destination);
    buttons.current[destination]?.focus();
  }

  return (
    <>
      <div className="landing-section-heading">
        <h2 id="feature-heading">Tính năng</h2>
        <div className="landing-tabs" role="tablist" aria-label="Chọn vai trò">
          {collections.map((collection, index) => (
            <button key={collection.title} id={id + "-tab-" + index} role="tab" type="button"
              ref={button => { buttons.current[index] = button; }}
              aria-selected={active === index} aria-controls={id + "-panel-" + index}
              tabIndex={active === index ? 0 : -1} onClick={() => setActive(index)}
              onKeyDown={event => onKeyDown(event, index)}>{collection.title}</button>
          ))}
        </div>
      </div>
      {collections.map((collection, index) => (
        <div key={collection.title} id={id + "-panel-" + index} role="tabpanel"
          aria-labelledby={id + "-tab-" + index} hidden={active !== index}>
          <div className="landing-cards landing-features-grid">
            {collection.features.map(({ icon: Icon, title, text, href, link }) => (
              <article className="landing-card" key={title}>
                <span className="landing-card-icon"><Icon size={22} aria-hidden="true" /></span>
                <h3>{title}</h3>
                <p>{text}</p>
                {href.startsWith("#") ? <a href={href} className="landing-card-link">{link}</a> :
                  <Link href={href} className="landing-card-link">{link}</Link>}
              </article>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
