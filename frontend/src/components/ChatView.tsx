import { useCallback, useEffect, useRef, useState } from "react";
import {
  chat,
  approve,
  reject,
  ChatDone,
  Candidate,
  PendingAction,
  ApiError,
  listFacts,
  addFact,
  deleteFact,
  Fact,
} from "../lib/api";
import { useVoice } from "../hooks/useVoice";
import { DemoBadge } from "./DemoBadge";
import { Check, X, Mic, MicOff, Send, Volume2, VolumeX, Trash2 } from "lucide-react";

interface Msg {
  role: "user" | "assistant" | "system";
  text: string;
  done?: ChatDone;
  pendingAction?: PendingAction | null;
  error?: boolean;
}

export function ChatView() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [facts, setFacts] = useState<Fact[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const onTranscript = useCallback((text: string) => {
    setInput((prev) => (prev ? `${prev} ${text}` : text));
  }, []);

  const voice = useVoice(onTranscript);

  const loadFacts = useCallback(async () => {
    try {
      setFacts(await listFacts());
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadFacts();
  }, [loadFacts]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function push(m: Msg) {
    setMessages((prev) => [...prev, m]);
  }

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || busy) return;
    setInput("");
    setBusy(true);
    push({ role: "user", text: content });
    try {
      const { done } = await chat(content, threadId ?? undefined);
      setThreadId(done.thread_id);
      push({ role: "assistant", text: "", done, pendingAction: done.pending_action });
      if (done.demo_mode && done.provider === "demo") {
        // gentle, honest note — the demo planner is not an LLM
      }
      if (done.pending_action) {
        voice.speak(`I'm ready to ${done.pending_action.summary}. Please approve or reject.`);
      } else if (done.status === "ok") {
        // spoken reply (short) uses the assistant text
      }
    } catch (e) {
      push({
        role: "system",
        text:
          e instanceof ApiError && e.status === 429
            ? "Rate limit exceeded — please wait a moment and try again."
            : e instanceof ApiError && e.status === 401
              ? "Session expired — please log in again."
              : "The AI provider is unavailable right now. Nothing was faked — please retry.",
        error: true,
      });
    } finally {
      setBusy(false);
    }
  }

  async function onApprove(threadIdToApprove: string) {
    setBusy(true);
    try {
      const res = await approve(threadIdToApprove);
      push({ role: "system", text: res.reply });
      loadFacts();
    } catch (e) {
      push({ role: "system", text: `Approval failed: ${e instanceof Error ? e.message : "unknown"}`, error: true });
    } finally {
      setBusy(false);
    }
  }

  async function onReject(threadIdToReject: string) {
    setBusy(true);
    try {
      const res = await reject(threadIdToReject);
      push({ role: "system", text: res.reply });
    } catch (e) {
      push({ role: "system", text: `Reject failed: ${e instanceof Error ? e.message : "unknown"}`, error: true });
    } finally {
      setBusy(false);
    }
  }

  async function onRemember() {
    const selection = window.prompt("What should I remember? (e.g. 'Shipper prefers early morning pickup')");
    if (!selection || !selection.trim()) return;
    try {
      await addFact(selection.trim());
      push({ role: "system", text: `Remembered: “${selection.trim()}”` });
      loadFacts();
    } catch (e) {
      push({ role: "system", text: `Could not remember: ${e instanceof Error ? e.message : "unknown"}`, error: true });
    }
  }

  return (
    <div className="grid lg:grid-cols-[1fr_300px] gap-6">
      <div className="flex flex-col h-[calc(100vh-160px)] min-h-[480px] rounded-2xl border border-slate-800 bg-slate-900/60">
        {/* header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
          <div className="text-sm font-semibold flex items-center gap-2">
            Disha — chat
            <DemoBadge />
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={onRemember}
              className="text-xs px-2 py-1 rounded-lg border border-slate-700 text-slate-300 hover:border-disha-600/50"
              title="Save a fact to memory (explicit only)"
            >
              + Remember
            </button>
            <button
              onClick={loadFacts}
              className="text-xs px-2 py-1 rounded-lg border border-slate-700 text-slate-300 hover:border-disha-600/50"
              title="Refresh memory"
            >
              Memory ({facts.length})
            </button>
            <button
              onClick={voice.toggleMuted}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200"
              title={voice.muted ? "Unmute voice replies" : "Mute voice replies"}
            >
              {voice.muted ? <VolumeX size={15} /> : <Volume2 size={15} />}
            </button>
          </div>
        </div>

        {/* messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-sm text-slate-400 space-y-2 pt-4">
              <p>Hi — I'm Disha, your freight coordinator. Try:</p>
              <ul className="space-y-1 text-xs">
                <li>• “Rourkela se Ranchi, 8 ton industrial goods, kal”</li>
                <li>• “Meri gaadi kal Ranchi se Kolkata jaa rahi hai, load milega?”</li>
                <li>• “Create a request: from Rourkela to Ranchi, 8 tonnes, tomorrow”</li>
                <li>• “Remember that I prefer open body trucks”</li>
              </ul>
            </div>
          )}
          {messages.map((m, i) => (
            <MessageRow
              key={i}
              msg={m}
              onApprove={onApprove}
              onReject={onReject}
              onSpeak={voice.speak}
              busy={busy}
            />
          ))}
          {busy && (
            <div className="text-xs text-slate-500 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-disha-500 animate-pulse" /> Disha is working…
            </div>
          )}
        </div>

        {/* voice + input */}
        <div className="border-t border-slate-800 p-3 space-y-2">
          {voice.error && <div className="text-xs text-red-400">{voice.error}</div>}
          {voice.state === "listening" && (
            <div className="text-xs text-disha-500 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-disha-500 animate-pulse" /> Listening… speak now
            </div>
          )}
          <div className="flex items-end gap-2">
            <button
              onClick={voice.state === "listening" ? voice.stopListening : voice.startListening}
              disabled={!voice.supported || busy}
              className={`p-2.5 rounded-xl border transition-colors ${
                voice.state === "listening"
                  ? "bg-red-500/20 border-red-500/50 text-red-400"
                  : "border-slate-700 text-slate-300 hover:border-disha-600/50 disabled:opacity-40"
              }`}
              title={voice.supported ? "Speak to Disha (browser speech)" : "Voice not supported in this browser — typing works"}
            >
              {voice.state === "listening" ? <MicOff size={16} /> : <Mic size={16} />}
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              rows={2}
              placeholder="Type your freight request… (Enter to send)"
              className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:border-disha-600/60"
            />
            <button
              onClick={() => send()}
              disabled={busy || !input.trim()}
              className="p-2.5 rounded-xl bg-disha-600 hover:bg-disha-500 text-white disabled:opacity-40 transition-colors"
            >
              <Send size={16} />
            </button>
          </div>
          <div className="text-[10px] text-slate-500">
            {voice.supported ? "Voice: utterance-based browser transcription (Chrome/Edge)." : "Voice not supported here — typing is the normal path."}
          </div>
        </div>
      </div>

      {/* memory panel */}
      <aside className="hidden lg:block">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sticky top-20">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">My memory</h3>
          {facts.length === 0 && <p className="text-xs text-slate-500">No facts saved. Say “remember that …” to add one.</p>}
          <ul className="space-y-2">
            {facts.map((f) => (
              <li key={f.id} className="group flex items-start justify-between gap-2 text-xs text-slate-300 bg-slate-950 rounded-lg px-2.5 py-2">
                <span>{f.text}</span>
                <button
                  onClick={async () => {
                    await deleteFact(f.id);
                    loadFacts();
                  }}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400"
                >
                  <Trash2 size={12} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}

function MessageRow({
  msg,
  onApprove,
  onReject,
  onSpeak,
  busy,
}: {
  msg: Msg;
  onApprove: (tid: string) => void;
  onReject: (tid: string) => void;
  onSpeak: (text: string) => void;
  busy: boolean;
}) {
  const [revealed, setRevealed] = useState(msg.role === "assistant" ? "" : msg.text);

  useEffect(() => {
    if (msg.role !== "assistant") return;
    const full = msg.done ? msg.done.reply ?? msg.text : msg.text;
    if (!full) {
      setRevealed(msg.text);
      return;
    }
    setRevealed("");
    const total = Math.min(900, full.length * 14);
    const step = Math.max(1, Math.ceil(full.length / 40));
    let i = 0;
    const timer = setInterval(() => {
      i += step;
      setRevealed(full.slice(0, i));
      if (i >= full.length) clearInterval(timer);
    }, total / 40);
    return () => clearInterval(timer);
  }, [msg]);

  if (msg.role === "system") {
    return (
      <div className={`text-xs px-3 py-2 rounded-lg border ${
        msg.error
          ? "bg-red-500/10 border-red-500/30 text-red-300"
          : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
      }`}>
        {msg.text}
      </div>
    );
  }

  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-disha-600/20 border border-disha-600/30 rounded-2xl rounded-br-md px-3.5 py-2.5 text-sm">
          {msg.text}
        </div>
      </div>
    );
  }

  const done = msg.done;
  const fullReply = done?.reply ?? msg.text;

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        <div className="bg-slate-950 border border-slate-800 rounded-2xl rounded-bl-md px-3.5 py-2.5 text-sm whitespace-pre-wrap">
          {revealed || fullReply}
        </div>

        {done?.provider && (
          <div className="flex items-center gap-2 text-[10px] text-slate-500">
            <span>provider: {done.provider}</span>
            {done.demo_mode && <DemoBadge />}
          </div>
        )}

        {done?.candidates && done.candidates.length > 0 && (
          <div className="space-y-1.5">
            {done.candidates.map((c) => (
              <CandidateCard key={c.id} c={c} />
            ))}
          </div>
        )}

        {msg.pendingAction && (
          <ApprovalCard
            action={msg.pendingAction}
            threadId={done!.thread_id}
            busy={busy}
            onApprove={onApprove}
            onReject={onReject}
            onSpeak={onSpeak}
          />
        )}

        {done?.status === "error" && !msg.pendingAction && (
          <div className="text-xs text-red-400">The operation could not be completed — nothing was written.</div>
        )}
      </div>
    </div>
  );
}

export function CandidateCard({ c }: { c: Candidate }) {
  const extra = c.extra as Record<string, any>;
  return (
    <div className="border border-slate-800 rounded-xl bg-slate-900/80 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="font-mono text-[11px] text-slate-400">{c.id}</div>
        <div className="text-sm font-bold text-disha-500">{c.total_score.toFixed(2)}</div>
      </div>
      <div className="text-xs text-slate-300 mt-0.5">
        {c.origin_city} → {c.destination_city}
        {extra?.capacity_tonnes != null && <span className="text-slate-500"> · {extra.capacity_tonnes}t</span>}
        {extra?.price_per_tonne != null && <span className="text-slate-500"> · ₹{Number(extra.price_per_tonne).toLocaleString()}/t</span>}
      </div>
      <div className="grid grid-cols-5 gap-1 mt-2">
        {Object.entries(c.factors).map(([k, v]) => (
          <div key={k} className="text-center">
            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-disha-500" style={{ width: `${v.score * 100}%` }} />
            </div>
            <div className="text-[9px] text-slate-500 mt-1">{k}</div>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-slate-500 mt-2">{c.explanation}</div>
    </div>
  );
}

export function ApprovalCard({
  action,
  threadId,
  busy,
  onApprove,
  onReject,
  onSpeak,
}: {
  action: PendingAction;
  threadId: string;
  busy: boolean;
  onApprove: (tid: string) => void;
  onReject: (tid: string) => void;
  onSpeak: (text: string) => void;
}) {
  return (
    <div className="border border-amber-500/40 bg-amber-500/5 rounded-xl p-3 space-y-2">
      <div className="text-xs font-semibold text-amber-300 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        Approval required — nothing has been written yet
      </div>
      <div className="text-sm text-slate-200">{action.summary}</div>
      <div className="text-[10px] font-mono text-slate-500 break-all">action: {action.type} · {action.created_at}</div>
      <div className="flex gap-2">
        <button
          disabled={busy}
          onClick={() => onApprove(threadId)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40"
        >
          <Check size={13} /> Approve
        </button>
        <button
          disabled={busy}
          onClick={() => onReject(threadId)}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 hover:border-red-500/60 hover:text-red-400 disabled:opacity-40"
        >
          <X size={13} /> Reject
        </button>
        <button
          onClick={() => onSpeak(action.summary)}
          className="text-xs px-2 py-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200"
        >
          <Volume2 size={13} />
        </button>
      </div>
    </div>
  );
}
