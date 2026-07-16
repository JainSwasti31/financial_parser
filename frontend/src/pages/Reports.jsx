import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ExportButtons from '../components/ExportButtons';
import { getReports } from '../services/api';

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getReports(page, 10);
      setReports(response.data.items);
      setTotalPages(Math.max(1, Math.ceil(response.data.total / response.data.page_size)));
    } catch (e) {
      setError(e.response?.data?.error?.message || 'Failed to load reports.');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Reports</h1>
        <p className="text-slate-400 mt-1">Parsed reports and approved exports</p>
      </div>
      {error && <div className="bg-red-500/10 border border-red-500/40 text-red-400 p-3 rounded-lg">{error}</div>}
      <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-800/80 text-xs uppercase text-slate-400">
              <tr><th className="p-4">File</th><th className="p-4">Document Type</th><th className="p-4">Validation</th><th className="p-4">Review</th><th className="p-4">Exports</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {loading ? <tr><td colSpan="5" className="p-8 text-center text-slate-400">Loading reports…</td></tr> : reports.length === 0 ? <tr><td colSpan="5" className="p-8 text-center text-slate-400">No parsed reports found.</td></tr> : reports.map(report => (
                <tr key={report.id} className="hover:bg-slate-700/20">
                  <td className="p-4"><Link className="text-indigo-300 hover:text-indigo-200 font-medium" to={`/reports/${report.id}`}>{report.original_file.name}</Link></td>
                  <td className="p-4 text-slate-300">{report.document_type || 'Unknown'}</td>
                  <td className="p-4 text-slate-300">{report.validation_status || '—'}</td>
                  <td className="p-4"><span className="text-slate-300">{report.review_status || 'Pending'}</span></td>
                  <td className="p-4"><ExportButtons reportId={report.id} enabled={report.export_available} reason={report.export_block_reason} compact />{!report.export_available && <Link to={`/review/${report.document_id}`} className="inline-block mt-2 text-xs text-amber-400 hover:text-amber-300">Review and approve →</Link>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t border-slate-700/50 flex justify-between text-sm text-slate-400">
          <span>Page {page} of {totalPages}</span>
          <div className="flex gap-2"><button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1 bg-slate-700 rounded disabled:opacity-40">Previous</button><button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} className="px-3 py-1 bg-slate-700 rounded disabled:opacity-40">Next</button></div>
        </div>
      </div>
    </div>
  );
};

export default Reports;
