import { Clock3, KeyRound, Link2, ScanLine } from "lucide-react";
import Link from "next/link";
import { HomeChecker } from "@/components/analysis/home-checker";
import { BinaryHero } from "@/components/binary-hero";
import { projectName } from "@/components/brand";
import { LandingFeatures } from "@/components/landing-features";
import { PosterCarousel } from "@/components/poster-carousel";
import { QuickChat } from "@/components/quick-chat";
import "./landing.css";

const signs = [
  { icon: Clock3, title: "Giục chuyển tiền ngay", text: "Người gửi dọa khóa tài khoản hoặc yêu cầu hành động trong thời gian rất ngắn." },
  { icon: Link2, title: "Đường link khác thường", text: "Tên miền gần giống tên thương hiệu hoặc trang yêu cầu đăng nhập bất ngờ." },
  { icon: KeyRound, title: "Xin OTP hoặc mật khẩu", text: "Người gửi đòi mã xác thực, mật khẩu hoặc thông tin tài khoản để tiếp tục." },
  { icon: ScanLine, title: "QR lệch người nhận", text: "Ngân hàng hoặc số tài khoản trong mã QR khác thông tin bạn đã xác minh." },
];

const steps = [
  { title: "Gửi nội dung", text: "Dán tin nhắn, link hoặc tải ảnh, biên lai và bản ghi âm." },
  { title: "Đọc và che thông tin", text: "Đọc chữ trong ảnh trên máy chủ và che dữ liệu nhạy cảm trước khi phân tích." },
  { title: "Đối chiếu dấu hiệu", text: "Kiểm tra các dấu hiệu trong nội dung, tên miền và cảnh báo đã được duyệt." },
  { title: "Xác minh trước khi trả", text: "Xem mức rủi ro, các đoạn trích và câu hỏi kiểm chứng." },
];

const questions = [
  { question: "Nếu kết quả báo nguy cơ cao thì làm gì?", answer: "Hãy tạm dừng chuyển tiền. Liên hệ người nhận hoặc đơn vị liên quan qua số điện thoại hoặc ứng dụng chính thức mà bạn tự tìm được." },
  { question: "Tôi có thể gửi những gì để kiểm tra?", answer: "Bạn có thể dán tin nhắn, đường link hoặc tải ảnh chụp và biên lai PNG/JPEG. Bản ghi âm cần Whisper trên máy chủ. Dùng mục kiểm tra QR cho mã liên kết và VietQR." },
  { question: "Ảnh và thông tin cá nhân được xử lý thế nào?", answer: "Ảnh được đọc trên máy chủ của ứng dụng. Bạn nên che thông tin riêng tư không cần thiết trước khi tải lên. Khi báo cáo, đội vận hành nhận các tín hiệu đã che để đối chiếu." },
  { question: "Báo cáo có tác dụng gì?", answer: "Chuyên viên có thể xem và gom báo cáo liên quan. Sau khi được duyệt, cảnh báo sẽ xuất hiện khi người khác kiểm tra nội dung trùng thông tin." },
  { question: "Tôi có thể gửi kết quả cho người thân không?", answer: "Chọn Hỏi người thân ở thẻ kết quả để tạo đường dẫn tóm tắt đã che thông tin, có hiệu lực 24 giờ." },
];

const rhythm = ["Dừng lại", "Kiểm tra", "Xác minh", "Quyết định"];

export default function Home() {
  return (
    <div className="landing">
      <section className="landing-hero" aria-labelledby="home-title">
        <BinaryHero />
        <div className="shell landing-hero-inner">
          <div className="landing-hero-copy">
            <p className="landing-hero-label"><span aria-hidden="true" />Trợ lý nhận diện lừa đảo</p>
            <h1 id="home-title">{projectName}</h1>
            <p>Kiểm tra tin nhắn, đường link và ảnh chụp đáng ngờ trước khi chuyển tiền.</p>
            <div className="landing-hero-actions">
              <Link href="/website" className="button primary">Kiểm tra ngay</Link>
              <a href="#quy-trinh" className="button secondary">Cách hoạt động</a>
            </div>
            <HomeChecker />
            <Link href="/truoc-khi-xac-nhan" className="transfer-entry">Đang chờ nhận tiền? Kiểm tra mã QR</Link>
          </div>
          <PosterCarousel />
        </div>
      </section>

      <div className="landing-strip">
        <div className="landing-strip-track" aria-hidden="true">
          {[0, 1].map(group => (
            <div className="landing-strip-group" key={group}>
              {[...rhythm, ...rhythm].map((item, index) => (
                <span key={index}>{item}<b>✦</b></span>
              ))}
            </div>
          ))}
        </div>
      </div>

      <section className="shell landing-section landing-signs" id="dau-hieu" aria-labelledby="signs-heading">
        <h2 id="signs-heading">Dấu hiệu thường gặp</h2>
        <div className="landing-cards landing-signs-grid">
          {signs.map(({ icon: Icon, title, text }) => (
            <article className="landing-card" key={title}>
              <span className="landing-card-icon"><Icon size={22} aria-hidden="true" /></span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-process" id="quy-trinh" aria-labelledby="process-heading">
        <div className="shell landing-section">
          <h2 id="process-heading">Cách hệ thống kiểm tra</h2>
          <ol className="landing-timeline">
            {steps.map(step => (
              <li key={step.title}>
                <div className="landing-step">
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="shell landing-section" id="tinh-nang" aria-labelledby="feature-heading">
        <LandingFeatures />
      </section>

      <section className="shell landing-section landing-faq" id="hoi-dap" aria-labelledby="faq-heading">
        <h2 id="faq-heading">Hỏi đáp</h2>
        <div className="landing-questions">
          {questions.map(({ question, answer }, index) => (
            <details name="tkc-faq" key={question} open={index === 0}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <div className="landing-end">
        <div className="shell">
          <p>Nhận được yêu cầu chuyển tiền đáng ngờ?</p>
          <Link href="/website" className="button primary">Kiểm tra nội dung</Link>
        </div>
      </div>
      <QuickChat />
    </div>
  );
}
