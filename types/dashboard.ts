export type DashboardState = "ready" | "loading" | "empty" | "error" | "unauthorized";

export type CaseStatus = "Draft" | "Reviewing" | "Conflict" | "Approved";

export type UrgencyLevel = "Critical" | "High" | "Medium" | "Low";

export interface SymptomItem {
  name: string;
  severity: "Mild" | "Moderate" | "Severe";
  duration: string;
}

export interface VitalSign {
  label: string;
  value: string;
  unit?: string;
  status: "normal" | "warning" | "alert";
}

export interface CaseDetails {
  ageGender?: string;
  vitals?: VitalSign[];
  symptomsList?: SymptomItem[];
  medicalSummaryText?: string;
  aiConfidence?: number;
  recommendedAction?: string;
  flaggedConflicts?: string[];
  assignedDoctor?: string;
  audioDuration?: string;
}

export interface CaseItem {
  id: string;
  patientLabel: string;
  chiefComplaintSnippet: string;
  status: CaseStatus;
  updatedAt: string;
  urgency: UrgencyLevel;
  details: CaseDetails;
}
