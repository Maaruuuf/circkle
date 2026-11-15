export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-label={label} className="flex justify-center p-8">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-line border-t-brand" />
    </div>
  );
}
