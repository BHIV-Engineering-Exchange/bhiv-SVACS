import runtime from "../mock/maritimeRuntime.json";

export default function ThreatAssessmentCard() {
  return (
    <div
      style={{
        border: "1px solid #333",
        padding: "20px",
        borderRadius: "10px",
        marginBottom: "20px"
      }}
    >
      <h2>Threat Assessment</h2>

      <p><strong>Threat Level:</strong> {runtime.threat_level}</p>

      <p>Runtime Operational</p>
    </div>
  );
}