import React, { useCallback, useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { deleteUser, getUsers, updateUser } from '../services/api';

const ManageUsers = () => {
  const { user: currentUser } = useContext(AuthContext);
  const [users, setUsers] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const pageSize = 10;

  const load = useCallback(async () => {
    try { const response = await getUsers(page, pageSize); setUsers(response.data.items); setTotal(response.data.total); setError(''); }
    catch (err) { setError(err.response?.data?.error?.message || 'Failed to load users.'); }
  }, [page]);
  useEffect(() => { load(); }, [load]);

  const patch = async (id, updates) => {
    try { await updateUser(id, updates); await load(); }
    catch (err) { setError(err.response?.data?.error?.message || 'Failed to update user.'); }
  };
  const remove = async (target) => {
    if (!window.confirm(`Delete ${target.name} (${target.email})? This cannot be undone.`)) return;
    try { await deleteUser(target.id); await load(); }
    catch (err) { setError(err.response?.data?.error?.message || 'Failed to delete user.'); }
  };

  return <div><div className="flex justify-between mb-6"><h1 className="text-3xl font-bold">Manage Users</h1><span className="text-slate-400">{total} users</span></div>{error && <div className="mb-4 text-red-400">{error}</div>}<div className="overflow-x-auto bg-slate-800/40 border border-slate-700/50 rounded-2xl"><table className="w-full text-left"><thead className="bg-slate-800 text-slate-300"><tr>{['Name','Email','Role','Active','Created','Actions'].map(label => <th key={label} className="p-4">{label}</th>)}</tr></thead><tbody className="divide-y divide-slate-700/50">{users.map(target => <tr key={target.id}><td className="p-4">{target.name}</td><td className="p-4 text-slate-300">{target.email}</td><td className="p-4"><select value={target.role} onChange={e => patch(target.id, { role: e.target.value })} className="bg-slate-900 border border-slate-700 rounded px-2 py-1"><option>Admin</option><option>Analyst</option></select></td><td className="p-4">{target.is_active ? 'Active' : 'Inactive'}</td><td className="p-4 text-slate-400">{new Date(target.created_at).toLocaleDateString()}</td><td className="p-4 space-x-3"><button onClick={() => patch(target.id, { is_active: !target.is_active })} className="text-amber-400 hover:text-amber-300">{target.is_active ? 'Deactivate' : 'Reactivate'}</button><button disabled={target.id === currentUser.id} onClick={() => remove(target)} className="text-red-400 hover:text-red-300 disabled:opacity-30">Delete</button></td></tr>)}</tbody></table></div>{total > pageSize && <div className="flex justify-center gap-3 mt-5"><button disabled={page === 1} onClick={() => setPage(page - 1)} className="px-3 py-1 bg-slate-700 rounded disabled:opacity-40">Previous</button><span className="text-slate-400">Page {page}</span><button disabled={page * pageSize >= total} onClick={() => setPage(page + 1)} className="px-3 py-1 bg-slate-700 rounded disabled:opacity-40">Next</button></div>}</div>;
};

export default ManageUsers;
