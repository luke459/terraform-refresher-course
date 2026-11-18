import {useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {api, post} from './api';
import type {Domain} from './api';
import {labWorkflow} from './labWorkflow';
import LabTerminal from './LabTerminal';
import type {LabJob} from './labWorkflow';

type File = {path: string; content: string};
type Props = {domain: Domain; latestAttemptId: string | null; connection: any; revision: number; refresh: () => void; notify: (text: string) => void};

function inline(text: string) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, i) => part.startsWith('`') ? <code key={i}>{part.slice(1, -1)}</code>
    : part.startsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part);
}
function Challenge({text}: {text: string}) {
  return <div className="simple-markdown">{text.split(/\n\n+/).map((block, i) => {
    if (/^#+ /.test(block)) return <h3 key={i}>{inline(block.replace(/^#+ /, ''))}</h3>;
    if (/^\d+\. /.test(block)) return <ol key={i}>{block.split('\n').map((line, n) => <li key={n}>{inline(line.replace(/^\d+\. /, ''))}</li>)}</ol>;
    return <p key={i}>{inline(block)}</p>;
  })}</div>;
}

export default function LabWorkspace({domain, latestAttemptId, connection, refresh, notify, revision}: Props) {
  const id = domain.id;
  const [attemptId, setAttemptId] = useState<string | null>(latestAttemptId);
  const [attempt, setAttempt] = useState<any>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState('');
  const [selectedFile, setSelectedFile] = useState('');
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [solution, setSolution] = useState<File[] | null>(null);
  const [showSolution, setShowSolution] = useState(false);

  useEffect(() => { if (latestAttemptId) setAttemptId(latestAttemptId); }, [latestAttemptId]);
  useEffect(() => {
    if (!attemptId) return;
    let active = true;
    const update = () => api(`/attempts/${attemptId}`).then(data => {if (active) setAttempt(data);})
      .catch(error => {if (active) setError(error.message);});
    update(); const timer = setInterval(update, 1500);
    return () => {active = false; clearInterval(timer);};
  }, [attemptId, revision]);
  useEffect(() => {if (attempt?.id) refresh();}, [attempt?.id, attempt?.status, attempt?.percentage, refresh]);
  useEffect(() => {setDrafts({}); setFiles([]); setSelectedFile('');}, [attemptId]);
  const changedFilesJob = attempt?.jobs?.find((job: any) => !['queued', 'running'].includes(job.status) && ['fmt', 'generate-config', 'provider-lock'].includes(job.operation))?.id;
  useEffect(() => {
    if (!attemptId) return;
    let active = true;
    api<File[]>(`/attempts/${attemptId}/files`).then(data => {
      if (!active) return;
      setFiles(data); setFileError('');
      setSelectedFile(current => data.some(file => file.path === current) ? current : (data.find(file => file.path === 'main.tf') || data[0])?.path || '');
    }).catch(error => {if (active) setFileError(error.message);});
    return () => {active = false;};
  }, [attemptId, changedFilesJob]);

  const workflow = labWorkflow(attempt);
  const {complete, graded, next, jobs} = workflow;
  const running = jobs.find(job => ['queued', 'running'].includes(job.status));
  const dirty = Object.keys(drafts).length > 0;
  const locked = busy || Boolean(running) || complete || !attempt;
  const file = files.find(file => file.path === selectedFile);

  async function start() {
    setBusy(true); setError('');
    try {const result = await post('/attempts', {domain_id: id}); setAttemptId(result.id); setAttempt(result); refresh();}
    catch (error) {setError((error as Error).message);} finally {setBusy(false);}
  }
  function receivedJob(job: LabJob) {
    setAttempt((current: any) => current ? {...current, jobs: [job, ...current.jobs.filter((item: LabJob) => item.id !== job.id)]} : current);
    api(`/attempts/${attemptId}`).then(setAttempt).catch(error => setError(error.message));
  }
  const runningJobId = running?.id;
  useEffect(() => {
    if (!runningJobId || !attemptId) return;
    const stream = new EventSource(`/api/jobs/${runningJobId}/events`);
    stream.onmessage = event => {
      try {
        const job = JSON.parse(event.data);
        setAttempt((current: any) => current ? {...current, jobs: current.jobs.map((item: LabJob) => item.id === job.id ? job : item)} : current);
        if (!['queued', 'running'].includes(job.status)) {
          stream.close();
          api(`/attempts/${attemptId}`).then(setAttempt).catch(error => setError(error.message));
          refresh();
        }
      } catch {stream.close();}
    };
    stream.onerror = () => stream.close(); // The regular attempt poll remains a fallback.
    return () => stream.close();
  }, [runningJobId, attemptId, refresh]);
  async function save() {
    setBusy(true); setError('');
    try {
      for (const [path, content] of Object.entries(drafts)) {
        await api(`/attempts/${attemptId}/files`, {method: 'PUT', body: JSON.stringify({path, content})});
        setFiles(current => current.map(file => file.path === path ? {...file, content} : file));
        setDrafts(current => {const result = {...current}; delete result[path]; return result;});
      }
      notify('Configuration saved. Review a new plan before applying.'); refresh();
    } catch (error) {setError((error as Error).message);} finally {setBusy(false);}
  }
  async function revealSolution() {
    if (showSolution) {setShowSolution(false); return;}
    try {if (!solution) setSolution(await api(`/domains/${id}/solution`)); setShowSolution(true);}
    catch (error) {setError((error as Error).message);}
  }

  return <div className="lab-page">
    <Link className="back-link" to={'/domain/' + id}>← Back to domain {id}</Link>
    <div className="page-heading lab-heading"><div><div className="eyebrow">HANDS-ON AWS CHALLENGE / DOMAIN {id}</div>
      <h1>{domain.lab_id.replace(/^lab-\d+-/, '').split('-').map(word => word[0].toUpperCase() + word.slice(1)).join(' ')}</h1>
      <p className="lead">Read the challenge, edit your files and run commands in your lab terminal.</p></div>
      <span className={'badge ' + (complete ? 'green' : 'purple')}>{complete ? '100% complete' : graded ? '50% apply verified' : 'Not yet graded'}</span>
    </div>
    <div className="lab-context"><span>{attempt ? `Account ${attempt.account} · ${attempt.region}` : connection?.connected ? `Account ${connection.account} · ${connection.region}` : 'Connect AWS to run this lab'}</span>
      <span>{domain.lab_minutes} min · Budget target &lt; ${domain.cost.target_usd.toFixed(2)} · usage may be billed</span></div>
    {error && <div className="notice error" role="alert">{error}</div>}

    <section className="panel lab-progress" aria-label="Lab progress">
      <div className="lab-progress-caption"><strong>Your lab progress</strong><span>{workflow.stages.filter(stage => stage.done).length} of 4 stages complete</span></div>
      <ol className="lab-stages">{workflow.stages.map((stage, index) => <li key={stage.title} className={stage.done ? 'done' : ''}>
        <span className="stage-number" aria-hidden="true">{stage.done ? '✓' : index + 1}</span><div><strong>{stage.title}</strong>
          <span>{stage.done ? 'Complete' : stage.description}</span></div></li>)}</ol>
      <div className="lab-next" role="status"><div><strong>{complete ? 'Lab complete' : running ? `Running: ${running.operation}` : dirty ? 'Next: save your changes' : !attempt ? 'Next: start a lab attempt' : `Next: ${next.label}`}</strong>
        <p>{running ? 'While this runs, you can keep reading the challenge. Results and progress update automatically.' : dirty ? `${Object.keys(drafts).length} unsaved ${Object.keys(drafts).length === 1 ? 'file' : 'files'}. Save before running checks or applying.` : next.hint}</p></div>
        {attempt && !complete && !running && dirty && <button className="button primary" aria-label="Next action: Save changes" disabled={busy} onClick={save}>Save changes</button>}
        {complete && <Link className="button secondary" to={Number(id) < 8 ? `/domain/${String(Number(id) + 1).padStart(2, '0')}` : '/practice'}>{Number(id) < 8 ? 'Continue to next domain' : 'Practice & exams'} →</Link>}
      </div>
      {!complete && <p className="lab-credit-note">Completion checkpoints: <strong>50% after all lab checks pass</strong> · <strong>100% after destroy and verified cleanup</strong>. The checks confirm the result, so running commands alone does not finish the lab.</p>}
    </section>

    <nav className="lab-section-links" aria-label="Workspace sections"><a href="#challenge-title">Challenge</a><a href="#editor-title">Editor</a><a href="#lab-command-output">Terminal</a><a href="#lab-checks">Checks</a></nav>
    <div className="lab-workbench">
      <section className="panel lab-challenge" aria-labelledby="challenge-title"><div className="workbench-heading"><div><span className="eyebrow">YOUR BRIEF</span><h2 id="challenge-title">The challenge</h2></div></div>
        <Challenge text={domain.challenge} />
        <button className="button quiet" aria-expanded={showSolution} onClick={revealSolution}>{showSolution ? 'Hide reference solution' : 'Compare reference solution'}</button>
        {showSolution && <div className="lab-reference"><p className="small muted">Use this to compare approaches after trying your own. You will still need to pass the lab checks and clean up.</p>{solution?.map(file => <details key={file.path}><summary>{file.path}</summary><pre>{file.content}</pre></details>)}</div>}
      </section>

      <section className="panel lab-editor" aria-labelledby="editor-title"><div className="workbench-heading"><div><span className="eyebrow">MAKE YOUR CHANGES</span><h2 id="editor-title">Workspace editor</h2></div>
        {attempt && <span className={'badge ' + (dirty ? 'purple' : '')}>{complete ? 'Read only' : dirty ? 'Unsaved changes' : 'All changes saved'}</span>}</div>
        {!attempt ? <div className="lab-empty"><h3>Your lab workspace</h3><p>Start an attempt to load the starter files here. This does not create cloud resources.</p>
          {connection?.connected ? <button className="button primary" disabled={busy} onClick={start}>{busy ? 'Preparing…' : 'Start lab attempt'}</button> : <Link className="button primary" to="/settings">Connect AWS to start</Link>}</div>
          : <>{fileError && <div className="notice error" role="alert">{fileError}</div>}
            <div className="lab-editor-toolbar"><label htmlFor="lab-file">File<select id="lab-file" aria-label="Workspace file" value={selectedFile} onChange={event => setSelectedFile(event.target.value)}>{files.map(file => <option key={file.path} value={file.path}>{file.path}{drafts[file.path] !== undefined ? ' • unsaved' : ''}</option>)}</select></label>
              <button className="button secondary" disabled={locked || !dirty} onClick={save}>Save changes</button></div>
            {file ? <textarea aria-label={'Edit ' + selectedFile} className="code-editor" spellCheck={false} value={drafts[selectedFile] ?? file.content} disabled={busy || Boolean(running) || complete}
              onChange={event => {const content = event.target.value; setDrafts(current => {const next = {...current}; if (content === file.content) delete next[selectedFile]; else next[selectedFile] = content; return next;});}} /> : <p className="lab-empty">Loading workspace files…</p>}
            <p className="editor-footnote">{complete ? 'This completed attempt is read only. Your files and progress are saved.' : 'Switch files freely; unsaved edits stay here until you save. Save changes applies all edited files.'}</p>
          </>}
      </section>

      <div className="lab-output" id="lab-command-output">
        <LabTerminal key={attemptId || 'new'} attemptId={attemptId} jobs={jobs} dirty={dirty} complete={complete} busy={busy} onBusy={setBusy} onJob={receivedJob} />
        <details className="panel terminal-hint"><summary>Need a hint?</summary><p>{next.hint}</p>
          <p>Type <code>help</code> in the terminal to see Terraform commands and the lab tools. Save a plan as <code>tfplan</code> before applying it. Run <code>lab grade</code> when you are ready to check your work, and <code>lab check-cleanup</code> after destroying the resources.</p>
        </details>
        <section className="panel checks-panel" id="lab-checks" aria-label="Lab validation checks"><h3>Lab checks {attempt?.results?.length ? `· ${attempt.results.filter((check: any) => check.status === 'pass').length}/${attempt.results.length} passing` : ''}</h3>
          {attempt?.results?.length ? attempt.results.map((check: any) => <div className={'check-result ' + check.status} key={check.id}><span>{check.status === 'pass' ? '✓' : '○'}</span><div><strong>{check.id.replaceAll('_', ' ')}</strong><p>{check.message}</p></div><span className="badge">{check.status}</span></div>)
            : <p className="small muted">After applying, check that a detailed plan has no changes, then run lab grade. Your results will appear here.</p>}</section>
      </div>
    </div>
    {attempt && <details className="panel lab-attempt-details"><summary>Attempt details & workspace path</summary><p>Attempt {attempt.id}</p><code>{attempt.workspace}</code>
      {['complete', 'cleaned'].includes(attempt.status) && <button className="button secondary" disabled={busy} onClick={start}>New attempt</button>}</details>}
  </div>;
}
