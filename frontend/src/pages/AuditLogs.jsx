import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAuditLogs } from '../services/api';

const AuditLogs = () => {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [documentId, setDocumentId] = useState('');
  const [action, setAction] = useState('');
  const load = useCallback(async () => {
    const response = await getAuditLogs(page, 20, { document_id: documentId || undefined, action: action || undefined });
    setItems(response.data.items); setPages(Math.max(1, Math.ceil(response.data.total / response.data.page_size)));
  }, [page, documentId, action]);
  useEffect(() => { load(); }, [load]);
  return <div className="space-y-6"><div><h1 className="text-3xl font-bold">Audit Logs</h1><p className="text-slate-400 mt-1">Document processing and review history</p></div><div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4 flex flex-wrap gap-3"><input value={documentId} onChange={e => {setPage(1); setDocumentId(e.target.value)}} type="number" placeholder="Document ID" className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2"/><input value={action} onChange={e => {setPage(1); setAction(e.target.value)}} placeholder="Filter by action" className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 min-w-64"/></div><div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl overflow-hidden"><div className="overflow-x-auto"><table className="w-full text-left"><thead className="bg-slate-800 text-xs uppercase text-slate-400"><tr><th className="p-4">Time</th><th className="p-4">Document</th><th className="p-4">Action</th><th className="p-4">Status</th><th className="p-4">Remarks</th></tr></thead><tbody className="divide-y divide-slate-700/50">{items.map(item => <tr key={item.id}><td className="p-4 text-sm text-slate-400">{new Date(item.created_at).toLocaleString()}</td><td className="p-4"><Link className="text-indigo-400" to={`/documents/${item.document_id}`}>#{item.document_id}</Link></td><td className="p-4">{item.action}</td><td className="p-4 text-slate-300">{item.status}</td><td className="p-4 text-sm text-slate-400 max-w-md">{item.remarks || '—'}</td></tr>)}</tbody></table></div><div className="p-4 border-t border-slate-700/50 flex justify-between"><span className="text-slate-400">Page {page} of {pages}</span><div className="flex gap-2"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="px-3 py-1 bg-slate-700 rounded disabled:opacity-40">Previous</button><button disabled={page===pages} onClick={()=>setPage(p=>p+1)} className="px-3 py-1 bg-slate-700 rounded disabled:opacity-40">Next</button></div></div></div></div>;
};
export default AuditLogs;
