/** Typed API client for the Dossier backend. */

const BASE = '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err.error?.message || res.statusText);
  }
  return res.json();
}

// ---- Types ----

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DetectedFace {
  bbox: BoundingBox;
  confidence: number;
  subject_type: 'human' | 'pet';
}

export interface DetectionResult {
  faces: DetectedFace[];
  image_width: number;
  image_height: number;
}

export interface Match {
  face_id: string;
  image_id: string;
  image_path: string;
  image_url: string;
  similarity_score: number;
  subject_type: 'human' | 'pet';
  bbox: BoundingBox;
  metadata?: {
    timestamp?: string;
    latitude?: number;
    longitude?: number;
  } | null;
  location?: {
    city?: string;
    neighborhood?: string;
  } | null;
}

export interface QueryResponse {
  session_id: string;
  total_results: number;
  results: Match[];
}

export interface Job {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  message: string;
  result?: Record<string, unknown>;
  error?: string;
}

export interface DossierDay {
  date: string;
  day_summary: string;
  entries: Array<{
    time: string;
    location: string;
    description: string;
    image_url: string;
    confidence: number;
  }>;
}

export interface Dossier {
  executive_summary: string;
  subject_type: string;
  date_range: string;
  days: DossierDay[];
  patterns: Array<{
    pattern_type: string;
    description: string;
    confidence: number;
  }>;
}

export interface IndexStats {
  total_images: number;
  total_faces: number;
  human_faces: number;
  pet_faces: number;
  human_vectors: number;
  pet_vectors: number;
  index_type: string;
}

// ---- API calls ----

export async function detect(file: File): Promise<DetectionResult> {
  const form = new FormData();
  form.append('image', file);
  return request('/detect', { method: 'POST', body: form });
}

export async function query(
  file: File,
  subjectType: string,
  bbox?: BoundingBox,
): Promise<QueryResponse> {
  const form = new FormData();
  form.append('image', file);
  form.append('subject_type', subjectType);
  if (bbox) {
    form.append('bbox_x', String(bbox.x));
    form.append('bbox_y', String(bbox.y));
    form.append('bbox_w', String(bbox.width));
    form.append('bbox_h', String(bbox.height));
  }
  return request('/query', { method: 'POST', body: form });
}

export async function runPipeline(
  file: File,
  subjectType: string,
  bbox?: BoundingBox,
): Promise<{ job_id: string; status: string }> {
  const form = new FormData();
  form.append('image', file);
  form.append('subject_type', subjectType);
  form.append('generate_narrative', 'true');
  if (bbox) {
    form.append('bbox_x', String(bbox.x));
    form.append('bbox_y', String(bbox.y));
    form.append('bbox_w', String(bbox.width));
    form.append('bbox_h', String(bbox.height));
  }
  return request('/pipeline', { method: 'POST', body: form });
}

export async function getJob(jobId: string): Promise<Job> {
  return request(`/jobs/${jobId}`);
}

export async function getIndexStats(): Promise<IndexStats> {
  return request('/index/stats');
}

export function mediaUrl(path: string): string {
  return `${BASE}/media/${path}`;
}
