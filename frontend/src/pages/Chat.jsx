import { useEffect, useRef, useState } from 'react'
import { sendChat } from '../api.js'

const EXAMPLES = [
  'How many paid leave days do employees get per year?',
  'What is the expense reimbursement policy?',
  'Is working from home allowed?',
  'How do I report a security incident?',
  'Hello, how are you today?',
]

function ScoreBar({ label, value }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div className="score-bar">
      <div className="score-bar-head">
        <span>{label}</span>
        <span className="score-value">{value != null ? value.toFixed(2) : '—'}</span>
      </div>
      <div className="score-track">
        <div
          className={`score-fill ${value >= 0.7 ? 'good' : 'bad'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function EvaluationPanel({ evaluation }) {
  if (!evaluation) return null
  if (evaluation.error) {
    return <div className="eval-error">Evaluation unavailable: {evaluation.error}</div>
  }
  const pass = evaluation.verdict === 'PASS'
  return (
    <div className="eval-panel">
      <div className="eval-header">
        <span className="section-title">Evaluator</span>
        <span className={`verdict ${pass ? 'pass' : 'fail'}`}>{evaluation.verdict}</span>
      </div>
      <ScoreBar label="Relevance" value={evaluation.relevance_score} />
      <ScoreBar label="Faithfulness" value={evaluation.faithfulness_score} />
      <ScoreBar label="Overall" value={evaluation.overall_score} />
      <p className="eval-reasoning">{evaluation.reasoning}</p>
      {!pass && evaluation.suggestions && evaluation.suggestions !== 'None' && (
        <p className="eval-suggestions">💡 {evaluation.suggestions}</p>
      )}
    </div>
  )
}

function Message({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="bubble">
        <p className="bubble-text">{message.content}</p>
        {!isUser && message.meta && (
          <div className="meta">
            <div className="badges">
              <span className={`badge ${message.meta.used_rag ? 'rag' : 'direct'}`}>
                {message.meta.used_rag ? 'RAG (Policy)' : 'Direct LLM'}
              </span>
              {message.meta.routing?.reasoning && (
                <details className="routing-details">
                  <summary>Routing reasoning</summary>
                  <p>{message.meta.routing.reasoning}</p>
                </details>
              )}
            </div>
            {message.meta.sources && message.meta.sources.length > 0 && (
              <div className="sources">
                <span className="section-title">Source policies</span>
                <div className="source-chips">
                  {message.meta.sources.map((s, idx) => (
                    <span key={idx} className="source-chip" title={s.snippet}>
                      📄 {s.source}
                      {s.page != null ? ` · p.${Number(s.page) + 1}` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {message.meta.context && (
              <details className="context-details">
                <summary>Retrieved context</summary>
                <pre>{message.meta.context}</pre>
              </details>
            )}
            <EvaluationPanel evaluation={message.meta.evaluation} />
          </div>
        )}
      </div>
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function submit(text) {
    const query = (text ?? input).trim()
    if (!query || loading) return
    setError(null)
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: query }])
    setLoading(true)
    try {
      const res = await sendChat(query)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          meta: {
            used_rag: res.used_rag,
            routing: res.routing,
            context: res.context,
            sources: res.sources,
            evaluation: res.evaluation,
          },
        },
      ])
    } catch (e) {
      setError(e.message)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Sorry, something went wrong: ${e.message}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-scroll">
        {messages.length === 0 && (
          <div className="empty-state">
            <h2>Ask me anything about HR policies</h2>
            <p>
              I route your question to the policy knowledge base (RAG) or answer directly, then an
              evaluator LLM scores every response.
            </p>
            <div className="examples">
              {EXAMPLES.map((q) => (
                <button key={q} className="chip" onClick={() => submit(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && (
          <div className="message assistant">
            <div className="bubble loading">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
              <span>Thinking &amp; evaluating…</span>
            </div>
          </div>
        )}
        {error && <div className="error-banner">{error}</div>}
        <div ref={bottomRef} />
      </div>
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about leave, benefits, expenses, IT security…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
