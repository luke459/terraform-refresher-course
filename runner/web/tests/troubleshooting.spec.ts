import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';

const cases=JSON.parse(readFileSync(new URL('../../../curriculum/troubleshooting/scenarios.json',import.meta.url),'utf8'));

test('debugging guide and repository workshop are reachable without AWS',async({page})=>{
  const errors:string[]=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Debugging & problem solving'}).click();
  await expect(page).toHaveURL(/\/troubleshooting$/);
  await expect(page.getByRole('heading',{name:'Debugging & problem solving',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'A repeatable debugging method',exact:true})).toBeVisible();
  await expect(page.getByRole('list',{name:'Debugging method'})).toContainText('Reproduce');
  await page.getByRole('button',{name:'Repository workshop',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Investigate an inherited repository',exact:true})).toBeVisible();
  await expect(page.locator('.lesson-prose')).toContainText('make check-troubleshooting');
  await expect(page.locator('.lesson-prose')).toContainText('requires no AWS access');
  await page.reload();
  await expect(page.getByRole('heading',{name:'A repeatable debugging method',exact:true})).toBeVisible();
  expect(errors).toEqual([]);
});

test('every diagnostic case gives feedback and supports keyboard choices',async({page})=>{
  await page.goto('/troubleshooting');
  await page.getByRole('button',{name:'Diagnostic casebook',exact:true}).click();
  await expect(page.getByRole('button',{name:'Check investigation'})).toBeDisabled();
  for(const [index,incident] of cases.entries()){
    await page.getByLabel('Diagnostic case',{exact:true}).selectOption(String(index));
    await expect(page.getByRole('heading',{name:incident.title,exact:true})).toBeVisible();
    await expect(page.getByLabel('Reported diagnostic')).toContainText(incident.diagnostic);
    for(const [qindex,question] of incident.questions.entries()){
      const option=question.options.find((option:{id:string})=>option.id===question.correct);
      const group=page.getByRole('group',{name:`${qindex+1}. ${question.label}`,exact:true});
      const radio=group.getByRole('radio',{name:option.label,exact:true});
      await radio.focus();await page.keyboard.press('Space');
      await expect(radio).toBeChecked();
    }
    await page.getByRole('button',{name:'Check investigation',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('You have got it.');
  }
  await page.getByLabel('Diagnostic case',{exact:true}).selectOption('0');
  await page.getByRole('radio',{name:'Provider API execution',exact:true}).check();
  await page.getByRole('button',{name:'Check investigation',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Not quite yet.');
  await expect(page.getByText('No remote API response appears in this diagnostic.',{exact:false})).toBeVisible();
});

test('debugging supplement fits a mobile viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/troubleshooting');
  await expect(page.getByRole('heading',{name:'A repeatable debugging method',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.getByRole('button',{name:'Diagnostic casebook',exact:true}).click();
  await expect(page.getByLabel('Diagnostic case',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
