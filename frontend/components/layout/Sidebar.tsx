"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  GitBranch,
  BarChart2,
  FolderOpen,
  Settings,
  LogOut,
  CheckCircle,
} from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/consultar",   label: "Consultar",       icon: Search },
  { href: "/protocolo",   label: "Protocolo P1→P6", icon: GitBranch },
  { href: "/simuladores", label: "Simuladores",      icon: BarChart2 },
  { href: "/documentos",  label: "Documentos",       icon: FolderOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside
      className="w-60 shrink-0 flex flex-col border-r border-border"
      style={{ backgroundColor: "var(--color-bg-sidebar, #F0F4FA)" }}
    >
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <Link href="/consultar" className="flex items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="Tribus-AI" className="h-7 w-auto" />
          <span className="font-semibold text-sm text-foreground">Tribus-AI</span>
        </Link>
      </div>

      {/* Navegação */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors",
                active
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <Icon size={16} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Rodapé */}
      <div className="p-4 border-t border-border space-y-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <CheckCircle size={12} className="text-emerald-500" />
          Sistema operacional
        </div>

        {user && (
          <div className="text-xs">
            <p className="font-medium truncate text-foreground">{user.nome}</p>
            <p className="text-muted-foreground truncate">{user.email}</p>
          </div>
        )}

        <div className="flex gap-3">
          {user?.perfil === "ADMIN" && (
            <Link
              href="/admin"
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              <Settings size={11} />
              Admin
            </Link>
          )}
          <button
            onClick={logout}
            className="text-xs text-muted-foreground hover:text-red-500 flex items-center gap-1 ml-auto cursor-pointer"
          >
            <LogOut size={11} />
            Sair
          </button>
        </div>
      </div>
    </aside>
  );
}
