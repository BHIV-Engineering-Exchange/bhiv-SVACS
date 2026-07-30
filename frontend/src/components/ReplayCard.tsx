import runtime from "../mock/maritimeRuntime.json";

export default function ReplayCard() {
  return (
    <div
      style={{
        border: "1px solid #333",
        padding: "20px",
        borderRadius: "10px",
        marginBottom: "20px"
      }}
    >
      <h2>Replay Status</h2>

      <p>{runtime.replay_status}</p>
    </div>
  );
}