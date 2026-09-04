import Link from "next/link";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md px-4 sm:px-6 py-24 text-center flex flex-col items-center gap-4">
      <Compass size={32} className="text-text-muted" aria-hidden="true" />
      <h1 className="text-2xl font-semibold text-text-primary">Page not found</h1>
      <p className="text-sm text-text-muted">
        The page you&apos;re looking for doesn&apos;t exist, or may have moved.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-accent text-white text-sm font-medium hover:opacity-90"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
