import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Footer } from "./Footer"

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="bg-muted/60 dark:bg-zinc-900 relative hidden overflow-hidden lg:flex lg:flex-col lg:items-center lg:justify-center lg:p-12">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,hsl(var(--primary)/0.18),transparent_45%),radial-gradient(circle_at_75%_80%,hsl(var(--accent)/0.24),transparent_40%)]" />
        <div className="relative z-10 space-y-6 text-center">
          <Logo variant="full" className="mx-auto h-16" asLink={false} />
          <div className="space-y-2">
            <h2 className="text-foreground text-2xl font-semibold tracking-tight">
              Norwegian Citizenship Automation
            </h2>
            <p className="text-muted-foreground max-w-md text-sm leading-relaxed">
              A transparent, explainable workflow for intake, eligibility
              scoring, and human review.
            </p>
          </div>
        </div>
      </div>
      <div className="bg-background flex flex-col gap-4 p-6 md:p-10">
        <div className="flex justify-end">
          <Appearance />
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  )
}
