import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { bulkProcessDocuments, getParserResult, uploadDocumentsBatch } from '../services/api';

const VALID_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const terminalStatuses = new Set(['Parsed', 'Validation Failed', 'Review Pending', 'Approved', 'Rejected']);

const Upload = () => {
  const [files, setFiles] = useState([]);
  const [queue, setQueue] = useState([]);
  const [failed, setFailed] = useState([]);
  const [error, setError] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const queueRef = useRef([]);

  useEffect(() => { queueRef.current = queue; }, [queue]);

  const addFiles = useCallback((incoming) => {
    setError('');
    const accepted = [];
    for (const file of Array.from(incoming)) {
      if (!VALID_TYPES.includes(file.type)) { setError(`${file.name}: unsupported file type.`); continue; }
      if (file.size > 25 * 1024 * 1024) { setError(`${file.name}: exceeds 25 MB.`); continue; }
      accepted.push(file);
    }
    setFiles(current => [...current, ...accepted].slice(0, 20));
  }, []);

  useEffect(() => {
    if (!processing || queue.length === 0) return undefined;
    const poll = async () => {
      const results = await Promise.all(queueRef.current.map(async item => {
        if (terminalStatuses.has(item.status)) return item;
        try {
          const { data } = await getParserResult(item.id);
          return { ...item, status: data.status, progress: data.processing_progress || 0, stage: data.processing_stage || data.status };
        } catch { return { ...item, stage: 'Status unavailable' }; }
      }));
      setQueue(results);
      if (results.every(item => terminalStatuses.has(item.status))) setProcessing(false);
    };
    poll();
    const timer = setInterval(poll, 2000);
    return () => clearInterval(timer);
  }, [processing, queue.length]);

  const upload = async () => {
    if (!files.length) return;
    setUploading(true); setError(''); setFailed([]);
    try {
      const response = await uploadDocumentsBatch(files, event => {
        if (event.total) setUploadProgress(Math.round(event.loaded * 100 / event.total));
      });
      setQueue(response.data.uploaded.map(item => ({ ...item, progress: 0, stage: 'Ready to parse' })));
      setFailed(response.data.failed || []);
      setFiles([]);
    } catch (e) {
      setError(e.response?.data?.error?.message || 'Batch upload failed.');
    } finally { setUploading(false); }
  };

  const bulkParse = async () => {
    const ids = queue.filter(item => item.status === 'Uploaded').map(item => item.id);
    if (!ids.length) return;
    try {
      const response = await bulkProcessDocuments(ids);
      const accepted = new Set(response.data.accepted);
      setQueue(items => items.map(item => accepted.has(item.id) ? { ...item, status: 'Processing', stage: 'Queued', progress: 0 } : item));
      setProcessing(true);
    } catch (e) { setError(e.response?.data?.error?.message || 'Bulk parse failed.'); }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div><h1 className="text-3xl font-bold">Batch Upload</h1><p className="text-slate-400 mt-1">Upload up to 20 PDF, JPG, or PNG documents, then parse them as a queue.</p></div>
      {error && <div className="bg-red-500/10 border border-red-500/40 text-red-400 p-3 rounded-lg">{error}</div>}
      <div onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); addFiles(event.dataTransfer.files); }} className="bg-slate-800/40 border-2 border-dashed border-slate-600 hover:border-indigo-500 rounded-2xl p-10 text-center">
        <p className="text-slate-300 mb-3">Drag multiple documents here</p>
        <label className="inline-block px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg cursor-pointer">Choose files<input multiple type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" onChange={event => addFiles(event.target.files)} /></label>
      </div>
      {files.length > 0 && <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5"><div className="flex justify-between mb-4"><h2 className="font-semibold">Selected files ({files.length})</h2><button onClick={() => setFiles([])} className="text-sm text-slate-400">Clear</button></div><div className="space-y-2">{files.map((file, index) => <div key={`${file.name}-${index}`} className="flex justify-between bg-slate-900/40 rounded-lg p-3 text-sm"><span>{file.name}</span><span className="text-slate-500">{(file.size / 1048576).toFixed(2)} MB</span></div>)}</div><button disabled={uploading} onClick={upload} className="mt-4 w-full py-2.5 bg-indigo-600 disabled:opacity-50 rounded-lg font-semibold">{uploading ? `Uploading ${uploadProgress}%` : 'Upload batch'}</button></div>}
      {queue.length > 0 && <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-5"><div className="flex flex-wrap justify-between gap-3 mb-4"><h2 className="font-semibold">Processing queue</h2><button onClick={bulkParse} disabled={processing || !queue.some(item => item.status === 'Uploaded')} className="px-4 py-2 bg-violet-600 disabled:opacity-40 rounded-lg text-sm font-semibold">Bulk parse</button></div><div className="space-y-3">{queue.map(item => <div key={item.id} className="bg-slate-900/40 rounded-lg p-3"><div className="flex justify-between gap-3 text-sm"><Link to={`/documents/${item.id}`} className="text-indigo-300">{item.name}</Link><span className="text-slate-400">{item.status}</span></div><div className="flex justify-between text-xs text-slate-500 mt-2"><span>{item.stage}</span><span>{item.progress}%</span></div><div className="h-1.5 bg-slate-700 rounded-full mt-1"><div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${item.progress}%` }} /></div></div>)}</div></div>}
      {failed.length > 0 && <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5"><h2 className="font-semibold text-red-300 mb-2">Files not uploaded</h2>{failed.map((item, index) => <p key={index} className="text-sm text-red-400">{item.name}: {item.error}</p>)}</div>}
    </div>
  );
};

export default Upload;
