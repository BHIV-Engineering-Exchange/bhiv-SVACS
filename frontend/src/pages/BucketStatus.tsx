import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import BucketSyncDonut from "@/components/charts/BucketSyncDonut";
import StatusDot from "@/components/shell/StatusDot";
import { fmtUtcDate } from "@/lib/time";
import { fmtNum } from "@/lib/format";

export default function BucketStatus() {
  const bucketQ = useQuery({ queryKey: ["bucket"], queryFn: () => adapter.fetchBucketStatus(), refetchInterval: 4000 });
  const data = bucketQ.data;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-12 gap-3">
        <Panel title="Bucket Sync" className="col-span-12 lg:col-span-4">
          {data && <BucketSyncDonut status={data} />}
        </Panel>

        <Panel title="Storage Verification" className="col-span-12 lg:col-span-8">
          {data && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Stat label="Sync %" value={`${(data.sync_percent * 100).toFixed(1)}%`} />
              <Stat label="Pending writes" value={fmtNum(data.pending_writes)} />
              <Stat label="Failed writes" value={fmtNum(data.failed_writes)} bad={data.failed_writes > 0} />
              <Stat label="Stages synced" value={`${data.stages_synced.length} / 4`} />
            </div>
          )}
          <div className="mt-4 flex items-center gap-2 text-xs">
            <StatusDot status={data?.failed_writes ? "degraded" : "live"} />
            <span className="text-fg-1">
              Last sync: <span className="font-mono">{data ? fmtUtcDate(data.last_sync_utc) : "—"}</span> UTC
            </span>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Stat({ label, value, bad }: { label: string; value: string; bad?: boolean }) {
  return (
    <div className="rounded-md border border-line bg-bg-2/40 p-4">
      <div className="text-2xs uppercase tracking-[0.18em] text-fg-2">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${bad ? "text-err" : "text-fg-0"}`}>
        {value}
      </div>
    </div>
  );
}
