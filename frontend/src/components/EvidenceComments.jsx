import React, { useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import axios from 'axios';
import {
  FaComment,
  FaCheck,
  FaTrash,
  FaPaperPlane,
  FaUserCircle,
  FaMicrophone,
  FaStop,
} from 'react-icons/fa';

import { useToast } from './ui';

/**
 * EvidenceComments — kompakt comment-tråd per evidens-felt (eller hele dokumentet).
 *
 * Brug:
 *   <EvidenceComments
 *     caseId="K-2026-0184"
 *     artifactId="dpia_dokument"
 *     sectionKey="risikovurdering"   // eller null for hele dokumentet
 *     user="pavi@kalundborg.dk"
 *   />
 *
 * Bygges typisk ind i EvidenceEditor pr. sektion + på toppen for "doc-level".
 *
 * Server-side emitterer kommentar-creation en notifikation + et timeline-event
 * så det vises i sagens audit-trail.
 */

const Wrap = styled.div`
  margin: 0.5rem 0 1rem;
  padding: 0.65rem 0.85rem;
  background: ${(p) => p.theme.colors.surfaceAlt || '#f6f8fb'};
  border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
  border-left: 2px solid ${(p) => p.theme.colors.primary || '#0d2e54'};
  border-radius: 0 4px 4px 0;
`;

const Header = styled.button`
  display: flex;
  align-items: center;
  gap: 0.45rem;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: ${(p) => p.theme.fonts.mono};
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: ${(p) => p.theme.colors.primary || '#0d2e54'};

  &:hover { text-decoration: underline; }

  .badge {
    background: ${(p) => p.theme.colors.primary || '#0d2e54'};
    color: white;
    border-radius: 8px;
    padding: 0.05rem 0.4rem;
    font-size: 0.65rem;
    font-weight: 600;
  }
`;

const Body = styled.div`
  margin-top: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const Item = styled.article`
  background: white;
  border: 1px solid ${(p) => p.theme.colors.borderSoft || '#e2e6ec'};
  border-radius: 4px;
  padding: 0.5rem 0.7rem;
  font-size: 0.85rem;
  opacity: ${(p) => (p.$resolved ? 0.55 : 1)};

  .meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.25rem;

    .who {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.7rem;
      color: ${(p) => p.theme.colors.textMuted};

      svg { font-size: 0.8rem; }
    }
    .actions {
      display: flex;
      gap: 0.3rem;

      button {
        background: transparent;
        border: none;
        color: ${(p) => p.theme.colors.textMuted};
        cursor: pointer;
        padding: 2px 4px;
        font-size: 0.7rem;

        &:hover { color: ${(p) => p.theme.colors.primary || '#0d2e54'}; }
      }
    }
  }
  .body {
    line-height: 1.5;
    color: ${(p) => p.theme.colors.text};
    white-space: pre-wrap;
  }
  .resolved-tag {
    font-family: ${(p) => p.theme.fonts.mono};
    font-size: 0.62rem;
    color: #2d6a31;
    margin-left: 0.4rem;
  }
`;

const ComposeRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  position: relative;

  textarea {
    width: 100%;
    min-height: 60px;
    padding: 0.45rem 0.6rem;
    font-family: inherit;
    font-size: 0.85rem;
    border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
    border-radius: 4px;
    resize: vertical;
  }
  .row {
    display: flex;
    justify-content: flex-end;
    gap: 0.4rem;
    align-items: center;

    .hint {
      flex: 1;
      font-size: 0.72rem;
      color: ${(p) => p.theme.colors.textMuted};
    }
    button {
      background: ${(p) => p.theme.colors.primary || '#0d2e54'};
      color: white;
      border: none;
      border-radius: 4px;
      padding: 0.4rem 0.75rem;
      cursor: pointer;
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;

      &:disabled { opacity: 0.45; cursor: not-allowed; }
    }
  }
`;

// Render @<email>-mentions som inline chips i kommentar-bodies
const MENTION_RE = /@([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/g;
function renderBodyWithMentions(text) {
  if (!text) return null;
  const parts = [];
  let lastIdx = 0;
  let match;
  let i = 0;
  // Reset regex state
  MENTION_RE.lastIndex = 0;
  while ((match = MENTION_RE.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index));
    }
    parts.push(
      <span
        key={`m-${i++}`}
        style={{
          background: 'rgba(13,46,84,0.08)',
          color: '#0d2e54',
          padding: '0.05rem 0.35rem',
          borderRadius: '3px',
          fontFamily: 'inherit',
          fontSize: '0.84em',
          fontWeight: 500,
        }}
        title={`Mention: ${match[1]}`}
      >
        @{match[1]}
      </span>,
    );
    lastIdx = match.index + match[0].length;
  }
  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx));
  }
  return parts;
}

function formatRelative(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return 'lige nu';
  if (min < 60) return `${min} min siden`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} t siden`;
  const days = Math.floor(h / 24);
  if (days < 7) return `${days} d siden`;
  return d.toLocaleDateString('da-DK', { day: 'numeric', month: 'short' });
}

const MentionDropdown = styled.div`
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  margin-bottom: 0.3rem;
  background: white;
  border: 1px solid ${(p) => p.theme.colors.border || '#d8dde6'};
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(13, 46, 84, 0.12);
  max-height: 240px;
  overflow-y: auto;
  z-index: 5;

  .item {
    padding: 0.45rem 0.7rem;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
    border-bottom: 1px solid #f1f3f7;

    &:last-child { border-bottom: none; }

    &.active, &:hover { background: rgba(13, 46, 84, 0.06); }

    .name {
      font-size: 0.85rem;
      color: ${(p) => p.theme.colors.text};
      font-weight: 500;
    }
    .email {
      font-family: ${(p) => p.theme.fonts.mono};
      font-size: 0.72rem;
      color: ${(p) => p.theme.colors.textMuted};
    }
    .role {
      display: inline-block;
      margin-left: 0.4rem;
      font-size: 0.65rem;
      color: ${(p) => p.theme.colors.textMuted};
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  }

  .empty {
    padding: 0.5rem 0.7rem;
    font-size: 0.78rem;
    color: ${(p) => p.theme.colors.textMuted};
    font-style: italic;
  }
`;

const EvidenceComments = ({
  caseId,
  artifactId,
  sectionKey = null,
  user,
  defaultOpen = false,
}) => {
  const toast = useToast();
  const [open, setOpen] = useState(defaultOpen);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [composeOpen, setComposeOpen] = useState(false);
  const [body, setBody] = useState('');
  const [posting, setPosting] = useState(false);

  // Whisper-diktering state
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // @-mention autocomplete state
  const textareaRef = useRef(null);
  const [mentionState, setMentionState] = useState({
    visible: false,
    query: '',
    startPos: -1,  // position af @ i body
    candidates: [],
    activeIndex: 0,
  });

  const startDictation = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error('Mikrofon-adgang ikke understøttet i denne browser');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mr.onstop = async () => {
        // Stop alle tracks så mikrofon-LED slukkes
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setTranscribing(true);
        try {
          const fd = new FormData();
          fd.append('audio', blob, 'recording.webm');
          fd.append('language', 'da');
          const r = await axios.post('/api/v3/transcribe', fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          const transcribed = r.data?.text || '';
          // Append til eksisterende tekst (eller erstat hvis tomt)
          setBody((prev) => prev ? `${prev} ${transcribed}` : transcribed);
          toast.success(`Transkriberet ${transcribed.length} tegn`);
        } catch (err) {
          toast.error(`Tale-til-tekst fejlede: ${err?.response?.data?.error?.message || err?.message}`);
        } finally {
          setTranscribing(false);
        }
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch (err) {
      toast.error(`Kunne ikke starte mikrofon: ${err.message}`);
    }
  };

  const stopDictation = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  };

  const fetchComments = async () => {
    if (!caseId || !artifactId) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ artifact_id: artifactId });
      if (sectionKey) params.set('section_key', sectionKey);
      const res = await axios.get(
        `/api/v3/cases/${encodeURIComponent(caseId)}/comments?${params.toString()}`,
      );
      setComments(res.data?.items || []);
    } catch (err) {
      // Stille — comments er nice-to-have
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, artifactId, sectionKey]);

  const handlePost = async () => {
    if (!body.trim() || !caseId || !artifactId) return;
    setPosting(true);
    try {
      await axios.post(
        `/api/v3/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(artifactId)}/comments`,
        {
          body: body.trim(),
          section_key: sectionKey || null,
          author: user || null,
        },
      );
      setBody('');
      setComposeOpen(false);
      fetchComments();
      toast.success('Kommentar sendt — vises også i sagens timeline');
    } catch (err) {
      toast.error(`Kunne ikke sende kommentar: ${err?.response?.data?.detail || err?.message}`);
    } finally {
      setPosting(false);
    }
  };

  // Detekt @-mention på cursor og hent autocomplete-kandidater
  const handleBodyChange = (e) => {
    const newBody = e.target.value;
    const cursor = e.target.selectionStart;
    setBody(newBody);

    // Find sidste @ før cursor uden mellemrum imellem
    const before = newBody.slice(0, cursor);
    const atIdx = before.lastIndexOf('@');
    if (atIdx === -1) {
      setMentionState((s) => ({ ...s, visible: false, candidates: [], query: '', startPos: -1 }));
      return;
    }
    const after = before.slice(atIdx + 1);
    // Hvis der er mellemrum/newline efter @ → ikke en aktiv mention
    if (/[\s\n]/.test(after)) {
      setMentionState((s) => ({ ...s, visible: false, candidates: [], query: '', startPos: -1 }));
      return;
    }
    // Aktivér ved @ med mindst 1 tegn efter (kan justeres)
    const query = after;
    setMentionState((s) => ({ ...s, visible: true, query, startPos: atIdx, activeIndex: 0 }));
  };

  // Fetch kandidater når query ændres
  useEffect(() => {
    if (!mentionState.visible) return;
    if (mentionState.query.length === 0) {
      // Vis aktive brugere generelt
      let cancelled = false;
      axios.get('/api/v3/users?limit=8')
        .then((r) => {
          if (!cancelled) setMentionState((s) => ({ ...s, candidates: r.data?.users || [] }));
        })
        .catch(() => {});
      return () => { cancelled = true; };
    }
    const handle = setTimeout(() => {
      axios.get(`/api/v3/users/search?q=${encodeURIComponent(mentionState.query)}&limit=8`)
        .then((r) => setMentionState((s) => ({ ...s, candidates: r.data?.users || [] })))
        .catch(() => {});
    }, 150);
    return () => clearTimeout(handle);
  }, [mentionState.visible, mentionState.query]);

  const insertMention = (email) => {
    setBody((prev) => {
      const before = prev.slice(0, mentionState.startPos);
      const afterStart = mentionState.startPos + 1 + mentionState.query.length;
      const after = prev.slice(afterStart);
      const insert = `@${email}`;
      const out = `${before}${insert} ${after}`;
      // Sæt cursor lige efter mention (best-effort i setTimeout fordi setState er async)
      setTimeout(() => {
        const newCursor = before.length + insert.length + 1;
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.setSelectionRange(newCursor, newCursor);
        }
      }, 0);
      return out;
    });
    setMentionState({ visible: false, query: '', startPos: -1, candidates: [], activeIndex: 0 });
  };

  const handleTextareaKeyDown = (e) => {
    if (!mentionState.visible || mentionState.candidates.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setMentionState((s) => ({
        ...s,
        activeIndex: (s.activeIndex + 1) % s.candidates.length,
      }));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setMentionState((s) => ({
        ...s,
        activeIndex: (s.activeIndex - 1 + s.candidates.length) % s.candidates.length,
      }));
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      const chosen = mentionState.candidates[mentionState.activeIndex];
      if (chosen) insertMention(chosen.email);
    } else if (e.key === 'Escape') {
      setMentionState((s) => ({ ...s, visible: false }));
    }
  };

  const handleResolve = async (id) => {
    try {
      await axios.post(`/api/v3/comments/${id}/resolve${user ? `?user=${encodeURIComponent(user)}` : ''}`);
      fetchComments();
      toast.info('Kommentar markeret som løst');
    } catch (err) {
      toast.error(`Kunne ikke markere som løst: ${err?.message}`);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Slet denne kommentar?')) return;
    try {
      await axios.delete(`/api/v3/comments/${id}`);
      fetchComments();
    } catch (err) {
      toast.error(`Kunne ikke slette: ${err?.message}`);
    }
  };

  const openCount = comments.filter((c) => !c.is_resolved).length;
  const totalCount = comments.length;

  if (!open && totalCount === 0) {
    return (
      <Wrap>
        <Header type="button" onClick={() => { setOpen(true); setComposeOpen(true); }} aria-label="Tilføj kommentar">
          <FaComment /> Tilføj kommentar
        </Header>
      </Wrap>
    );
  }

  return (
    <Wrap>
      <Header type="button" onClick={() => setOpen((v) => !v)}>
        <FaComment />
        Kommentarer
        {totalCount > 0 && (
          <span className="badge">{openCount > 0 ? openCount : totalCount}</span>
        )}
      </Header>

      {open && (
        <Body>
          {loading && <div style={{ fontSize: '0.78rem', color: '#5f6b7a' }}>Henter…</div>}
          {!loading && comments.length === 0 && (
            <div style={{ fontSize: '0.78rem', color: '#5f6b7a', fontStyle: 'italic' }}>
              Ingen kommentarer endnu.
            </div>
          )}
          {comments.map((c) => (
            <Item key={c.id} $resolved={c.is_resolved}>
              <div className="meta">
                <span className="who">
                  <FaUserCircle />
                  {c.author || 'Anonym'}
                  <span style={{ marginLeft: 4, opacity: 0.7 }}>·</span>
                  <span style={{ marginLeft: 4 }}>{formatRelative(c.created_at)}</span>
                  {c.is_resolved && <span className="resolved-tag">✓ løst</span>}
                </span>
                <span className="actions">
                  {!c.is_resolved && (
                    <button
                      type="button"
                      onClick={() => handleResolve(c.id)}
                      title="Markér som løst"
                      aria-label="Markér som løst"
                    >
                      <FaCheck />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDelete(c.id)}
                    title="Slet kommentar"
                    aria-label="Slet kommentar"
                  >
                    <FaTrash />
                  </button>
                </span>
              </div>
              <div className="body">{renderBodyWithMentions(c.body)}</div>
            </Item>
          ))}

          {!composeOpen && (
            <button
              type="button"
              onClick={() => setComposeOpen(true)}
              style={{
                background: 'transparent',
                border: '1px dashed #d8dde6',
                color: '#0d2e54',
                padding: '0.4rem 0.7rem',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: '0.78rem',
                alignSelf: 'flex-start',
              }}
            >
              + Skriv kommentar
            </button>
          )}

          {composeOpen && (
            <ComposeRow>
              {mentionState.visible && mentionState.candidates.length > 0 && (
                <MentionDropdown role="listbox" aria-label="@-mention forslag">
                  {mentionState.candidates.map((u, idx) => (
                    <div
                      key={u.email}
                      className={`item ${idx === mentionState.activeIndex ? 'active' : ''}`}
                      onMouseDown={(e) => { e.preventDefault(); insertMention(u.email); }}
                      role="option"
                      aria-selected={idx === mentionState.activeIndex}
                    >
                      <div className="name">
                        {u.display_name}
                        <span className="role">{u.role}</span>
                      </div>
                      <div className="email">{u.email}</div>
                    </div>
                  ))}
                </MentionDropdown>
              )}
              {mentionState.visible && mentionState.candidates.length === 0 && mentionState.query.length > 0 && (
                <MentionDropdown>
                  <div className="empty">
                    Ingen brugere matcher "@{mentionState.query}" — admin kan tilføje via Indstillinger
                  </div>
                </MentionDropdown>
              )}
              <textarea
                ref={textareaRef}
                value={body}
                onChange={handleBodyChange}
                onKeyDown={handleTextareaKeyDown}
                placeholder="Skriv en kommentar — brug @email for at notificere kolleger"
                maxLength={4000}
                aria-label="Kommentar-tekst"
                autoFocus
              />
              <div className="row">
                <span className="hint">
                  {body.length}/4000 tegn
                  {transcribing && ' · transkriberer…'}
                </span>
                <button
                  type="button"
                  onClick={recording ? stopDictation : startDictation}
                  disabled={transcribing}
                  title={recording ? 'Stop og transkribér' : 'Diktér med Whisper'}
                  style={{
                    background: recording ? '#a02020' : 'transparent',
                    color: recording ? 'white' : '#0d2e54',
                    border: `1px solid ${recording ? '#a02020' : '#d8dde6'}`,
                  }}
                  aria-label={recording ? 'Stop diktering' : 'Start diktering'}
                >
                  {recording ? <FaStop /> : <FaMicrophone />}
                  {recording ? 'Stop' : ''}
                </button>
                <button
                  type="button"
                  onClick={() => { setComposeOpen(false); setBody(''); stopDictation(); }}
                  style={{ background: 'transparent', color: '#0d2e54', border: '1px solid #d8dde6' }}
                >
                  Annullér
                </button>
                <button type="button" onClick={handlePost} disabled={posting || !body.trim() || recording}>
                  <FaPaperPlane /> {posting ? 'Sender…' : 'Send'}
                </button>
              </div>
            </ComposeRow>
          )}
        </Body>
      )}
    </Wrap>
  );
};

export default EvidenceComments;
