import { ENTITY_TYPE, labelOf } from "@/lib/labels";

interface Props {
  entities: { type?: string; display: string }[];
}

/**
 * Danh sách thực thể đã che (ví dụ 0123****89). Chỉ nhận `display`, không bao giờ nhận giá trị thô.
 * Mỗi thực thể một dòng, nhãn trên giá trị dưới, để địa chỉ/đường link không bị cắt đôi giữa chữ.
 */
export default function EntityList({ entities }: Props) {
  return (
    <ul className="space-y-2">
      {entities.map((e, i) => {
        const label = labelOf(ENTITY_TYPE, e.type);
        return (
          <li key={`${e.display}-${i}`} className="rounded-lg bg-slate-100 px-3 py-2">
            {label && <span className="block text-slate-700">{label}</span>}
            <span className="block break-words font-bold">{e.display}</span>
          </li>
        );
      })}
    </ul>
  );
}
