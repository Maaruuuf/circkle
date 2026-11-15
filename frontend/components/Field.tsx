import type { InputHTMLAttributes } from "react";
import { inputClass } from "@/lib/ui";

export function Field({
  label,
  id,
  hint,
  ...props
}: { label: string; id: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <input id={id} name={id} className={inputClass} {...props} />
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}
