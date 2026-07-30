import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

interface Point {
  time?: string;
  label?: string;
  ts?: string;
  signal: number;
  perception: number;
  intelligence: number;
  state: number;
}

const colors = {
  signal: "#22d3ee",
  perception: "#4ade80",
  intelligence: "#a78bfa",
  state: "#fbbf24",
};

export default function EventsOverTime({
  data,
}: {
  data: Point[];
}) {
  const timeKey =
    data[0]?.time != null ? "time" : data[0]?.label != null ? "label" : "ts";

  return (
    <div className="chart-surface h-full min-h-[260px] w-full flex-1">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{
            top: 8,
            right: 12,
            left: 4,
            bottom: 4,
          }}
        >
          <CartesianGrid
            stroke="#1c2530"
            strokeDasharray="3 3"
            vertical={false}
          />

          <XAxis
            dataKey={timeKey}
            stroke="#5e6b76"
            tick={{
              fontSize: 10,
              fontFamily: "JetBrains Mono",
            }}
            axisLine={{ stroke: "#1c2530" }}
            tickLine={false}
          />

          <YAxis
            stroke="#5e6b76"
            tick={{
              fontSize: 10,
              fontFamily: "JetBrains Mono",
            }}
            axisLine={{ stroke: "#1c2530" }}
            tickLine={false}
            width={42}
          />

          <Tooltip
            contentStyle={{
              background: "#0b1014",
              border: "1px solid #1c2530",
              borderRadius: 8,
              fontSize: 11,
              fontFamily: "JetBrains Mono",
            }}
            labelStyle={{
              color: "#9aa7b2",
            }}
          />

          <Legend
            wrapperStyle={{
              fontSize: 10,
              color: "#9aa7b2",
              paddingTop: 8,
            }}
            iconType="circle"
            iconSize={8}
            align="center"
            verticalAlign="bottom"
          />

          <Line
            type="monotone"
            dataKey="signal"
            name="Signal"
            stroke={colors.signal}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />

          <Line
            type="monotone"
            dataKey="perception"
            name="Perception"
            stroke={colors.perception}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />

          <Line
            type="monotone"
            dataKey="intelligence"
            name="Intelligence"
            stroke={colors.intelligence}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />

          <Line
            type="monotone"
            dataKey="state"
            name="State"
            stroke={colors.state}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}