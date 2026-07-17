import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';

const ProfilePage = () => {
  const { user, updateProfile } = useContext(AuthContext);
  const [form, setForm] = useState({ name: '', email: '', current_password: '', password: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => setForm(value => ({ ...value, name: user?.name || '', email: user?.email || '' })), [user]);

  const submit = async (event) => {
    event.preventDefault();
    setMessage(''); setError('');
    const payload = { name: form.name, email: form.email };
    if (form.password) Object.assign(payload, { current_password: form.current_password, password: form.password });
    try {
      await updateProfile(payload);
      setForm(value => ({ ...value, current_password: '', password: '' }));
      setMessage('Profile updated successfully.');
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update profile.');
    }
  };

  const field = (key, label, type = 'text') => <label className="block"><span className="block text-sm text-slate-300 mb-1">{label}</span><input type={type} value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} className="w-full bg-slate-900/70 border border-slate-700 rounded-lg px-4 py-2" /></label>;
  return <div className="max-w-xl"><h1 className="text-3xl font-bold mb-6">Edit Profile</h1><form onSubmit={submit} className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 space-y-4">{message && <p className="text-emerald-400">{message}</p>}{error && <p className="text-red-400">{error}</p>}{field('name', 'Name')}{field('email', 'Email', 'email')}<div className="border-t border-slate-700 pt-4"><p className="text-sm text-slate-400 mb-3">Leave password fields blank to keep your current password.</p><div className="space-y-4">{field('current_password', 'Current password', 'password')}{field('password', 'New password', 'password')}</div></div><button className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-medium">Save profile</button></form></div>;
};

export default ProfilePage;
