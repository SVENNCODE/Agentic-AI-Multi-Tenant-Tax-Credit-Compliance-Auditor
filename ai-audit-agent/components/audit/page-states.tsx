import Link from "next/link";
import { AppNav } from "@/components/app-nav";

export function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F7F8FA]">
      <AppNav />
      <main className="px-6 py-12">
        <div className="max-w-3xl mx-auto space-y-8">{children}</div>
      </main>
    </div>
  );
}

export function PageHeading({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle?: string }) {
  return (
    <div>
      <span className="font-mono text-xs tracking-[0.2em] text-[#5C7C74]">{eyebrow}</span>
      <h1 className="text-xl font-medium text-[#12161C] mt-2">{title}</h1>
      {subtitle && <p className="text-sm text-[#5B6470] mt-1">{subtitle}</p>}
    </div>
  );
}

export function LoadingState() {
  return (
    <PageShell>
      <p className="text-sm text-[#5B6470] text-center py-24">Loading your results…</p>
    </PageShell>
  );
}

export function NotFoundState() {
  return (
    <PageShell>
      <div className="text-center max-w-sm mx-auto py-16">
        <h2 className="text-lg font-medium text-[#12161C]">No results yet</h2>
        <p className="text-sm text-[#5B6470] mt-2">
          Complete the intake questionnaire to see your residency status, eligible
          credits, and filing readiness here.
        </p>
        <Link
          href="/questionnaire"
          className="inline-block mt-6 bg-[#1B6E67] hover:bg-[#16564F] text-white text-sm px-4 py-2 rounded-md"
        >
          Start the questionnaire
        </Link>
      </div>
    </PageShell>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <PageShell>
      <p role="alert" className="text-sm text-[#B3432F] text-center py-24">{message}</p>
    </PageShell>
  );
}
