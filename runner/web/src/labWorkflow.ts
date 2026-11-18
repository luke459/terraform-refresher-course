export type LabJob = {
  id: string; operation: string; status: string; log?: string; result?: any;
  exit_code?: number | null; config_hash?: string; params?: string | Record<string, any>; created?: number;
};

export function labWorkflow(attempt: any) {
  const jobs: LabJob[] = attempt?.jobs || []; // API returns newest first.
  const latest = (operation: string) => jobs.find(job => job.operation === operation);
  const succeeded = (operation: string) => latest(operation)?.status === 'succeeded';
  const current = (job?: LabJob) => !job?.config_hash || !attempt?.current_hash || job.config_hash === attempt.current_hash;
  const complete = attempt?.status === 'complete';
  const graded = complete || Boolean(attempt?.verified_hash && ['apply_verified', 'cleanup_pending'].includes(attempt.status));
  const applied = graded || (succeeded('apply') && current(latest('apply')));
  const configured = applied || (succeeded('validate') && current(latest('validate')));
  const applyIndex = jobs.findIndex(job => job.operation === 'apply' && job.status === 'succeeded');
  const destroyIndex = jobs.findIndex(job => job.operation === 'destroy' && job.status === 'succeeded');
  const destroyed = succeeded('destroy') && (applyIndex < 0 || destroyIndex < applyIndex);
  const noChangePlan = jobs.some((job, index) => job.operation === 'plan' && job.status === 'succeeded'
    && job.exit_code === 0 && current(job) && applyIndex >= 0 && index < applyIndex
    && (() => {const params = typeof job.params === 'string' ? JSON.parse(job.params) : job.params;
      return !params?.refresh_only && (!params?.terminal_args || params.detailed_exitcode);})());
  const stages = [
    {title: 'Prepare configuration', description: 'Edit, initialize, format and validate.', done: configured},
    {title: 'Plan & apply', description: 'Review the plan, then apply it.', done: applied},
    {title: 'Grade the lab', description: 'No-change plan + passing checks → 50%.', done: graded},
    {title: 'Clean up & finish', description: 'Destroy + verified absence → 100%.', done: complete},
  ];
  let next = {label: 'Initialize workspace', operation: 'init', endpoint: 'run', hint: 'Read the challenge and edit the starter. Initialize before running Terraform checks.'};
  if (complete) next = {label: 'Lab complete', operation: '', endpoint: '', hint: 'You have passed the lab checks and cleaned up. Your completion is saved.'};
  else if (destroyed) next = {label: 'Verify cleanup', operation: '', endpoint: 'teardown-check', hint: graded ? 'Destroy succeeded. Verify that the owned resources are absent to finish.' : 'Check that the resources are gone. Because this attempt was destroyed before grading, you will need a new attempt for completion credit.'};
  else if (graded) next = {label: 'Destroy lab resources', operation: 'destroy', endpoint: 'run', hint: 'Your checks passed. Next, destroy the resources and verify cleanup to finish the lab.'};
  else if (applied && noChangePlan) next = {label: 'Grade lab · 50%', operation: '', endpoint: 'validate', hint: 'The plan has no changes. You are ready to grade the lab.'};
  else if (applied) next = {label: 'Plan again (check no changes)', operation: 'plan', endpoint: 'run', hint: 'Apply succeeded. Run Plan again; it must show no changes before grading.'};
  else if (configured && succeeded('plan') && current(latest('plan')) && (() => {const params = latest('plan')?.params; const parsed = typeof params === 'string' ? JSON.parse(params) : params; return !parsed?.terminal_args || parsed.save_plan;})()) next = {label: 'Apply saved plan', operation: 'apply', endpoint: 'run', hint: 'Review the plan output, then apply the exact saved plan.'};
  else if (configured) next = {label: 'Plan changes', operation: 'plan', endpoint: 'run', hint: 'Your configuration is valid. Run Plan and read what Terraform wants to change.'};
  else if (succeeded('init') && succeeded('fmt')) next = {label: 'Validate configuration', operation: 'validate', endpoint: 'run', hint: 'Check the configuration now. If an error appears, fix it before planning.'};
  else if (succeeded('init')) next = {label: 'Format configuration', operation: 'fmt', endpoint: 'run', hint: 'Format the edited files, then validate the configuration.'};
  return {stages, next, complete, graded, applied, destroyed, latest, jobs};
}
