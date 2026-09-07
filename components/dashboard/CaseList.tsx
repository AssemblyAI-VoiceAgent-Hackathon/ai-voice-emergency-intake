"use client";

import React, { useState } from "react";
import { StructuredCase } from "@/types/structuredCase";
import CaseCard from "./CaseCard";
import { Search, Inbox } from "lucide-react";

interface CaseListProps {
  cases: StructuredCase[];
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
}

export default function CaseList({
  cases,
  selectedCaseId,
  onSelectCase,
}: CaseListProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredCases = cases.filter((c) => {
    const q = searchQuery.toLowerCase();
    const patientRef = c.subject.patientReference || "";
    return (
      c.caseId.toLowerCase().includes(q) ||
      patientRef.toLowerCase().includes(q) ||
      c.chiefComplaint.text.toLowerCase().includes(q) ||
      c.summary.oneLine.toLowerCase().includes(q) ||
      c.status.toLowerCase().includes(q)
    );
  });

  return (
    <aside className="w-full md:w-[320px] lg:w-[360px] flex-shrink-0 bg-[#000000] border-r border-zinc-800/80 flex flex-col h-full overflow-hidden">
      {/* Header & Search Bar */}
      <div className="p-4 border-b border-zinc-800/80 space-y-3 bg-[#0a0a0f]">
        <div className="flex items-center justify-between">
          <h2 className="text-xs uppercase tracking-widest font-bold text-zinc-400">
            Cases ({cases.length})
          </h2>
          <span className="text-[10px] px-2 py-0.5 rounded bg-[#3954C0]/20 text-blue-300 font-semibold border border-[#3954C0]/30">
            v1.0.0 Contract
          </span>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search patient, complaint, status..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-[#111116] border border-zinc-800 focus:border-[#3954C0] rounded-lg text-xs text-white placeholder-zinc-500 focus:outline-none transition-colors"
          />
        </div>
      </div>

      {/* Cards Scrollable Container */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5 custom-scrollbar">
        {filteredCases.length === 0 ? (
          <div className="py-12 px-4 text-center space-y-2">
            <Inbox className="w-8 h-8 text-zinc-600 mx-auto" />
            <p className="text-xs text-zinc-400 font-medium">No matching cases found</p>
          </div>
        ) : (
          filteredCases.map((c) => (
            <CaseCard
              key={c.caseId}
              caseItem={c}
              isSelected={c.caseId === selectedCaseId}
              onSelect={() => onSelectCase(c.caseId)}
            />
          ))
        )}
      </div>
    </aside>
  );
}
