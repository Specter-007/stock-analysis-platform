import { Suspense } from "react";
import VerifyEmailPageClient from "@/components/auth/VerifyEmailPageClient";

export const metadata = {
  title: "Verify email — Stock Analyst",
};

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailPageClient />
    </Suspense>
  );
}
