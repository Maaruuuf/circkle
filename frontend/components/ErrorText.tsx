export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-xl bg-danger-soft px-3 py-2 text-sm text-danger">
      {message}
    </p>
  );
}

export function SuccessText({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="status" className="rounded-xl bg-success-soft px-3 py-2 text-sm text-success">
      {message}
    </p>
  );
}
