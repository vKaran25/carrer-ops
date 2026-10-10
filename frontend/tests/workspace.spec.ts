import { test, expect, type Page } from '@playwright/test';

async function fixtures(page:Page,configured=true){
  const fact={id:'fixture-fact',text:'Built Java payment APIs.',category:'project',evidence:'Built Java payment APIs.'};
  let profile:Record<string,unknown>|null={filename:'fictional-fixture.tex',raw_resume_text:fact.text,latex_source:'fixture source',structured_facts:{facts:[fact]},updated_at:'2026-10-09T10:00:00Z'};
  const job={id:1,title:'Java backend engineer — fictional fixture',company:'Fictional Test Co',location:'Remote',url:'https://example.org/fixture',source:'ats',description:'Fictional test role: Java payment APIs.',description_snippet:'Fictional test role: Java payment APIs.',fit_score:72,explanation:'Matches your stored Java project. Company tier unknown; no tier match claimed.',status:'found',application:{id:1,status:'found',applied_at:null as string|null,outcome:null as string|null,draft:null as unknown,critique:null as unknown,tailored_cover_letter:null as string|null,curated_resume:null as unknown}};
  const calls:{path:string;method:string;body:string|null}[]=[];
  let learning=false;
  let sources=[{company:'Fictional Test Co',url:'https://example.org/careers',enabled:true,provider:'static',industry:null,company_tier:null}];
  await page.route('**/api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname.replace('/api',''),method=request.method();
    calls.push({path,method,body:request.postData()});
    let result:unknown;
    if(path==='/bootstrap')result={model_configured:configured,model:configured?'fixture/model:free':null,free_models_only:true,resume:profile?{filename:'fictional-fixture.tex',fact_count:1}:null,counts:{found:job.status==='found'?1:0,tailored:job.status==='tailored'?1:0,applied:job.status==='applied'?1:0,interviewing:job.status==='interviewing'?1:0,resolved:job.status==='resolved'?1:0},source_count:1,pdf_compiler_available:true};
    else if(path==='/jobs')result=[job];
    else if(path==='/jobs/1')result=job;
    else if(path==='/search')result={jobs:[job],relaxation_note:'Some preferences are unknown; hard filters preserved.',warnings:[],query_spec:{hard_filters:{tech_stack_keywords:['java']},soft_preferences:[]}};
    else if(path==='/jobs/1/tailor'){job.application.draft={bullets:[{text:fact.text,fact_ids:[fact.id]}],cover_letter_claims:[{text:fact.text,fact_ids:[fact.id]}]};job.application.critique={passed:true,checks:[]};job.application.tailored_cover_letter= fact.text;job.application.status=job.status='tailored';result={draft:job.application.draft,critique:job.application.critique};}
    else if(path==='/jobs/1/curate'){job.application.curated_resume={artifact_id:'a'.repeat(32),layout_note:'New clean layout from stored facts; original PDF/Word formatting is not preserved',edit_count:1,pdf_url:'/api/artifacts/'+ 'a'.repeat(32)+'/resume.pdf',tex_url:'/api/artifacts/'+ 'a'.repeat(32)+'/resume.tex'};result=job.application.curated_resume;}
    else if(path==='/jobs/1/research')result={company:job.company,sufficient_information:false,rounds:[],difficulty_note:'Not enough public information found',prep_tips:[],sources:[],cached:false};
    else if(path==='/jobs/1/mark-applied'){expect(request.postDataJSON()).toEqual({explicit_action:true});job.application.status=job.status='applied';job.application.applied_at='2026-10-09T10:00:00Z';result=job.application;}
    else if(path==='/jobs/1/status'){const data=request.postDataJSON();job.application.status=job.status=data.status;job.application.outcome=data.outcome;result=job.application;}
    else if(path==='/resume'&&method==='POST'){expect(request.postData()).toContain('fictional-upload.txt');result=profile;}
    else if(path==='/resume'&&method==='DELETE'){profile=null;result={removed:true};}
    else if(path==='/resume')result=profile;
    else if(path==='/memory')result=[];
    else if(path.startsWith('/personalization')){if(path==='/personalization/consent')learning=request.postDataJSON().enabled;result={active:false,enabled:learning,outcome_count:0,minimum_outcomes:6,weights:{},reason:learning?'Cold start: ranking uses Layer 1 only':'Local learning is off'};}
    else if(path==='/sources'&&method==='PUT'){sources=request.postDataJSON();result=sources;}
    else if(path==='/sources')result=sources;
    else if(path==='/free-models')result=[{id:'fixture/model:free',name:'Fictional test model'}];
    else result={};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(result)});
  });
  return {calls,job};
}

test('initial page clearly explains missing model and has no invented job cards',async({page})=>{
  await fixtures(page,false);await page.goto('/');
  await expect(page.getByRole('heading',{name:'Find your next role.'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Keywords',exact:true})).toHaveClass(/selected/);
  await expect(page.getByText('Keyword search is ready to use.')).toBeVisible();
  await expect(page.locator('.job-card')).toHaveCount(0);
});

test('search renders grounded explanation and opens job details without automatic tailoring',async({page})=>{
  const state=await fixtures(page);await page.goto('/');
  await page.getByLabel('Describe the jobs you want').fill('Java backend jobs');await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.getByRole('region',{name:'Job details'})).toBeVisible();
  await expect(page.getByText('Company tier unknown',{exact:false})).toBeVisible();
  expect(state.calls.some(c=>c.path.endsWith('/tailor'))).toBeFalsy();
  expect(state.calls.some(c=>c.path.endsWith('/mark-applied'))).toBeFalsy();
  await page.screenshot({path:'test-results/search-results-desktop.png',fullPage:true});
});

test('tailoring is single job on demand and applied changes only after the explicit button',async({page})=>{
  const state=await fixtures(page);await page.goto('/tracker');
  await page.locator('.tracker-card').click();await page.getByRole('button',{name:'Tailor draft',exact:true}).click();
  await expect(page.getByText('Facts verified',{exact:true})).toBeVisible();
  expect(state.job.status).toBe('tailored');expect(state.calls.filter(c=>c.path.endsWith('/tailor'))).toHaveLength(1);
  await page.getByRole('button',{name:'Mark as applied',exact:true}).click();
  await expect(page.getByText('Applied by your action')).toBeVisible();expect(state.job.status).toBe('applied');
  await page.reload();await expect(page.getByRole('region',{name:'Applied applications'}).locator('.tracker-card')).toHaveCount(1);
});

test('board and list views toggle and preference survives reload',async({page})=>{
  await fixtures(page);await page.goto('/tracker');await page.getByRole('button',{name:'List',exact:true}).click();await expect(page.locator('table')).toBeVisible();await page.reload();await expect(page.locator('table')).toBeVisible();await page.getByRole('button',{name:'Board',exact:true}).click();await expect(page.getByRole('region',{name:'Application pipeline'})).toBeVisible();
});

test('manual interview and offer outcomes update the tracker',async({page})=>{
  const state=await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();await page.getByRole('button',{name:'Mark as applied',exact:true}).click();
  await expect(page.getByLabel('Pipeline status')).toBeVisible();await page.getByLabel('Pipeline status').selectOption('interviewing');await page.getByRole('combobox',{name:'Outcome',exact:true}).selectOption('interview');await page.getByRole('button',{name:'Update tracker',exact:true}).click();
  await expect(page.getByRole('region',{name:'Interviewing applications'}).locator('.tracker-card')).toHaveCount(1);
  await page.getByLabel('Pipeline status').selectOption('resolved');await page.getByRole('combobox',{name:'Outcome',exact:true}).selectOption('offer');await page.getByRole('button',{name:'Update tracker',exact:true}).click();
  await expect(page.getByRole('region',{name:'Resolved applications'}).locator('.tracker-card')).toHaveCount(1);expect(state.job.application.outcome).toBe('offer');
});

test('obscure company research shows insufficient information without invented rounds',async({page})=>{
  await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();await page.getByRole('button',{name:'Research company',exact:true}).click();await expect(page.getByText('Not enough public information found',{exact:false})).toBeVisible();await expect(page.locator('.research-round')).toHaveCount(0);
});

test('curation displays the honest new-layout note and PDF and tex links',async({page})=>{
  await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();await page.getByRole('button',{name:'Curate resume',exact:true}).click();await expect(page.getByText('New clean layout from stored facts',{exact:false})).toBeVisible();await expect(page.getByRole('link',{name:'Preview PDF',exact:false})).toHaveAttribute('href',/resume.pdf$/);await expect(page.getByRole('link',{name:'Download .tex'})).toHaveAttribute('href',/resume.tex$/);
});

test('resume upload displays exact extracted facts and source',async({page})=>{
  await fixtures(page);await page.goto('/resume');await page.getByLabel('Upload resume').setInputFiles({name:'fictional-upload.txt',mimeType:'text/plain',buffer:Buffer.from('Built Java payment APIs.')});await expect(page.locator('.fact').getByText('Built Java payment APIs.',{exact:true})).toBeVisible();await expect(page.getByText('fictional-fixture.tex',{exact:true})).toBeVisible();
});

test('sources are saved with only user-provided metadata and free model catalog is visible',async({page})=>{
  const state=await fixtures(page);await page.goto('/settings');await page.getByText('Add a company career page',{exact:true}).click();await page.getByLabel('Company name',{exact:true}).fill('Another Fictional Co');await page.getByLabel('Public career page URL').fill('https://example.net/careers');await page.getByRole('button',{name:'Add source',exact:true}).click();await page.getByRole('button',{name:'Save source changes'}).click();await expect(page.getByText('Sources saved')).toBeVisible();
  const body=JSON.parse(state.calls.find(c=>c.path==='/sources'&&c.method==='PUT')!.body!);expect(body[1].company_tier).toBeNull();expect(body[1].industry).toBeNull();await page.getByRole('button',{name:'Check current free tool models'}).click();await expect(page.getByText('fixture/model:free',{exact:true})).toBeVisible();
});

test('mobile pages fit the viewport and navigation stays usable',async({page})=>{
  await page.setViewportSize({width:390,height:844});await fixtures(page);
  for(const path of ['/','/tracker','/resume','/settings']){await page.goto(path);await expect(page.locator('h1')).toBeVisible();await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.screenshot({path:'test-results/mobile-'+(path==='/'?'search':path.slice(1))+'.png',fullPage:true});}
});

test('API failure is shown honestly without fabricated fallback content',async({page})=>{
  await fixtures(page);await page.route('**/api/search',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Free model temporarily unavailable'})}));await page.goto('/');await page.getByLabel('Describe the jobs you want').fill('Java jobs');await page.getByRole('button',{name:'Find jobs',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Free model temporarily unavailable');await expect(page.locator('.job-card')).toHaveCount(0);
});


test('local learning stays off until explicit opt-in and can be revoked',async({page})=>{
  const state=await fixtures(page);await page.goto('/settings');await expect(page.getByRole('button',{name:'Recalibrate now'})).toBeDisabled();
  await page.getByRole('button',{name:'Enable local learning',exact:true}).click();await expect(page.getByRole('button',{name:'Turn off local learning',exact:true})).toBeVisible();
  expect(state.calls.find(c=>c.path==='/personalization/consent')?.body).toBe(JSON.stringify({enabled:true}));
  await page.getByRole('button',{name:'Turn off local learning',exact:true}).click();await expect(page.getByRole('button',{name:'Recalibrate now'})).toBeDisabled();
});

test('mobile search results and detail panel fit the viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});await fixtures(page);await page.goto('/');await page.getByLabel('Describe the jobs you want').fill('Java backend jobs');await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.getByRole('region',{name:'Job details'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.screenshot({path:'test-results/mobile-search-results.png',fullPage:true});
});
