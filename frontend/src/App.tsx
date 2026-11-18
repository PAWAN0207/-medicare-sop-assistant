import { useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import {
  Activity,
  ArrowUp,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  FileText,
  HeartPulse,
  History,
  Menu,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRound,
  X,
} from 'lucide-react'

// --------------------------------------------------
// Types
// --------------------------------------------------

type Citation = {
  sop_id: string
  version: string
  title: string
  section: string
  section_title: string
  page: number
}

type ApiResponse = {
  answer: string
  refused: boolean
  reason: string
  citations: Citation[]
  cached: boolean
  index_generation: number
  request_id: string
}

type ApiError = {
  error?: {
    code?: string
    message?: string
    request_id?: string
    details?: Record<string, unknown>
  }
}

type Message = {
  id: number
  role: 'user' | 'assistant'
  content: string
  response?: ApiResponse
  error?: boolean
  requestId?: string
}

// --------------------------------------------------
// Configuration
// --------------------------------------------------

// Local development:
// VITE_API_BASE_URL is not required.
// Vite proxy forwards /api to localhost:8000.
//
// Production:
// Set VITE_API_BASE_URL to your deployed backend URL.

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || '/api'
).replace(/\/+$/, '')

const API_URL = `${API_BASE_URL}/v1/ask`

const suggestions = [
  'What is the procedure for a needle-stick injury?',
  'What should I do during a Code Pink emergency?',
  'How should biomedical waste be segregated?',
  'What is the procedure for handling patient complaints?',
]

// --------------------------------------------------
// Main Application
// --------------------------------------------------

function App() {
  const [userId, setUserId] = useState('U2001')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [mobileSidebar, setMobileSidebar] = useState(false)
  const [showStaff, setShowStaff] = useState(false)

  // ------------------------------------------------
  // Send Question to Backend
  // ------------------------------------------------

  async function sendQuestion(
    event?: FormEvent<HTMLFormElement>,
    suggestedQuestion?: string,
  ) {
    event?.preventDefault()

    const text = (suggestedQuestion ?? question).trim()
    const staffId = userId.trim()

    if (loading || !text || !staffId) {
      return
    }

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: text,
    }

    setMessages((previous) => [...previous, userMessage])
    setQuestion('')
    setLoading(true)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',

        headers: {
          'Content-Type': 'application/json',
        },

        body: JSON.stringify({
          user_id: staffId,
          question: text,
        }),
      })

      // Safely parse the API response
      let data: ApiResponse | ApiError

      try {
        data = await response.json()
      } catch {
        throw new Error(
          `The server returned an invalid response (${response.status}).`,
        )
      }

      // --------------------------------------------
      // Handle Backend Errors
      // --------------------------------------------

      if (!response.ok) {
        const errorData = data as ApiError

        const errorMessage =
          errorData?.error?.message ||
          'Unable to process your request. Please try again.'

        const requestId =
          errorData?.error?.request_id ||
          response.headers.get('X-Request-ID') ||
          undefined

        setMessages((previous) => [
          ...previous,
          {
            id: Date.now() + 1,
            role: 'assistant',
            content: errorMessage,
            error: true,
            requestId,
          },
        ])

        return
      }

      // --------------------------------------------
      // Handle Successful Response
      // --------------------------------------------

      const result = data as ApiResponse

      if (typeof result.answer !== 'string') {
        throw new Error('The server response is missing the answer field.')
      }

      setMessages((previous) => [
        ...previous,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: result.answer,
          response: result,
        },
      ])
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Unable to connect to the server.'

      setMessages((previous) => [
        ...previous,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: errorMessage,
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  // ------------------------------------------------
  // Start New Conversation
  // ------------------------------------------------

  function newChat() {
    setMessages([])
    setQuestion('')
    setMobileSidebar(false)
  }

  // ------------------------------------------------
  // Render UI
  // ------------------------------------------------

  return (
    <div className="app-shell">

      {/* Mobile Sidebar Overlay */}

      {mobileSidebar && (
        <button
          className="mobile-overlay"
          onClick={() => setMobileSidebar(false)}
          aria-label="Close navigation"
        />
      )}

      {/* ------------------------------------------ */}
      {/* Sidebar */}
      {/* ------------------------------------------ */}

      <aside
        className={`sidebar ${mobileSidebar ? 'sidebar-open' : ''}`}
      >
        <div className="brand">

          <div className="brand-icon">
            <HeartPulse size={23} />
          </div>

          <div>
            <h1>MediCare</h1>
            <span>SOP ASSISTANT</span>
          </div>

          <button
            className="icon-button mobile-close"
            onClick={() => setMobileSidebar(false)}
            aria-label="Close sidebar"
          >
            <X size={19} />
          </button>

        </div>

        {/* New Conversation */}

        <button
          className="new-chat-button"
          onClick={newChat}
        >
          <Plus size={18} />
          <span>New conversation</span>
        </button>

        {/* Workspace Navigation */}

        <div className="sidebar-section">

          <span className="section-label">
            WORKSPACE
          </span>

          <button className="nav-item active">
            <MessageSquare size={18} />
            <span>SOP Assistant</span>
          </button>

          <button
            className="nav-item"
            onClick={newChat}
          >
            <History size={18} />
            <span>Conversation history</span>
          </button>

          <button className="nav-item">
            <BookOpen size={18} />
            <span>SOP Library</span>
          </button>

        </div>

        {/* Sidebar Bottom */}

        <div className="sidebar-bottom">

          <div className="security-card">

            <ShieldCheck size={19} />

            <div>
              <strong>Secure workspace</strong>
              <span>Role-based document access</span>
            </div>

          </div>

          {/* Staff Profile */}

          <button
            className="profile-button"
            onClick={() => setShowStaff(!showStaff)}
            aria-expanded={showStaff}
          >

            <div className="avatar">
              <UserRound size={18} />
            </div>

            <div className="profile-details">
              <strong>Clinic Staff</strong>
              <span>{userId || 'No staff ID'}</span>
            </div>

            <ChevronDown size={16} />

          </button>

          {/* Staff ID Editor */}

          {showStaff && (
            <div className="staff-editor">

              <label htmlFor="staff-id">
                Staff ID
              </label>

              <input
                id="staff-id"
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                placeholder="Enter staff ID"
                maxLength={50}
              />

              <span>
                Access is determined by the backend.
              </span>

            </div>
          )}

        </div>

      </aside>

      {/* ------------------------------------------ */}
      {/* Main Area */}
      {/* ------------------------------------------ */}

      <main className="main-area">

        {/* Top Navigation */}

        <header className="topbar">

          <div className="topbar-left">

            <button
              className="icon-button mobile-menu"
              onClick={() => setMobileSidebar(true)}
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>

            <div>

              <div className="breadcrumb">
                Workspace <span>/</span> SOP Assistant
              </div>

              <div className="page-title">
                Clinical Knowledge Assistant
              </div>

            </div>

          </div>

          <div className="topbar-right">

            <div className="system-status">
              <span />
              System workspace
            </div>

            <div className="top-avatar">
              <UserRound size={18} />
            </div>

          </div>

        </header>

        {/* ---------------------------------------- */}
        {/* Chat Container */}
        {/* ---------------------------------------- */}

        <section className="chat-container">

          <div className="chat-content">

            {/* Welcome Screen */}

            {messages.length === 0 ? (

              <div className="welcome-section">

                <div className="welcome-badge">
                  <Sparkles size={14} />
                  AI-POWERED SOP KNOWLEDGE
                </div>

                <div className="welcome-icon">
                  <Stethoscope size={31} />
                </div>

                <h2>
                  Your clinical knowledge,
                  <br />
                  <span>one question away.</span>
                </h2>

                <p className="welcome-description">
                  Get reliable answers from your organisation&apos;s
                  Standard Operating Procedures. Every answer is
                  grounded in approved documentation and includes
                  source references.
                </p>

                {/* Suggested Questions */}

                <div className="suggestion-heading">
                  <span>GET STARTED</span>
                  <span>Suggested questions</span>
                </div>

                <div className="suggestion-grid">

                  {suggestions.map((item, index) => (

                    <button
                      className="suggestion-card"
                      key={item}
                      onClick={() => {
                        void sendQuestion(undefined, item)
                      }}
                      disabled={loading || !userId.trim()}
                    >

                      <div className="suggestion-icon">

                        {index === 0 ? (
                          <Activity size={19} />
                        ) : index === 1 ? (
                          <ShieldCheck size={19} />
                        ) : index === 2 ? (
                          <FileText size={19} />
                        ) : (
                          <BookOpen size={19} />
                        )}

                      </div>

                      <span>{item}</span>

                      <ArrowUp
                        size={16}
                        className="suggestion-arrow"
                      />

                    </button>

                  ))}

                </div>

                <div className="trust-note">
                  <ShieldCheck size={15} />
                  Answers are generated using accessible SOP documentation.
                </div>

              </div>

            ) : (

              /* ---------------------------------- */
              /* Conversation Messages */
              /* ---------------------------------- */

              <div className="conversation">

                {messages.map((message) => (

                  <div
                    className={`message-row ${message.role}`}
                    key={message.id}
                  >

                    {/* Message Avatar */}

                    <div className="message-avatar">

                      {message.role === 'user' ? (
                        <UserRound size={17} />
                      ) : (
                        <HeartPulse size={18} />
                      )}

                    </div>

                    <div className="message-body">

                      <div className="message-author">

                        {message.role === 'user'
                          ? 'You'
                          : 'MediCare Assistant'}

                      </div>

                      {/* Message Content */}

                      <div
                        className={`message-bubble ${
                          message.error ? 'error-bubble' : ''
                        }`}
                      >

                        {message.role === 'assistant' &&
                        !message.error ? (

                          <div className="markdown-content">

                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{

                                h1: ({ children }) => (
                                  <h2 className="answer-heading">
                                    {children}
                                  </h2>
                                ),

                                h2: ({ children }) => (
                                  <h2 className="answer-heading">
                                    {children}
                                  </h2>
                                ),

                                h3: ({ children }) => (
                                  <h3 className="answer-subheading">
                                    {children}
                                  </h3>
                                ),

                                p: ({ children }) => (
                                  <p className="answer-paragraph">
                                    {children}
                                  </p>
                                ),

                                ul: ({ children }) => (
                                  <ul className="answer-list">
                                    {children}
                                  </ul>
                                ),

                                ol: ({ children }) => (
                                  <ol className="answer-list ordered-list">
                                    {children}
                                  </ol>
                                ),

                                li: ({ children }) => (
                                  <li className="answer-list-item">
                                    {children}
                                  </li>
                                ),

                                strong: ({ children }) => (
                                  <strong className="answer-bold">
                                    {children}
                                  </strong>
                                ),

                                blockquote: ({ children }) => (
                                  <blockquote className="answer-quote">
                                    {children}
                                  </blockquote>
                                ),

                                code: ({ children }) => (
                                  <code className="answer-code">
                                    {children}
                                  </code>
                                ),

                                table: ({ children }) => (
                                  <div className="answer-table-wrapper">

                                    <table className="answer-table">
                                      {children}
                                    </table>

                                  </div>
                                ),

                              }}
                            >
                              {message.content}
                            </ReactMarkdown>

                          </div>

                        ) : (

                          message.content

                        )}

                      </div>

                      {/* -------------------------------- */}
                      {/* Response Metadata */}
                      {/* -------------------------------- */}

                      {message.response && (

                        <div className="response-meta">

                          {/* Refusal Information */}

                          {message.response.refused ? (

                            <div className="refusal-note">

                              <ShieldCheck size={16} />

                              This question could not be answered from
                              the available SOP documentation.

                              {message.response.reason && (
                                <span>
                                  Reason: {message.response.reason}
                                </span>
                              )}

                            </div>

                          ) : (

                            <>

                              <div className="answer-status">
                                <CheckCircle2 size={15} />
                                Grounded in SOP documentation
                              </div>

                              {/* Citations */}

                              {message.response.citations?.length > 0 && (

                                <div className="citations">

                                  <div className="citation-heading">
                                    <BookOpen size={16} />
                                    Source references
                                  </div>

                                  {message.response.citations.map(
                                    (citation, index) => (

                                      <div
                                        className="citation-card"
                                        key={`${citation.sop_id}-${citation.section}-${index}`}
                                      >

                                        <FileText size={17} />

                                        <div>

                                          <strong>
                                            {citation.title}
                                          </strong>

                                          <span>
                                            {citation.sop_id} · Version{' '}
                                            {citation.version}
                                          </span>

                                          <span>
                                            Section {citation.section}:{' '}
                                            {citation.section_title} · Page{' '}
                                            {citation.page}
                                          </span>

                                        </div>

                                      </div>

                                    ),
                                  )}

                                </div>

                              )}

                            </>

                          )}

                          {/* Request Information */}

                          <div className="request-details">

                            {message.response.cached && (
                              <span>Cached response</span>
                            )}

                            <span>
                              Request ID: {message.response.request_id}
                            </span>

                          </div>

                        </div>

                      )}

                      {/* Error Request ID */}

                      {message.error && message.requestId && (

                        <div className="request-details">
                          <span>
                            Request ID: {message.requestId}
                          </span>
                        </div>

                      )}

                    </div>

                  </div>

                ))}

                {/* Loading Indicator */}

                {loading && (

                  <div className="message-row assistant">

                    <div className="message-avatar">
                      <HeartPulse size={18} />
                    </div>

                    <div className="message-body">

                      <div className="message-author">
                        MediCare Assistant
                      </div>

                      <div className="typing-indicator">

                        <span />
                        <span />
                        <span />

                        <span>
                          Reviewing SOP documentation...
                        </span>

                      </div>

                    </div>

                  </div>

                )}

                <div className="conversation-end" />

              </div>

            )}

          </div>

          {/* ---------------------------------------- */}
          {/* Message Composer */}
          {/* ---------------------------------------- */}

          <div className="composer-area">

            <form
              className="composer"
              onSubmit={(event) => {
                void sendQuestion(event)
              }}
            >

              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Ask a question about clinic SOPs..."
                rows={2}
                maxLength={1000}
                disabled={loading}
                aria-label="Ask a question about clinic SOPs"

                onKeyDown={(event) => {

                  if (
                    event.key === 'Enter' &&
                    !event.shiftKey &&
                    !event.nativeEvent.isComposing
                  ) {
                    event.preventDefault()
                    void sendQuestion()
                  }

                }}
              />

              {/* Composer Footer */}

              <div className="composer-footer">

                <div className="composer-hint">
                  <ShieldCheck size={15} />
                  Answers include verified SOP citations
                </div>

                <div className="composer-actions">

                  <span>
                    {question.length}/1000
                  </span>

                  <button
                    className="send-button"
                    type="submit"
                    disabled={
                      !question.trim() ||
                      !userId.trim() ||
                      loading
                    }
                    aria-label="Send question"
                  >

                    <Send size={17} />
                    Ask SOPs

                  </button>

                </div>

              </div>

            </form>

            {/* Disclaimer */}

            <div className="disclaimer">
              Always follow your organisation&apos;s approved clinical
              protocols. AI-generated responses should be verified
              against the cited SOP.
            </div>

          </div>

        </section>

      </main>

    </div>
  )
}

export default App