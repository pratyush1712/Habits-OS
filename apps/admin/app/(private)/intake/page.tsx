import { logIntakeAction } from "@/lib/actions";
import { api, type SourceEvent } from "@/lib/api-client";
import { asRecord, readArray } from "@/lib/data-helpers";
import {
  INTAKE_PRODUCTS,
  intakeItemKey,
  type IntakeIngredientPreset,
  type IntakeProductPreset,
} from "@/lib/intake-catalog";
import { NoticeBanner } from "@/components/common/notice-banner";
import { PageHeader } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";
import { readNotice, resolveSearchParams } from "@/lib/notice";

const RETURN_PATH = "/intake";
const DEFAULT_TIMEZONE = "America/New_York";

function formatDateInTimezone(date: Date, timezone: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    day: "2-digit",
    month: "2-digit",
    timeZone: timezone,
    year: "numeric",
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return `${values.year}-${values.month}-${values.day}`;
}

function fieldClassName(): string {
  return "h-12 w-full border-2 border-slate-950 bg-white px-3 text-base font-bold text-slate-950 outline-none focus:border-blue-700 focus:ring-4 focus:ring-yellow-300";
}

function buttonClassName(color: "blue" | "green" | "white" = "blue"): string {
  if (color === "green") {
    return "inline-flex min-h-14 items-center justify-center border-2 border-slate-950 bg-green-500 px-6 py-3 text-center text-lg font-black uppercase tracking-wide text-slate-950 no-underline hover:bg-green-400 active:translate-y-0.5";
  }

  if (color === "white") {
    return "inline-flex min-h-14 items-center justify-center border-2 border-slate-950 bg-white px-6 py-3 text-center text-lg font-black uppercase tracking-wide text-slate-950 no-underline hover:bg-yellow-200 active:translate-y-0.5";
  }

  return "inline-flex min-h-14 items-center justify-center border-2 border-slate-950 bg-blue-600 px-6 py-3 text-center text-lg font-black uppercase tracking-wide text-white no-underline hover:bg-blue-500 active:translate-y-0.5";
}

function itemRecords(event: SourceEvent): Record<string, unknown>[] {
  const metrics = asRecord(event.metrics) ?? asRecord(event.raw_payload);
  return readArray(metrics, "items")
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null);
}

function stringValue(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  return typeof value === "string" ? value : "";
}

function numberValue(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? `${value}` : "";
}

function hiddenIngredientFields(product: IntakeProductPreset, ingredient: IntakeIngredientPreset) {
  const itemKey = intakeItemKey(product.productKey, ingredient.ingredientKey);
  const label = `${product.productLabel} — ${ingredient.ingredientLabel}`;

  return (
    <>
      <input name="itemKey" type="hidden" value={itemKey} />
      <input name={`itemLabel.${itemKey}`} type="hidden" value={label} />
      <input name={`brandKey.${itemKey}`} type="hidden" value={product.brandKey} />
      <input name={`brandLabel.${itemKey}`} type="hidden" value={product.brandLabel} />
      <input name={`productKey.${itemKey}`} type="hidden" value={product.productKey} />
      <input name={`productLabel.${itemKey}`} type="hidden" value={product.productLabel} />
      <input name={`ingredientKey.${itemKey}`} type="hidden" value={ingredient.ingredientKey} />
      <input name={`ingredientLabel.${itemKey}`} type="hidden" value={ingredient.ingredientLabel} />
      <input name={`category.${itemKey}`} type="hidden" value={ingredient.category} />
      <input name={`timeOfDay.${itemKey}`} type="hidden" value={product.defaultTimeOfDay} />
      <input name={`amount.${itemKey}`} type="hidden" value={ingredient.amount ?? ""} />
      <input name={`unit.${itemKey}`} type="hidden" value={ingredient.unit ?? ""} />
      <input name={`caffeineMg.${itemKey}`} type="hidden" value={ingredient.caffeineMg ?? ""} />
      <input name={`notes.${itemKey}`} type="hidden" value={ingredient.notes ?? product.evidence} />
    </>
  );
}

function ingredientAmount(ingredient: IntakeIngredientPreset): string {
  if (ingredient.amount === undefined || !ingredient.unit) {
    return "amount unknown";
  }

  return `${ingredient.amount} ${ingredient.unit}`;
}

function ingredientSummary(product: IntakeProductPreset): string {
  const highlights = product.ingredients
    .filter((ingredient) => ingredient.category !== "amino_acid" || ingredient.amount === undefined)
    .slice(0, 4)
    .map((ingredient) => ingredient.ingredientLabel);

  return `${product.ingredients.length} tracked ingredients: ${highlights.join(", ")}${product.ingredients.length > highlights.length ? ", and more" : ""}.`;
}

export default async function IntakePage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await resolveSearchParams(searchParams);
  const notice = await readNotice(searchParams);
  const selectedDate = params.date ?? formatDateInTimezone(new Date(), DEFAULT_TIMEZONE);
  const month = selectedDate.slice(0, 7);
  const events = await api.events({
    end: selectedDate,
    event_type: "intake",
    limit: 200,
    start: selectedDate,
  });
  const firstProduct = INTAKE_PRODUCTS[0];

  return (
    <div className="mx-auto space-y-6">
      <PageHeader
        actions={
          <form action={logIntakeAction}>
            <input name="localDate" type="hidden" value={selectedDate} />
            <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
            <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />
            {firstProduct.ingredients.map((ingredient) => (
              <span key={ingredient.ingredientKey}>{hiddenIngredientFields(firstProduct, ingredient)}</span>
            ))}
            <Button className="focus-ring" type="submit">
              Log {firstProduct.productLabel}
            </Button>
          </form>
        }
        eyebrow="Intake"
        subtitle="Track the actual ingredients inside your mushroom coffees, creamers, adaptogens, and sleep drinks."
        title="Ingredient-level intake tracker"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <section className="mt-6 border-4 border-slate-950 bg-blue-100 p-5">
        <h2 className="m-0 text-2xl font-black">Pick date</h2>
        <form className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end" method="GET">
          <label className="block flex-1">
            <span className="mb-2 block text-lg font-black">Date</span>
            <input className={fieldClassName()} defaultValue={selectedDate} name="date" type="date" />
          </label>
          <button className={buttonClassName("blue")} type="submit">
            Load
          </button>
        </form>
      </section>

      <section className="border-4 border-slate-950 bg-white p-5">
        <div className="border-b-4 border-slate-950 pb-3">
          <h2 className="m-0 text-3xl font-black uppercase">Brand bundles</h2>
          <p className="m-0 mt-2 text-base font-bold text-slate-700">
            Use these buttons when you consumed the whole product. HabitOS stores each included ingredient as its own intake event.
          </p>
        </div>
        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          {INTAKE_PRODUCTS.map((product) => (
            <article className="border-2 border-slate-950 bg-yellow-100 p-4" key={product.productKey}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="m-0 font-mono text-xs font-black tracking-[0.16em] text-slate-700 uppercase">
                    {product.brandLabel}
                  </p>
                  <h3 className="m-0 text-2xl font-black">{product.productLabel}</h3>
                  <p className="m-0 mt-2 text-sm font-bold text-slate-700">{product.evidence}</p>
                </div>
                <form action={logIntakeAction} className="shrink-0">
                  <input name="localDate" type="hidden" value={selectedDate} />
                  <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
                  <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />
                  {product.ingredients.map((ingredient) => (
                    <span key={ingredient.ingredientKey}>{hiddenIngredientFields(product, ingredient)}</span>
                  ))}
                  <button className={buttonClassName("green")} type="submit">
                    Log full bundle
                  </button>
                </form>
              </div>
              <p className="m-0 mt-4 border-2 border-slate-950 bg-white p-3 text-sm font-black text-slate-800">
                {ingredientSummary(product)}
              </p>
              <details className="mt-3 border-2 border-slate-950 bg-white p-3">
                <summary className="cursor-pointer font-mono text-xs font-black uppercase tracking-[0.16em] text-slate-700">
                  View ingredient list
                </summary>
                <div className="mt-3 flex flex-wrap gap-2">
                  {product.ingredients.map((ingredient) => (
                    <span className="border-2 border-slate-950 bg-slate-50 px-2 py-1 font-mono text-xs font-black" key={ingredient.ingredientKey}>
                      {ingredient.ingredientLabel} · {ingredientAmount(ingredient)}
                    </span>
                  ))}
                </div>
              </details>
            </article>
          ))}
        </div>
      </section>

      <details className="mt-6 border-4 border-slate-950 bg-white p-5">
        <summary className="cursor-pointer text-2xl font-black uppercase text-slate-950">
          Advanced: pick individual ingredients
        </summary>
        <p className="m-0 mt-3 max-w-3xl text-base font-bold text-slate-700">
          Most days, use the product bundle buttons above. Open this only when you skipped or mixed specific components.
        </p>

        <form action={logIntakeAction} className="mt-5">
          <input name="localDate" type="hidden" value={selectedDate} />
          <input name="returnPath" type="hidden" value={`${RETURN_PATH}?date=${selectedDate}`} />
          <input name="timezone" type="hidden" value={DEFAULT_TIMEZONE} />

          <div className="grid gap-4">
            {INTAKE_PRODUCTS.map((product) => (
              <fieldset className="border-2 border-slate-950 bg-slate-50 p-4" key={product.productKey}>
                <legend className="px-2 text-xl font-black">{product.productLabel}</legend>
                <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                  {product.ingredients.map((ingredient) => {
                    const itemKey = intakeItemKey(product.productKey, ingredient.ingredientKey);
                    const label = `${product.productLabel} — ${ingredient.ingredientLabel}`;

                    return (
                      <label className="block border-2 border-slate-950 bg-white p-3" key={itemKey}>
                        <span className="flex gap-3 text-lg font-black">
                          <input className="mt-1 size-5" name="itemKey" type="checkbox" value={itemKey} />
                          <span>{ingredient.ingredientLabel}</span>
                        </span>
                        <span className="mt-1 block font-mono text-xs font-black uppercase text-slate-600">
                          {ingredient.category} · {ingredientAmount(ingredient)}
                        </span>
                        <input name={`itemLabel.${itemKey}`} type="hidden" value={label} />
                        <input name={`brandKey.${itemKey}`} type="hidden" value={product.brandKey} />
                        <input name={`brandLabel.${itemKey}`} type="hidden" value={product.brandLabel} />
                        <input name={`productKey.${itemKey}`} type="hidden" value={product.productKey} />
                        <input name={`productLabel.${itemKey}`} type="hidden" value={product.productLabel} />
                        <input name={`ingredientKey.${itemKey}`} type="hidden" value={ingredient.ingredientKey} />
                        <input name={`ingredientLabel.${itemKey}`} type="hidden" value={ingredient.ingredientLabel} />
                        <input name={`category.${itemKey}`} type="hidden" value={ingredient.category} />
                        <input name={`timeOfDay.${itemKey}`} type="hidden" value={product.defaultTimeOfDay} />
                        <input name={`amount.${itemKey}`} type="hidden" value={ingredient.amount ?? ""} />
                        <input name={`unit.${itemKey}`} type="hidden" value={ingredient.unit ?? ""} />
                        <input name={`caffeineMg.${itemKey}`} type="hidden" value={ingredient.caffeineMg ?? ""} />
                        <input name={`notes.${itemKey}`} type="hidden" value={ingredient.notes ?? product.evidence} />
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            ))}
          </div>

          <section className="mt-6 border-4 border-slate-950 bg-white p-5">
            <h2 className="m-0 text-2xl font-black">After saving</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="flex gap-3 border-2 border-slate-950 bg-green-100 p-4 text-xl font-black">
                <input className="mt-1 size-6" defaultChecked name="recompute" type="checkbox" value="true" />
                <span>Recompute {month}</span>
              </label>
              <label className="flex gap-3 border-2 border-slate-950 bg-blue-100 p-4 text-xl font-black">
                <input className="mt-1 size-6" name="render" type="checkbox" value="true" />
                <span>Render PDF too</span>
              </label>
            </div>
            <button className={`${buttonClassName("blue")} mt-5 w-full sm:w-auto`} type="submit">
              Save selected ingredients
            </button>
          </section>
        </form>
      </details>

      <section className="mt-6 border-4 border-slate-950 bg-white p-5">
        <h2 className="m-0 text-2xl font-black">Already saved for {selectedDate}</h2>
        {events.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[820px] border-collapse text-left">
              <thead>
                <tr className="bg-slate-950 text-white">
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Ingredient</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Product</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Category</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Time</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Amount</th>
                  <th className="border-2 border-slate-950 p-3 text-lg font-black">Notes</th>
                </tr>
              </thead>
              <tbody>
                {events.flatMap((event) =>
                  itemRecords(event).map((item, index) => (
                    <tr key={`${event.id}-${index}`}>
                      <td className="border-2 border-slate-950 p-3 text-lg font-bold">
                        {stringValue(item, "ingredient_label") || stringValue(item, "label") || stringValue(item, "key") || "Intake item"}
                      </td>
                      <td className="border-2 border-slate-950 p-3 text-sm font-black">
                        {stringValue(item, "product_label") || stringValue(item, "brand_label") || "—"}
                      </td>
                      <td className="border-2 border-slate-950 p-3 font-mono text-sm font-black uppercase">
                        {stringValue(item, "category") || "other"}
                      </td>
                      <td className="border-2 border-slate-950 p-3 font-mono text-sm font-black uppercase">
                        {stringValue(item, "time_of_day") || "unknown"}
                      </td>
                      <td className="border-2 border-slate-950 p-3 font-mono text-sm font-bold">
                        {[numberValue(item, "amount"), stringValue(item, "unit")].filter(Boolean).join(" ") || "—"}
                      </td>
                      <td className="border-2 border-slate-950 p-3 text-sm font-bold">
                        {stringValue(item, "notes") || "—"}
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 border-2 border-slate-950 bg-yellow-200 p-4 text-xl font-black">
            Nothing saved for this date yet.
          </p>
        )}
      </section>
    </div>
  );
}
