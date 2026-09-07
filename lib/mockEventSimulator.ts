export type CaseEventType =
  | "case.snapshot"
  | "case.updated"
  | "case.tool_status"
  | "case.review_status"
  | "case.error";

export interface CaseEvent {
  eventId: string;
  eventType: CaseEventType;
  caseId: string;
  caseVersion: number;
  occurredAt: string;
  data: any;
}

export function startMockEventStream(
  caseId: string,
  onEvent: (event: CaseEvent) => void,
  initialVersion: number = 3
): () => void {
  let currentVersion = initialVersion;
  let lastEvent: CaseEvent | null = null;

  const intervalId = setInterval(() => {
    const rand = Math.random();

    // 1 in 5 times (~20%): duplicate event with SAME eventId and caseVersion as lastEvent
    if (rand < 0.2 && lastEvent !== null) {
      onEvent(lastEvent);
      return;
    }

    // 1 in 5 times (~20%): stale event with OLDER caseVersion
    if (rand >= 0.2 && rand < 0.4 && currentVersion > 1) {
      const staleVersion = Math.max(1, currentVersion - 1);
      const staleEvent: CaseEvent = {
        eventId: `evt_stale_${Date.now()}_${Math.floor(Math.random() * 1000)}`,
        eventType: "case.updated",
        caseId,
        caseVersion: staleVersion,
        occurredAt: new Date(Date.now() - 60000).toISOString(),
        data: {
          notes: "Stale event update attempt",
        },
      };
      onEvent(staleEvent);
      return;
    }

    // Otherwise (60%): valid new event with bumped caseVersion
    currentVersion += 1;
    const newEventId = `evt_${Date.now()}_${Math.floor(Math.random() * 10000)}`;

    const event: CaseEvent = {
      eventId: newEventId,
      eventType: "case.updated",
      caseId,
      caseVersion: currentVersion,
      occurredAt: new Date().toISOString(),
      data: {
        // Trivial change description / patch data
        bumpSymptomSeverity: true,
        updateTimestamp: new Date().toLocaleTimeString(),
      },
    };

    lastEvent = event;
    onEvent(event);
  }, 8000);

  return () => {
    clearInterval(intervalId);
  };
}
