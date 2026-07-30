import MaritimeIntelligenceCard from "../components/MaritimeIntelligenceCard";
import ReplayCard from "../components/ReplayCard";
import TTGCard from "../components/TTGCard";
import ThreatAssessmentCard from "../components/ThreatAssessmentCard";
import SensorFusionCard from "../components/SensorFusionCard";
import KnowledgeLineageCard from "../components/KnowledgeLineageCard";
import VesselMatchCard from "../components/VesselMatchCard";

export default function MaritimeCommandCenter() {
  return (
    <div style={{ padding: "30px" }}>
      <h1>SVACS Maritime Command Center</h1>

      <MaritimeIntelligenceCard />

      <VesselMatchCard />

      <SensorFusionCard />

      <KnowledgeLineageCard />

      <ReplayCard />

      <TTGCard />

      <ThreatAssessmentCard />
    </div>
  );
}