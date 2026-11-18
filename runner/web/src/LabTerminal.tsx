import {useEffect, useRef, useState} from 'react';
import {post} from './api';
import type {LabJob} from './labWorkflow';

type Props = {attemptId: string | null; jobs: LabJob[]; dirty: boolean; complete: boolean; busy: boolean;
  onBusy: (value: boolean) => void; onJob: (job: LabJob) => void};
type Notice = {id: number; command: string; message: string; error?: boolean};

export function terminalCommand(job: LabJob) {
  const params = typeof job.params === 'string' ? JSON.parse(job.params) : job.params;
  if (params?.terminal_command) return params.terminal_command as string;
  const tools: Record<string, string> = {'validate-lab': 'grade', 'teardown-check': 'check-cleanup', 'reaper-preview': 'recover',
    'reaper-execute': 'recover --execute', 'reconcile-locks': 'probe-locks'};
  if (tools[job.operation]) return 'lab ' + tools[job.operation];
  if (['capture-baseline', 'simulate-drift', 'setup-import', 'migrate-remote', 'migrate-local'].includes(job.operation)) return 'lab ' + job.operation;
  return job.log?.split('\n').find(line => line.startsWith('$ terraform '))?.slice(2) || job.operation;
}

export default function LabTerminal({attemptId, jobs, dirty, complete, busy, onBusy, onJob}: Props) {
  const [input, setInput] = useState('');
  const [notices, setNotices] = useState<Notice[]>([]);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [hiddenJobs, setHiddenJobs] = useState<Set<string>>(new Set());
  const [historyIndex, setHistoryIndex] = useState(-1);
  const savedInput = useRef('');
  const prompt = useRef<HTMLInputElement>(null);
  const output = useRef<HTMLDivElement>(null);
  const followOutput = useRef(true);
  const running = jobs.find(job => ['queued', 'running'].includes(job.status));
  const history = jobs.map(terminalCommand);
  const notice = (command: string, message: string, error = false) => setNotices(current => [...current, {id: Date.now(), command, message, error}]);
  const timeline = [
    ...jobs.filter(job => !hiddenJobs.has(job.id)).map(job => ({kind: 'job' as const, created: job.created || 0, job})),
    ...notices.map(item => ({kind: 'notice' as const, created: item.id / 1000, item})),
  ].sort((a, b) => a.created - b.created);

  useEffect(() => {
    if (followOutput.current && output.current) output.current.scrollTop = output.current.scrollHeight;
  }, [jobs, notices]);
  function clear() {setHiddenJobs(new Set(jobs.map(job => job.id))); setNotices([]);}
  async function cancel() {
    if (confirmation) {setConfirmation(null); setInput(''); notice('no', 'Canceled. No command was run.'); return;}
    if (!running) {setInput(''); return;}
    try {await post(`/jobs/${running.id}/cancel`); notice('^C', 'Cancellation requested. Wait for the command to stop before continuing.');}
    catch (error) {notice('^C', (error as Error).message, true);}
  }
  async function submit() {
    const command = input.trim();
    if (!command || busy || running || !attemptId) return;
    setHistoryIndex(-1); followOutput.current = true;
    if (command === 'clear' && !confirmation) {clear(); setInput(''); return;}
    if (confirmation && !['yes', 'no'].includes(command)) {notice(command, 'Type yes to continue or no to cancel.'); setInput(''); return;}
    if (confirmation && command === 'no') {await cancel(); return;}
    const requested = confirmation || command;
    if (complete && command !== 'help') {notice(command, 'This attempt is complete. Start a new attempt to run more commands.'); setInput(''); return;}
    if (dirty && command !== 'help' && !/^(?:terraform(?: -chdir=bootstrap)? destroy|lab (?:check-cleanup|recover))(?:\s|$)/.test(requested)) {
      notice(command, 'Save your edited files first. Your command has not run.', true); setInput(''); return;
    }
    onBusy(true);
    try {
      const result = await post(`/attempts/${attemptId}/terminal`, {command: requested, confirmed: Boolean(confirmation)});
      if (result.confirmation_required) {setConfirmation(requested); notice(requested, result.message);}
      else if (result.job) {setConfirmation(null); onJob(result.job);}
      else {notice(command, result.message || 'Done.');}
      setInput('');
    } catch (error) {notice(requested, (error as Error).message, true); setConfirmation(null); setInput('');}
    finally {onBusy(false); prompt.current?.focus();}
  }
  return <section className="terminal-panel lab-terminal" aria-label="Lab terminal">
    <div className="terminal-title"><span><span className="terminal-lights" aria-hidden="true">● ● ●</span>Lab terminal</span><span className="badge">{running ? 'Running' : busy ? 'Submitting' : complete ? 'Complete' : 'Ready'}</span></div>
    <div className="terminal-transcript" ref={output} tabIndex={0} aria-label="Terminal output" role="log" aria-live="polite"
      onScroll={() => {const element = output.current; if (element) followOutput.current = element.scrollHeight - element.scrollTop - element.clientHeight < 60;}}>
      <p className="terminal-welcome">{attemptId ? 'Your lab workspace is ready. Type a command and press Enter. Type help if you get stuck.' : 'Start a lab attempt to open your terminal.'}</p>
      {timeline.map(entry => {
        if (entry.kind === 'notice') {const item = entry.item; return <div className={'terminal-entry terminal-notice ' + (item.error ? 'failed' : '')} key={'notice-' + item.id}><div className="terminal-command">$ {item.command}</div><pre>{item.message}</pre></div>;}
        const job = entry.job;
        return <div className="terminal-entry" key={job.id}>
        <div className="terminal-command"><span aria-hidden="true">$ </span>{terminalCommand(job)}</div>
        {job.log && <pre>{job.log.replace(/^\$ terraform [^\n]*\n/, '')}</pre>}
        {job.result && <pre>{JSON.stringify(typeof job.result === 'string' ? JSON.parse(job.result) : job.result, null, 2)}</pre>}
        {!['queued', 'running'].includes(job.status) && <p className={'terminal-exit ' + job.status}>{job.status}{job.exit_code != null ? ` · exit ${job.exit_code}` : ''}{job.exit_code === 2 && job.status === 'succeeded' ? ' (changes proposed)' : ''}</p>}
      </div>;})}
    </div>
    <form className="terminal-prompt" onSubmit={event => {event.preventDefault(); submit();}}>
      <span aria-hidden="true">{confirmation ? '?' : '$'}</span>
      <input ref={prompt} aria-label="Terminal command" autoComplete="off" autoCapitalize="off" spellCheck={false}
        placeholder={confirmation ? 'Type yes or no' : running ? 'Running… Ctrl+C to cancel' : attemptId ? 'Enter a command…' : 'Start an attempt first'}
        disabled={!attemptId} readOnly={busy || Boolean(running)} value={input} onChange={event => {setInput(event.target.value); setHistoryIndex(-1);}}
        onKeyDown={event => {
          if (event.ctrlKey && event.key.toLowerCase() === 'c') {if (!window.getSelection()?.toString()) {event.preventDefault(); cancel();}}
          else if (event.ctrlKey && event.key.toLowerCase() === 'l') {event.preventDefault(); clear();}
          else if (event.key === 'Escape' && confirmation) {event.preventDefault(); cancel();}
          else if (event.key === 'ArrowUp' && history.length && !confirmation) {
            event.preventDefault(); if (historyIndex < 0) savedInput.current = input;
            const index = Math.min(historyIndex + 1, history.length - 1); setHistoryIndex(index); setInput(history[index]);
          } else if (event.key === 'ArrowDown' && historyIndex >= 0 && !confirmation) {
            event.preventDefault(); const index = historyIndex - 1; setHistoryIndex(index); setInput(index < 0 ? savedInput.current : history[index]);
          }
        }} />
      <span className="terminal-enter" aria-hidden="true">↵</span>
    </form>
    <div className="terminal-footer"><span>{confirmation ? 'Waiting for your confirmation' : dirty ? 'Unsaved files · save before running commands' : 'Enter to run · ↑↓ history · Ctrl+C stop'}</span>
      {running && <button type="button" onClick={cancel}>Stop command</button>}</div>
  </section>;
}
