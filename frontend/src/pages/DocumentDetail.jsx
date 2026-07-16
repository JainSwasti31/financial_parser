import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getDocumentById, processDocument, reprocessDocument, getParserResult } from '../services/api';
import ExportButtons from '../components/ExportButtons';

const STATUS_COLORS = {
  Uploaded:         'bg-slate-500/20 text-slate-300 border-slate-500/30',
  Processing:       'bg-amber-500/20 text-amber-300 border-amber-500/30',
  Parsed:           'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  'Review Pending': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  'Validation Failed': 'bg-red-500/20 text-red-300 border-red-500/30',
};

const DocumentDetail = () => {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('fields');
  const pollRef = useRef(null);

  useEffect(() => {
    fetchData();
    return () => clearInterval(pollRef.current);
  }, [id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [docRes, resultRes] = await Promise.allSettled([
        getDocumentById(id),
        getParserResult(id)
      ]);
      if (docRes.status === 'fulfilled') setDoc(docRes.value.data);
      if (resultRes.status === 'fulfilled') {
        setResult(resultRes.value.data);
        if (resultRes.value.data.status === 'Processing' && !pollRef.current) startPolling();
      }
    } catch (err) {
      setError('Failed to load document.');
    } finally {
      setLoading(false);
    }
  };

  const startPolling = () => {
    setProcessing(true);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await getParserResult(id);
        setResult(res.data);
        setDoc(prev => ({ ...prev, status: res.data.status }));
        if (res.data.status !== 'Processing') {
          clearInterval(pollRef.current);
          setProcessing(false);
        }
      } catch (e) {
        clearInterval(pollRef.current);
        setProcessing(false);
      }
    }, 2500);
  };

  const handleProcess = async () => {
    setError('');
    try {
      await processDocument(id);
      setDoc(prev => ({ ...prev, status: 'Processing' }));
      startPolling();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start processing.');
    }
  };

  const handleReprocess = async () => {
    setError('');
    try {
      await reprocessDocument(id);
      setDoc(prev => ({ ...prev, status: 'Processing' }));
      startPolling();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start reprocessing.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!doc) {
    return <div className="text-center py-20 text-red-400">{error || 'Document not found.'}</div>;
  }

  const status = result?.status || doc?.status;
  const statusClass = STATUS_COLORS[status] || STATUS_COLORS['Uploaded'];
  const isParsed = ['Parsed', 'Validation Failed', 'Review Pending', 'Approved', 'Rejected'].includes(status);
  const canProcess = status === 'Uploaded';
  const canReprocess = isParsed || status === 'Review Pending';
  const isProcessing = processing || status === 'Processing';
  const needsReview = ['Validation Failed', 'Review Pending'].includes(status);
  const isApproved = status === 'Approved';
  const parsedFields = result?.report?.parsed_fields;
  const rawText = result?.report?.raw_text;
  const docType = result?.report?.document_type;
  const fieldValidations = result?.report?.field_validations || {};
  const validationStatus = result?.report?.validation_status;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <Link to="/documents" className="text-indigo-400 hover:text-indigo-300 transition-colors flex items-center text-sm w-fit">
        <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
        Back to Documents
      </Link>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Document Header Card */}
      <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 p-8 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-40 h-40 bg-indigo-500/10 rounded-full blur-3xl"></div>
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6 relative">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">{doc.document_name}</h1>
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${statusClass}`}>
                {isProcessing ? '⚡ Processing...' : status}
              </span>
              {docType && (
                <span className="px-3 py-1 bg-violet-500/20 text-violet-300 text-xs font-semibold rounded-full border border-violet-500/30">
                  {docType}
                </span>
              )}
            </div>
          </div>
          {/* Action Buttons */}
          <div className="flex gap-3 shrink-0 flex-wrap">
            {canProcess && !isProcessing && (
              <button
                onClick={handleProcess}
                className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-indigo-500/30 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.364-.447.44a1.1 1.1 0 01-1.563 0l-.447-.44-.347-.364z" />
                </svg>
                Process with AI
              </button>
            )}
            {needsReview && !isProcessing && (
              <Link
                to={`/review/${doc.id}`}
                className="px-5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-amber-500/20 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Review & Edit
              </Link>
            )}
            {isParsed && !needsReview && !isApproved && !isProcessing && (
              <Link
                to={`/review/${doc.id}`}
                className="px-5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-violet-500/20 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Approve / Reject
              </Link>
            )}
            {canReprocess && !isProcessing && (
              <button
                onClick={handleReprocess}
                className="px-5 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm font-medium transition-all flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Reprocess
              </button>
            )}
            {isProcessing && (
              <div className="px-5 py-2 bg-amber-500/10 text-amber-300 border border-amber-500/30 rounded-lg text-sm font-medium min-w-48">
                <div className="flex justify-between gap-3"><span>{result?.processing_stage || 'Running AI pipeline'}</span><span>{result?.processing_progress || 0}%</span></div>
                <div className="h-1 bg-slate-700 rounded mt-2"><div className="h-full bg-amber-400 rounded" style={{width: `${result?.processing_progress || 0}%`}} /></div>
              </div>
            )}
            <ExportButtons reportId={result?.report?.id} enabled={isApproved} compact />
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 border-t border-slate-700/50 pt-6">
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Type</p>
            <p className="text-white">{doc.document_type}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Size</p>
            <p className="text-white">{(doc.file_size / (1024 * 1024)).toFixed(2)} MB</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Uploaded</p>
            <p className="text-white">{new Date(doc.created_at).toLocaleDateString()}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Processing Time</p>
            <p className="text-white">{result?.processing_time ? `${parseFloat(result.processing_time).toFixed(1)}s` : '—'}</p>
          </div>
        </div>
      </div>

      {/* Results Panel */}
      {isParsed && result?.report && (
        <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 shadow-xl overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-slate-700/50">
            {['fields', 'raw_text'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-4 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'text-indigo-300 border-b-2 border-indigo-400'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab === 'fields' ? '📊 Parsed Fields' : '📄 Raw OCR Text'}
              </button>
            ))}
          </div>

          <div className="p-6">
            {activeTab === 'fields' && parsedFields && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(parsedFields).filter(([k]) => k !== 'error').map(([key, value]) => {
                  const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                  if (Array.isArray(value)) {
                    return (
                      <div key={key} className="col-span-full">
                        <p className="text-xs text-slate-500 uppercase font-semibold mb-2">{label}</p>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm border-collapse">
                            <thead>
                              <tr className="bg-slate-700/50">
                                {Object.keys(value[0] || {}).map(col => (
                                  <th key={col} className="text-left text-slate-300 px-3 py-2 text-xs uppercase">{col}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {value.map((row, i) => (
                                <tr key={i} className="border-t border-slate-700/30 hover:bg-slate-700/20">
                                  {Object.values(row).map((v, j) => (
                                    <td key={j} className="px-3 py-2 text-slate-300">{v ?? '—'}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    );
                  }
                  return (
                    <div key={key} className="bg-slate-700/20 rounded-xl p-4 border border-slate-700/30">
                      <p className="text-xs text-slate-500 uppercase font-semibold mb-1">{label}</p>
                      <p className="text-white font-medium">{value ?? '—'}</p>
                    </div>
                  );
                })}
              </div>
            )}
            {activeTab === 'raw_text' && (
              <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono bg-slate-900/50 rounded-xl p-4 max-h-[600px] overflow-y-auto leading-relaxed">
                {rawText || 'No OCR text available.'}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Review Pending Banner */}
      {status === 'Review Pending' && (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-2xl p-6 flex items-start gap-4">
          <svg className="w-6 h-6 text-orange-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <p className="text-orange-300 font-semibold">Flagged for Manual Review</p>
            <p className="text-slate-400 text-sm mt-1">
              The AI could not fully parse this document. This may be due to a corrupted file, unsupported format, or unreadable scan quality. Try reprocessing or contact support.
            </p>
            <button onClick={handleReprocess} className="mt-3 text-sm text-orange-300 hover:text-orange-200 underline">
              Try Reprocessing
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentDetail;
