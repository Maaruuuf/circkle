"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ErrorText } from "@/components/ErrorText";
import { Field } from "@/components/Field";
import { authApi, errorMessage } from "@/lib/api";
import { primaryButton } from "@/lib/ui";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await authApi.register({ email, username, password });
      router.push("/login?registered=1");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1 className="text-xl font-bold">Create your account</h1>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email" id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field
          label="Username"
          id="username"
          autoComplete="username"
          required
          minLength={3}
          maxLength={30}
          pattern="[a-zA-Z0-9_]{3,30}"
          hint="3-30 letters, numbers or underscores"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <Field
          label="Password"
          id="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          maxLength={128}
          hint="At least 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <ErrorText message={error} />
        <button type="submit" disabled={busy} className={`${primaryButton} w-full`}>
          {busy ? "Creating…" : "Sign up"}
        </button>
      </form>
      <p className="text-center text-sm">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-brand">Log in</Link>
      </p>
    </>
  );
}
