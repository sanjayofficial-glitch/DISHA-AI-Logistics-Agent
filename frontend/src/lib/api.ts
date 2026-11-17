/** API client — talks to the DISHA backend. The Clerk-style JWT is sent as
 *  Authorization: Bearer. Never store API keys in the browser. */

const API_URL = (import.meta.env.VITE_DISHA_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

const TOKEN_KEY = "disha_demo_token";
const USER_KEY = "disha_demo_user";

export interface DemoUser {
  user_id: string;
  display_name: string;
  role: "shipper" | "transporter";
}

export function saveSession(token: string, user: DemoUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): DemoUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DemoUser;
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401) {
    clearSession();
  }
  return res;
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await request(path, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export interface ChatDone {
  type: "done";
  status: string;
  thread_id: string;
  provider: string;
  reply: string;
  approval_required: boolean;
  pending_action: PendingAction | null;
  candidates: Candidate[];
  search_mode?: string | null;
  demo_mode: boolean;
}

export interface PendingAction {
  type: string;
  payload: Record<string, unknown>;
  summary: string;
  created_at: string;
}

export interface Candidate {
  id: string;
  source_table: string;
  origin_city: string;
  destination_city: string;
  total_score: number;
  factors: Record<string, { score: number; note: string }>;
  explanation: string;
  extra: Record<string, unknown>;
  is_demo: boolean;
  source: string;
}

/** POST /chat and collect the ndjson stream. */
export async function chat(message: string, threadId?: string): Promise<{ chunks: string[]; done: ChatDone }> {
  const res = await request("/chat", {
    method: "POST",
    body: JSON.stringify({ message, thread_id: threadId ?? null }),
  });
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const text = await res.text();
  const chunks: string[] = [];
  let done: ChatDone | null = null;
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    const obj = JSON.parse(line);
    if (obj.type === "chunk") chunks.push(obj.text as string);
    else if (obj.type === "done") done = obj as ChatDone;
  }
  if (!done) throw new ApiError(500, "stream ended without done event");
  return { chunks, done };
}

export async function approve(threadId: string) {
  return apiJson<{ status: string; reply: string }>("/approve", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId }),
  });
}

export async function reject(threadId: string) {
  return apiJson<{ status: string; reply: string }>("/reject", {
    method: "POST",
    body: JSON.stringify({ thread_id: threadId }),
  });
}

export interface ThreadEvent {
  id: number;
  thread_id: string;
  user_id: string;
  node: string;
  status: string;
  payload_summary: string;
  created_at: string;
}

export async function threadEvents(threadId: string): Promise<ThreadEvent[]> {
  const data = await apiJson<{ events: ThreadEvent[] }>(`/threads/${threadId}/events`);
  return data.events;
}

export async function threads(): Promise<string[]> {
  const data = await apiJson<{ threads: string[] }>("/threads");
  return data.threads;
}

export interface Metrics {
  request_to_match_seconds: number | null;
  eligible_trucks_found: number | null;
  offers_sent: number | null;
  acceptance_rate: number | null;
  time_to_booking_confirmation_seconds: number | null;
  match_success_rate: number | null;
  is_demo: boolean;
  source: string;
}

export async function metrics(): Promise<Metrics> {
  return apiJson<Metrics>("/metrics");
}

export interface MarketplaceRequest {
  id: string;
  shipper_user_id: string;
  origin_city: string;
  destination_city: string;
  goods: string;
  weight_tonnes: number;
  vehicle_type: string;
  pickup_date: string;
  budget_inr: number | null;
  status: string;
  created_at: string;
  confirmed_at: string | null;
  status_explained?: string;
}

export async function myRequests(): Promise<MarketplaceRequest[]> {
  return (await apiJson<{ requests: MarketplaceRequest[] }>("/portal/shipper/requests")).requests;
}

export interface Shipment {
  id: string;
  origin_city: string;
  destination_city: string;
  goods: string;
  weight_tonnes: number;
  pickup_date: string;
  budget_inr: number | null;
  status: string;
  score: number;
  factors: Record<string, { score: number; note: string }>;
  explanation: string;
  is_demo: boolean;
  status_explained?: string;
}

export async function truckerShipments(): Promise<Shipment[]> {
  return (await apiJson<{ shipments: Shipment[] }>("/portal/trucker/shipments")).shipments;
}

export interface Offer {
  id: string;
  request_id: string;
  transporter_user_id: string;
  trip_id: string | null;
  price_inr: number | null;
  status: string;
  origin_city?: string;
  destination_city?: string;
  goods?: string;
  weight_tonnes?: number;
  pickup_date?: string;
}

export async function myOffers(): Promise<Offer[]> {
  return (await apiJson<{ offers: Offer[] }>("/portal/trucker/offers")).offers;
}

export interface NotificationRow {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string;
  read: number;
  created_at: string;
}

export async function myNotifications(): Promise<NotificationRow[]> {
  return (await apiJson<{ notifications: NotificationRow[] }>("/portal/notifications")).notifications;
}

export interface Fact {
  id: string;
  user_id: string;
  text: string;
  created_at: string;
  updated_at: string;
}

export async function listFacts(): Promise<Fact[]> {
  return (await apiJson<{ facts: Fact[] }>("/memory")).facts;
}

export async function addFact(text: string): Promise<Fact> {
  return (await apiJson<{ fact: Fact }>("/memory", {
    method: "POST",
    body: JSON.stringify({ text }),
  })).fact;
}

export async function deleteFact(id: string) {
  await apiJson(`/memory/${id}`, { method: "DELETE" });
}

// --- Command Center: statistical/read-only views --------------------------

export interface MarketStats {
  active_trips: number;
  pending_shipments: number;
  pending_requests: number;
  my_pending_requests: number;
  is_demo: boolean;
  source: string;
}

export async function marketStats(): Promise<MarketStats> {
  return apiJson<MarketStats>("/market/stats");
}

export interface TripRow {
  id: string;
  transporter_user_id: string;
  origin_city: string;
  destination_city: string;
  departure_date: string | null;
  capacity_tonnes: number | null;
  price_per_tonne: number | null;
  vehicle_type: string;
  reliability_score: number | null;
  status: string;
  note: string;
  source: string;
  is_demo?: boolean;
}

export async function marketTrips(): Promise<TripRow[]> {
  const data = await apiJson<{ trips: TripRow[] }>("/market/trips");
  return data.trips;
}

export interface ApprovalRow {
  thread_id: string;
  type: string;
  summary: string;
  created_at: string;
}

export async function approvals(): Promise<ApprovalRow[]> {
  const data = await apiJson<{ approvals: ApprovalRow[] }>("/approvals");
  return data.approvals;
}

export interface QuotePayload {
  available: boolean;
  reason?: string;
  origin?: string;
  destination?: string;
  distance_assumption_km?: number;
  weight_tonnes?: number;
  vehicle_type?: string;
  total_inr?: number;
  per_tonne_inr?: number;
  breakdown?: {
    distance_assumption_km: number;
    base_charge_per_km_inr: number;
    fuel_toll_factor: number;
    formula: string;
  };
  assumptions?: string[];
  is_estimate?: boolean;
}

export async function quotePrice(opts: {
  origin: string;
  destination: string;
  weight_tonnes: number;
  vehicle_type?: string;
}): Promise<QuotePayload> {
  const data = await apiJson<{ quote: QuotePayload }>("/market/quote", {
    method: "POST",
    body: JSON.stringify(opts),
  });
  return data.quote;
}

export interface NegotiationRow {
  id: string;
  request_id: string;
  offer_id: string | null;
  party_user_id: string;
  amount_inr: number | null;
  message: string;
  status: string;
  created_at: string;
  source: string;
}

export async function negotiations(requestId: string): Promise<NegotiationRow[]> {
  const data = await apiJson<{ negotiations: NegotiationRow[] }>(
    `/portal/negotiations/${encodeURIComponent(requestId)}`,
  );
  return data.negotiations;
}

export async function notifications(): Promise<NotificationRow[]> {
  return (await apiJson<{ notifications: NotificationRow[] }>("/portal/notifications")).notifications;
}
