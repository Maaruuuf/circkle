"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/components/AuthContext";
import { ErrorText, SuccessText } from "@/components/ErrorText";
import { Field } from "@/components/Field";
import { ApiError, authApi, errorMessage } from "@/lib/api";
import { safeNextPath } from "@/lib/safe-redirect";
import { primaryButton, secondaryButton } from "@/lib/ui";

export function LoginForm() {
  const { login, status } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNextPath(params.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(
    params.get("error") === "google_failed" ? "Google sign-in failed. Please try again." : null,
  );
  const [info, setInfo] = useState<string | null>(params.get("registered") ? "Account created! You can log in now." : null);
  const [needsVerification, setNeedsVerification] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, router, next]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNeedsVerification(false);
    try {
      await login(email, password);
      router.replace(next);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "EMAIL_NOT_VERIFIED") setNeedsVerification(true);
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const resend = async () => {
    try {
      setInfo((await authApi.resendVerification(email)).message);
      setError(null);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  };

  return (
    <>
      <h1 className="text-xl font-bold">Log in</h1>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        <ErrorText message={error} />
        <SuccessText message={info} />
        {needsVerification && (
          <button type="button" onClick={resend} className="text-sm font-semibold text-brand">
            Resend verification email
          </button>
        )}
        <button type="submit" disabled={busy} className={`${primaryButton} w-full`}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      {/* A normal link (full page navigation): the browser is sent to Google and back. */}
      <a href={authApi.googleLoginUrl} className={`${secondaryButton} w-full`}>
        Continue with Google
      </a>
      <div className="flex justify-between text-sm">
        <Link href="/forgot-password" className="text-brand">Forgot password?</Link>
        <Link href="/register" className="font-semibold text-brand">Create account</Link>
      </div>
    </>
  );
}
