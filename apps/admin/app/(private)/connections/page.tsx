import Link from "next/link";
import { subDays } from "date-fns";
import { format } from "date-fns";

import { JsonPanel } from "@/components/common/json-panel";
import { NoticeBanner } from "@/components/common/notice-banner";
import { PageHeader, Section } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { dayOneSyncAction, whoopSyncAction } from "@/lib/actions";
import { api } from "@/lib/api-client";
import { readNotice } from "@/lib/notice";

const RETURN_PATH = "/connections";

/**
 * Connector and integration management surface.
 */
export default async function ConnectionsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const notice = await readNotice(searchParams);
  const defaultStart = format(subDays(new Date(), 14), "yyyy-MM-dd");
  const defaultEnd = format(new Date(), "yyyy-MM-dd");
  const [status, whoopStatus, dayOneStatus, remarkableStatus] = await Promise.all([
    api.status(),
    api.whoopStatus(),
    api.dayOneStatus(),
    api.remarkableStatus(),
  ]);

  return (
    <div className="space-y-16">
      <PageHeader
        eyebrow="Connections"
        subtitle="OAuth, SQLite reachability, and sync surfaces belong in one place."
        title="Connector status"
      />

      {notice ? <NoticeBanner tone={notice.tone}>{notice.message}</NoticeBanner> : null}

      <Section
        kicker="Actions"
        lede="Start OAuth and request connector syncs without exposing the API host to the browser."
        number="01"
        title="Connection controls"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <section className="paper-panel p-5">
            <p className="mono-label m-0">WHOOP</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button asChild className="focus-ring">
                <Link href="/api/connections/whoop/start">Start WHOOP OAuth</Link>
              </Button>
            </div>
            <form action={whoopSyncAction} className="mt-5 grid gap-3">
              <input name="returnPath" type="hidden" value={RETURN_PATH} />
              <input name="recompute" type="hidden" value="true" />
              <label className="space-y-2">
                <span className="field-label">External user ID</span>
                <Input name="externalUserId" placeholder="WHOOP user id" type="text" />
              </label>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="field-label">Start</span>
                  <Input defaultValue={defaultStart} name="start" type="date" />
                </label>
                <label className="space-y-2">
                  <span className="field-label">End</span>
                  <Input defaultValue={defaultEnd} name="end" type="date" />
                </label>
              </div>
              <Button className="focus-ring" type="submit" variant="outline">
                Request WHOOP sync
              </Button>
            </form>
          </section>

          <section className="paper-panel p-5">
            <p className="mono-label m-0">Day One</p>
            <form action={dayOneSyncAction} className="mt-4 grid gap-3">
              <input name="returnPath" type="hidden" value={RETURN_PATH} />
              <input name="recompute" type="hidden" value="true" />
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="field-label">Start</span>
                  <Input defaultValue={defaultStart} name="start" type="date" />
                </label>
                <label className="space-y-2">
                  <span className="field-label">End</span>
                  <Input defaultValue={defaultEnd} name="end" type="date" />
                </label>
              </div>
              <Button className="focus-ring" type="submit" variant="outline">
                Request Day One sync
              </Button>
            </form>
          </section>
        </div>
      </Section>

      <Section
        kicker="Payloads"
        lede="The backend still owns truth; the admin app makes that truth legible."
        number="02"
        title="Current connection state"
      >
        <div className="data-column grid gap-4 lg:grid-cols-2">
          <JsonPanel data={status} title="status" />
          <JsonPanel data={whoopStatus} title="whoop/status" />
          <JsonPanel data={dayOneStatus} title="dayone/status" />
          <JsonPanel data={remarkableStatus} title="remarkable/status" />
        </div>
      </Section>
    </div>
  );
}
