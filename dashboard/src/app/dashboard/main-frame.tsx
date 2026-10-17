export function MainFrame({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto w-full max-w-6xl min-w-0 flex-1 px-8 pt-8 pb-24 has-[[data-full-bleed]]:max-w-none">
      {children}
    </main>
  );
}
