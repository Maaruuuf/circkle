"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { ErrorText, SuccessText } from "@/components/ErrorText";
import { Field } from "@/components/Field";
import { authApi, errorMessage } from "@/lib/api";
import { primaryButton } from "@/lib/ui";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setMessage((await authApi.forgotPassword(email)).message);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1 className="text-xl font-bold">Forgot your password?</h1>
      <p className="text-sm text-muted">Enter your email and we will send you a reset link.</p>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <ErrorText message={error} />
        <SuccessText message={message} />
        <button type="submit" disabled={busy} className={`${primaryButton} w-full`}>
          {busy ? "Sending…" : "Send reset link"}
        </button>
      </form>
      <Link href="/login" className="block text-center text-sm text-brand">Back to log in</Link>
    </>
  );
}
