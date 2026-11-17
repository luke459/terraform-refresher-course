import { lazy, Suspense, useState } from 'react';
import { Link } from 'react-router-dom';
import casebook from '../../../curriculum/troubleshooting/scenarios.json';

const Method = lazy(() => import('../../../curriculum/troubleshooting/lesson.mdx'));
const Workshop = lazy(() => import('../../../curriculum/troubleshooting/workshop.mdx'));
const steps = ['Orient', 'Reproduce', 'Classify', 'Isolate', 'Repair', 'Prove'];

export default function Troubleshooting() {
  const [tab, setTab] = useState('method');
  return <>
    <div className="page-heading"><div><div className="eyebrow">PRACTICAL SUPPLEMENT</div><h1>Debugging & problem solving</h1><p className="lead">Investigate an existing Terraform repository and prove a focused repair.</p></div><span className="badge purple">60–90 min</span></div>
    <ol className="debug-method" aria-label="Debugging method">{steps.map((step, index) => <li key={step}><span>{index + 1}</span>{step}</li>)}</ol>
    <div className="tab-row large">{[['method', 'The method'], ['cases', 'Diagnostic casebook'], ['workshop', 'Repository workshop']].map(([id, label]) => <button key={id} className={tab === id ? 'active' : ''} aria-pressed={tab === id} onClick={() => setTab(id)}>{label}</button>)}</div>
    {tab === 'cases' ? <Casebook /> : <div className="lesson-layout debug-layout"><article className="panel lesson-prose"><Suspense fallback={<p role="status">Loading the troubleshooting guide…</p>}>{tab === 'method' ? <Method /> : <Workshop />}</Suspense></article><aside className="lesson-aside"><section className="panel"><div className="eyebrow">INVESTIGATION HABITS</div><h3>Keep the evidence together</h3><ul><li>Record the exact root, versions and input context.</li><li>Read the first causal diagnostic.</li><li>Test one hypothesis at a time.</li><li>Rerun the original failing check.</li><li>Review the resulting plan and account for partial success.</li></ul></section><section className="panel"><h3>Practice locally</h3><p>The workshop uses Terraform’s built-in local resource. It requires no AWS credentials and creates no cloud resources.</p><button className="button secondary full" onClick={() => setTab(tab === 'workshop' ? 'cases' : 'workshop')}>{tab === 'workshop' ? 'Try diagnostic cases' : 'Open repository workshop'}</button></section><section className="panel"><h3>Related course topics</h3><p><Link className="text-link" to="/domain/03">Workflow and command flags →</Link></p><p><Link className="text-link" to="/domain/06">State, drift and locking →</Link></p><Link className="text-link" to="/domain/07">Import and provider logging →</Link></section></aside></div>}
  </>;
}

function Casebook() {
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Record<string, string>>>({});
  const [reviewed, setReviewed] = useState<Record<string, boolean>>({});
  const current = casebook[index];
  const chosen = answers[current.id] || {};
  const complete = current.questions.every(question => chosen[question.id] !== undefined);
  const correct = current.questions.every(question => chosen[question.id] === question.correct);
  return <section className="panel debug-casebook">
    <div className="section-heading"><div><div className="eyebrow">SEVEN REPOSITORY INCIDENTS</div><h2>Choose evidence before a fix</h2><p className="muted">Identify the stage, choose a useful experiment, then decide what would prove the repair.</p></div><span className="badge">Case {index + 1} / {casebook.length}</span></div>
    <div className="debug-case-select"><label htmlFor="diagnostic-case">Diagnostic case</label><select id="diagnostic-case" value={index} onChange={event => setIndex(Number(event.target.value))}>{casebook.map((item, i) => <option key={item.id} value={i}>{i + 1}. {item.title}</option>)}</select></div>
    <h3>{current.title}</h3><p>{current.brief}</p><pre aria-label="Reported diagnostic">{current.diagnostic}</pre>
    {current.questions.map((question, i) => <fieldset className="debug-question" key={current.id + question.id}><legend>{i + 1}. {question.label}</legend><div className="answer-options">{question.options.map(option => <label className={'answer-option ' + (chosen[question.id] === option.id ? 'selected' : '')} key={option.id}><input type="radio" name={current.id + question.id} checked={chosen[question.id] === option.id} onChange={() => { setAnswers({ ...answers, [current.id]: { ...chosen, [question.id]: option.id } }); setReviewed({ ...reviewed, [current.id]: false }); }} /><span>{option.label}</span></label>)}</div>{reviewed[current.id] && <div className={'answer-feedback ' + (chosen[question.id] === question.correct ? 'good' : 'wrong')}><p><strong>{chosen[question.id] === question.correct ? 'Correct. ' : 'Reconsider. '}</strong>{question.options.find(option => option.id === chosen[question.id])?.reason}</p>{chosen[question.id] !== question.correct && <p><strong>Better next step: </strong>{question.options.find(option => option.id === question.correct)?.reason}</p>}</div>}</fieldset>)}
    <div className="choice-row"><button className="button primary" disabled={!complete} onClick={() => setReviewed({ ...reviewed, [current.id]: true })}>Check investigation</button><button className="button secondary" disabled={index === casebook.length - 1} onClick={() => setIndex(index + 1)}>Next case →</button></div>
    {reviewed[current.id] && <p role="status" className={'feedback ' + (correct ? 'good' : 'wrong')}>{correct ? 'Investigation verified. You matched the failure stage, a useful experiment, and the proof of repair.' : 'Review this investigation. Use the evidence and explanations to refine your next step.'}</p>}
  </section>;
}
