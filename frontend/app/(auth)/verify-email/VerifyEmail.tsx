"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorText, SuccessText } from "@/components/ErrorText";
import { Spinner } from "@/components/Spinner";
import { authApi, errorMessage } from "@/lib/api";
import { primaryButton } from "@/lib/ui";

export function VerifyEmail() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<"working" | "ok" | "failed">(token ? "working" : "failed");
  const [message, setMessage] = useState<string | null>(token ? null : "This verification link is missing its token.");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return; // tokens are single-use: never submit twice (React strict mode)
    started.current = true;
    authApi
      .verifyEmail(token)
      .then(() => setState("ok"))
      .catch((caught) => {
        setMessage(errorMessage(caught));
        setState("failed");
      });
  }, [token]);

  return (
    <>
      <h1 className="text-xl font-bold">Email verification</h1>
      {state === "working" && <Spinner label="Verifying" />}
      {state === "ok" && <SuccessText message="Your email is verified. Thank you!" />}
      {state === "failed" && <ErrorText message={message} />}
      <Link href="/login" className={`${primaryButton} w-full`}>Continue to log in</Link>
    </>
  );
}
