import { StructuredCase } from "@/types/structuredCase";
import exampleCase from "@/contracts/examples/structured-case.example.json";
import sufficientCase from "@/contracts/examples/structured-case.sufficient.example.json";
import conflictingCase from "@/contracts/examples/structured-case.conflicting.example.json";

export const SYNTHETIC_CASES: StructuredCase[] = [
  exampleCase,
  sufficientCase,
  conflictingCase,
] as StructuredCase[];
