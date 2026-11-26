import Checker from "@/components/Checker";
import { ShieldIcon } from "@/components/icons";
import "../globals.css";

export default function Home() {
  return (
    <div className="day-two-preview mx-auto flex min-h-dvh w-full max-w-xl flex-col px-4">
      <header className="flex items-center gap-2 py-4 text-blue-800">
        <ShieldIcon className="size-8 shrink-0" />
        <span className="text-xl font-bold">Trước Khi Chuyển</span>
      </header>
      <Checker />
    </div>
  );
}
