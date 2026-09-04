import { Suspense } from "react";
import ResetPasswordPageClient from "@/components/auth/ResetPasswordPageClient";

export const metadata = {
  title: "Reset password — Stock Analyst",
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordPageClient />
    </Suspense>
  );
}
