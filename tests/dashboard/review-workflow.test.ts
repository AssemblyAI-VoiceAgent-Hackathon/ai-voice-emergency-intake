import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { applyEdits } from "../../lib/applyEdits.ts";
import {
  buildStaffReviewPayload,
  canApproveReview,
  conflictToEdit,
  parseConflictVersion,
  shouldApplyEvent,
  unresolvedRequiredGaps,
} from "../../lib/reviewWorkflow.ts";
import type { StructuredCase } from "../../types/structuredCase";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function loadCase(name: string): StructuredCase {
  return JSON.parse(readFileSync(join(root, "contracts", "examples", name), "utf8")) as StructuredCase;
}

test("ignores duplicate event ids and stale versions", () => {
  const seen = new Set(["evt_1"]);
  assert.equal(shouldApplyEvent("evt_1", 4, seen, 3), "duplicate");
  assert.equal(shouldApplyEvent("evt_2", 2, seen, 3), "stale");
  assert.equal(shouldApplyEvent("evt_3", 3, seen, 3), "apply");
  assert.equal(shouldApplyEvent("evt_4", 5, seen, 3), "apply");
});

test("staff edits survive a later structured-case overlay", () => {
  const original = loadCase("structured-case.example.json");
  const pending = [
    {
      op: "replace" as const,
      path: "/chiefComplaint/text",
      value: "Staff-corrected chest pain",
      reason: "Confirmed on arrival",
    },
  ];
  const laterAi = {
    ...original,
    caseVersion: original.caseVersion + 1,
    chiefComplaint: { ...original.chiefComplaint, text: "AI restated chest discomfort" },
  };
  const merged = applyEdits(laterAi, pending);
  assert.equal(merged.chiefComplaint.text, "Staff-corrected chest pain");
  assert.equal(merged.caseVersion, original.caseVersion + 1);
});

test("blocks approve until required gaps and human triage are complete", () => {
  const conflicting = loadCase("structured-case.conflicting.example.json");
  const required = unresolvedRequiredGaps(conflicting.informationGaps, []);
  assert.ok(required.length > 0);
  assert.equal(
    canApproveReview({
      triageCode: "",
      triageLabel: "Urgent",
      unresolvedRequiredCount: required.length,
    }),
    false
  );
  assert.equal(
    canApproveReview({
      triageCode: "ESI-2",
      triageLabel: "Urgent",
      unresolvedRequiredCount: 0,
    }),
    true
  );
  assert.equal(
    canApproveReview({
      triageCode: "ESI-2",
      triageLabel: "Urgent",
      unresolvedRequiredCount: 0,
      reviewStatus: "approved",
    }),
    false
  );
});

test("conflict selection queues a Role 3 compatible staff edit", () => {
  const conflicting = loadCase("structured-case.conflicting.example.json");
  const allergy = conflicting.conflicts[0];
  const edit = conflictToEdit(conflicting, allergy, 0);
  assert.ok(edit);
  assert.equal(edit?.path, "/history/allergies");
  assert.equal(edit?.op, "replace");
  const applied = applyEdits(conflicting, [edit!]);
  assert.equal(applied.history.allergies[0]?.name, "penicillin allergy reported");
});

test("409 envelope exposes latestCaseVersion without dropping edits", () => {
  const version = parseConflictVersion({
    error: {
      code: "CASE_VERSION_CONFLICT",
      message: "The submitted case version is stale.",
      latestCaseVersion: 7,
    },
  });
  assert.equal(version, 7);
  const pending = [
    {
      op: "replace" as const,
      path: "/chiefComplaint/text",
      value: "Kept after 409",
      reason: "Staff correction",
    },
  ];
  assert.equal(pending.length, 1);
});

test("review payloads match the three Role 5 actions", () => {
  const draft = buildStaffReviewPayload({
    caseId: "case_demo_001",
    caseVersion: 3,
    action: "save_draft",
    edits: [],
    idempotencyKey: "review-demo-draft-01",
  });
  assert.equal(draft.action, "save_draft");
  assert.equal(draft.finalTriage, null);

  const more = buildStaffReviewPayload({
    caseId: "case_demo_001",
    caseVersion: 3,
    action: "request_more_information",
    edits: [],
    questions: ["Any known allergies?"],
    idempotencyKey: "review-demo-info-01",
  });
  assert.equal(more.informationRequest?.questions.length, 1);

  const approve = buildStaffReviewPayload({
    caseId: "case_demo_001",
    caseVersion: 3,
    action: "approve",
    edits: [
      {
        op: "replace",
        path: "/history/allergies",
        value: [{ name: "penicillin", status: "reported", details: null, sourceRefs: [] }],
        reason: "Confirmed by staff",
      },
    ],
    triageCode: "ESI-2",
    triageLabel: "Urgent",
    idempotencyKey: "review-demo-approve-01",
  });
  assert.equal(approve.finalTriage?.code, "ESI-2");
  assert.equal(approve.edits.length, 1);
});
