import { useEffect, useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { adapter } from "@/api/adapter";
import Panel from "@/components/primitives/Panel";
import { fmtUtc } from "@/lib/time";
import { truncId } from "@/lib/format";
import { Search, Upload, Loader2, Camera, Image as ImageIcon, File as FileIcon, Scan, X } from "lucide-react";

import { env } from "@/env";

const rawApi = env.api.intelligence || env.api.signal;
const SVACS_API = rawApi.replace(/\/+$/, "");

export default function Signals() {
  const [q, setQ] = useState("");
  const [src, setSrc] = useState<"ALL" | "AIS" | "RADAR" | "ACOUSTIC" | "OTHER">("ALL");

  const [uploading, setUploading]     = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [uploadError, setUploadError]   = useState<string | null>(null);
  const [previewUrl, setPreviewUrl]     = useState<string | null>(null);
  const [showUploadMenu, setShowUploadMenu] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const photoLibRef = useRef<HTMLInputElement>(null);

  const [pendingFile, setPendingFile] = useState<globalThis.File | null>(null);
  const [navalLength, setNavalLength] = useState("");
  const [navalBeam, setNavalBeam] = useState("");
  const [navalDisplacement, setNavalDisplacement] = useState("");
  const [navalVesselType, setNavalVesselType] = useState("");
  const [navalHullColor, setNavalHullColor] = useState("");
  const [navalDescription, setNavalDescription] = useState("");

  const hasAnyNavalField = Boolean(
    navalLength || navalBeam || navalDisplacement || navalVesselType || navalHullColor || navalDescription
  );
  const canAnalyze = Boolean(pendingFile || hasAnyNavalField);

  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const sigQ = useQuery({
    queryKey: ["signals"],
    queryFn: () => adapter.fetchSignals(),
    refetchInterval: 3000,
  });

  const rows = (sigQ.data ?? [])
    .filter((s) => src === "ALL" || s.source === src)
    .filter(
      (s) =>
        !q ||
        s.trace_id.toLowerCase().includes(q.toLowerCase()) ||
        (s.vessel_id ?? "").toLowerCase().includes(q.toLowerCase()),
    );

  const startCamera = async () => {
    setShowUploadMenu(false);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      setIsCameraOpen(true);
    } catch (err) {
      console.error("Failed to access camera", err);
      alert("Failed to access camera. Please ensure permissions are granted.");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.pause();
    }
    setIsCameraOpen(false);
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" });
            selectFile(file);
            stopCamera();
          }
        }, "image/jpeg", 0.9);
      }
    }
  };

  useEffect(() => {
    if (isCameraOpen && streamRef.current && videoRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [isCameraOpen]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []);

  function selectFile(file: globalThis.File) {
    if (!file.type.startsWith("image/")) {
      setUploadError("Please select a valid image file.");
      return;
    }
    if (file.size === 0) {
      setUploadError("The selected image is empty.");
      return;
    }
    setPendingFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setUploadResult(null);
    setUploadError(null);
  }

  function clearAll() {
    setPendingFile(null);
    setPreviewUrl(null);
    setUploadResult(null);
    setUploadError(null);
    setNavalLength("");
    setNavalBeam("");
    setNavalDisplacement("");
    setNavalVesselType("");
    setNavalHullColor("");
    setNavalDescription("");
  }

  async function analyzeWithImage() {
    if (!pendingFile) return;
    const file = pendingFile;

    setUploadResult(null);
    setUploadError(null);
    setUploading(true);

    const endpoints = SVACS_API
      ? [`${SVACS_API}/intelligence/image?quick=true`]
      : ["http://localhost:8000/intelligence/image?quick=true"];

    const uniqueEndpoints = Array.from(new Set(endpoints));

    let lastError: Error | null = null;
    let successResult = null;

    for (const endpoint of uniqueEndpoints) {
      try {
        const form = new FormData();
        form.append("file", file);
        if (navalLength) form.append("length_m", navalLength);
        if (navalBeam) form.append("beam_m", navalBeam);
        if (navalDisplacement) form.append("displacement_tons", navalDisplacement);
        if (navalVesselType) form.append("vessel_type", navalVesselType);
        if (navalHullColor) form.append("hull_color", navalHullColor);
        if (navalDescription) form.append("description", navalDescription);

        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 150000);
        const res = await fetch(endpoint, {
          method: "POST",
          body: form,
          signal: controller.signal,
        });
        window.clearTimeout(timeoutId);

        const payload = await res.json().catch(() => null);

        if (res.ok) {
          successResult = { ...payload, isTextOnly: false };
          break;
        } else {
          const detail = payload?.detail;
          const message = typeof detail === "string" ? detail : detail?.message || detail?.error;
          lastError = new Error(message || `Server returned HTTP ${res.status}`);
        }
      } catch (err: any) {
        lastError = err?.name === "AbortError"
          ? new Error("Backend image analysis timed out after 150 seconds. Check the Render backend deployment logs.")
          : err;
      }
    }

    if (successResult !== null) {
      setUploadResult(successResult);
      if (successResult.explainable_image_base64) {
        setPreviewUrl(`data:image/jpeg;base64,${successResult.explainable_image_base64}`);
      }
    } else {
      setUploadError(
        lastError?.message === "Failed to fetch"
          ? `Cannot connect to the configured backend at ${SVACS_API || "the local API"}. Check the frontend API URL and backend CORS settings.`
          : lastError?.message || "Upload failed"
      );
    }
    setUploading(false);
  }

  async function analyzeTextOnly() {
    setUploadResult(null);
    setUploadError(null);
    setUploading(true);

    const endpoint = SVACS_API
      ? `${SVACS_API}/naval/identify`
      : "http://localhost:8000/naval/identify";

    try {
      const form = new FormData();
      if (navalLength) form.append("length_m", navalLength);
      if (navalBeam) form.append("beam_m", navalBeam);
      if (navalDisplacement) form.append("displacement_tons", navalDisplacement);
      if (navalVesselType) form.append("vessel_type", navalVesselType);
      if (navalHullColor) form.append("hull_color", navalHullColor);
      if (navalDescription) form.append("description", navalDescription);

      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 30000);
      const res = await fetch(endpoint, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      window.clearTimeout(timeoutId);

      const payload = await res.json().catch(() => null);

      if (res.ok && payload) {
        setUploadResult({
          isTextOnly: true,
          naval_knowledge_candidates: payload.candidates,
          naval_knowledge_note:
            "These are knowledge-based candidate matches from curated Indian Naval specs, based on the details you provided. No image was analyzed.",
        });
      } else {
        setUploadError(payload?.detail || `Server returned HTTP ${res.status}`);
      }
    } catch (err: any) {
      setUploadError(
        err?.name === "AbortError"
          ? "Request timed out."
          : err?.message === "Failed to fetch"
          ? `Cannot connect to the configured backend at ${SVACS_API || "the local API"}. Check the frontend API URL and backend CORS settings.`
          : err?.message || "Request failed"
      );
    }
    setUploading(false);
  }

  function analyze() {
    if (pendingFile) {
      analyzeWithImage();
    } else if (hasAnyNavalField) {
      analyzeTextOnly();
    }
  }

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    selectFile(file);
    e.target.value = "";
  }

  const riskColor: Record<string, string> = {
    LOW:      "text-green-400",
    MEDIUM:   "text-yellow-400",
    HIGH:     "text-orange-400",
    CRITICAL: "text-red-500",
  };

  const validationBg: Record<string, string> = {
    ALLOW: "bg-green-500/20 text-green-400",
    FLAG:  "bg-yellow-500/20 text-yellow-400",
    DENY:  "bg-red-500/20 text-red-400",
  };

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Vessel Image Intelligence" noPad={false} overflowVisible className="relative z-30">
        <div className="flex flex-col gap-4">
          <p className="text-sm text-fg-2">
            Upload a vessel photograph, and/or tell us what you know, to identify vessel class, operator, and risk level. An image is not required.
          </p>

          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setShowUploadMenu(!showUploadMenu)}
                disabled={uploading}
                className="flex items-center gap-2 rounded-full border border-accent-cyan/40 bg-accent-cyan/10 px-5 py-2.5 text-sm font-medium text-accent-cyan hover:bg-accent-cyan/20 disabled:opacity-50 transition-all shadow-sm"
              >
                {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                {uploading ? "Analysing..." : "Upload Vessel Image (optional)"}
              </button>

              {showUploadMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowUploadMenu(false)} />
                  <div className="absolute top-full left-0 mt-2 w-56 rounded-xl border border-line bg-bg-1 shadow-2xl z-20 overflow-hidden flex flex-col py-2 animate-in fade-in slide-in-from-top-2">
                    <button className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-bg-2/50 text-left transition-colors" onClick={() => { fileInputRef.current?.click(); setShowUploadMenu(false); }}>
                      <FileIcon size={18} className="text-fg-1" />
                      <span className="font-medium text-fg-0">Attach File</span>
                    </button>
                    <button className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-bg-2/50 text-left transition-colors" onClick={() => { fileInputRef.current?.click(); setShowUploadMenu(false); }}>
                      <Scan size={18} className="text-fg-1" />
                      <span className="font-medium text-fg-0">Scan Document</span>
                    </button>
                    <button className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-bg-2/50 text-left transition-colors" onClick={() => { photoLibRef.current?.click(); setShowUploadMenu(false); }}>
                      <ImageIcon size={18} className="text-fg-1" />
                      <span className="font-medium text-fg-0">Photo Library</span>
                    </button>
                    <button className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-bg-2/50 text-left transition-colors" onClick={startCamera}>
                      <Camera size={18} className="text-fg-1" />
                      <span className="font-medium text-fg-0">Take Photo</span>
                    </button>
                  </div>
                </>
              )}
            </div>
            <span className="text-xs text-fg-2">
              JPG, PNG — image will be processed through Samachar Vision Runtime
            </span>
            <input ref={fileInputRef} type="file" accept="image/*,image/jpeg,image/png,image/webp,image/gif" className="hidden" onChange={handleImageUpload} />
            <input ref={photoLibRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
          </div>

          {isCameraOpen && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-bg-0/80 backdrop-blur-sm p-4">
              <div className="flex flex-col gap-4 rounded-2xl border border-line bg-bg-1 p-6 shadow-2xl animate-in zoom-in-95 max-w-3xl w-full">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-fg-0 flex items-center gap-2">
                    <Camera size={20} className="text-accent-cyan" />
                    Take Photo
                  </h3>
                  <button onClick={stopCamera} className="rounded-full p-2 text-fg-2 hover:bg-bg-2 hover:text-fg-0 transition-colors">
                    <X size={20} />
                  </button>
                </div>
                <div className="relative overflow-hidden rounded-xl bg-black aspect-video w-full flex items-center justify-center">
                  <video ref={videoRef} autoPlay playsInline className="h-full w-full object-contain" />
                </div>
                <div className="flex justify-center mt-4 gap-4">
                  <button onClick={stopCamera} className="flex items-center gap-2 rounded-full border border-line bg-bg-2 px-6 py-3 font-bold text-fg-1 hover:text-fg-0 hover:bg-bg-3 transition-all active:scale-95">
                    <X size={20} />
                    Close Camera
                  </button>
                  <button onClick={capturePhoto} className="flex items-center gap-2 rounded-full bg-accent-cyan px-8 py-3 font-bold text-bg-0 hover:bg-accent-cyan/90 transition-all active:scale-95 shadow-lg shadow-accent-cyan/20">
                    <Camera size={20} />
                    Capture Photo
                  </button>
                </div>
                <canvas ref={canvasRef} className="hidden" />
              </div>
            </div>
          )}

          {!uploadResult && (
            <div className="rounded-xl border border-line bg-bg-2/40 p-4 flex flex-col gap-3">
              <p className="text-xs text-fg-2">
                Optional — add any details you know, with or without an image. All fields are optional.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-2xs uppercase tracking-widest text-fg-2">Approx. Length (m)</label>
                  <input type="number" value={navalLength} onChange={(e) => setNavalLength(e.target.value)} placeholder="e.g. 160" className="input w-full mt-1" disabled={uploading} />
                </div>
                <div>
                  <label className="text-2xs uppercase tracking-widest text-fg-2">Approx. Beam / Width (m)</label>
                  <input type="number" value={navalBeam} onChange={(e) => setNavalBeam(e.target.value)} placeholder="e.g. 17.4" className="input w-full mt-1" disabled={uploading} />
                </div>
                <div>
                  <label className="text-2xs uppercase tracking-widest text-fg-2">Approx. Displacement (tonnes)</label>
                  <input type="number" value={navalDisplacement} onChange={(e) => setNavalDisplacement(e.target.value)} placeholder="e.g. 7500" className="input w-full mt-1" disabled={uploading} />
                </div>
                <div>
                  <label className="text-2xs uppercase tracking-widest text-fg-2">Vessel Type</label>
                  <select value={navalVesselType} onChange={(e) => setNavalVesselType(e.target.value)} className="input w-full mt-1" disabled={uploading}>
                    <option value="">Unknown / not sure</option>
                    <option value="destroyer">Destroyer</option>
                    <option value="frigate">Frigate</option>
                    <option value="corvette">Corvette</option>
                    <option value="carrier">Aircraft Carrier</option>
                    <option value="submarine">Submarine</option>
                  </select>
                </div>
                <div>
                  <label className="text-2xs uppercase tracking-widest text-fg-2">Hull Colour</label>
                  <input type="text" value={navalHullColor} onChange={(e) => setNavalHullColor(e.target.value)} placeholder="e.g. grey" className="input w-full mt-1" disabled={uploading} />
                </div>
                <div className="col-span-2">
                  <label className="text-2xs uppercase tracking-widest text-fg-2">Description (funnels, mast, superstructure, etc.)</label>
                  <textarea value={navalDescription} onChange={(e) => setNavalDescription(e.target.value)} placeholder="e.g. single funnel, angled stealth superstructure" className="input w-full mt-1" rows={2} disabled={uploading} />
                </div>
              </div>

              {pendingFile && (
                <p className="text-2xs text-fg-2">
                  Image staged: <span className="text-fg-0">{pendingFile.name}</span> — will be analyzed by the trained vision model, alongside any details above.
                </p>
              )}
              {!pendingFile && (
                <p className="text-2xs text-fg-2 italic">
                  No image selected — submitting will match only against the details above using the knowledge pack (no vision-model result).
                </p>
              )}

              <div className="flex gap-2">
                <button onClick={analyze} disabled={uploading || !canAnalyze} className="flex items-center gap-2 rounded-full bg-accent-cyan px-5 py-2 text-sm font-bold text-bg-0 hover:bg-accent-cyan/90 disabled:opacity-50 transition-all active:scale-95">
                  {uploading ? <Loader2 size={14} className="animate-spin" /> : <Scan size={14} />}
                  {uploading ? "Analysing..." : "Analyze"}
                </button>
                <button onClick={clearAll} disabled={uploading} className="rounded-full border border-line px-5 py-2 text-sm text-fg-1 hover:bg-bg-2 disabled:opacity-50 transition-all">
                  Clear
                </button>
              </div>
              {!canAnalyze && (
                <p className="text-2xs text-fg-2">Select an image and/or fill in at least one detail above to enable Analyze.</p>
              )}
            </div>
          )}

          {(previewUrl || uploadResult || uploadError) && (
            <div className="flex gap-4">
              {previewUrl && (
                <img src={previewUrl} alt="Vessel" className="h-40 w-60 rounded border border-line object-cover" />
              )}

              {uploading && (
                <div className="flex items-center gap-2 text-sm text-fg-2">
                  <Loader2 size={14} className="animate-spin" />
                  {pendingFile ? "Processing through Samachar → SVACS pipeline..." : "Matching against Indian Naval knowledge pack..."}
                </div>
              )}

              {uploadError && (
                <div className="rounded border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
                  {uploadError}
                </div>
              )}

              {uploadResult && (
                <div className="flex flex-col gap-2 rounded border border-line bg-bg-2/40 p-4 text-sm flex-1">
                  {!uploadResult.isTextOnly && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-xs uppercase tracking-widest text-fg-2">Vessel Identification</span>
                        <span className={`rounded px-2 py-0.5 text-xs font-bold ${validationBg[uploadResult.validation_status] ?? ""}`}>
                          {uploadResult.validation_status}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-x-6 gap-y-1 font-mono">
                        <span className="text-fg-2">Ship Type</span>
                        <span className="font-bold text-fg-0 uppercase">{uploadResult.vessel_class}</span>

                        <span className="text-fg-2">Confidence</span>
                        <span className="text-fg-0">{(uploadResult.confidence_score * 100).toFixed(1)}%</span>

                        {uploadResult.top_predictions && uploadResult.top_predictions.length > 0 && (
                          <>
                            <span className="text-fg-2 mt-2">Top Predictions</span>
                            <div className="flex flex-col mt-2">
                              {uploadResult.top_predictions.map((p: any, idx: number) => (
                                <span key={idx} className="text-fg-1 text-xs">
                                  {idx + 1}. {p.class} ({Number(p.confidence).toFixed(1)}%)
                                </span>
                              ))}
                            </div>
                          </>
                        )}

                        <span className="text-fg-2 mt-2">Risk Level</span>
                        <span className={`font-bold mt-2 ${riskColor[uploadResult.risk_level] ?? ""}`}>
                          {uploadResult.risk_level}
                        </span>

                        <span className="text-fg-2 mt-2">OCR Text</span>
                        <span className="text-fg-0 mt-2">{uploadResult.ocr_text ?? "—"}</span>

                        <span className="text-fg-2 mt-2">Trace ID</span>
                        <span className="text-accent-cyan mt-2">{truncId(uploadResult.trace_id)}</span>

                        <span className="text-fg-2 mt-2">Source</span>
                        <span className="text-fg-0 mt-2">{uploadResult.classification_source ?? "YOLO"}</span>
                      </div>

                      <div className="mt-2 border-t border-line pt-2">
                        <p className="text-xs text-fg-2 mb-1">Explanation</p>
                        <ul className="text-xs text-fg-1 space-y-0.5 list-disc list-inside">
                          {Array.isArray(uploadResult.explanation)
                            ? uploadResult.explanation.map((e: string, i: number) => <li key={i}>{e}</li>)
                            : <li>{uploadResult.explanation}</li>}
                        </ul>
                      </div>
                    </>
                  )}

                  {uploadResult.naval_knowledge_candidates && uploadResult.naval_knowledge_candidates.length > 0 && (
                    <div className={uploadResult.isTextOnly ? "" : "border-t border-line pt-2"}>
                      <p className="text-xs text-fg-2 mb-1">Naval Knowledge Pack — Candidate Matches</p>
                      {uploadResult.naval_knowledge_note && (
                        <p className="text-2xs text-fg-2 italic mb-1">{uploadResult.naval_knowledge_note}</p>
                      )}
                      <ul className="text-xs text-fg-1 space-y-1">
                        {uploadResult.naval_knowledge_candidates.map((c: any, i: number) => (
                          <li key={i}>
                            <span className="font-bold text-fg-0">{c.class_name ?? "No match"}</span>
                            {c.confidence_pct != null && (
                              <span className="text-accent-cyan"> — {c.confidence_pct}%</span>
                            )}
                            {c.risk_level && (
                              <span className={`ml-2 font-bold ${riskColor[c.risk_level] ?? ""}`}>
                                [{c.risk_level}]
                              </span>
                            )}
                            {c.reasoning && c.reasoning.length > 0 && (
                              <ul className="list-disc list-inside ml-3 text-fg-2">
                                {c.reasoning.map((r: string, j: number) => <li key={j}>{r}</li>)}
                              </ul>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {uploadResult.ship_identification && uploadResult.ship_identification.method !== "not_applicable" && (
                    <div className="border-t border-line pt-2">
                      <p className="text-xs text-fg-2 mb-1">Ship Identification</p>
                      {uploadResult.ship_identification.matched ? (
                        <p className="text-sm text-fg-0">
                          <span className="font-bold">{uploadResult.ship_identification.ship_name}</span>
                          {" "}({uploadResult.ship_identification.pennant}) — identified via hull pennant number
                        </p>
                      ) : (
                        <div className="text-xs text-fg-1">
                          <p className="italic text-fg-2 mb-1">Pennant number not legible — possible ships in this class:</p>
                          <ul className="list-disc list-inside">
                            {uploadResult.ship_identification.roster.map((s: any, i: number) => (
                              <li key={i}>{s.name} ({s.pennant})</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {!uploadResult.isTextOnly && uploadResult.evidence_chain?.length > 0 && (
                    <div className="border-t border-line pt-2">
                      <p className="text-xs text-fg-2 mb-1">Evidence Chain</p>
                      <ul className="text-xs text-fg-1 space-y-0.5">
                        {uploadResult.evidence_chain.map((e: string, i: number) => (
                          <li key={i} className="flex gap-1">
                            <span className="text-accent-cyan">—</span> {e}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="mt-1">
                    <button onClick={clearAll} className="text-xs text-accent-cyan hover:underline">
                      Start a new search
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </Panel>

      <Panel
        title="Signal Chunks (Live)"
        noPad
        right={
          <div className="flex items-center gap-2">
            <select value={src} onChange={(e) => setSrc(e.target.value as typeof src)} className="input">
              <option value="ALL">All sources</option>
              <option value="AIS">AIS</option>
              <option value="RADAR">RADAR</option>
              <option value="ACOUSTIC">ACOUSTIC</option>
              <option value="OTHER">OTHER</option>
            </select>
            <div className="relative">
              <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-fg-2" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by trace_id or vessel" className="input pl-7" />
            </div>
          </div>
        }
      >
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-2xs uppercase tracking-[0.14em] text-fg-2">
              <th className="px-4 py-2">Time (UTC)</th>
              <th className="px-4 py-2">Trace ID</th>
              <th className="px-4 py-2">Chunk</th>
              <th className="px-4 py-2">Vessel</th>
              <th className="px-4 py-2">Source</th>
              <th className="px-4 py-2">Frequency</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {rows.map((s) => (
              <tr key={s.chunk_id} className="border-t border-line/60 hover:bg-bg-2/40">
                <td className="px-4 py-2 tabular-nums text-fg-1">{fmtUtc(s.ts_utc)}</td>
                <td className="px-4 py-2 text-accent-cyan">{truncId(s.trace_id)}</td>
                <td className="px-4 py-2 text-fg-1">{s.chunk_id}</td>
                <td className="px-4 py-2 text-fg-0">{s.vessel_id ?? "—"}</td>
                <td className="px-4 py-2 text-fg-1">{s.source}</td>
                <td className="px-4 py-2 text-fg-1">{s.frequency_band ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
