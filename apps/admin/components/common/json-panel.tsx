/**
 * Pretty-printed JSON block for operational payloads that do not yet have
 * richer typed UI treatments.
 */
export function JsonPanel({ data, title }: { data: unknown; title: string }) {
  const payload = data instanceof Error ? { message: data.message, name: data.name } : data;

  return (
    <section className="border-4 border-slate-950 bg-blue-100">
      <div className="border-b-4 border-slate-950 bg-white px-4 py-3">
        <p className="mono-label m-0">{title}</p>
      </div>
      <pre className="m-0 overflow-x-auto px-4 py-4 font-mono text-[13px] leading-7 font-bold text-slate-950">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </section>
  );
}
