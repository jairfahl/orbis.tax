import { AdminGuard } from "@/components/layout/AdminGuard";
import { Sidebar } from "@/components/layout/Sidebar";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-5xl mx-auto">{children}</div>
        </main>
      </div>
    </AdminGuard>
  );
}
