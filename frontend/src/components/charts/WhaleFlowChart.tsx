"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { fmtUsd } from "@/lib/api";

interface WhaleData {
  name: string;
  usd: number;
  asset: string;
}

export default function WhaleFlowChart({ data }: { data: WhaleData[] }) {
  if (data.length === 0) {
    return <p className="text-xs text-slate-500">No whale flow data</p>;
  }

  return (
    <div style={{ width: "100%", height: 220, minHeight: 220 }}>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis 
            dataKey="name" 
            stroke="#94a3b8" 
            fontSize={10} 
            tickLine={false}
            axisLine={false}
          />
          <YAxis 
            stroke="#94a3b8" 
            fontSize={10} 
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => fmtUsd(v)}
          />
          <Tooltip 
            contentStyle={{ 
              background: "#0d1722", 
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: "12px"
            }}
            formatter={(value: any) => [fmtUsd(value), "USD"]}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Bar dataKey="usd" fill="#14f195" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
