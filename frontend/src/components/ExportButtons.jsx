import React, { useState } from 'react';
import { exportReport } from '../services/api';

const ExportButtons = ({ reportId, enabled, compact = false, reason: disabledReason }) => {
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');
  const reason = disabledReason || 'Exports are available after parsing and manual approval are complete.';

  const download = async (format) => {
    if (!enabled || !reportId) return;
    setLoading(format);
    setError('');
    try {
      const response = await exportReport(reportId, format);
      const extension = format === 'excel' ? 'xlsx' : format;
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `report_${reportId}.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.error?.message || 'Export failed.');
    } finally {
      setLoading('');
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2" title={!enabled ? reason : 'Download the latest approved report'}>
        {[['pdf', 'PDF'], ['excel', 'Excel'], ['csv', 'CSV']].map(([format, label]) => (
          <button
            key={format}
            onClick={() => download(format)}
            disabled={!enabled || !reportId || !!loading}
            className={`${compact ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm'} bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors`}
          >
            {loading === format ? 'Preparing…' : label}
          </button>
        ))}
      </div>
      {!enabled && <p className="text-xs text-slate-500">{reason}</p>}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
};

export default ExportButtons;
