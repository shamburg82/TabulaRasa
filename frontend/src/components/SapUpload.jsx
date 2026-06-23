import { useState, useRef } from 'react';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { uploadSap } from '../api/stage1.js';

const ACCEPT = '.pdf,.docx,.doc';

/**
 * Reusable upload widget for a SAP document.
 *
 * Props:
 *   studyId         optional pre-filled study id (locked when set)
 *   onUploaded({ studyId, response })  fired on 202 success
 *   compact         hides the study_id field (when studyId is provided)
 */
export default function SapUpload({ studyId: lockedStudyId = null, onUploaded, compact = false }) {
  const [studyId, setStudyId] = useState(lockedStudyId || '');
  const [versionTag, setVersionTag] = useState('');
  const [houseStandards, setHouseStandards] = useState('');
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const pick = (f) => {
    setError(null);
    if (!f) return;
    if (!/\.(pdf|docx?|DOCX?|PDF)$/.test(f.name)) {
      setError('Unsupported file type. Expected PDF or Word.');
      return;
    }
    setFile(f);
  };

  const submit = async () => {
    setError(null);
    const sid = (lockedStudyId || studyId).trim();
    if (!sid) return setError('Study ID is required.');
    if (!/^[A-Za-z0-9_\-.]+$/.test(sid)) {
      return setError('Study ID may only contain letters, numbers, dash, underscore, dot.');
    }
    if (!file) return setError('Please choose a SAP file.');

    setBusy(true);
    try {
      const response = await uploadSap(sid, {
        file,
        versionTag: versionTag.trim() || null,
        houseStandards: houseStandards.trim() || null,
      });
      onUploaded && onUploaded({ studyId: sid, response });
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      {!compact && (
        <Field label="Study ID" required>
          <input
            type="text"
            value={studyId}
            onChange={(e) => setStudyId(e.target.value)}
            disabled={busy || !!lockedStudyId}
            placeholder="ABC-301"
            className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm font-mono"
          />
        </Field>
      )}

      <Field label="SAP file" required>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            pick(e.dataTransfer.files?.[0]);
          }}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded p-5 text-center cursor-pointer transition-colors ${
            dragging
              ? 'border-ink bg-paper-deep'
              : 'border-paper-deep bg-white hover:bg-paper-deep/40'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0])}
          />
          {file ? (
            <div className="flex items-center justify-center gap-2 text-sm">
              <FileText size={16} />
              <span className="font-mono">{file.name}</span>
              <span className="text-ink-faint font-mono text-[11px]">
                ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </span>
              <button
                type="button"
                className="ml-2 text-ink-muted hover:text-accent"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-1 text-ink-muted text-xs">
              <Upload size={20} className="text-ink-faint" />
              <span>Drop a PDF or Word file here, or click to browse.</span>
            </div>
          )}
        </div>
      </Field>

      <Field label="Version tag" hint="Optional. Example: v2.1 (amendment 3)">
        <input
          type="text"
          value={versionTag}
          onChange={(e) => setVersionTag(e.target.value)}
          disabled={busy}
          placeholder="v2.1"
          className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-sm font-mono"
        />
      </Field>

      <Field
        label="House standards"
        hint="Optional. Reference identifier or paste a snippet for gap defaults."
      >
        <textarea
          value={houseStandards}
          onChange={(e) => setHouseStandards(e.target.value)}
          disabled={busy}
          placeholder="SOP-BIO-014"
          rows={2}
          className="w-full bg-white border border-paper-deep rounded px-2 py-1.5 text-xs leading-relaxed"
        />
      </Field>

      {error && (
        <div className="text-xs text-accent font-mono bg-paper-deep border border-paper-deep p-2 rounded">
          {error}
        </div>
      )}

      <button
        onClick={submit}
        disabled={busy || !file || !(lockedStudyId || studyId.trim())}
        className="btn-primary text-xs px-4 py-2 rounded font-medium flex items-center gap-2 disabled:opacity-50"
      >
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
        {busy ? 'Starting extraction...' : 'Upload SAP & start extraction'}
      </button>
    </div>
  );
}

function Field({ label, required, hint, children }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-ink-muted mb-1 flex items-center gap-2">
        <span>{label}</span>
        {required && <span className="text-accent">*</span>}
        {hint && <span className="normal-case tracking-normal text-ink-faint">— {hint}</span>}
      </div>
      {children}
    </div>
  );
}
