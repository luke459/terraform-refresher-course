import {expect,test} from '@playwright/test';
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';

let cleanupAttemptId='';

test.afterEach(async({request})=>{
  test.setTimeout(180000);
  if(!cleanupAttemptId)return;
  const headers={'X-Tfprep':'1'};
  async function waitJob(id:string){
    await expect.poll(async()=> (await (await request.get('/api/jobs/'+id)).json()).status,{timeout:120000,intervals:[300]}).not.toMatch(/^(queued|running)$/);
  }
  const detail=await (await request.get('/api/attempts/'+cleanupAttemptId)).json();
  if(detail.status==='complete')return;
  for(const job of detail.jobs.filter((job:any)=>['queued','running'].includes(job.status))){
    await request.post('/api/jobs/'+job.id+'/cancel',{headers});await waitJob(job.id);
  }
  for(const endpoint of ['run','reaper?execute=true','teardown-check']){
    const result=await request.post(`/api/attempts/${cleanupAttemptId}/${endpoint}`,{headers,data:endpoint==='run'?{operation:'destroy'}:undefined});
    if(result.ok()){const job=await result.json();await waitJob(job.id);}
  }
  const final=await (await request.get('/api/attempts/'+cleanupAttemptId)).json();
  expect(final.resources.every((resource:any)=>resource.status==='absent')).toBeTruthy();
});

test('profile onboarding, workspace editing, live AWS grade, and verified cleanup',async({page})=>{
  const profile=process.env.TFPREP_AWS_PROFILE;
  if(!profile)throw new Error('Set TFPREP_AWS_PROFILE explicitly for the live browser test.');
  const root=fileURLToPath(new URL('../../../',import.meta.url));
  let attemptId='';
  async function waitJob(id:string){
    await expect.poll(async()=> (await (await page.request.get('/api/jobs/'+id)).json()).status,{timeout:180000,intervals:[300]}).not.toMatch(/^(queued|running)$/);
    return (await (await page.request.get('/api/jobs/'+id)).json());
  }
  async function command(text:string){
    const response=page.waitForResponse(r=>r.url().endsWith(`/attempts/${attemptId}/terminal`)&&r.request().method()==='POST');
    const input=page.getByRole('textbox',{name:'Terminal command',exact:true});
    await input.fill(text);await input.press('Enter');
    let result=await (await response).json();
    if(result.confirmation_required){
      const confirmed=page.waitForResponse(r=>r.url().endsWith(`/attempts/${attemptId}/terminal`)&&r.request().method()==='POST');
      await input.fill('yes');await input.press('Enter');result=await (await confirmed).json();
    }
    expect((await waitJob(result.job.id)).status).toBe('succeeded');
    await expect(page.locator('.terminal-exit').last()).toContainText('succeeded');
  }
  try{
    await page.goto('/settings');
    await page.getByLabel('AWS CLI profile name').fill(profile);
    await page.getByLabel('Primary lab region').selectOption('eu-west-2');
    await page.getByRole('button',{name:'Test connection & continue',exact:true}).click();
    await expect(page.getByText(/Account \d{12}/)).toBeVisible({timeout:30000});
    await page.goto('/lab/08');
    const start=page.getByRole('button',{name:'Start lab attempt',exact:true});
    const response=page.waitForResponse(r=>r.url().endsWith('/api/attempts')&&r.request().method()==='POST');
    if(await start.isVisible())await start.click();
    else await page.getByRole('button',{name:'New attempt',exact:true}).click();
    attemptId=(await (await response).json()).id;
    await page.getByLabel('Edit main.tf').fill(readFileSync(root+'curriculum/domain-08/solution/main.tf','utf8'));
    await page.getByRole('button',{name:'Save changes',exact:true}).click();
    await expect(page.getByText('Configuration saved. Review a new plan before applying.')).toBeVisible();
    for(const text of ['terraform init','terraform fmt','terraform validate','terraform plan -out=tfplan -detailed-exitcode','terraform apply tfplan','terraform plan -out=tfplan -detailed-exitcode'])await command(text);
    await command('lab grade');
    await expect(page.getByText('50% apply verified',{exact:true})).toBeVisible();
    await page.reload();
    await expect(page.getByText('50% apply verified',{exact:true})).toBeVisible();
    await command('terraform destroy');
    await command('lab check-cleanup');
    await expect(page.getByText('100% complete',{exact:true})).toBeVisible();
    const detail=await (await page.request.get('/api/attempts/'+attemptId)).json();
    expect(detail.resources.every((r:any)=>r.status==='absent')).toBeTruthy();
    mkdirSync(root+'docs/evidence',{recursive:true});
    writeFileSync(root+'docs/evidence/browser-live.json',JSON.stringify({passed:true,account:detail.account,region:detail.region,attempt_id:attemptId,domain_id:'08',status:detail.status,jobs:detail.jobs.map(({id,operation,status,config_hash,plan_hash,result}:any)=>({id,operation,status,config_hash,plan_hash,result}))},null,2)+'\n');
    await page.screenshot({path:root+'docs/evidence/browser-live.png',fullPage:true});
  }finally{
    cleanupAttemptId=attemptId;
  }
});
