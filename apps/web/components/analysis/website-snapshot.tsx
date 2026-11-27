import { LoaderCircle } from "lucide-react";

export function WebsiteSnapshot({ picture, host }: { picture?: string; host?: string }) {
  if (!picture) return <div className="website-snapshot-pending" role="status">
    <LoaderCircle size={22} className="spinning" aria-hidden="true" />
    <span>Đang chụp ảnh website…</span>
  </div>;

  return <figure className="website-snapshot">
    <div className="website-snapshot-screen" role="region" tabIndex={0} aria-label="Cuộn để xem ảnh website">
      <img src={picture} alt={host ? `Ảnh chụp website ${host}` : "Ảnh chụp website"} />
    </div>
    {host && <figcaption className="muted">{host}</figcaption>}
  </figure>;
}
