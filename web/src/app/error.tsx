"use client";

// Last-resort error screen (React render errors). API errors are handled per page.
export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="card space-y-3 p-5">
      <h1 className="text-xl font-black">Something went wrong</h1>
      <p className="text-sm text-muted">{error.message}</p>
      <button onClick={reset} className="btn btn-primary w-full">Try again</button>
    </div>
  );
}
