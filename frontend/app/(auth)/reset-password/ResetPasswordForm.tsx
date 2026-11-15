"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ErrorText, SuccessText } from "@/components/ErrorText";
import { Field } from "@/components/Field";
import { authApi, errorMessage } from "@/lib/api";
import { primaryButton } from "@/lib/ui";

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (password !== confirm) return setError("Passwords do not match.");
    setBusy(true);
    setError(null);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  if (!token) return <ErrorText message="This reset link is missing its token." />;
  if (done) {
    return (
      <>
        <SuccessText message="Password updated. You can log in with your new password." />
        <Link href="/login" className={`${primaryButton} w-full`}>Log in</Link>
      </>
    );
  }
  return (
    <>
      <h1 className="text-xl font-bold">Choose a new password</h1>
      <form onSubmit={submit} className="space-y-4">
        <Field label="New password" id="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} />
        <Field label="Confirm new password" id="confirm" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        <ErrorText message={error} />
        <button type="submit" disabled={busy} className={`${primaryButton} w-full`}>
          {busy ? "Saving…" : "Update password"}
        </button>
      </form>
    </>
  );
}
