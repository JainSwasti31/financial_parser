import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ExportButtons from '../components/ExportButtons';
import { getReport } from '../services/api';

const ReportDetail = () => {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    try { setReport((await getReport(id)).data); }
    catch (e) { setError(e.response?.data?.error?.message || 'Failed to load report.'); }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  if (error) return <div className="text-red-400 py-16 text-center">{error}</div>;
  if (!report) return <div className="text-slate-400 py-16 text-center">Loading report…</div>;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <Link to="/reports" className="text-indigo-400 text-sm">← Back to Reports</Link>
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-7 flex flex-wrap justify-between gap-5">
        <div><h1 className="text-2xl font-bold">{report.original_file.name}</h1><p className="text-slate-400 mt-1">{report.document_type} · {report.review_status}</p></div>
        <div><ExportButtons reportId={report.id} enabled={report.export_available} reason={report.export_block_reason} />{!report.export_available && <Link to={`/review/${report.document_id}`} className="inline-block mt-3 text-sm text-amber-400 hover:text-amber-300">Review and approve this report →</Link>}</div>
      </div>
      {[['Original File Information', report.original_file], ['Extracted Fields', report.extracted_fields]].map(([title, values]) => (
        <div key={title} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6"><h2 className="text-lg font-semibold mb-4">{title}</h2><div className="grid md:grid-cols-2 gap-3">{Object.entries(values || {}).map(([key, value]) => <div key={key} className="bg-slate-900/40 rounded-lg p-3"><p className="text-xs uppercase text-slate-500">{key.replace(/_/g, ' ')}</p><p className="text-slate-200 break-words">{typeof value === 'object' ? JSON.stringify(value) : value ?? '—'}</p></div>)}</div></div>
      ))}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6"><h2 className="text-lg font-semibold mb-4">Validation Results</h2><div className="space-y-2">{Object.entries(report.validation_results || {}).map(([key, value]) => <div key={key} className="flex justify-between gap-4 bg-slate-900/40 rounded-lg p-3"><span>{key.replace(/_/g, ' ')}</span><span className={value.status === 'valid' ? 'text-emerald-400' : 'text-red-400'}>{value.status}: {value.message}</span></div>)}</div></div>
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 grid md:grid-cols-3 gap-4"><div><p className="text-xs text-slate-500">PROCESSING TIME</p><p>{report.processing_time ? `${report.processing_time.toFixed(2)}s` : '—'}</p></div><div><p className="text-xs text-slate-500">REVIEWED BY</p><p>{report.reviewed_by?.name || 'Not reviewed'}</p></div><div><p className="text-xs text-slate-500">REMARKS</p><p>{report.remarks || '—'}</p></div></div>
    </div>
  );
};

export default ReportDetail;
