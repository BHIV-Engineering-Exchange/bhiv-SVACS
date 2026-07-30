import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import { fmtUtc, fmtUtcDate } from "@/lib/time";
import { fmtConfidence, truncId } from "@/lib/format";
import { Radio, Eye, Brain, Flag, Search, AlertOctagon, Copy } from "lucide-react";
import type { StageId, TraceLifecycle } from "@/domain/types";
import clsx from "clsx";

const stageMeta: Record<StageId, { icon: typeof Radio; color: string; label: string }> = {
  signal: { icon: Radio, color: "text-stage-signal", label: "signal_chunk" },
  perception: { icon: Eye, color: "text-stage-perception", label: "perception_event" },
  intelligence: { icon: Brain, color: "text-stage-intelligence", label: "intelligence_event" },
  state: { icon: Flag, color: "text-stage-state", label: "state_event" },
  bucket: { icon: Radio, color: "text-stage-bucket", label: "bucket_write" },
};

export default function TraceExplorer() {
  const [traceId, setTraceId] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);

  const recentQ = useQuery({
    queryKey: ["recent-traces"],
    queryFn: async () => {
      const sigs = await adapter.fetchSignals();
      return sigs.slice(0, 12);
    },
    refetchInterval: 6000,
  });

  const traceQ = useQuery({
    queryKey: ["trace", submitted],
    queryFn: () => adapter.fetchTrace(submitted!),
    enabled: !!submitted,
  });

  const onSearch = () => setSubmitted(traceId.trim() || null);

  const useFirstAvailable = () => {
    const id = recentQ.data?.[0]?.trace_id;
    if (id) {
      setTraceId(id);
      setSubmitted(id);
    }
  };

  return (
    <div className="space-y-4">
      <Panel
        title="Trace Search"
        right={
          <button onClick={useFirstAvailable} className="text-2xs text-fg-2 hover:text-fg-0">
            Use first recent trace →
          </button>
        }
      >
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-2" />
            <input
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSearch()}
              placeholder="Paste a trace_id (e.g. trc_…)"
              className="input w-full pl-9 font-mono"
            />
          </div>
          <button onClick={onSearch} className="btn">
            Inspect
          </button>
        </div>

        {recentQ.data && (
          <div className="mt-3">
            <div className="mb-1 text-2xs uppercase tracking-[0.18em] text-fg-2">
              Recent traces
            </div>
            <div className="flex flex-wrap gap-1">
              {recentQ.data.slice(0, 8).map((s) => (
                <button
                  key={s.trace_id}
                  onClick={() => {
                    setTraceId(s.trace_id);
                    setSubmitted(s.trace_id);
                  }}
                  className="chip border-line bg-bg-2 font-mono text-fg-1 hover:text-fg-0"
                >
                  {truncId(s.trace_id, 8, 6)}
                </button>
              ))}
            </div>
          </div>
        )}
      </Panel>

      {submitted && traceQ.data && <Lifecycle data={traceQ.data} />}
      {!submitted && (
        <Panel title="Lifecycle">
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-sm text-fg-2">
            <Search size={20} />
            Enter a trace_id above or click a recent trace to inspect its full lifecycle.
          </div>
        </Panel>
      )}
    </div>
  );
}

function Lifecycle({ data }: { data: TraceLifecycle }) {
  const events: Array<
    | { stage: StageId; ts: string; node: React.ReactNode }
    | { stage: StageId; missing: true }
  > = [];

  const order: StageId[] = ["signal", "perception", "intelligence", "state"];
  const tsMap: Record<StageId, string | undefined> = {
    signal: data.signal?.ts_utc,
    perception: data.perception?.ts_utc,
    intelligence: data.intelligence?.ts_utc,
    state: data.state?.ts_utc,
    bucket: undefined,
  };

  for (const s of order) {
    const present = tsMap[s];
    if (!present) {
      events.push({ stage: s, missing: true });
      continue;
    }
    let body: React.ReactNode = null;
    if (s === "signal" && data.signal) {
      body = <KV pairs={{
        chunk_id: data.signal.chunk_id,
        vessel_id: data.signal.vessel_id ?? "—",
        source: data.signal.source,
        frequency_band: data.signal.frequency_band ?? "—",
      }} />;
    } else if (s === "perception" && data.perception) {
      body = <KV pairs={{
        kind: data.perception.kind,
        vessel_id: data.perception.vessel_id ?? "—",
        confidence: fmtConfidence(data.perception.confidence),
      }} />;
    } else if (s === "intelligence" && data.intelligence) {
      body = <KV pairs={{
        validation: data.intelligence.validation,
        confidence: fmtConfidence(data.intelligence.confidence),
        reasons: data.intelligence.reasons.join(", "),
      }} />;
    } else if (s === "state" && data.state) {
      body = <KV pairs={{
        from_state: data.state.from_state,
        to_state: data.state.to_state,
        validation: data.state.validation,
        confidence: fmtConfidence(data.state.confidence),
      }} />;
    }
    events.push({ stage: s, ts: present, node: body });
  }

  return (
    <Panel
      title="Trace Lifecycle"
      right={
        <button
          onClick={() => navigator.clipboard?.writeText(data.trace_id)}
          className="flex items-center gap-1 text-2xs text-fg-2 hover:text-fg-0"
        >
          <Copy size={11} /> {truncId(data.trace_id, 12, 6)}
        </button>
      }
    >
      <ol className="relative space-y-3">
        <span className="absolute left-[15px] top-2 bottom-2 w-px bg-line" />
        {events.map((e, idx) => {
          if ("missing" in e) {
            return (
              <li key={idx} className="relative flex items-start gap-3 pl-9">
                <span className="absolute left-[6px] top-2 flex h-[18px] w-[18px] items-center justify-center rounded-full border border-err/60 bg-bg-1 text-err">
                  <AlertOctagon size={11} />
                </span>
                <div className="flex-1 rounded-md border border-err/30 bg-err/10 px-3 py-2 text-xs text-err">
                  <span className="font-semibold uppercase tracking-[0.14em]">
                    {stageMeta[e.stage].label}
                  </span>{" "}
                  missing — continuity gap detected
                </div>
              </li>
            );
          }
          const meta = stageMeta[e.stage];
          const Icon = meta.icon;
          return (
            <li key={idx} className="relative flex items-start gap-3 pl-9">
              <span
                className={clsx(
                  "absolute left-[6px] top-2 flex h-[18px] w-[18px] items-center justify-center rounded-full border bg-bg-1",
                  meta.color,
                  "border-current",
                )}
              >
                <Icon size={10} />
              </span>
              <div className="flex-1 rounded-md border border-line bg-bg-2/40 px-3 py-2">
                <div className="flex items-center justify-between text-xs">
                  <span className={clsx("font-semibold uppercase tracking-[0.14em]", meta.color)}>
                    {meta.label}
                  </span>
                  <span className="font-mono tabular-nums text-fg-2">
                    {fmtUtcDate(e.ts)} UTC
                  </span>
                </div>
                <div className="mt-1.5">{e.node}</div>
              </div>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}

function KV({ pairs }: { pairs: Record<string, string> }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      {Object.entries(pairs).map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-mono text-fg-2">{k}</dt>
          <dd className="font-mono text-fg-0">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
