import CallScreen from "@/components/CallScreen";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Aira - Emergency Voice Assistant",
  description: "Patient-facing voice call screen for immediate emergency symptom capture and medical summary generation.",
};

export default function CallPage() {
  return (
    <main className="w-full min-h-screen bg-[#0a0a0f] flex items-center justify-center">
      <div className="w-full max-w-md min-h-screen shadow-2xl relative overflow-hidden flex flex-col">
        <CallScreen />
      </div>
    </main>
  );
}
