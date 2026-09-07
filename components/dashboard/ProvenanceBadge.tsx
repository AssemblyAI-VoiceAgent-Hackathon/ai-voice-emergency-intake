"use client";

import React from "react";
import { ProvenanceItem } from "@/types/structuredCase";
import { CheckCircle2, HelpCircle, UserCheck, ShieldCheck } from "lucide-react";

interface ProvenanceBadgeProps {
  fieldPath: string;
  provenanceList: ProvenanceItem[] | undefined;
}

export default function ProvenanceBadge({
  fieldPath,
  provenanceList,
}: ProvenanceBadgeProps) {
  if (!provenanceList || provenanceList.length === 0) return null;

  const match = provenanceList.find((p) => p.fieldPath === fieldPath);
  if (!match) return null;

  const getConfidenceBadge = (conf: string) => {
    switch (conf.toLowerCase()) {
      case "high":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "medium":
        return "bg-yellow-500/20 text-yellow-300 border-yellow-500/40";
      case "low":
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
    }
  };

  const getVerificationIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case "staff_confirmed":
        return <UserCheck className="w-3 h-3 text-emerald-400" />;
      case "verified_record":
        return <ShieldCheck className="w-3 h-3 text-blue-400" />;
      case "reported":
      case "unverified":
      default:
        return <HelpCircle className="w-3 h-3 text-amber-400" />;
    }
  };

  const getVerificationBadgeStyle = (status: string) => {
    switch (status.toLowerCase()) {
      case "staff_confirmed":
      case "verified_record":
        return "bg-blue-500/20 text-blue-300 border-blue-500/30";
      case "reported":
      case "unverified":
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
    }
  };

  return (
    <div className="inline-flex items-center space-x-1.5 align-middle ml-2">
      {/* Confidence Badge */}
      <span
        className={`text-[10px] font-semibold px-2 py-0.5 rounded border capitalize ${getConfidenceBadge(
          match.confidence
        )}`}
        title={`AI Confidence: ${match.confidence}`}
      >
        {match.confidence} confidence
      </span>

      {/* Verification Status Badge */}
      <span
        className={`text-[10px] font-medium px-2 py-0.5 rounded border flex items-center space-x-1 capitalize ${getVerificationBadgeStyle(
          match.verificationStatus
        )}`}
        title={`Verification Status: ${match.verificationStatus}`}
      >
        {getVerificationIcon(match.verificationStatus)}
        <span>{match.verificationStatus.replace("_", " ")}</span>
      </span>
    </div>
  );
}
