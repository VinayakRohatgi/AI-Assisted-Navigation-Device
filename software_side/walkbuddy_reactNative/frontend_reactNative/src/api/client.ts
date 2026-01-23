// frontend_reactNative/src/api/client.ts
import Constants from "expo-constants";
import { API_BASE } from "../config";

// --- My Custom Two-Brain Types ---
export interface DetectionEvent {
  label: string;
  direction: string;
  distance_m: number | null;
  confidence: number;
}

export interface SlowLaneResponse {
  events: DetectionEvent[];
  answer?: string;
  safe: boolean;
  source: "safety_gate" | "slow_lane_llm";
}

// --- Upstream Types (Preserved) ---
export type CapturedFrame = {
  frameId: string;
  timestamp: string;
  source: string;
  imageBase64: string;
  width: number;
  height: number;
};

export type Detection = {
  id: number;
  label: string;
  confidence: number;
  bbox_norm: {
    cx: number;
    cy: number;
    w: number;
    h: number;
  };
  side: "left" | "center" | "right";
  severity: "near" | "medium" | "far";
  distance_m: number | null;
};

export type VisionResult = {
  frame_id: string;
  timestamp: string;
  source: string;
  detections: Detection[];
};

export type OcrBlock = {
  id: number;
  text: string;
  confidence: number;
  bbox_norm: {
    cx: number;
    cy: number;
    w: number;
    h: number;
  };
};

export type OcrResult = {
  frame_id: string;
  timestamp: string;
  source: string;
  blocks: OcrBlock[];
};

export type BboxPixels = {
  x: number;
  y: number;
  width: number;
  height: number;
};

// --- Helper Functions ---

export function bboxNormToPixels(
  bbox: { cx: number; cy: number; w: number; h: number },
  frameWidth: number,
  frameHeight: number
): BboxPixels {
  const width = bbox.w * frameWidth;
  const height = bbox.h * frameHeight;
  const x = (bbox.cx - bbox.w / 2) * frameWidth;
  const y = (bbox.cy - bbox.h / 2) * frameHeight;
  return { x, y, width, height };
}

// --- API Implementation ---

// Simple health/status check
export async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/docs`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return { status: "ok" };
  } catch (err) {
    console.error("Error fetching status:", err);
    throw err;
  }
}

// Native Two-Brain Logic (Multipart)
export async function detectObject(imageBlob: Blob): Promise<{ events: DetectionEvent[] }> {
  const formData = new FormData();
  formData.append("file", imageBlob as any, "frame.jpg");

  const res = await fetch(`${API_BASE}/detect`, {
    method: "POST",
    body: formData,
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Detect failed: ${res.status}`);
  }
  return await res.json();
}

export async function askTwoBrain(
  imageBlob: Blob,
  question: string
): Promise<SlowLaneResponse> {
  const formData = new FormData();
  formData.append("file", imageBlob as any, "frame.jpg");
  formData.append("question", question);

  const res = await fetch(`${API_BASE}/two_brain`, {
    method: "POST",
    body: formData,
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`TwoBrain failed: ${res.status}`);
  }
  return await res.json();
}

// --- InferenceClient Interface (Upstream Legacy Support) ---

export interface InferenceClient {
  detectVision(frame: CapturedFrame): Promise<VisionResult>;
  readText(frame: CapturedFrame): Promise<OcrResult>;
}

export class HttpInferenceClient implements InferenceClient {
  private readonly visionPath = "/vision/detect";
  private readonly ocrPath = "/vision/ocr";

  constructor(private baseUrl: string = API_BASE) { }

  private url(path: string) {
    if (this.baseUrl.endsWith("/") && path.startsWith("/")) {
      return this.baseUrl.slice(0, -1) + path;
    }
    return `${this.baseUrl}${path}`;
  }

  private async postJson<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(this.url(path), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return (await res.json()) as T;
  }

  async detectVision(frame: CapturedFrame): Promise<VisionResult> {
    const payload = {
      frame_id: frame.frameId,
      timestamp: frame.timestamp,
      source: frame.source,
      image: frame.imageBase64,
    };
    return await this.postJson<VisionResult>(this.visionPath, payload);
  }

  async readText(frame: CapturedFrame): Promise<OcrResult> {
    const payload = {
      frame_id: frame.frameId,
      timestamp: frame.timestamp,
      source: frame.source,
      image: frame.imageBase64,
    };
    return await this.postJson<OcrResult>(this.ocrPath, payload);
  }
}

export class MockInferenceClient implements InferenceClient {
  async detectVision(frame: CapturedFrame): Promise<VisionResult> {
    const now = new Date().toISOString();
    return {
      frame_id: frame.frameId,
      timestamp: now,
      source: frame.source,
      detections: [
        {
          id: 1,
          label: "mock_obstacle",
          confidence: 0.95,
          bbox_norm: { cx: 0.5, cy: 0.5, w: 0.3, h: 0.3 },
          side: "center",
          severity: "near",
          distance_m: 1.2,
        },
      ],
    };
  }

  async readText(frame: CapturedFrame): Promise<OcrResult> {
    const now = new Date().toISOString();
    return {
      frame_id: frame.frameId,
      timestamp: now,
      source: frame.source,
      blocks: [
        {
          id: 1,
          text: "Mock text",
          confidence: 0.9,
          bbox_norm: { cx: 0.5, cy: 0.5, w: 0.4, h: 0.2 },
        },
      ],
    };
  }
}

