/**
 * Pretty-printed JSON block for operational payloads that do not yet have
 * richer typed UI treatments.
 */
export function JsonPanel({
  data,
  title,
}: {
  data: unknown;
  title: string;
}) {
  const payload =
    data instanceof Error
      ? {
        message: data.message,
        name: data.name,
      }
      : data;

  return (
    <section className="paper-panel-inset">
      <div className="border-b border-rule px-4 py-3">
        <p className="mono-label m-0">{title}</p>
      </div>
      <pre className="m-0 overflow-x-auto px-4 py-4 text-[12.5px] leading-7 text-ink">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </section>
  );
}
