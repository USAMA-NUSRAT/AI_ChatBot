import { useEffect, useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function Documents() {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState(null) // { type: 'ok' | 'error', text }
  const fileInputRef = useRef(null)

  async function loadDocuments() {
    try {
      const res = await fetch(`${API_URL}/api/documents`)
      if (!res.ok) throw new Error('Could not load documents')
      setDocuments(await res.json())
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  async function uploadFile(e) {
    const file = e.target.files[0]
    e.target.value = '' // allow choosing the same file again later
    if (!file) return

    setUploading(true)
    setMessage(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API_URL}/api/documents`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setMessage({ type: 'ok', text: `"${data.filename}" saved as ${data.chunk_count} chunks` })
      loadDocuments()
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setUploading(false)
    }
  }

  async function deleteDocument(doc) {
    if (!confirm(`Delete "${doc.filename}" and all its chunks?`)) return
    try {
      const res = await fetch(`${API_URL}/api/documents/${doc.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')
      setMessage({ type: 'ok', text: `"${doc.filename}" deleted` })
      loadDocuments()
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    }
  }

  return (
    <section className="documents">
      <div className="documents-header">
        <h2>Documents</h2>
        <button onClick={() => fileInputRef.current.click()} disabled={uploading}>
          {uploading ? 'Uploading…' : 'Upload file'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={uploadFile}
          hidden
        />
      </div>

      {message && <p className={`documents-message ${message.type}`}>{message.text}</p>}

      {documents.length === 0 ? (
        <p className="documents-empty">No documents yet. Upload a .pdf, .txt or .md file.</p>
      ) : (
        <ul className="documents-list">
          {documents.map((doc) => (
            <li key={doc.id}>
              <span className="doc-name">{doc.filename}</span>
              <span className="doc-meta">{doc.chunk_count} chunks</span>
              <button className="doc-delete" onClick={() => deleteDocument(doc)} title="Delete">
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default Documents
