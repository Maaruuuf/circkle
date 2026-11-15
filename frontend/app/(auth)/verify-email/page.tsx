import type { Metadata } from "next";
import { Suspense } from "react";
import { VerifyEmail } from "./VerifyEmail";

export const metadata: Metadata = { title: "Verify email" };

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmail />
    </Suspense>
  );
}
