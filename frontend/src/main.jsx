import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, AlertCircle, ArrowUpRight, CalendarCheck, CalendarClock, CalendarDays, ChevronLeft,
  ChevronRight, CircleCheck, CircleX, Phone, Plus, RefreshCw, Search, Stethoscope, Trash2, Users, X,
} from 'lucide-react';
import './styles.css';

const statuses = { scheduled: 'Scheduled', checked_in: 'Checked in', completed: 'Completed', cancelled: 'Cancelled' };
const statusIcons = { scheduled: CalendarClock, checked_in: Activity, completed: CalendarCheck, cancelled: CircleX };
const urgencies = { routine: 'Routine', soon: 'Soon', urgent: 'Urgent' };
const departments = {
  general: 'General medicine', cardiology: 'Cardiology', orthopedics: 'Orthopedics',
  pediatrics: 'Pediatrics', dermatology: 'Dermatology', ent: 'ENT',
};
const empty = { patient_name: '', patient_phone: '', doctor_id: '', scheduled_for: '', reason: '', status: 'scheduled', urgency: 'routine', notes: '' };
const pad = value => String(value).padStart(2, '0');

function parse(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
function dateLabel(value) {
  const date = parse(value);
  return date ? date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Date unavailable';
}
function timeLabel(value) {
  const date = parse(value);
  return date ? date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }) : '';
}
function toLocalInput(value) {
  const date = parse(value) ?? new Date();
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json' } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}). Please check the appointment details.`);
  }
  return response.status === 204 ? null : response.json();
}

function AppointmentDialog({ appointment, doctors, onClose, onSaved }) {
  const [form, setForm] = useState(() => appointment ? {
    patient_name: appointment.patient_name,
    patient_phone: appointment.patient_phone,
    doctor_id: String(appointment.doctor_id),
    scheduled_for: toLocalInput(appointment.scheduled_for),
    reason: appointment.reason,
    status: appointment.status,
    urgency: appointment.urgency,
    notes: appointment.notes,
  } : { ...empty, scheduled_for: toLocalInput(null) });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const dialog = useRef(null);
  useEffect(() => { dialog.current.showModal(); return () => dialog.current?.close(); }, []);
  const change = event => setForm({ ...form, [event.target.name]: event.target.value });

  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const body = {
      ...form,
      doctor_id: Number(form.doctor_id),
      scheduled_for: new Date(form.scheduled_for).toISOString(),
    };
    try {
      await api(appointment ? `/api/appointments/${appointment.id}` : '/api/appointments', { method: appointment ? 'PUT' : 'POST', body: JSON.stringify(body) });
      onSaved(appointment ? 'Appointment updated' : 'Appointment booked');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  async function remove() {
    setBusy(true); setError('');
    try { await api(`/api/appointments/${appointment.id}`, { method: 'DELETE' }); onSaved('Appointment deleted'); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  const bookable = doctors.filter(doctor => doctor.active || String(doctor.id) === String(form.doctor_id));
  return <dialog ref={dialog} onCancel={event => { if (busy) event.preventDefault(); else onClose(); }} aria-labelledby="dialog-title">
    <header className="dialog-header"><div><p className="eyebrow">{appointment ? `MQ-${String(appointment.id).padStart(4, '0')}` : 'FRONT DESK'}</p><h2 id="dialog-title">{appointment ? 'Appointment details' : 'Book an appointment'}</h2></div><button type="button" className="icon-button" aria-label="Close dialog" title="Close" onClick={onClose} disabled={busy}><X size={20}/></button></header>
    <form onSubmit={submit}>
      {error && <p className="error" role="alert">{error}</p>}
      {!doctors.length && <p className="hint" role="alert">No doctors are registered yet. Run <code>python scripts/seed.py</code> to load the clinic roster.</p>}
      <div className="form-grid">
        <label>Patient name<input name="patient_name" autoFocus required minLength={3} maxLength={120} value={form.patient_name} onChange={change} placeholder="Who is visiting?"/></label>
        <label>Contact number<input name="patient_phone" required minLength={6} maxLength={20} pattern="[0-9+\- ]+" title="Digits, spaces, + and - only" value={form.patient_phone} onChange={change} placeholder="+91 98765 43210"/></label>
        <label>Doctor<select name="doctor_id" required value={form.doctor_id} onChange={change}><option value="" disabled>Select a doctor</option>{bookable.map(doctor => <option key={doctor.id} value={doctor.id}>{doctor.full_name} — {departments[doctor.department]}{doctor.active ? '' : ' (inactive)'}</option>)}</select></label>
        <label>Date and time<input type="datetime-local" name="scheduled_for" required value={form.scheduled_for} onChange={change}/></label>
        <label>Status<select name="status" value={form.status} onChange={change}>{Object.entries(statuses).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>Urgency<select name="urgency" value={form.urgency} onChange={change}>{Object.entries(urgencies).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      </div>
      <label>Reason for visit<textarea name="reason" rows={2} maxLength={500} value={form.reason} onChange={change} placeholder="Briefly describe the symptoms or purpose"/></label>
      <label>Front-desk notes<textarea name="notes" rows={2} maxLength={1000} value={form.notes} onChange={change} placeholder="Insurance, referring doctor, accessibility needs"/></label>
      {deleting && <div className="delete-confirm"><p>Delete this appointment permanently?</p><button type="button" className="danger" disabled={busy} onClick={remove}>Delete appointment</button><button type="button" disabled={busy} onClick={() => setDeleting(false)}>Keep appointment</button></div>}
      <footer className="dialog-footer">{appointment && <button type="button" className="icon-button danger-text" aria-label="Delete appointment" title="Delete appointment" disabled={busy} onClick={() => setDeleting(true)}><Trash2 size={18}/></button>}<span className="spacer"/><button type="button" disabled={busy} onClick={onClose}>Cancel</button><button className="primary" disabled={busy || !doctors.length}>{busy ? 'Saving...' : appointment ? 'Save changes' : 'Confirm booking'}</button></footer>
    </form>
  </dialog>;
}

function App() {
  const [appointments, setAppointments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [hasNext, setHasNext] = useState(false);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [modal, setModal] = useState(undefined);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ q: query, limit: '13', offset: String(page * 12) });
        if (status) params.set('status', status);
        const [rows, counts, roster] = await Promise.all([
          api(`/api/appointments?${params}`, { signal: controller.signal }),
          api('/api/stats', { signal: controller.signal }),
          api('/api/doctors?active=true', { signal: controller.signal }),
        ]);
        if (!controller.signal.aborted) { setAppointments(rows.slice(0, 12)); setHasNext(rows.length > 12); setStats(counts); setDoctors(roster); }
      } catch (e) { if (e.name !== 'AbortError') setError(e.message); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, query ? 220 : 0);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [status, query, page, revision]);

  useEffect(() => { if (notice) { const timer = setTimeout(() => setNotice(''), 4000); return () => clearTimeout(timer); } }, [notice]);

  function filter(value) { setStatus(value); setPage(0); }
  function saved(message) { setModal(undefined); setNotice(message); setPage(0); setRevision(value => value + 1); }
  const metrics = [
    ['scheduled', 'Scheduled', CalendarClock, 'Confirmed and waiting'],
    ['checked_in', 'Checked in', Activity, 'Currently with a doctor'],
    ['completed', 'Completed', CalendarCheck, 'Consultation finished'],
    ['urgent', 'Urgent queue', AlertCircle, 'Urgent and still open'],
  ];

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="MediQueue home"><span className="brand-mark"><Stethoscope size={22}/></span><span>MediQueue<span className="brand-caption">CLINIC FRONT DESK</span></span></a>
      <p className="nav-label">TODAY</p>
      <nav aria-label="Appointment navigation">
        {[['', CalendarDays, 'All appointments'], ['scheduled', CalendarClock, 'Scheduled'], ['checked_in', Activity, 'Checked in'], ['completed', CalendarCheck, 'Completed'], ['cancelled', CircleX, 'Cancelled']].map(([value, Icon, label]) => <button key={value} className={status === value ? 'nav-item active' : 'nav-item'} aria-label={label} title={label} aria-pressed={status === value} onClick={() => filter(value)}><Icon size={18}/><span>{label}</span><span className="nav-count">{stats ? (value ? stats[value] : stats.total) : '-'}</span></button>)}
      </nav>
      <div className="sidebar-bottom"><span className="avatar">KS</span><div><strong>Khushi Sarawagi</strong><small>24BCS10361</small></div></div>
    </aside>
    <main>
      <header className="topbar"><span>Clinic <span className="crumb">/</span> Front desk</span><span className="workspace-dot">Reception online</span></header>
      <div className="page-content">
        <div className="page-title"><div><p className="eyebrow">CARE COORDINATION</p><h1>Appointments</h1><p className="muted">Keep every patient visit booked, checked in and completed on time.</p></div><button className="primary" onClick={() => setModal(null)} aria-label="Book appointment"><Plus size={18}/> Book appointment</button></div>
        <section className="overview" aria-label="Clinic overview">
          {metrics.map(([key, label, Icon, foot]) => <div className={`metric ${key}`} key={key}><span className="metric-label">{label}<Icon size={18}/></span><strong>{stats ? stats[key] : '-'}</strong><span className="metric-foot">{foot}</span></div>)}
        </section>
        <div className="workspace-grid">
          <section className="queue-section" aria-label="Appointment list">
            <div className="section-heading"><h2>Appointment queue</h2><button className="icon-button" aria-label="Refresh appointments" title="Refresh appointments" onClick={() => setRevision(value => value + 1)} disabled={loading}><RefreshCw size={17} className={loading ? 'spin' : ''}/></button></div>
            <div className="filters">
              <div className="tabs" aria-label="Appointment status">{[['', 'All'], ...Object.entries(statuses)].map(([value, label]) => <button key={value} className={status === value ? 'selected' : ''} aria-pressed={status === value} onClick={() => filter(value)}>{label}</button>)}</div>
              <label className="search"><Search size={17}/><input aria-label="Search appointments" placeholder="Search patient, phone or reason..." value={query} onChange={event => { setQuery(event.target.value); setPage(0); }}/></label>
            </div>
            {error ? <div className="empty error" role="alert"><AlertCircle/><h3>Appointments could not be loaded</h3><p>{error}</p><button onClick={() => setRevision(value => value + 1)}>Try again</button></div>
              : loading ? <div className="empty" role="status"><RefreshCw className="spin"/><p>Loading appointments...</p></div>
              : appointments.length === 0 ? <div className="empty"><CalendarDays size={32}/><h3>{query || status ? 'No matching appointments' : 'The queue is clear'}</h3><p>{query || status ? 'Nothing matches the current filter.' : 'No visits have been booked yet.'}</p>{!query && !status && <button onClick={() => setModal(null)}><Plus size={16}/> Book appointment</button>}</div>
              : <div className="table-wrap"><table><thead><tr><th>Patient</th><th>Doctor</th><th>Scheduled</th><th>Status</th><th>Urgency</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>
                {appointments.map(appointment => { const Icon = statusIcons[appointment.status]; return <tr key={appointment.id}>
                  <td><div className="patient-cell"><span className={`status-icon ${appointment.status}`}><Icon size={18}/></span><div><button className="row-link" onClick={() => setModal(appointment)}>{appointment.patient_name}</button><small>MQ-{String(appointment.id).padStart(4, '0')} <span className="dot-separator">/</span> {appointment.patient_phone}</small></div></div></td>
                  <td><div className="doctor-cell"><strong>{appointment.doctor_name}</strong><small>{departments[appointment.doctor_department] || appointment.doctor_department}</small></div></td>
                  <td className="date"><strong>{dateLabel(appointment.scheduled_for)}</strong><small>{timeLabel(appointment.scheduled_for)}</small></td>
                  <td><span className={`status ${appointment.status}`}><span/>{statuses[appointment.status]}</span></td>
                  <td><span className={`urgency ${appointment.urgency}`}><i/>{urgencies[appointment.urgency]}</span></td>
                  <td><button className="icon-button" aria-label={`Open appointment ${appointment.id}`} title="Open appointment" onClick={() => setModal(appointment)}><ArrowUpRight size={17}/></button></td>
                </tr>; })}
              </tbody></table></div>}
            <footer className="table-footer"><span>{error ? 'Unavailable' : loading ? 'Updating...' : `${appointments.length} appointments on this page`}</span><div><button className="icon-button" aria-label="Previous page" title="Previous page" disabled={page === 0 || loading || Boolean(error)} onClick={() => setPage(value => value - 1)}><ChevronLeft size={16}/></button><span>Page {page + 1}</span><button className="icon-button" aria-label="Next page" title="Next page" disabled={!hasNext || loading || Boolean(error)} onClick={() => setPage(value => value + 1)}><ChevronRight size={16}/></button></div></footer>
          </section>
          <aside className="right-rail">
            <img className="clinic-image" src="/clinic.svg" alt="Illustration of a clinic reception desk"/>
            <div className="rail-section"><p className="eyebrow">PATIENT FLOW</p><h2>Calmer front desks start here.</h2><p className="muted">One queue for booking, check-in and follow-up across every department.</p></div>
            <div className="rail-section"><h3><Users size={15}/> Doctors on duty</h3>{doctors.length ? doctors.slice(0, 6).map(doctor => <div className="doctor-row" key={doctor.id}><Stethoscope size={15}/><span>{doctor.full_name}<small>{departments[doctor.department]}</small></span></div>) : <p className="muted">No active doctors yet.</p>}</div>
            <div className="rail-section"><h3>Departments</h3>{Object.entries(departments).map(([key, label]) => <div className="department-row" key={key}><span className={`dept-dot ${key}`}/>{label}</div>)}</div>
            <div className="ownership"><Phone size={17}/><span>Reception desk<br/><small>MediQueue · Student DevOps Capstone</small></span></div>
          </aside>
        </div>
        <footer className="page-footer"><span>MediQueue / Clinic appointment desk</span><span>Khushi Sarawagi · 24BCS10361</span></footer>
      </div>
    </main>
    {modal !== undefined && <AppointmentDialog key={modal?.id || 'new'} appointment={modal} doctors={doctors} onClose={() => setModal(undefined)} onSaved={saved}/>}
    <div className="toast-region" role="status">{notice && <div className="toast"><CircleCheck size={18}/>{notice}</div>}</div>
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
