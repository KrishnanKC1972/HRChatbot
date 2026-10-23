import { NavLink, Route, Routes } from 'react-router-dom'
import Chat from './pages/Chat.jsx'
import Dashboard from './pages/Dashboard.jsx'

export default function App() {
  return (
    <div className="layout">
      <header className="topbar">
        <div className="brand">
          <span className="brand-logo">HR</span>
          <div>
            <h1>HR Policy Assistant</h1>
            <p>Agentic RAG · Intelligent Routing · Automated Evaluation</p>
          </div>
        </div>
        <nav>
          <NavLink to="/" end>
            Chat
          </NavLink>
          <NavLink to="/dashboard">Evaluation Dashboard</NavLink>
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  )
}
