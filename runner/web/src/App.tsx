import { createContext, lazy, Suspense, useCallback, useContext, useEffect, useState } from 'react';
import type { ComponentType, FormEvent, ReactNode } from 'react';
import { Link, NavLink, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { api, post } from './api';
import type { Domain, Question } from './api';
import Exercises from './Exercises';
import Troubleshooting from './Troubleshooting';
import LabWorkspace from './LabWorkspace';

const Context = createContext<any>(null);
const lessons = import.meta.glob<{ default: ComponentType }>('../../../curriculum/domain-*/lesson.mdx');

function Icon({ name = 'grid', size = 18 }: { name?: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    book: <><path d="M3 4h6a4 4 0 014 3v14a4 4 0 00-4-3H3z" /><path d="M21 4h-6a4 4 0 00-2 3v14a4 4 0 014-3h4z" /></>,
    cloud: <path d="M6 18a5 5 0 01-1-10 7 7 0 0113 1 4.5 4.5 0 010 9H6z" />,
    exam: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8h6M9 12h6M9 16h3" /></>,
    arrow: <path d="M5 12h14m-6-6l6 6-6 6" />,
    check: <path d="M5 12l4 4L19 6" />,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    terminal: <><rect x="2" y="4" width="20" height="16" rx="3" /><path d="M6 9l3 3-3 3m6 0h5" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.grid}</svg>;
}

function useLoad<T = any>(path: string, revision = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { let active = true; api<T>(path).then(result => { if (active) { setData(result); setError(''); } }).catch(error => { if (active) setError(error.message); }); return () => { active = false; }; }, [path, revision]);
  return { data, error, setData };
}

function Loading() { return <div className="loading" role="status"><span className="spinner" />Loading course…</div>; }
function ErrorBox({ children }: { children: ReactNode }) { return <div className="notice error" role="alert">{children}</div>; }
function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={'badge ' + tone}>{children}</span>; }

export default function App() {
  const [revision, setRevision] = useState(0);
  const domains = useLoad<Domain[]>('/domains', revision);
  const progress = useLoad('/progress', revision);
  const connection = useLoad('/connection', revision);
  const [toast, setToast] = useState('');
  const refresh = useCallback(() => setRevision(value => value + 1), []);
  const context = { domains: domains.data || [], progress: progress.data, connection: connection.data, refresh, revision, notify: setToast };
  const completed = progress.data?.domains?.filter((item: any) => item.attempts.some((attempt: any) => attempt.status === 'complete')).length || 0;
  return <Context.Provider value={context}><div className="app-shell">
    <aside className="sidebar">
      <Link className="brand" to="/"><span className="brand-symbol">tf<span>›</span></span><div>tfprep<small>TERRAFORM REFRESHER</small></div></Link>
      <div className="course-badge">ASSOCIATE <strong>004</strong><span>1.12</span></div>
      <nav aria-label="Main navigation"><NavLink to="/" end><Icon />Overview</NavLink><NavLink to="/practice"><Icon name="exam" />Practice & exams</NavLink><NavLink to="/troubleshooting"><Icon name="terminal" />Debugging & problem solving</NavLink><NavLink to="/settings"><Icon name="cloud" />AWS connection<span className={'connection-dot ' + (connection.data?.connected ? 'online' : '')} /></NavLink></nav>
      <div className="nav-label">COURSE DOMAINS <span>{completed}/8</span></div>
      <nav className="domain-nav" aria-label="Course domains">{(domains.data || []).map(domain => <NavLink key={domain.id} to={'/domain/' + domain.id}><span className="nav-number">{domain.id}</span><span>{domain.title}</span></NavLink>)}</nav>
      <div className="sidebar-bottom"><span className="local-dot" /><div>Runs on your machine<small>Local progress · Your AWS account</small></div><Icon name="terminal" /></div>
    </aside>
    <div className="main-shell"><header className="topbar"><span>Learning workspace <span className="slash">/</span> Terraform Associate 004</span><span className="topbar-right"><span className="local-dot" />LOCAL COURSE<Link to="/settings" className="avatar" aria-label="Connection settings">L</Link></span></header>
      <main className="main-content">{toast && <div className="notice" role="status">{toast}<button aria-label="Dismiss notification" onClick={() => setToast('')}>×</button></div>}
        {domains.error ? <ErrorBox>{domains.error}</ErrorBox> : !domains.data ? <Loading /> : <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/domain/:id" element={<DomainPage />} />
          <Route path="/lab/:id" element={<LabPage />} />
          <Route path="/practice" element={<Practice />} />
          <Route path="/troubleshooting" element={<Troubleshooting />} />
          <Route path="/exam/:id" element={<ExamPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<section className="panel"><h1>Page not found</h1><Link to="/">Return to your course</Link></section>} />
        </Routes>}
      </main><footer className="page-footer"><span>Terraform Associate 004 refresher</span><span>Built for hands-on practice. Independent exam preparation.</span></footer>
    </div>
  </div></Context.Provider>;
}

function Overview() {
  const { domains, progress, connection } = useContext(Context);
  const completed = progress?.domains?.filter((item: any) => item.attempts.some((a: any) => a.status === 'complete')).length || 0;
  const next = domains.find((domain: Domain) => !progress?.domains?.find((item: any) => item.domain_id === domain.id)?.attempts.some((a: any) => a.status === 'complete')) || domains[0];
  const mastered = progress?.domains?.filter((item: any) => item.mastery.mastered).length || 0;
  return <>
    <div className="page-heading"><div><div className="eyebrow">YOUR LEARNING WORKSPACE</div><h1>Your Terraform refresher</h1><p className="lead">Pick up where you left off. Catch up on what changed.</p></div><Badge tone="purple">2023 → 2026</Badge></div>
    <section className="welcome-card"><div className="welcome-copy"><Badge tone="dark">TERRAFORM ASSOCIATE 004</Badge><h2>Familiar foundations.<br />A few important changes.</h2><p>Pick up the workflow again, try the 1.12 features, and put them into practice in AWS.</p><Link className="button light" to={'/domain/' + (next?.id || '01')}>{completed ? 'Continue learning' : 'Start your refresher'}<Icon name="arrow" /></Link></div><div className="welcome-code" aria-label="Terraform learning workflow"><div className="code-window-dots"><i /><i /><i /><span>your-next-chapter.tf</span></div><pre><span className="syntax-purple">course</span>{' "terraform" "004" {\n'}{'  baseline   = '}<span className="syntax-green">"1.12.2"</span>{'\n  domains    = '}<span className="syntax-orange">8</span>{'\n  approach   = '}<span className="syntax-green">"hands-on"</span>{'\n  confidence = '}<span className="syntax-purple">building</span>{'\n}'}</pre><div className="code-caption"><Icon name="check" size={14} />Learn → Apply → Verify → Clean up</div></div></section>
    <div className="stats-grid"><div className="stat"><span className="stat-icon purple"><Icon name="book" /></span><div><strong>{completed}<small> / 8</small></strong><span>Domains completed</span></div></div><div className="stat"><span className="stat-icon mint"><Icon name="check" /></span><div><strong>{mastered}<small> / 8</small></strong><span>Domains mastered</span></div></div><div className="stat"><span className="stat-icon amber"><Icon name="clock" /></span><div><strong>12–16<small> hrs</small></strong><span>Estimated course time</span></div></div></div>
    {!connection?.connected && <div className="connection-banner"><span className="stat-icon"><Icon name="cloud" /></span><div><strong>Connect your AWS sandbox</strong><p>Use an existing CLI profile or IAM access keys. Lessons and quizzes are ready without a connection.</p></div><Link className="button secondary" to="/settings">Set up AWS<Icon name="arrow" size={15} /></Link></div>}
    <div className="section-heading"><div><h2>The eight exam domains</h2><p className="muted">Each domain has a short refresher, an exercise and a lab to try.</p></div><span className="small muted">37 objectives · 8 labs</span></div>
    <div className="domain-grid">{domains.map((domain: Domain) => { const status = progress?.domains?.find((item: any) => item.domain_id === domain.id); const complete = status?.attempts.some((a: any) => a.status === 'complete'); const active = status?.attempts.length > 0; return <Link to={'/domain/' + domain.id} className={'domain-card ' + (complete ? 'finished' : '')} key={domain.id}><div className="domain-card-top"><span className="domain-number">{domain.id}</span><Badge tone={complete ? 'green' : active ? 'purple' : ''}>{complete ? 'Complete' : active ? 'In progress' : domain.difficulty}</Badge></div><h3>{domain.title}</h3><p>{domain.subtitle}</p><div className="domain-card-bottom"><span><Icon name="clock" size={14} />{domain.minutes} min</span><span>{domain.objectives.length} objectives</span><Icon name="arrow" size={18} /></div></Link>; })}</div>
    <section className="exam-callout"><div><div className="eyebrow">WORK WITH AN EXISTING REPOSITORY</div><h2>Build a method for debugging Terraform</h2><p className="muted">Work through seven examples, then try fixing a small local project yourself.</p></div><Link className="button secondary" to="/troubleshooting">Learn to troubleshoot<Icon name="arrow" /></Link></section>
    <section className="exam-callout"><div><div className="eyebrow">CHECK YOUR READINESS</div><h2>A practice run before exam day</h2><p className="muted">Try original practice questions, read some HCL and take a timed mock when you feel ready.</p></div><Link className="button primary" to="/practice">Explore assessments<Icon name="arrow" /></Link></section>
  </>;
}

function QuestionCard({ question, onAnswer, initial = [], reveal, disabled = false }: { question: Question; onAnswer: (selected: string[]) => Promise<any>; initial?: string[]; reveal?: any; disabled?: boolean }) {
  const [selected, setSelected] = useState<string[]>(initial);
  const [feedback, setFeedback] = useState<any>(reveal);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setSelected(initial); setFeedback(reveal); setError(''); }, [question.id, disabled]);
  async function check() { setBusy(true); try { setFeedback(await onAnswer(selected)); setError(''); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  return <div className="question-card"><div className="question-meta"><Badge>{question.objectives.join(' · ')}</Badge><span>{question.type === 'multiple' ? 'Multiple answer' : question.type === 'boolean' ? 'True / false' : 'Single answer'}</span></div><h3>{question.prompt}</h3>{question.code && <pre>{question.code}</pre>}<fieldset className="answer-options"><legend className="sr-only">Answer choices</legend>{Object.entries(question.choices).map(([key, value]) => <label className={'answer-option ' + (selected.includes(key) ? 'selected' : '')} key={key}><input type={question.type === 'multiple' ? 'checkbox' : 'radio'} name={question.id} checked={selected.includes(key)} disabled={disabled} onChange={() => { setSelected(question.type === 'multiple' ? selected.includes(key) ? selected.filter(item => item !== key) : [...selected, key] : [key]); setFeedback(null); }} /><span className="answer-letter">{key.toUpperCase()}</span><span>{value}</span></label>)}</fieldset>{!disabled && <button className="button secondary" disabled={!selected.length || busy} onClick={check}>{busy ? 'Saving…' : 'Save answer'}</button>}{error && <ErrorBox>{error}</ErrorBox>}{feedback?.rationale && <div className={'answer-feedback ' + (feedback.correct ? 'good' : 'wrong')}><strong>{feedback.correct ? 'Correct.' : 'Not quite. Let\'s look at why.'}</strong>{Object.entries(feedback.rationale as Record<string, string>).map(([letter, text]) => <p key={letter}><b>{letter.toUpperCase()}.</b> {text}</p>)}</div>}</div>;
}

function DomainPage() {
  const { id = '01' } = useParams();
  const { domains, refresh } = useContext(Context);
  const domain: Domain = domains.find((item: Domain) => item.id === id);
  const [tab, setTab] = useState('lesson');
  const [diffMode,setDiffMode]=useState(false);
  useEffect(() => setTab('lesson'), [id]);
  if (!domain) return <ErrorBox>Domain not found.</ErrorBox>;
  const module = lessons[`../../../curriculum/domain-${id}/lesson.mdx`];
  return <><Link to="/" className="back-link">← All domains</Link><div className="page-heading"><div><div className="eyebrow">DOMAIN {id} / ASSOCIATE 004</div><h1>{domain.title}</h1><p className="lead">{domain.subtitle}</p></div><Link className="button primary" to={'/lab/' + id}><Icon name="terminal" />Open AWS lab</Link></div><div className="lesson-meta"><span><Icon name="clock" size={15} />{domain.minutes} minutes</span><span>{domain.objectives.length} exam objectives</span><span>{domain.exercises.length} interactive exercises</span></div><div className="tab-row large">{[['lesson', 'Refresher lesson'], ['exercises', 'Interactive exercises'], ['checkpoints', 'Check your understanding']].map(([key, label]) => <button className={tab === key ? 'active' : ''} key={key} onClick={() => setTab(key)}>{label}</button>)}</div>
    {tab === 'lesson' && <div className="lesson-layout"><article className="panel lesson-prose">{module ? <Lesson module={module} domainId={id} /> : <p>Lesson content is not available.</p>}</article><aside className="lesson-aside"><section className="panel"><div className="eyebrow">YOUR CATCH-UP</div><h3>2023 vs 2026</h3><button className="button quiet diff-toggle" onClick={()=>setDiffMode(!diffMode)} aria-pressed={diffMode}>{diffMode?'Show then & now':'Show unified diff'}</button>{diffMode?<pre className="delta-diff"><span className="diff-removed">− {domain.delta.before}</span>{'\n\n'}<span className="diff-added">+ {domain.delta.after}</span></pre>:<><div className="delta-before"><span>THEN</span><p>{domain.delta.before}</p></div><div className="delta-after"><span>NOW</span><p>{domain.delta.after}</p></div></>}</section><section className="panel"><div className="eyebrow">EXAM COVERAGE</div><h3>Objective checklist</h3>{domain.objectives.map(objective => <div className="objective-row" key={objective}><span className="objective-square" />{objective}</div>)}<button className="button secondary full" onClick={() => setTab('checkpoints')}>Try the checkpoints<Icon name="arrow" size={14} /></button></section><section className="lab-mini"><Icon name="cloud" /><h3>Put it into practice</h3><p>{domain.lab_id.replaceAll('-', ' ')}</p><Link to={'/lab/' + id}>Open the challenge →</Link></section></aside></div>}
    {tab === 'exercises' && <Exercises exercises={domain.exercises} />}
    {tab === 'checkpoints' && <div className="checkpoint-stack"><p className="muted">Three quick checkpoints. Explanations appear after you save an answer.</p>{domain.checkpoints.map(question => <section className="panel" key={question.id}><QuestionCard question={question} onAnswer={async selected => { const result = await post(`/domains/${id}/checkpoints`, { question_id: question.id, selected }); refresh(); return result; }} /></section>)}<Link className="button primary" to={'/lab/' + id}>Continue to the AWS lab<Icon name="arrow" /></Link></div>}
  </>;
}

const lessonCache = new Map<string, ReturnType<typeof lazy>>();
function Lesson({ module, domainId }: { module: () => Promise<{ default: ComponentType }>; domainId: string }) {
  if (!lessonCache.has(domainId)) lessonCache.set(domainId, lazy(module));
  const Component = lessonCache.get(domainId)!;
  return <Suspense fallback={<Loading />}><Component /></Suspense>;
}

function SettingsPage() {
  const { connection, progress, refresh, notify } = useContext(Context);
  const [mode, setMode] = useState('profile');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const doctor = useLoad('/doctor');
  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    const payload: any = { mode, region: data.get('region') };
    if (mode === 'profile') payload.profile = data.get('profile');
    else { payload.access_key_id = data.get('access_key_id'); payload.secret_access_key = data.get('secret_access_key'); if (data.get('session_token')) payload.session_token = data.get('session_token'); }
    setBusy(true); setError('');
    try { await post('/connection', payload); form.reset(); refresh(); notify('AWS identity verified. Your live labs are ready.'); } catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  return <><div className="page-heading"><div><div className="eyebrow">COURSE SETUP</div><h1>Connect your AWS sandbox</h1><p className="lead">Choose how the course accesses your account.</p></div><Badge tone={connection?.connected ? 'green' : ''}>{connection?.connected ? 'Connected' : 'Not connected'}</Badge></div><div className="settings-layout"><section className="panel"><h2>AWS access</h2><p className="muted">We will check your AWS identity without creating any resources.</p>{connection?.connected && <div className="identity-card"><Icon name="check" /><div><strong>Account {connection.account}</strong><code>{connection.arn}</code><span>{connection.region} · {connection.mode === 'profile' ? `Profile: ${connection.profile}` : 'Access keys for this session'}</span></div><button className="button quiet" onClick={async () => { try { await api('/connection', { method: 'DELETE' }); refresh(); } catch (error) { setError((error as Error).message); } }}>Disconnect</button></div>}<div className="connection-methods"><button className={mode === 'profile' ? 'selected' : ''} onClick={() => setMode('profile')}><Icon name="terminal" /><strong>CLI profile</strong><span>Use an existing named profile</span></button><button className={mode === 'keys' ? 'selected' : ''} onClick={() => setMode('keys')}><Icon name="cloud" /><strong>IAM access keys</strong><span>Enter credentials for this session</span></button></div><form onSubmit={connect}>{mode === 'profile' ? <label>AWS CLI profile name<input name="profile" placeholder="course-sandbox" defaultValue={connection?.profile || ''} required autoComplete="off" /><small>Uses your host's AWS configuration and existing SSO login.</small></label> : <><label>Access key ID<input name="access_key_id" placeholder="AKIA… or ASIA…" required autoComplete="off" /></label><label>Secret access key<input name="secret_access_key" type="password" required autoComplete="new-password" /></label><label>Session token <span className="muted">(optional)</span><input name="session_token" type="password" autoComplete="new-password" /><small>Include this when using temporary credentials.</small></label></>}<label>Primary lab region<select name="region" defaultValue={connection?.region || 'us-east-1'}><option value="eu-west-1">Europe — Ireland (eu-west-1)</option><option value="us-east-1">US East — N. Virginia (us-east-1)</option><option value="eu-west-2">Europe — London (eu-west-2)</option></select><small>Domain 02 uses a fixed N. Virginia/London provider pair.</small></label>{error && <ErrorBox>{error}</ErrorBox>}<button className="button primary" disabled={busy}>{busy ? 'Testing connection…' : 'Test connection & continue'}<Icon name="arrow" /></button></form></section><aside><section className="panel"><div className="eyebrow">YOUR CREDENTIALS</div><h3>Stay in control</h3><p>Entered keys stay in server memory for this course session. They are never saved in progress records or your browser.</p><p className="muted">After a restart, enter keys again. A saved profile name can be reused after you reconnect. Existing lab attempts stay tied to their original AWS account.</p><Link to="/" className="text-link">Continue with lessons →</Link></section><section className="panel runtime-card"><div className="eyebrow">LOCAL RUNTIME</div><h3>Tool check</h3>{doctor.data ? <><div>Terraform <Badge tone={doctor.data.terraform.correct ? 'green' : 'amber'}>{doctor.data.terraform.version || 'Missing'}</Badge></div><div>AWS CLI <Badge>{doctor.data.aws_cli ? 'Available' : 'Missing'}</Badge></div><div>TFLint <Badge>{doctor.data.tflint ? 'Available' : 'Missing'}</Badge></div></> : <Loading />}</section></aside></div><section className="panel"><div className="eyebrow">LOCAL DATA</div><h2>Private artifact retention</h2><p className="muted">Once cleanup is verified, you can remove private plans, state files and debug logs. Your HCL and progress stay saved.</p>{progress?.domains?.flatMap((domain: any) => domain.attempts.filter((attempt: any) => attempt.status === 'complete').map((attempt: any) => <div className="resume-row" key={attempt.id}><span>Domain {domain.domain_id} · {attempt.id}</span><button className="button secondary" onClick={async () => { try { const result = await post(`/attempts/${attempt.id}/purge-artifacts`); notify(`Removed ${result.removed_files} private artifacts. Source and progress retained.`); } catch (error) { setError((error as Error).message); } }}>Purge private artifacts</button></div>))}{!progress?.domains?.some((domain: any) => domain.attempts.some((attempt: any) => attempt.status === 'complete')) && <p className="small muted">Completed lab attempts appear here after apply validation and verified teardown.</p>}</section></>;
}

function LabPage() {
  const { id = '01' } = useParams();
  const { domains, progress, connection, refresh, notify, revision } = useContext(Context);
  const domain: Domain = domains.find((item: Domain) => item.id === id);
  if (!domain) return <ErrorBox>Domain not found.</ErrorBox>;
  const latestAttemptId = progress?.domains?.find((item: any) => item.domain_id === id)?.attempts[0]?.id || null;
  return <LabWorkspace key={id} domain={domain} latestAttemptId={latestAttemptId} connection={connection}
    refresh={refresh} notify={notify} revision={revision} />;
}

function Practice() {
  const { domains, progress, refresh } = useContext(Context);
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [questionCount,setQuestionCount]=useState(57);
  async function start(mode: string, domain_id?: string, mock_set = 'A') { setBusy(true); try { const result = await post('/exams', { mode, domain_id: domain_id || null, mock_set, question_count:mode==='mock'?questionCount:null }); refresh(); navigate('/exam/' + result.id); } catch (error) { setError((error as Error).message); } finally { setBusy(false); } }
  const active = progress?.exams?.filter((exam: any) => !exam.submitted) || [];
  return <><div className="page-heading"><div><div className="eyebrow">ASSESSMENT WORKSPACE</div><h1>Practice with purpose</h1><p className="lead">See what you remember, learn from the explanations and try a timed run when you are ready.</p></div><Badge tone="purple">120 original scenarios</Badge></div>{error && <ErrorBox>{error}</ErrorBox>}{active.length > 0 && <section className="panel"><h2>Resume a session</h2>{active.map((exam: any) => <Link className="resume-row" key={exam.id} to={'/exam/' + exam.id}><span>{exam.mode === 'mock' ? 'Timed mock exam' : 'Practice session'}</span><span>{new Date(exam.created * 1000).toLocaleString()}</span><Icon name="arrow" /></Link>)}</section>}<label className="mock-length">Mock length<select value={questionCount} onChange={event=>setQuestionCount(Number(event.target.value))}><option value={57}>57 questions — full objective coverage</option><option value={37}>37 questions — shorter practice</option><option value={20}>20 questions — shorter practice</option></select></label><div className="mock-grid">{['A', 'B'].map(set => <section className="mock-card" key={set}><Badge tone="purple">MOCK EXAM {set}</Badge><h2>One focused hour.</h2><p>{questionCount} questions · 60 minutes · Mixed domains</p><ul><li>Flag questions and return before submitting.</li><li>The deadline survives refreshes and restarts.</li><li>Explanations unlock after submission.</li></ul><button className="button primary" disabled={busy} onClick={() => start('mock', undefined, set)}>Start mock {set}<Icon name="arrow" /></button></section>)}</div><div className="section-heading"><div><h2>Practice by domain</h2><p className="muted">Untimed practice with explanations after every answer.</p></div><button className="button secondary" disabled={busy} onClick={() => start('practice')}>Mixed practice</button></div><div className="practice-domain-list">{domains.map((domain: Domain) => <div className="panel practice-row" key={domain.id}><span className="domain-number">{domain.id}</span><div><h3>{domain.title}</h3><span className="muted small">Objectives {domain.objectives.join(', ')}</span></div><button className="button secondary" disabled={busy} onClick={() => start('practice', domain.id)}>Practice<Icon name="arrow" size={15} /></button></div>)}</div><p className="small muted">Use these scores to guide your practice. The question mix is designed for this course and does not predict your certification result.</p>{progress?.exams?.some((exam: any) => exam.submitted) && <section className="panel"><h2>Completed sessions</h2>{progress.exams.filter((exam: any) => exam.submitted).map((exam: any) => <Link className="resume-row" key={exam.id} to={'/exam/' + exam.id}><span>{exam.mode === 'mock' ? 'Mock exam' : 'Practice'} · {new Date(exam.submitted * 1000).toLocaleDateString()}</span><Badge tone="purple">{exam.score}%</Badge><span>Review →</span></Link>)}</section>}</>;
}

function ExamPage() {
  const { id = '' } = useParams();
  const { refresh } = useContext(Context);
  const [exam, setExam] = useState<any>(null);
  const [index, setIndex] = useState(0);
  const [now, setNow] = useState(Date.now() / 1000);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');
  const [flagged, setFlagged] = useState(false);
  useEffect(() => { api(`/exams/${id}`).then(data => { setExam(data); setOffset(data.server_time - Date.now() / 1000); }).catch(error => setError(error.message)); }, [id]);
  useEffect(() => { const interval = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(interval); }, []);
  useEffect(() => { if (exam?.deadline && !exam.submitted && now + offset >= exam.deadline) api(`/exams/${id}`).then(data => { setExam(data); refresh(); }).catch(error => setError(error.message)); }, [now, exam?.deadline, exam?.submitted]);
  useEffect(() => setFlagged(Boolean(exam?.answers?.[exam?.questions[index]?.id]?.flagged)), [index, exam?.id]);
  if (error && !exam) return <ErrorBox>{error}</ErrorBox>;
  if (!exam) return <Loading />;
  const question: Question = exam.questions[index];
  const remaining = Math.max(0, (exam.deadline || 0) - now - offset);
  const seconds = `${Math.floor(remaining / 60).toString().padStart(2, '0')}:${Math.floor(remaining % 60).toString().padStart(2, '0')}`;
  const selected = exam.answers[question.id]?.selected || [];
  return <><Link className="back-link" to="/practice">← Practice & exams</Link><div className="page-heading"><div><div className="eyebrow">{exam.mode === 'mock' ? 'TIMED MOCK EXAM' : 'DOMAIN PRACTICE'}</div><h1>{exam.submitted ? 'Review your results' : 'Work through each scenario'}</h1><p className="lead">Question {index + 1} of {exam.questions.length}</p></div>{exam.submitted ? <Badge tone="purple">{exam.score}% practice score</Badge> : exam.deadline && <div className={'exam-timer ' + (remaining < 300 ? 'urgent' : '')}><Icon name="clock" />{seconds}<small>remaining</small></div>}</div>{error && <ErrorBox>{error}</ErrorBox>}<div className="exam-layout"><section className="panel"><QuestionCard key={question.id} question={question} initial={selected} disabled={Boolean(exam.submitted)} reveal={exam.submitted ? { correct: JSON.stringify([...selected].sort()) === JSON.stringify([...(question.correct || [])].sort()), rationale: question.rationale } : undefined} onAnswer={async selected => { const result = await api(`/exams/${id}/answers`, { method: 'PUT', body: JSON.stringify({ question_id: question.id, selected, flagged }) }); setExam((current: any) => ({ ...current, answers: { ...current.answers, [question.id]: { selected, flagged } } })); return result; }} />{!exam.submitted && <label className="inline-check flag-control"><input type="checkbox" checked={flagged} onChange={event => { const value = event.target.checked; setFlagged(value); api(`/exams/${id}/answers`, { method: 'PUT', body: JSON.stringify({ question_id: question.id, selected, flagged: value }) }).then(() => setExam((current: any) => ({ ...current, answers: { ...current.answers, [question.id]: { selected, flagged: value } } }))).catch(error => setError(error.message)); }} />Flag for review</label>}<div className="exam-navigation"><button className="button secondary" disabled={index === 0} onClick={() => setIndex(index - 1)}>← Previous</button><span>{index + 1} / {exam.questions.length}</span><button className="button secondary" disabled={index === exam.questions.length - 1} onClick={() => setIndex(index + 1)}>Next →</button></div></section><aside className="panel exam-map"><h3>Question navigator</h3><div className="question-map">{exam.questions.map((q: Question, i: number) => <button key={q.id} aria-label={'Go to question ' + (i + 1)} className={(i === index ? 'current ' : '') + (exam.answers[q.id]?.selected.length ? 'answered ' : '') + (exam.answers[q.id]?.flagged ? 'flagged' : '')} onClick={() => setIndex(i)}>{i + 1}</button>)}</div><p className="small muted">Filled = saved answer · Orange = flagged</p>{!exam.submitted && <button className="button primary full" onClick={async () => { try { setExam(await post(`/exams/${id}/submit`)); refresh(); } catch (error) { setError((error as Error).message); } }}>Submit {exam.mode === 'mock' ? 'exam' : 'practice'}</button>}{exam.submitted && <p className="small muted">Review explanations for every choice. Use another practice session to revisit gaps.</p>}</aside></div></>;
}
