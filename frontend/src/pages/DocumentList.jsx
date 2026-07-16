import React, { useState, useEffect, useContext, useCallback, useRef } from 'react';
import { getDocuments, deleteDocument } from '../services/api';
import { AuthContext } from '../context/AuthContext';
import { Link } from 'react-router-dom';

const EMPTY_FILTERS = { search: '', document_type: '', status: '', uploaded_by: '', date_from: '', date_to: '', processing_time_min: '', processing_time_max: '' };

const DocumentList = () => {
  const [documents, setDocuments] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const latestRequest = useRef(0);
  
  const { user } = useContext(AuthContext);

  const fetchDocuments = useCallback(async (pageNumber) => {
    const requestId = ++latestRequest.current;
    setLoading(true);
    setError('');
    try {
      const params = Object.fromEntries(Object.entries(appliedFilters).filter(([, value]) => value !== ''));
      const response = await getDocuments(pageNumber, 10, params);
      if (requestId !== latestRequest.current) return;
      setDocuments(response.data.items);
      setTotalPages(Math.max(1, Math.ceil(response.data.total / response.data.page_size)));
    } catch {
      if (requestId === latestRequest.current) setError('Failed to fetch documents.');
    } finally {
      if (requestId === latestRequest.current) setLoading(false);
    }
  }, [appliedFilters]);

  useEffect(() => {
    fetchDocuments(page);
  }, [page, fetchDocuments]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      setAppliedFilters({ ...filters });
    }, 350);
    return () => clearTimeout(timer);
  }, [filters]);

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await deleteDocument(id);
      fetchDocuments(page); // refresh list
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to delete document.');
    }
  };

  const formatSize = (bytes) => (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  const applyFilters = (event) => { event.preventDefault(); setPage(1); setAppliedFilters(filters); };
  const resetFilters = () => { setFilters(EMPTY_FILTERS); setAppliedFilters(EMPTY_FILTERS); setPage(1); };

  return (
    <div className="max-w-7xl mx-auto p-6 mt-8">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-3xl font-bold text-white">Documents</h2>
        <Link 
          to="/upload" 
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-500/30 flex items-center space-x-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>Upload New</span>
        </Link>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg text-sm mb-6">
          {error}
        </div>
      )}

      <form onSubmit={applyFilters} className="bg-slate-800/40 rounded-2xl border border-slate-700/50 p-5 mb-6 space-y-4">
        <div className="flex flex-col md:flex-row gap-3">
          <input value={filters.search} onChange={e => setFilters({...filters, search: e.target.value})} placeholder="Search PAN, GST, invoice, account, employee, company, or upload date" className="flex-1 bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2 text-sm" />
          <button className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium">Search & Filter</button>
          <button type="button" onClick={resetFilters} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm">Reset</button>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <select value={filters.document_type} onChange={e => setFilters({...filters, document_type: e.target.value})} className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm">
            <option value="">All document and file types</option>
            <optgroup label="Classified document type">{['Bank Statement','Invoice','Salary Slip','GST Return','ITR','Balance Sheet','Profit & Loss'].map(value => <option key={value} value={value}>{value}</option>)}</optgroup>
            <optgroup label="Original file type">{['PDF','JPG','JPEG','PNG'].map(value => <option key={value} value={value}>{value}</option>)}</optgroup>
          </select>
          <select value={filters.status} onChange={e => setFilters({...filters, status: e.target.value})} className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm"><option value="">All statuses</option>{['Uploaded','Processing','Parsed','Validation Failed','Review Pending','Approved','Rejected'].map(value => <option key={value}>{value}</option>)}</select>
          {user?.role === 'Admin' && <input type="number" value={filters.uploaded_by} onChange={e => setFilters({...filters, uploaded_by: e.target.value})} placeholder="Uploader user ID" className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm" />}
          <input type="date" value={filters.date_from} onChange={e => setFilters({...filters, date_from: e.target.value})} title="Uploaded from" className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm" />
          <input type="date" value={filters.date_to} onChange={e => setFilters({...filters, date_to: e.target.value})} title="Uploaded through" className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm" />
          <input type="number" min="0" step="0.1" value={filters.processing_time_min} onChange={e => setFilters({...filters, processing_time_min: e.target.value})} placeholder="Min processing seconds" className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm" />
          <input type="number" min="0" step="0.1" value={filters.processing_time_max} onChange={e => setFilters({...filters, processing_time_max: e.target.value})} placeholder="Max processing seconds" className="bg-slate-900/70 border border-slate-700 rounded-lg px-3 py-2 text-sm" />
        </div>
      </form>

      <div className="bg-slate-800/40 rounded-2xl border border-slate-700/50 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-800/80 text-slate-300 text-sm uppercase tracking-wider border-b border-slate-700/50">
                <th className="p-4 font-medium">Name</th>
                <th className="p-4 font-medium">Status</th>
                <th className="p-4 font-medium">Date</th>
                <th className="p-4 font-medium">Size</th>
                <th className="p-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {loading ? (
                <tr>
                  <td colSpan="5" className="p-8 text-center text-slate-400">Loading documents...</td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan="5" className="p-8 text-center text-slate-400">No documents found.</td>
                </tr>
              ) : (
                documents.map(doc => (
                  <tr key={doc.id} className="hover:bg-slate-700/20 transition-colors group">
                    <td className="p-4 text-white font-medium flex items-center space-x-3">
                      <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <Link to={`/documents/${doc.id}`} className="hover:text-indigo-300 transition-colors">
                        {doc.document_name}
                      </Link>
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded-full border border-slate-600">
                        {doc.status}
                      </span>
                      {doc.status === 'Processing' && <div className="mt-2 min-w-28"><div className="flex justify-between text-[10px] text-slate-500"><span>{doc.processing_stage}</span><span>{doc.processing_progress}%</span></div><div className="h-1 bg-slate-700 rounded"><div className="h-full bg-indigo-500 rounded" style={{width: `${doc.processing_progress}%`}} /></div></div>}
                    </td>
                    <td className="p-4 text-slate-400 text-sm">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-slate-400 text-sm">
                      {formatSize(doc.file_size)}
                    </td>
                    <td className="p-4 text-right space-x-3">
                      <Link to={`/documents/${doc.id}`} className="text-indigo-400 hover:text-indigo-300 text-sm transition-colors">
                        View
                      </Link>
                      {user?.role === 'Admin' && (
                        <button 
                          onClick={() => handleDelete(doc.id)}
                          className="text-red-400 hover:text-red-300 text-sm transition-colors opacity-0 group-hover:opacity-100"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-slate-800/80 p-4 border-t border-slate-700/50 flex justify-between items-center text-sm text-slate-400">
            <span>Page {page} of {totalPages}</span>
            <div className="flex space-x-2">
              <button 
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1 bg-slate-700 rounded hover:bg-slate-600 disabled:opacity-50 transition-colors"
              >
                Previous
              </button>
              <button 
                disabled={page === totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1 bg-slate-700 rounded hover:bg-slate-600 disabled:opacity-50 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentList;
