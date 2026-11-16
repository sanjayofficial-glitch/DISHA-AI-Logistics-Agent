/** Browser-native voice: Web Speech API (Chrome/Edge). Utterance-based
 *  input — transcription appears in the input box before sending. */
import { useCallback, useEffect, useRef, useState } from "react";

type VoiceState = "idle" | "listening" | "transcribing" | "error" | "speaking";

interface VoiceApi {
  state: VoiceState;
  supported: boolean;
  startListening: () => void;
  stopListening: () => void;
  speak: (text: string) => void;
  stopSpeaking: () => void;
  muted: boolean;
  toggleMuted: () => void;
  error: string | null;
}

const SpeechRecognitionImpl =
  (window as unknown as Record<string, any>).SpeechRecognition ??
  (window as unknown as Record<string, any>).webkitSpeechRecognition;

export function useVoice(onTranscript: (text: string) => void): VoiceApi {
  const [state, setState] = useState<VoiceState>("idle");
  const [muted, setMuted] = useState(() => localStorage.getItem("disha_muted") === "1");
  const [error, setError] = useState<string | null>(null);
  const recRef = useRef<any>(null);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  const supported = typeof SpeechRecognitionImpl !== "undefined";

  useEffect(() => {
    if (!supported) return;
    const rec = new SpeechRecognitionImpl();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => setState("listening");
    rec.onresult = (event: any) => {
      setState("transcribing");
      const transcript = Array.from(event.results)
        .map((r: any) => r[0]?.transcript ?? "")
        .join("");
      if (transcript) onTranscriptRef.current(transcript);
      setState("idle");
    };
    rec.onerror = (event: any) => {
      setError(`Voice error: ${event?.error ?? "unknown"}. Typing works as normal.`);
      setState("error");
      setTimeout(() => setState("idle"), 1500);
    };
    rec.onend = () => setState((s) => (s === "speaking" ? s : "idle"));
    recRef.current = rec;
    return () => {
      try {
        rec.abort();
      } catch {
        /* noop */
      }
    };
  }, [supported]);

  const startListening = useCallback(() => {
    setError(null);
    if (!recRef.current) return;
    try {
      recRef.current.start();
    } catch {
      /* already started */
    }
  }, []);

  const stopListening = useCallback(() => {
    try {
      recRef.current?.stop();
    } catch {
      /* noop */
    }
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (muted || !text || typeof window === "undefined" || !("speechSynthesis" in window)) return;
      setState("speaking");
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "en-IN";
      u.onend = () => setState("idle");
      u.onerror = () => setState("idle");
      window.speechSynthesis.speak(u);
    },
    [muted],
  );

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setState("idle");
  }, []);

  const toggleMuted = useCallback(() => {
    setMuted((m) => {
      const next = !m;
      localStorage.setItem("disha_muted", next ? "1" : "0");
      if (next) window.speechSynthesis?.cancel();
      return next;
    });
  }, []);

  return { state, supported, startListening, stopListening, speak, stopSpeaking, muted, toggleMuted, error };
}
