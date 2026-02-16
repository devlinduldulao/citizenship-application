import { createFileRoute } from "@tanstack/react-router"

import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - FastAPI Template",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <p className="text-muted-foreground text-xs font-medium tracking-[0.12em] uppercase">
          Dashboard
        </p>
        <h1 className="text-3xl truncate max-w-2xl font-semibold tracking-tight">
          Hi, {currentUser?.full_name || currentUser?.email} 👋
        </h1>
        <p className="text-muted-foreground">
          Welcome back. Your application workspace is ready.
        </p>
      </div>

      <div className="bg-card border-border/60 rounded-xl border p-6 shadow-sm">
        <p className="text-sm text-muted-foreground leading-relaxed">
          Use the sidebar to manage applications, review explainability signals,
          and complete case decisions with full auditability.
        </p>
      </div>
    </div>
  )
}
