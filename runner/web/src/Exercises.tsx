import { useState } from 'react';
import type { Exercise } from './api';

function Scenarios({ exercise }: { exercise: Exercise }) {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [graded, setGraded] = useState(false);
  const mapping=exercise.id==='architecture-triage';
  return <div className="scenario-list">{mapping && <><p className="small muted">Drag a category onto a scenario, or use its radio options with the keyboard.</p><div className="choice-row">{[...new Set(exercise.cases?.flatMap(item=>item.choices))].map(choice=><span className="drag-token" draggable onDragStart={event=>event.dataTransfer.setData('text/plain',choice)} key={choice}>{choice}</span>)}</div></>}{exercise.cases?.map((item, index) => <fieldset className={'scenario '+(mapping?'drop-zone':'')} key={index} onDragOver={mapping?event=>event.preventDefault():undefined} onDrop={mapping?event=>{event.preventDefault();const value=event.dataTransfer.getData('text/plain');if(item.choices.includes(value)){setAnswers({...answers,[index]:value});setGraded(false);}}:undefined}>
    <legend><span className="step-number">{index + 1}</span> {item.prompt}</legend>
    <div className="choice-row">{item.choices.map(choice => <label className={'choice-chip ' + (answers[index] === choice ? 'selected' : '')} key={choice}>
      <input type="radio" name={`${exercise.id}-${index}`} value={choice} checked={answers[index] === choice} onChange={() => { setAnswers({ ...answers, [index]: choice }); setGraded(false); }} />{choice}
    </label>)}</div>
    {graded && <p className={answers[index] === item.correct ? 'feedback good' : 'feedback wrong'}>{answers[index] === item.correct ? 'Correct. ' : `Choose ${item.correct}. `}{item.explanation}</p>}
  </fieldset>)}<button className="button secondary" onClick={() => setGraded(true)} disabled={Object.keys(answers).length !== exercise.cases?.length}>Check predictions</button></div>;
}

function Constraints() {
  const [constraint, setConstraint] = useState('~> 5.80.0');
  const [version, setVersion] = useState('5.92.0');
  const [checked, setChecked] = useState(false);
  const parts = version.split('.').map(Number);
  const valid = /^\d+\.\d+\.\d+$/.test(version);
  const allowed = valid && parts[0] === 5 && (constraint === '~> 5.80.0' ? parts[1] === 80 : constraint === '~> 5.80' ? parts[1] >= 80 : true);
  return <div><div className="field-grid"><label>Version constraint<select value={constraint} onChange={e => { setConstraint(e.target.value); setChecked(false); }}><option>~&gt; 5.80.0</option><option>~&gt; 5.80</option><option>&gt;= 5.0, &lt; 6.0</option></select></label><label>Candidate version<input value={version} onChange={e => { setVersion(e.target.value); setChecked(false); }} /></label></div><button className="button secondary" onClick={() => setChecked(true)}>Resolve version</button>{checked && <p className={'feedback ' + (allowed ? 'good' : 'wrong')}>{!valid ? 'Enter a semantic version such as 5.92.0.' : allowed ? `${version} satisfies ${constraint}. A committed lockfile can still select a different allowed version.` : `${version} is outside ${constraint}. ~> permits only the rightmost specified component to increase.`}</p>}</div>;
}

function Evaluation() {
  const [step, setStep] = useState(0);
  const [unknown, setUnknown] = useState(false);
  const stages = [
    ['Input validation', 'Known input values can be checked while planning. Invalid inputs block further work.'],
    ['Precondition', unknown ? 'This condition depends on an apply-time ID, so its evaluation is deferred until that ID is known.' : 'The required values are known. Terraform checks the precondition before the resource operation.'],
    ['Resource operation', 'Terraform creates or updates the resource if its blocking conditions allow it.'],
    ['Postcondition', 'Verify the guarantee after planning/applying or after a data read. Known values may allow evaluation during planning. A failed postcondition blocks dependent work.'],
    ['Top-level check', 'Assess infrastructure without blocking the Terraform operation. Failed assertions emit warnings; the course grader still treats them as unsuccessful.'],
  ];
  return <div><label className="inline-check"><input type="checkbox" checked={unknown} onChange={e => setUnknown(e.target.checked)} />Precondition uses an apply-time value</label><div className="flow-steps">{stages.map(([name], index) => <button key={name} className={step === index ? 'active' : ''} onClick={() => setStep(index)}>{index + 1}. {name}</button>)}</div><div className="simulation-output"><strong>{stages[step][0]}</strong><p>{stages[step][1]}</p></div><button className="button secondary" onClick={() => setStep((step + 1) % stages.length)}>Next evaluation →</button></div>;
}

function StateInspector() {
  const [mode, setMode] = useState('sensitive');
  const [answer, setAnswer] = useState<string | null>(null);
  const states = { sensitive: '{\n  "type": "random_password",\n  "values": {\n    "result": "example-only-password",\n    "sensitive": true\n  }\n}', ephemeral: '{\n  "type": "aws_secretsmanager_secret_version",\n  "values": {\n    "secret_string_wo": null,\n    "secret_string_wo_version": 1\n  }\n}' };
  return <div><div className="tab-row">{['sensitive', 'ephemeral'].map(value => <button key={value} className={mode === value ? 'active' : ''} onClick={() => { setMode(value); setAnswer(null); }}>{value === 'sensitive' ? 'sensitive = true' : 'ephemeral + write-only'}</button>)}</div><pre>{states[mode as keyof typeof states]}</pre><p>Does this illustrative state persist the password plaintext?</p><div className="choice-row">{['Yes', 'No'].map(choice => <button className="button secondary" key={choice} onClick={() => setAnswer(choice)}>{choice}</button>)}</div>{answer && <p className={'feedback ' + ((answer === 'Yes') === (mode === 'sensitive') ? 'good' : 'wrong')}>{mode === 'sensitive' ? 'Sensitive marks redact normal output but the managed password is still persisted.' : 'The ephemeral value is omitted; a null write-only field is expected. The real lab also scans actual state, plan, and retained files.'}</p>}</div>;
}

function Locks() {
  const [owner, setOwner] = useState<string | null>(null);
  const [message, setMessage] = useState('No lock exists. Start run A, then try run B.');
  function acquire(run: string) { if (owner) setMessage(`Run ${run}: Error acquiring the state lock. Run ${owner} owns key.tflock; wait for it to finish.`); else { setOwner(run); setMessage(`Run ${run} acquired key.tflock using an S3 conditional write.`); } }
  return <div><div className="lock-diagram"><div className={owner === 'A' ? 'lock-owner' : ''}>Run A</div><span>→</span><div className="lock-object">{owner ? '🔒' : '○'} key.tflock</div><span>←</span><div className={owner === 'B' ? 'lock-owner' : ''}>Run B</div></div><div className="choice-row"><button className="button secondary" onClick={() => acquire('A')}>Start run A</button><button className="button secondary" onClick={() => acquire('B')}>Start run B</button><button className="button quiet" onClick={() => { setOwner(null); setMessage('The owning run finished and deleted its lock. A waiting run can now acquire it.'); }}>Finish owning run</button></div><p className="simulation-output" role="status">{message}</p><p className="muted small">Simulation only. Never force-unlock a live operation just to make another run proceed.</p></div>;
}

function LogTriage() {
  const [scope, setScope] = useState('provider');
  const logs = [{ scope: 'core', level: 'TRACE', message: 'graph walk: visiting aws_ssm_parameter.metadata' }, { scope: 'provider', level: 'DEBUG', message: 'SSM PutParameter: request started' }, { scope: 'provider', level: 'ERROR', message: 'AccessDeniedException: ssm:PutParameter is not allowed by the selected role' }, { scope: 'core', level: 'TRACE', message: 'graph walk: resource operation failed' }];
  return <div><label>Log scope<select value={scope} onChange={e => setScope(e.target.value)}><option value="provider">Provider only</option><option value="core">Core only</option><option value="all">All components</option></select></label><pre>{logs.filter(item => scope === 'all' || item.scope === scope).map(item => `[${item.level}] ${item.scope}: ${item.message}`).join('\n')}</pre><p className="feedback good">TF_LOG_PROVIDER isolates provider messages. An AccessDenied response is a permissions failure, not a reason to delete state. Real debug logs can contain secrets; retain them privately.</p></div>;
}

function Governance() {
  const [framework, setFramework] = useState('Sentinel');
  const [level, setLevel] = useState('advisory');
  const [override, setOverride] = useState(false);
  const [mode, setMode] = useState('remote');
  const [trigger, setTrigger] = useState('CLI');
  const [speculative, setSpeculative] = useState(false);
  const [simulation, setSimulation] = useState('Choose how to start and execute a simulated run.');
  const levels = framework === 'Sentinel' ? ['advisory', 'soft-mandatory', 'hard-mandatory'] : ['advisory', 'mandatory'];
  return <div><div className="notice">Local simulation — no HCP account or API calls.</div><div className="org-tree"><div>Organization</div><span>↓</span><div>Project: tf-004-refresher</div><span>↓</span><div>Workspace: aws-hcp-lab</div></div><div className="field-grid"><label>Policy framework<select value={framework} onChange={e => { setFramework(e.target.value); setLevel('advisory'); }}><option>Sentinel</option><option>OPA</option></select></label><label>Enforcement<select value={level} onChange={e => setLevel(e.target.value)}>{levels.map(item => <option key={item}>{item}</option>)}</select></label></div><label className="inline-check"><input type="checkbox" checked={override} onChange={e => setOverride(e.target.checked)} />Authorized override is configured and available</label><p className="simulation-output">{level === 'advisory' ? 'A failed policy reports its result and allows the run to continue.' : override ? 'A failed policy stops the run until an authorized user explicitly overrides it under the applicable policy-set settings.' : 'A failed policy blocks the run. Correct the configuration or review permitted override settings.'}</p><div className="field-grid"><label>Workflow trigger<select value={trigger} onChange={e => setTrigger(e.target.value)}><option>CLI</option><option>VCS</option><option>API</option></select></label><label>Execution mode<select value={mode} onChange={e => setMode(e.target.value)}><option>remote</option><option>local</option><option>agent</option></select></label></div><label className="inline-check"><input type="checkbox" checked={speculative} onChange={e => setSpeculative(e.target.checked)} />Speculative preview only</label><button className="button secondary" onClick={() => setSimulation(`${trigger}-driven request → plan executed ${mode === 'remote' ? 'in the hosted environment' : mode === 'agent' ? 'by a connected agent' : 'on the local machine'} → ${speculative ? 'preview complete; no apply and no downstream apply trigger' : 'approved apply → dependent workspace can be queued by a configured run trigger'}.`)}>Simulate workflow</button><p className="simulation-output" role="status">{simulation}</p><p className="small muted">Projects group workspaces. Variable sets can share scoped values; run triggers connect successful applies. Trigger and execution mode describe different parts of the workflow.</p></div>;
}

export default function Exercises({ exercises }: { exercises: Exercise[] }) {
  return <div className="exercise-stack">{exercises.map(exercise => <section className="panel exercise" key={exercise.id}>
    <div className="eyebrow">INTERACTIVE EXERCISE</div><h3>{exercise.title}</h3><p className="muted">{exercise.description}</p>
    {exercise.id === 'constraint-solver' ? <Constraints /> : exercise.id === 'evaluation-order' ? <Evaluation /> : exercise.id === 'state-leak-inspector' ? <StateInspector /> : exercise.id === 'lock-contention' ? <Locks /> : exercise.id === 'log-triage' ? <LogTriage /> : exercise.id === 'governance-sandbox' ? <><Governance /><Scenarios exercise={exercise} /></> : <Scenarios exercise={exercise} />}
  </section>)}</div>;
}
