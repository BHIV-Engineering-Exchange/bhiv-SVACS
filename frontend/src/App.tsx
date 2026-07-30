import { Routes, Route, Navigate } from "react-router-dom";
import AppShell from "./components/shell/AppShell";
import Overview from "./pages/Overview";
import LivePipeline from "./pages/LivePipeline";
import Signals from "./pages/Signals";
import Perception from "./pages/Perception";
import Intelligence from "./pages/Intelligence";
import StateEngine from "./pages/StateEngine";
import Vessels from "./pages/Vessels";
import Alerts from "./pages/Alerts";
import TraceExplorer from "./pages/TraceExplorer";
import BucketStatus from "./pages/BucketStatus";
import SystemHealth from "./pages/SystemHealth";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Overview />} />
        <Route path="/pipeline" element={<LivePipeline />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/perception" element={<Perception />} />
        <Route path="/intelligence" element={<Intelligence />} />
        <Route path="/state" element={<StateEngine />} />
        <Route path="/vessels" element={<Vessels />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/trace" element={<TraceExplorer />} />
        <Route path="/bucket" element={<BucketStatus />} />
        <Route path="/health" element={<SystemHealth />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
