export type StructuredCaseStatus =
  | "collecting"
  | "needs_information"
  | "ready_for_review";

export interface PatientSubject {
  patientReference: string | null;
  ageYears: number | null;
  sexAtBirth: string;
}

export interface ChiefComplaint {
  text: string;
  onsetText: string | null;
  sourceRefs: string[];
}

export interface Symptom {
  name: string;
  present: boolean;
  onsetText: string | null;
  severity0To10: number | null;
  location: string | null;
  notes: string | null;
  sourceRefs: string[];
}

export interface Observation {
  name: string;
  value: number | string;
  unit: string | null;
  origin: string;
  observedAt: string;
  sourceRefs: string[];
}

export interface HistoryItem {
  name: string;
  status: string;
  details: string | null;
  sourceRefs: string[];
}

export interface History {
  conditions: HistoryItem[];
  medications: HistoryItem[];
  allergies: HistoryItem[];
}

export interface CaseSummary {
  oneLine: string;
  narrative: string;
}

export interface SafetySignal {
  code: string;
  label: string;
  status: string;
  evidenceSourceRefs: string[];
}

export interface InformationGap {
  fieldPath: string;
  question: string;
  priority: string;
}

export interface ConflictValue {
  value: string;
  sourceRefs: string[];
}

export interface ConflictItem {
  fieldPath: string;
  values: ConflictValue[];
  status: string;
}

export interface ProvenanceItem {
  fieldPath: string;
  sourceRefs: string[];
  confidence: string;
  verificationStatus: string;
}

export interface ExtractionMetadata {
  promptVersion: string;
  model: string;
  completedAt: string;
  outcome: string;
}

export interface StructuredCase {
  schemaVersion: string;
  caseId: string;
  sessionId: string;
  caseVersion: number;
  status: StructuredCaseStatus;
  capturedAt: string;
  language: string;
  subject: PatientSubject;
  informants: string[];
  chiefComplaint: ChiefComplaint;
  symptoms: Symptom[];
  observations: Observation[];
  history: History;
  summary: CaseSummary;
  safetySignals: SafetySignal[];
  informationGaps: InformationGap[];
  conflicts: ConflictItem[];
  provenance: ProvenanceItem[];
  extractionMetadata: ExtractionMetadata;
}
