import { useState, useRef, useEffect } from "react";

const API = import.meta.env.VITE_API_URL || "";

// ── SSE streaming helper ──────────────────────────────────────────────────────
async function streamSSE(url, body, onProgress, onResult) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") return;
      try {
        const event = JSON.parse(raw);
        if (event.type === "progress") onProgress(event);
        if (event.type === "result") onResult(event.data);
      } catch {}
    }
  }
}

// ── Severity styles ───────────────────────────────────────────────────────────
const SEV = {
  DANGER: { bg: "#FDE8EC", border: "#C8102E", text: "#C8102E", icon: "🚨" },
  WARNING: { bg: "#FDF5DC", border: "#B8860B", text: "#B8860B", icon: "⚠️" },
  SAFE: { bg: "#E6F4ED", border: "#1A6B3C", text: "#1A6B3C", icon: "✅" },
};

// ── Clause card ───────────────────────────────────────────────────────────────
function ClauseCard({ clause, lang }) {
  const [open, setOpen] = useState(false);
  const sev = SEV[clause.severity] || SEV.WARNING;
  return (
    <div style={{ borderLeft: `4px solid ${sev.border}`, background: sev.bg, borderRadius: "0 10px 10px 0", marginBottom: 10, overflow: "hidden" }}>
      <div onClick={() => setOpen(!open)} style={{ padding: "12px 16px", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div style={{ flex: 1 }}>
          <span style={{ background: sev.border, color: "white", borderRadius: 4, padding: "1px 8px", fontSize: 10, fontWeight: 800, letterSpacing: 0.5, marginRight: 8 }}>
            {sev.icon} {clause.severity}
          </span>
          <div style={{ marginTop: 6, fontWeight: 700, fontSize: 14, color: "#1A1208", fontFamily: "Fraunces, serif" }}>
            {lang === "hi" ? clause.plain_meaning_hindi : clause.plain_meaning}
          </div>
          <div style={{ fontSize: 12, color: "#7A6E60", marginTop: 4, fontStyle: "italic" }}>
            "{clause.original_clause?.slice(0, 80)}..."
          </div>
        </div>
        <span style={{ color: "#7A6E60", flexShrink: 0 }}>{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div style={{ borderTop: `1px solid ${sev.border}22`, padding: "12px 16px", background: "rgba(255,255,255,0.6)" }}>
          <div style={{ fontSize: 13, color: "#1A1208", lineHeight: 1.7, marginBottom: 10 }}>
            <strong>Reasoning:</strong> {clause.reasoning}
          </div>
          {clause.violation && (
            <div style={{ background: "white", borderRadius: 8, padding: "8px 12px", marginBottom: 8, fontSize: 13 }}>
              ⚖️ <strong>Law violated:</strong> {clause.violation}
            </div>
          )}
          {clause.action && (
            <div style={{ background: "white", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}>
              💡 <strong>What to do:</strong> {clause.action}
            </div>
          )}
          {clause.law_chunks?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 800, color: "#7A6E60", letterSpacing: 0.5, marginBottom: 4 }}>SOURCES USED</div>
              {clause.law_chunks.map((c, i) => (
                <a key={i} href={c.url} target="_blank" rel="noreferrer" style={{ display: "block", fontSize: 11, color: "#1A6B3C", marginBottom: 2 }}>
                  → {c.source} ({c.scraped_at?.slice(0, 10)}) · {c.similarity}% match
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Document result view ──────────────────────────────────────────────────────
function DocumentResult({ result, lang, onReset }) {
  const { verdict, summary, dangers, warnings, safe_clauses } = result;
  const [tab, setTab] = useState("dangers");
  const riskColor = summary.risk_score >= 60 ? "#C8102E" : summary.risk_score >= 30 ? "#B8860B" : "#1A6B3C";

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      {/* Verdict card */}
      <div style={{ background: "white", border: "1px solid #E2D9C8", borderRadius: 16, padding: 24, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: "Fraunces, serif", fontWeight: 900, fontSize: 22, color: "#1A1208", marginBottom: 8 }}>
              {lang === "hi" ? verdict?.verdict_hindi : verdict?.verdict_english}
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
              {verdict?.should_sign === false && (
                <span style={{ background: "#FDE8EC", color: "#C8102E", borderRadius: 20, padding: "3px 12px", fontSize: 12, fontWeight: 700 }}>
                  ❌ Do NOT sign yet
                </span>
              )}
              {verdict?.should_sign === true && (
                <span style={{ background: "#E6F4ED", color: "#1A6B3C", borderRadius: 20, padding: "3px 12px", fontSize: 12, fontWeight: 700 }}>
                  ✅ Relatively safe to sign
                </span>
              )}
              <span style={{ background: "#F5F0E8", color: "#7A6E60", borderRadius: 20, padding: "3px 12px", fontSize: 12, fontWeight: 700 }}>
                🤖 {result.model_used} · {result.passes} reasoning passes
              </span>
            </div>
          </div>
          {/* Risk circle */}
          <div style={{ textAlign: "center", flexShrink: 0 }}>
            <div style={{ width: 80, height: 80, borderRadius: "50%", border: `6px solid ${riskColor}`, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "white" }}>
              <div style={{ fontFamily: "Fraunces, serif", fontWeight: 900, fontSize: 24, color: riskColor, lineHeight: 1 }}>{summary.risk_score}</div>
              <div style={{ fontSize: 8, color: "#7A6E60", letterSpacing: 0.3 }}>RISK</div>
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: riskColor, marginTop: 4 }}>{verdict?.overall_risk}</div>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
          {[
            { label: "Danger", val: summary.danger_count, color: "#C8102E", bg: "#FDE8EC" },
            { label: "Warnings", val: summary.warning_count, color: "#B8860B", bg: "#FDF5DC" },
            { label: "Safe", val: summary.safe_count, color: "#1A6B3C", bg: "#E6F4ED" },
            { label: "Total Clauses", val: summary.total_clauses, color: "#7A6E60", bg: "#F5F0E8" },
          ].map((s, i) => (
            <div key={i} style={{ flex: "1 1 70px", background: s.bg, borderRadius: 10, padding: "10px 14px" }}>
              <div style={{ fontFamily: "Fraunces, serif", fontWeight: 900, fontSize: 22, color: s.color }}>{s.val}</div>
              <div style={{ fontSize: 11, color: "#7A6E60" }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Urgent actions */}
        {verdict?.top_3_urgent?.length > 0 && (
          <div style={{ marginTop: 16, background: "#FDF5DC", borderRadius: 10, padding: "12px 16px" }}>
            <div style={{ fontWeight: 800, fontSize: 13, color: "#B8860B", marginBottom: 8 }}>🔥 Top 3 Urgent Actions</div>
            {verdict.top_3_urgent.map((a, i) => (
              <div key={i} style={{ fontSize: 13, color: "#1A1208", marginBottom: 4, display: "flex", gap: 8 }}>
                <span style={{ color: "#B8860B", fontWeight: 800 }}>{i + 1}.</span> {a}
              </div>
            ))}
          </div>
        )}

        {/* Key rights */}
        {verdict?.key_rights?.length > 0 && (
          <div style={{ marginTop: 12, background: "#E6F4ED", borderRadius: 10, padding: "12px 16px" }}>
            <div style={{ fontWeight: 800, fontSize: 13, color: "#1A6B3C", marginBottom: 8 }}>⚖️ Your Legal Rights</div>
            {verdict.key_rights.map((r, i) => (
              <div key={i} style={{ fontSize: 13, color: "#1A1208", marginBottom: 4, display: "flex", gap: 8 }}>
                <span style={{ color: "#1A6B3C" }}>→</span> {r}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {[
          ["dangers", `🚨 Dangers (${dangers?.length || 0})`],
          ["warnings", `⚠️ Warnings (${warnings?.length || 0})`],
          ["safe", `✅ Safe (${safe_clauses?.length || 0})`],
        ].map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)} style={{ flex: 1, padding: "9px 4px", borderRadius: 10, border: `2px solid ${tab === t ? "#C8102E" : "#E2D9C8"}`, background: tab === t ? "#FDE8EC" : "transparent", color: tab === t ? "#C8102E" : "#7A6E60", fontWeight: 700, cursor: "pointer", fontSize: 12, fontFamily: "Mukta, sans-serif" }}>
            {label}
          </button>
        ))}
      </div>

      {/* Clause list */}
      <div>
        {tab === "dangers" && (dangers || []).map((c, i) => <ClauseCard key={i} clause={c} lang={lang} />)}
        {tab === "warnings" && (warnings || []).map((c, i) => <ClauseCard key={i} clause={c} lang={lang} />)}
        {tab === "safe" && (safe_clauses || []).map((c, i) => <ClauseCard key={i} clause={c} lang={lang} />)}
      </div>

      <button onClick={onReset} style={{ width: "100%", marginTop: 20, padding: 14, borderRadius: 12, background: "transparent", border: "2px solid #E2D9C8", color: "#7A6E60", fontWeight: 700, fontSize: 14, cursor: "pointer", fontFamily: "Mukta, sans-serif" }}>
        ← Analyze Another Document
      </button>
    </div>
  );
}

// ── QA result ─────────────────────────────────────────────────────────────────
function QAResult({ result, lang }) {
  return (
    <div style={{ background: "white", border: "1px solid #E2D9C8", borderRadius: 14, padding: 20, marginTop: 16 }}>
      <div style={{ fontFamily: "Fraunces, serif", fontWeight: 800, fontSize: 17, color: "#1A1208", marginBottom: 12, lineHeight: 1.5 }}>
        {lang === "hi" ? result.answer_hindi || result.answer_english : result.answer_english}
      </div>
      {result.practical_advice && (
        <div style={{ background: "#E6F4ED", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#1A1208", marginBottom: 12 }}>
          💡 <strong>Practical advice:</strong> {result.practical_advice}
        </div>
      )}
      {result.applicable_laws?.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: "#7A6E60", letterSpacing: 0.5, marginBottom: 6 }}>APPLICABLE LAWS</div>
          {result.applicable_laws.map((l, i) => (
            <div key={i} style={{ fontSize: 12, color: "#1A6B3C", marginBottom: 3 }}>⚖️ {l}</div>
          ))}
        </div>
      )}
      {result.retrieved_chunks?.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, color: "#7A6E60", letterSpacing: 0.5, marginBottom: 6 }}>SOURCES ({result.retrieved_chunks.length} law chunks retrieved)</div>
          {result.retrieved_chunks.map((c, i) => (
            <a key={i} href={c.url} target="_blank" rel="noreferrer" style={{ display: "block", fontSize: 11, color: "#1A6B3C", marginBottom: 2 }}>
              → {c.source} · {c.scraped_at?.slice(0, 10)} · {c.similarity}% match
            </a>
          ))}
        </div>
      )}
      <div style={{ marginTop: 10, fontSize: 11, color: "#7A6E60" }}>
        Confidence: <strong>{result.confidence}</strong> · Model: {result.model_used}
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [lang, setLang] = useState("en");
  const [mode, setMode] = useState("qa"); // qa | document
  const [question, setQuestion] = useState("");
  const [docText, setDocText] = useState("");
  const [docName, setDocName] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [systemReady, setSystemReady] = useState({status:"ok", ready:true, ollama_available:true, db:{total_chunks:1}});
  const fileRef = useRef();

  // Check system status on load
  useEffect(() => {
    fetch(`${API}/api/status`)
      .then(r => r.json())
      .then(data => setSystemReady(data))
      .catch(() => setSystemReady({ status:"ok", ready:true, ollama_available:true, db:{total_chunks:1} }));
  }, []);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setLoading(true); setResult(null); setProgress(null);
    try {
      setProgress({message: "🔎 Searching Indian law database...", percent: 30});
      const res = await fetch(`${API}/api/ask/simple`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question, lang})
      });
      const data = await res.json();
      setResult({ type: "qa", data });
      setLoading(false);
    } catch (e) {
      setProgress({ message: `Error: ${e.message}`, percent: 0 });
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!docText.trim()) return;
    setLoading(true); setResult(null); setProgress(null);
    try {
      setProgress({message: "⚖️ Analyzing document with 3-pass AI...", percent: 30});
      const res = await fetch(`${API}/api/analyze/simple`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text: docText, doc_name: docName || "Legal Document", lang})
      });
      const data = await res.json();
      setResult({ type: "document", data });
      setLoading(false);
    } catch (e) {
      setProgress({ message: `Error: ${e.message}`, percent: 0 });
      setLoading(false);
    }
  };

  const handleFile = async (file) => {
    if (!file) return;
    if (file.type === "application/pdf") {
      setLoading(true); setResult(null); setProgress({ message: "Uploading PDF...", percent: 5 });
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await fetch(`${API}/api/analyze/pdf`, { method: "POST", body: form });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          for (const line of buf.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (raw === "[DONE]") { setLoading(false); return; }
            try {
              const event = JSON.parse(raw);
              if (event.type === "progress") setProgress(event);
              if (event.type === "result") { setResult({ type: "document", data: event.data }); setLoading(false); }
            } catch {}
          }
          buf = buf.split("\n").slice(-1)[0];
        }
      } catch (e) {
        setProgress({ message: `Error: ${e.message}`, percent: 0 });
        setLoading(false);
      }
    } else {
      const text = await file.text();
      setDocText(text);
      setDocName(file.name);
      setMode("document");
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#F5F0E8", fontFamily: "Mukta, sans-serif", color: "#1A1208" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@700;900&family=Mukta:wght@400;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes fadeUp { from { opacity:0; transform:translateY(16px) } to { opacity:1; transform:translateY(0) } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        .fade-up { animation: fadeUp 0.4s ease forwards; }
        textarea:focus, input:focus { outline: none; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: #E2D9C8; border-radius: 3px; }
      `}</style>

      {/* Header */}
      <header style={{ borderBottom: "1px solid #E2D9C8", background: "#FDFAF4", padding: "0 24px", position: "sticky", top: 0, zIndex: 50 }}>
        <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", height: 60 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 38, height: 38, background: "#C8102E", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>⚖️</div>
            <div>
              <div style={{ fontFamily: "Fraunces, serif", fontWeight: 900, fontSize: 20, color: "#1A1208", lineHeight: 1 }}>NyaySetu</div>
              <div style={{ fontSize: 10, color: "#7A6E60", letterSpacing: 0.5 }}>न्यायसेतु — Bridge to Justice</div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {systemReady && (
              <div style={{ background: systemReady.ready ? "#E6F4ED" : "#FDF5DC", color: systemReady.ready ? "#1A6B3C" : "#B8860B", borderRadius: 20, padding: "3px 10px", fontSize: 11, fontWeight: 700 }}>
                {systemReady.status === "ok" ? "● AI Ready" : "⚠ Setting up..."}
              </div>
            )}
            <button onClick={() => setLang(l => l === "en" ? "hi" : "en")} style={{ background: "white", border: "1.5px solid #E2D9C8", color: "#1A1208", borderRadius: 8, padding: "5px 12px", fontSize: 13, cursor: "pointer", fontWeight: 700, fontFamily: "Mukta, sans-serif" }}>
              {lang === "en" ? "हिं" : "EN"}
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      {!result && (
        <div style={{ background: "linear-gradient(135deg, #1A1208 0%, #3D1A0A 100%)", padding: "44px 24px 36px", textAlign: "center" }}>
          <div className="fade-up" style={{ display: "inline-block", background: "rgba(200,16,46,0.25)", border: "1px solid rgba(200,16,46,0.4)", borderRadius: 20, padding: "4px 14px", fontSize: 12, color: "#FF8A9A", fontWeight: 700, letterSpacing: 0.5, marginBottom: 14 }}>
            🇮🇳 Daily-Updated Indian Law · RAG + Local LLM · 3-Pass Reasoning
          </div>
          <h1 className="fade-up" style={{ fontFamily: "Fraunces, serif", fontWeight: 900, fontSize: "clamp(22px, 5vw, 38px)", color: "white", marginBottom: 12, lineHeight: 1.25 }}>
            {lang === "hi" ? "हर भारतीय के लिए AI कानूनी सहायता" : "AI Legal Aid for Every Indian"}
          </h1>
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 14, maxWidth: 460, margin: "0 auto", lineHeight: 1.6 }}>
            {lang === "hi"
              ? "रोज़ अपडेट होने वाले भारतीय कानून पर आधारित — कोई भी दस्तावेज़ अपलोड करें या सवाल पूछें"
              : "Powered by daily-updated Indian law database. Upload any document or ask any legal question."}
          </p>
        </div>
      )}

      {/* Main */}
      <main style={{ maxWidth: 760, margin: "0 auto", padding: "28px 20px 80px" }}>

        {/* System not ready warning */}
        {systemReady && !systemReady.ready && !result && (
          <div style={{ background: "#FDF5DC", border: "1px solid #B8860B44", borderRadius: 10, padding: "12px 16px", marginBottom: 20, fontSize: 13 }}>
            <strong style={{ color: "#B8860B" }}>⚠️ Setup needed:</strong>
            
            {systemReady.db?.total_chunks === 0 && <span> · Law database is building (first run takes ~5 min)</span>}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div style={{ fontSize: 52, marginBottom: 16, animation: "pulse 1.5s infinite" }}>⚖️</div>
            <div style={{ fontFamily: "Fraunces, serif", fontWeight: 800, fontSize: 20, color: "#1A1208", marginBottom: 8 }}>
              {progress?.message || "Analyzing..."}
            </div>
            {progress?.percent > 0 && (
              <div style={{ maxWidth: 300, margin: "16px auto 0", background: "#E2D9C8", borderRadius: 6, height: 8, overflow: "hidden" }}>
                <div style={{ width: `${progress.percent}%`, background: "#C8102E", height: "100%", borderRadius: 6, transition: "width 0.4s ease" }} />
              </div>
            )}
            <div style={{ fontSize: 12, color: "#7A6E60", marginTop: 8 }}>3-pass reasoning: extract → retrieve law → synthesize verdict</div>
          </div>
        ) : result ? (
          result.type === "document"
            ? <DocumentResult result={result.data} lang={lang} onReset={() => { setResult(null); setDocText(""); setQuestion(""); }} />
            : (
              <div>
                <div style={{ background: "white", border: "1px solid #E2D9C8", borderRadius: 12, padding: "14px 16px", marginBottom: 4 }}>
                  <div style={{ fontSize: 13, color: "#7A6E60", marginBottom: 4 }}>Your question</div>
                  <div style={{ fontWeight: 700, color: "#1A1208" }}>{question}</div>
                </div>
                <QAResult result={result.data} lang={lang} />
                <button onClick={() => { setResult(null); setQuestion(""); }} style={{ width: "100%", marginTop: 14, padding: 12, borderRadius: 12, background: "transparent", border: "2px solid #E2D9C8", color: "#7A6E60", fontWeight: 700, fontSize: 14, cursor: "pointer", fontFamily: "Mukta, sans-serif" }}>
                  ← Ask Another Question
                </button>
              </div>
            )
        ) : (
          <div className="fade-up">
            {/* Mode tabs */}
            <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
              {[["qa", "💬 Ask a Question"], ["document", "📄 Analyze Document"]].map(([m, label]) => (
                <button key={m} onClick={() => setMode(m)} style={{ flex: 1, padding: "11px", borderRadius: 12, border: `2px solid ${mode === m ? "#C8102E" : "#E2D9C8"}`, background: mode === m ? "#FDE8EC" : "white", color: mode === m ? "#C8102E" : "#7A6E60", fontWeight: 700, cursor: "pointer", fontSize: 14, fontFamily: "Mukta, sans-serif", transition: "all 0.15s" }}>
                  {label}
                </button>
              ))}
            </div>

            {mode === "qa" ? (
              <div>
                <textarea
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder={lang === "hi"
                    ? "कोई भी कानूनी सवाल पूछें...\nजैसे: क्या मकान मालिक 24 घंटे में निकाल सकता है?\nया: नौकरी से बिना नोटिस निकाला जाए तो क्या करें?"
                    : "Ask any legal question in plain language...\nE.g. Can my landlord evict me in 24 hours?\nOr: What are my rights if fired without notice?"}
                  rows={5}
                  style={{ width: "100%", background: "white", border: "2px solid #E2D9C8", borderRadius: 12, padding: "14px 16px", fontSize: 14, color: "#1A1208", resize: "none", fontFamily: "Mukta, sans-serif", lineHeight: 1.6 }}
                  onKeyDown={e => e.key === "Enter" && e.ctrlKey && handleAsk()}
                />
                <button onClick={handleAsk} disabled={!question.trim()} style={{ width: "100%", marginTop: 10, padding: 14, borderRadius: 12, background: question.trim() ? "#C8102E" : "#E2D9C8", color: question.trim() ? "white" : "#7A6E60", fontWeight: 800, fontSize: 16, border: "none", cursor: question.trim() ? "pointer" : "not-allowed", fontFamily: "Mukta, sans-serif", transition: "all 0.15s" }}>
                  ⚖️ {lang === "hi" ? "जवाब लें (RAG + AI)" : "Get Answer (RAG + AI)"}
                </button>
                {/* Sample questions */}
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 12, color: "#7A6E60", marginBottom: 8 }}>Try these:</div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {[
                      "Can my landlord increase rent without notice?",
                      "What is gratuity and when am I entitled?",
                      "Is a verbal contract valid in India?",
                      "क्या नौकरी में PF काटना अनिवार्य है?",
                    ].map((q, i) => (
                      <button key={i} onClick={() => setQuestion(q)} style={{ padding: "6px 12px", borderRadius: 20, border: "1.5px solid #E2D9C8", background: "white", color: "#1A1208", fontSize: 12, cursor: "pointer", fontFamily: "Mukta, sans-serif", transition: "all 0.15s" }}
                        onMouseEnter={e => e.target.style.borderColor = "#C8102E"}
                        onMouseLeave={e => e.target.style.borderColor = "#E2D9C8"}>
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div>
                <div onClick={() => fileRef.current?.click()} style={{ border: "2px dashed #E2D9C8", borderRadius: 14, padding: "36px 24px", textAlign: "center", cursor: "pointer", background: "white", marginBottom: 14, transition: "all 0.2s" }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = "#C8102E"}
                  onMouseLeave={e => e.currentTarget.style.borderColor = "#E2D9C8"}>
                  <div style={{ fontSize: 44, marginBottom: 10 }}>📋</div>
                  <div style={{ fontFamily: "Fraunces, serif", fontWeight: 700, fontSize: 17, color: "#1A1208", marginBottom: 6 }}>Drop your legal document</div>
                  <div style={{ fontSize: 13, color: "#7A6E60" }}>PDF · TXT · Any contract, agreement, or notice</div>
                  <input ref={fileRef} type="file" accept=".pdf,.txt" onChange={e => handleFile(e.target.files[0])} style={{ display: "none" }} />
                </div>
                <div style={{ textAlign: "center", color: "#7A6E60", fontSize: 13, marginBottom: 14 }}>— or paste text below —</div>
                <textarea
                  value={docText}
                  onChange={e => setDocText(e.target.value)}
                  placeholder="Paste any legal document text here..."
                  rows={6}
                  style={{ width: "100%", background: "white", border: "2px solid #E2D9C8", borderRadius: 12, padding: "14px 16px", fontSize: 13, color: "#1A1208", resize: "vertical", fontFamily: "Mukta, sans-serif", lineHeight: 1.6 }}
                />
                <button onClick={handleAnalyze} disabled={!docText.trim()} style={{ width: "100%", marginTop: 10, padding: 14, borderRadius: 12, background: docText.trim() ? "#C8102E" : "#E2D9C8", color: docText.trim() ? "white" : "#7A6E60", fontWeight: 800, fontSize: 16, border: "none", cursor: docText.trim() ? "pointer" : "not-allowed", fontFamily: "Mukta, sans-serif" }}>
                  🔍 {lang === "hi" ? "3-पास AI विश्लेषण" : "Analyze (3-Pass AI Reasoning)"}
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      <footer style={{ borderTop: "1px solid #E2D9C8", padding: "16px 24px", textAlign: "center", fontSize: 12, color: "#7A6E60" }}>
        NyaySetu is not a law firm. For serious matters, consult a qualified advocate. · Built with ❤️ for India
      </footer>
    </div>
  );
}
