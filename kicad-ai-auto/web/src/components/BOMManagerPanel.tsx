/**
 * BOM Manager Panel (Phase 11A-5)
 */

import React, { useState } from "react";
import { usePCBStore } from "../stores/pcbStore";
import { Footprint } from "../types";

interface ComponentAlternative {
  lcsc: string;
  manufacturer: string;
  mpn: string;
  price: number;
  stock: number;
}

interface BOMLineItem {
  reference: string;
  value: string;
  footprint: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  stock: number;
  lifecycle: string;
  category: string;
  warnings: string[];
  alternatives: ComponentAlternative[];
}

interface BOMOptimizationReport {
  totalCost: number;
  savings: number;
  items: BOMLineItem[];
  warnings: string[];
}

const BOMManagerPanel: React.FC = () => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [searchText, setSearchText] = useState("");
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [report, setReport] = useState<BOMOptimizationReport | null>(null);
  const pcbData = usePCBStore((s) => s.pcbData);

  if (!pcbData?.footprints) return null;

  const bomItems: BOMLineItem[] = pcbData.footprints.map((fp: Footprint) => ({
    reference: fp.reference || fp.id,
    value: fp.value || "",
    footprint: fp.footprintName || fp.libraryName || "",
    quantity: 1,
    unitPrice: 0,
    totalPrice: 0,
    stock: 0,
    lifecycle: "unknown",
    category: "",
    warnings: [],
    alternatives: [],
  }));

  const filteredItems = bomItems.filter((item) => {
    if (!searchText) return true;
    const s = searchText.toLowerCase();
    return item.reference.toLowerCase().includes(s) ||
      item.value.toLowerCase().includes(s) ||
      item.footprint.toLowerCase().includes(s);
  });

  const totalCost = bomItems.reduce((sum, i) => sum + i.unitPrice * i.quantity, 0);

  const getLifecycleColor = (status: string) => {
    switch (status) {
      case "active": return "#4caf50";
      case "nrnd": return "#ffab40";
      case "eol": return "#f44336";
      default: return "#888";
    }
  };

  return (
    <div style={{ flex: 1, height: "100%", background: "#1e1a2e", borderRight: "1px solid #2d2d2d", display: "flex", flexDirection: "column", gap: 8, padding: 8, overflow: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ color: "#e0e0e0", fontSize: 12, fontWeight: 600 }}>BOM Manager</span>
      </div>
      <div style={{ flex: 1, overflow: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
          <thead><tr style={{ color: "#888" }}>
            <th style={{ textAlign: "left" }}>Ref</th>
            <th style={{ textAlign: "left" }}>Value</th>
            <th style={{ textAlign: "left" }}>Footprint</th>
            <th style={{ textAlign: "center" }}>Qty</th>
            <th style={{ textAlign: "right" }}>Stock</th>
            <th style={{ textAlign: "center" }}>Lifecycle</th>
          </tr></thead>
          <tbody>
            {filteredItems.map((item) => (
              <tr key={item.reference} style={{ cursor: "pointer" }} onClick={() => setSelectedIds((prev) => prev.includes(item.reference) ? prev.filter((id) => id !== item.reference) : [...item.reference])}>
                <td style={{ color: "#e0e0e0", padding: "2px 6px" }}>{item.reference}</td>
                <td style={{ color: "#ccc", padding: "2px 6px" }}>{item.value}</td>
                <td style={{ color: "#888", padding: "2px 6px" }}>{item.footprint}</td>
                <td style={{ textAlign: "center", padding: "2px 6px" }}>{item.quantity}</td>
                <td style={{ textAlign: "right", padding: "2px 6px" }}>{item.stock > 0 ? item.stock : "-"}</td>
                <td style={{ textAlign: "center", padding: "2px 6px" }}><span style={{ color: getLifecycleColor(item.lifecycle), fontSize: 9 }}>{item.lifecycle}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {report && (
        <div style={{ marginTop: 8, padding: 8, background: "#252530", borderRadius: 4, fontSize: 10, color: "#aaa" }}>
          Cost: {totalCost.toFixed(2)} | Components: {bomItems.length}
        </div>
      )}
    </div>
  );
};

export default BOMManagerPanel;