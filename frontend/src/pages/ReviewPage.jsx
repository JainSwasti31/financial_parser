import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getReview, updateFields, approveDocument, rejectDocument, reprocessDocument } from '../services/api';

const STATUS_BADGE = {
  valid:   'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  invalid: 'bg-red-500/15 text-red-300 border-red-500/30',
  missing: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
};

const STATUS_ICON = { valid: '✓', invalid: '✗', missing: '!' };
const errorMessage = (error, fallback) =>
  error.response?.data?.error?.message || error.response?.data?.detail || fallback;

const DOC_STATUS_COLORS = {
  Approved:           'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  Rejected:           'bg-red-500/20 text-red-300 border-red-500/30',
  Parsed:             'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  'Validation Failed':'bg-red-500/20 text-red-300 border-red-500/30',
  'Review Pending':   'bg-amber-500/20 text-amber-300 border-amber-500/30',
  Processing:         'bg-blue-500/20 text-blue-300 border-blue-500/30',
};

const ReviewPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [editedFields, setEditedFields] = useState({});
  const [validations, setValidations] = useState({});
  const [confidences, setConfidences] = useState({});
  const [remarks, setRemarks] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dirty, setDirty] = useState(false);

  const fetchReview = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getReview(id);
      setData(res.data);
      setEditedFields({ ...res.data.parsed_fields });
      setValidations(res.data.field_validations || {});
      setConfidences(res.data.field_confidences || {});
      setRemarks(res.data.remarks || '');
    } catch (e) {
      setError(errorMessage(e, 'Failed to load review data.'));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchReview(); }, [fetchReview]);

  const handleFieldChange = (key, value) => {
    setEditedFields(prev => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSaveFields = async () => {
    setSaving(true);
    setError('');
    try {
      const res = await updateFields(id, editedFields);
      setValidations(res.data.field_validations);
      setConfidences(res.data.field_confidences || {});
      setData(prev => ({ ...prev, validation_status: res.data.validation_status }));
      setDirty(false);
      setSuccess('Fields saved and re-validated.');
      setTimeout(() => setSuccess(''), 3000);
    } catch (e) {
      setError(errorMessage(e, 'Failed to save fields.'));
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    setActionLoading('approve');
    setError('');
    try {
      await approveDocument(id, remarks);
      navigate(`/documents/${id}`);
    } catch (e) {
      setError(errorMessage(e, 'Approval failed.'));
      setActionLoading('');
    }
  };

  const handleReject = async () => {
    if (!remarks.trim()) { setError('Please provide a reason for rejection.'); return; }
    setActionLoading('reject');
    setError('');
    try {
      await rejectDocument(id, remarks);
      navigate(`/documents/${id}`);
    } catch (e) {
      setError(errorMessage(e, 'Rejection failed.'));
      setActionLoading('');
    }
  };

  const handleReprocess = async () => {
    setActionLoading('reprocess');
    try {
      await reprocessDocument(id);
      navigate(`/documents/${id}`);
    } catch (e) {
      setError(errorMessage(e, 'Failed to trigger reprocess.'));
      setActionLoading('');
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (error && !data) return (
    <div className="text-center py-20 text-red-400">{error}</div>
  );

  const isLocked = data?.review_status === 'Approved' || data?.review_status === 'Rejected';
  const validCount   = Object.values(validations).filter(v => v.status === 'valid').length;
  const invalidCount = Object.values(validations).filter(v => v.status === 'invalid').length;
  const missingCount = Object.values(validations).filter(v => v.status === 'missing').length;
  const fieldKeys = [...new Set([
    ...Object.keys(editedFields || {}),
    ...Object.keys(validations || {}).filter(key => key !== 'duplicate_document'),
  ])];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <Link to={`/documents/${id}`}
        className="text-indigo-400 hover:text-indigo-300 transition-colors flex items-center text-sm w-fit">
        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Document
      </Link>

      {/* Alerts */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg text-sm">{error}</div>
      )}
      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 px-4 py-3 rounded-lg text-sm">{success}</div>
      )}

      {/* Header */}
      <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 p-8 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-40 h-40 bg-violet-500/10 rounded-full blur-3xl" />
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 relative">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Manual Review</h1>
            <p className="text-slate-400 text-sm">{data?.document_name}</p>
            <div className="flex items-center gap-3 mt-3 flex-wrap">
              <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${DOC_STATUS_COLORS[data?.document_status] || ''}`}>
                {data?.document_status}
              </span>
              <span className="px-3 py-1 bg-violet-500/20 text-violet-300 text-xs font-semibold rounded-full border border-violet-500/30">
                {data?.document_type}
              </span>
              <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${
                data?.validation_status === 'Passed' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                data?.validation_status === 'Failed' ? 'bg-red-500/20 text-red-300 border-red-500/30' :
                'bg-amber-500/20 text-amber-300 border-amber-500/30'
              }`}>
                Validation: {data?.validation_status}
              </span>
            </div>
          </div>
          {/* Field stats */}
          <div className="flex gap-4 shrink-0">
            {[['✓ Valid', validCount, 'text-emerald-400'], ['✗ Invalid', invalidCount, 'text-red-400'], ['! Missing', missingCount, 'text-amber-400']].map(([label, count, cls]) => (
              <div key={label} className="text-center">
                <div className={`text-2xl font-bold ${cls}`}>{count}</div>
                <div className="text-xs text-slate-500">{label}</div>
              </div>
            ))}
          </div>
        </div>
        {isLocked && (
          <div className={`mt-4 px-4 py-2 rounded-lg text-sm font-medium inline-flex items-center gap-2 ${
            data.review_status === 'Approved' ? 'bg-emerald-500/10 text-emerald-300' : 'bg-red-500/10 text-red-300'
          }`}>
            {data.review_status === 'Approved' ? '✓' : '✗'} This document has been <strong>{data.review_status}</strong>.
            {data.remarks && <span className="text-slate-400"> Remarks: {data.remarks}</span>}
          </div>
        )}
      </div>

      {/* Editable Fields */}
      <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 shadow-xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50">
          <h2 className="text-lg font-semibold text-white">Extracted Fields</h2>
          {!isLocked && dirty && (
            <button
              onClick={handleSaveFields}
              disabled={saving}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-all flex items-center gap-2"
            >
              {saving ? <><div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> Validating...</> : '💾 Save & Re-validate'}
            </button>
          )}
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {fieldKeys.filter(key => !Array.isArray(editedFields[key]) && key !== 'error').map(key => {
            const value = editedFields[key];
            const fieldValidation = validations[key];
            const status = fieldValidation?.status || 'valid';
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const confidence = confidences[key];
            const confidenceClass = confidence >= 85 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' : confidence >= 60 ? 'bg-amber-500/15 text-amber-300 border-amber-500/30' : 'bg-red-500/15 text-red-300 border-red-500/30';
            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-slate-400 uppercase font-semibold">{label}</label>
                  {fieldValidation && (
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border flex items-center gap-1 ${STATUS_BADGE[status]}`}>
                      <span>{STATUS_ICON[status]}</span> {status}
                    </span>
                  )}
                  {confidence !== undefined && <span title="AI extraction confidence" className={`ml-1 px-2 py-0.5 text-xs font-semibold rounded-full border ${confidenceClass}`}>{confidence}% confidence</span>}
                </div>
                <input
                  type="text"
                  value={value ?? ''}
                  onChange={e => handleFieldChange(key, e.target.value)}
                  disabled={isLocked}
                  className={`w-full bg-slate-900/60 border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:opacity-60 disabled:cursor-not-allowed ${
                    status === 'invalid' ? 'border-red-500/60' :
                    status === 'missing' ? 'border-amber-500/60' :
                    'border-slate-700/50 focus:border-indigo-500/50'
                  }`}
                  placeholder={`Enter ${label}`}
                />
                {fieldValidation && status !== 'valid' && (
                  <p className={`text-xs mt-1 ${status === 'invalid' ? 'text-red-400' : 'text-amber-400'}`}>
                    {fieldValidation.message}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {data?.rich_content && (
        <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 p-6 shadow-xl">
          <h2 className="text-lg font-semibold text-white mb-4">Tables, Signatures & QR Codes</h2>
          <div className="grid grid-cols-3 gap-3 mb-4 text-center">
            <div className="bg-slate-900/50 rounded-lg p-3"><p className="text-2xl font-bold">{data.rich_content.tables?.length || 0}</p><p className="text-xs text-slate-500">Tables</p></div>
            <div className="bg-slate-900/50 rounded-lg p-3"><p className="text-2xl font-bold">{data.rich_content.signatures?.length || 0}</p><p className="text-xs text-slate-500">Signature regions</p></div>
            <div className="bg-slate-900/50 rounded-lg p-3"><p className="text-2xl font-bold">{data.rich_content.qr_codes?.length || 0}</p><p className="text-xs text-slate-500">QR codes</p></div>
          </div>
          {data.rich_content.qr_codes?.map((qr, index) => <p key={index} className="text-sm text-slate-300 break-all">Page {qr.page}: {qr.value}</p>)}
          {data.rich_content.tables?.map((table, index) => <div key={index} className="mt-4 overflow-x-auto"><p className="text-xs text-slate-500 mb-1">Page {table.page}, table {table.table}</p><table className="w-full text-xs"><tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex} className="border-t border-slate-700">{row.map((cell, cellIndex) => <td key={cellIndex} className="p-2">{cell || '—'}</td>)}</tr>)}</tbody></table></div>)}
        </div>
      )}

      {/* Review Actions */}
      {!isLocked && (
        <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 p-6 shadow-xl space-y-4">
          <h2 className="text-lg font-semibold text-white">Review Decision</h2>
          <div>
            <label className="text-xs text-slate-400 uppercase font-semibold mb-1 block">
              Remarks {data?.review_status !== 'Approved' && <span className="text-red-400">*required for rejection</span>}
            </label>
            <textarea
              rows={3}
              value={remarks}
              onChange={e => setRemarks(e.target.value)}
              placeholder="Add review remarks or rejection reason..."
              className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 resize-none"
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleApprove}
              disabled={!!actionLoading || dirty}
              title={dirty ? 'Save fields first before approving' : ''}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-emerald-500/20 flex items-center gap-2"
            >
              {actionLoading === 'approve' ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : '✓'}
              Approve
            </button>
            <button
              onClick={handleReject}
              disabled={!!actionLoading}
              className="px-6 py-2.5 bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-red-500/20 flex items-center gap-2"
            >
              {actionLoading === 'reject' ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : '✗'}
              Reject
            </button>
            <button
              onClick={handleReprocess}
              disabled={!!actionLoading}
              className="px-6 py-2.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 rounded-lg text-sm font-semibold transition-all flex items-center gap-2"
            >
              {actionLoading === 'reprocess' ? <div className="w-4 h-4 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" /> : '↺'}
              Reprocess
            </button>
            {dirty && (
              <p className="text-amber-400 text-sm self-center">⚠ Unsaved changes — save fields before approving.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewPage;
