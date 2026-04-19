"use client";
import { useAuthStore } from "@/store/auth";

const WA_URL =
  "https://wa.me/5511999999999?text=Ol%C3%A1%2C%20quero%20assinar%20o%20Tribus-AI%20ap%C3%B3s%20meu%20trial";

function diasRestantes(trialEndsAt: string): number {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const fim = new Date(trialEndsAt);
  fim.setHours(0, 0, 0, 0);
  return Math.max(0, Math.round((fim.getTime() - hoje.getTime()) / 86_400_000));
}

export function TrialBanner() {
  const user = useAuthStore((s) => s.user);

  if (!user?.trial_ends_at) return null;
  if (user.subscription_status && user.subscription_status !== "trial") return null;

  const dias = diasRestantes(user.trial_ends_at);

  const msg =
    dias === 0
      ? "Seu período de teste encerra hoje."
      : dias === 1
      ? "Você tem apenas 1 dia para finalizar sua experiência."
      : `Você tem ${dias} dias para finalizar sua experiência.`;

  return (
    <div
      className="w-full flex items-center justify-between gap-4 px-5 py-2.5 text-sm"
      style={{
        background: dias <= 2 ? "#dc2626" : "#1d4ed8",
        color: "#fff",
      }}
    >
      <span>
        {msg}{" "}
        <span style={{ opacity: 0.85 }}>Gostou do que viu?</span>
      </span>

      <a
        href={WA_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="shrink-0 font-semibold whitespace-nowrap rounded-full px-4 py-1 text-xs transition-opacity hover:opacity-80"
        style={{ background: "rgba(255,255,255,0.20)", border: "1px solid rgba(255,255,255,0.35)" }}
      >
        Vamos assinar?!
      </a>
    </div>
  );
}
