import { test, expect, type Page } from '@playwright/test';

async function fixtures(page:Page,configured=true,withResume=true,withTracker=true){
  const fact={id:'fixture-fact',text:'Built Java payment APIs.',category:'project',evidence:'Built Java payment APIs.'};
  let profile:Record<string,unknown>|null={filename:'fictional-fixture.docx',raw_resume_text:fact.text,latex_source:'fixture source',structured_facts:{facts:[fact]},updated_at:'2026-10-09T10:00:00Z'};
  if(!withResume)profile=null;
  const job={id:1,title:'Java backend engineer — fictional fixture',company:'Fictional Test Co',location:'Remote',url:'https://example.org/fixture',source:'ats',description:'Fictional test role: Java payment APIs.',description_snippet:'Fictional test role: Java payment APIs.',fit_score:72,explanation:'Matches your stored Java project. Company tier unknown; no tier match claimed.',status:'interested',application:{id:1,status:'interested',applied_at:null as string|null,outcome:null as string|null,draft:null as unknown,critique:null as unknown,tailored_cover_letter:null as string|null,curated_resume:null as unknown}};
  let tracked=withTracker;
  if(!tracked)job.status=job.application.status='discovered';
  const response={jobs:[job],relaxation_note:'Some preferences are unknown; hard filters preserved.',warnings:[] as string[],query_spec:{hard_filters:{tech_stack_keywords:['java']},soft_preferences:[]}};
  let turns:{id:number;query:string;mode:string;resume_filename:string|null;resume_changed:boolean;created_at:string;result:typeof response}[]=[];
  const calls:{path:string;method:string;body:string|null}[]=[];
  let learning=false;
  let memory={active:false,last_query:'',resume_changed:false,effective_filters:['Resume relevance'],preferences:null as {query:string}|null};
  let sources=[{company:'Fictional Test Co',url:'https://example.org/careers',enabled:true,provider:'static',industry:null,company_tier:null}];
  await page.route('**/api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname.replace('/api',''),method=request.method();
    calls.push({path,method,body:request.postData()});
    let result:unknown;
    if(path==='/bootstrap')result={auth_mode:'local',web_search_configured:true,model_configured:configured,model:configured?'fixture/model:free':null,free_models_only:true,resume:profile?{filename:'fictional-fixture.docx',fact_count:1}:null,counts:{interested:job.status==='interested'?1:0,tailored:job.status==='tailored'?1:0,applied:job.status==='applied'?1:0,interviewing:job.status==='interviewing'?1:0,resolved:job.status==='resolved'?1:0},source_count:1,pdf_compiler_available:true};
    else if(path==='/jobs')result=tracked?[job]:[];
    else if(path==='/jobs/1')result=job;
    else if(path==='/chat')result=turns.map(t=>({...t,result:{...t.result,jobs:t.result.jobs.map(j=>({...j,status:job.status,fit_score:t.resume_changed?null:j.fit_score}))}}));
    else if(path==='/search/context'){if(method==='DELETE'){memory.active=false;memory.last_query='';}result=memory;}
    else if(path==='/search/preferences'){memory.preferences=method==='DELETE'?null:{query:request.postDataJSON().query};result=memory;}
    else if(path==='/search/runs')result=[];
    else if(path==='/search'){const data=request.postDataJSON();memory.active=true;memory.last_query=data.query;const turn={id:turns.length+1,query:data.query,mode:data.mode,resume_filename:profile?String(profile.filename):null,resume_changed:false,created_at:'2026-10-11T10:00:00Z',result:{...response,jobs:tracked?[]:[{...job}]}};turns.push(turn);result={id:'fixture-run-'+turn.id,request_key:data.request_key,query:data.query,status:'succeeded',phase:'complete',attempt:1,turn_id:turn.id};}
    else if(path==='/linkedin-search')result={url:'https://www.linkedin.com/jobs/search/?keywords=Java+engineer&location=Pune'};
    else if(path==='/chat/import-job'){const data=request.postDataJSON();Object.assign(job,{title:data.title,company:data.company,description:data.description,url:'https://www.linkedin.com/jobs/view/12345',source:'user_import'});const turn={id:turns.length+1,query:'Import LinkedIn job: '+data.title,mode:'import',resume_filename:String(profile?.filename),resume_changed:false,created_at:'2026-10-11T10:00:00Z',result:{...response,jobs:[{...job}],warnings:['Imported from details you pasted. Check the original listing to confirm it is still open.']}};turns.push(turn);result={...turn.result,turn_id:turn.id};}
    else if(path==='/jobs/1/interest'&&method==='DELETE'){tracked=false;job.status=job.application.status='dismissed';result={removed:true};}
    else if(path==='/jobs/1/interest'){expect(request.postDataJSON().turn_id).toBeGreaterThan(0);tracked=true;job.application.status=job.status='interested';result=job.application;}
    else if(path==='/jobs/1/tailor'){job.application.draft={bullets:[{text:fact.text,fact_ids:[fact.id]}],cover_letter_claims:[{text:fact.text,fact_ids:[fact.id]}]};job.application.critique={passed:true,checks:[]};job.application.tailored_cover_letter= fact.text;job.application.status=job.status='tailored';result={draft:job.application.draft,critique:job.application.critique};}
    else if(path==='/jobs/1/curate'){job.application.curated_resume={artifact_id:'a'.repeat(32),layout_note:'New clean layout from stored facts; original PDF/Word formatting is not preserved',edit_count:1,pdf_url:'/api/artifacts/'+ 'a'.repeat(32)+'/resume.pdf',tex_url:'/api/artifacts/'+ 'a'.repeat(32)+'/resume.tex'};result=job.application.curated_resume;}
    else if(path==='/jobs/1/research')result={company:job.company,sufficient_information:false,rounds:[],difficulty_note:'Not enough public information found',prep_tips:[],sources:[],cached:false};
    else if(path==='/jobs/1/mark-applied'){expect(request.postDataJSON()).toEqual({explicit_action:true});job.application.status=job.status='applied';job.application.applied_at='2026-10-09T10:00:00Z';result=job.application;}
    else if(path==='/jobs/1/status'){const data=request.postDataJSON();job.application.status=job.status=data.status;job.application.outcome=data.outcome;result=job.application;}
    else if(path==='/resume'&&method==='POST'){expect(request.postData()).toContain('fictional-upload.docx');profile={filename:'fictional-upload.docx',raw_resume_text:fact.text,latex_source:null,structured_facts:{facts:[fact]},updated_at:'2026-10-11T10:00:00Z'};turns.forEach(t=>t.resume_changed=true);result=profile;}
    else if(path==='/resume'&&method==='DELETE'){profile=null;turns.forEach(t=>t.resume_changed=true);result={removed:true};}
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
  await expect(page.getByRole('button',{name:'Replace resume',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Remove resume',exact:true})).toBeEnabled();
  await expect(page.getByRole('link',{name:'Check service status',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeEnabled();
  await expect(page.locator('.chat-job')).toHaveCount(0);
});

test('chat search persists jobs and Interested is the only tracker intake',async({page})=>{
  const state=await fixtures(page,true,true,false);await page.goto('/');
  await page.getByLabel('Describe the jobs you want').fill('Java backend jobs');await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.locator('.chat-job')).toHaveCount(1);
  expect(state.job.status).toBe('discovered');
  await expect(page.getByRole('button',{name:'Tailor draft',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Curate resume',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Research company',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Mark as applied',exact:true})).toHaveCount(0);
  await page.locator('.chat-job>summary').click();
  await expect(page.getByText('Job description',{exact:true})).toBeVisible();
  await page.getByText('Why this job matches',{exact:true}).click();
  await expect(page.getByText('Company tier unknown',{exact:false})).toBeVisible();
  expect(JSON.parse(state.calls.find(c=>c.path==='/search')!.body!)).toEqual(expect.objectContaining({query:'Java backend jobs',mode:'resume',limit:15,request_key:expect.any(String)}));
  expect(state.calls.some(c=>c.path.endsWith('/tailor'))).toBeFalsy();
  expect(state.calls.some(c=>c.path.endsWith('/mark-applied'))).toBeFalsy();
  await page.reload();await expect(page.locator('.chat-turn')).toHaveCount(1);
  await page.locator('.chat-job>summary').click();
  await page.screenshot({path:'test-results/chat-results-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Interested',exact:true}).click();
  await expect(page.getByRole('link',{name:'In Interested · Open tracker',exact:false})).toBeVisible();
  expect(state.job.status).toBe('interested');
  expect(state.calls.filter(c=>c.path.endsWith('/interest'))).toHaveLength(1);
  await page.goto('/tracker');
  await expect(page.getByRole('region',{name:'Interested applications'}).locator('.tracker-card')).toHaveCount(1);
  await expect(page.getByRole('region',{name:'Found applications'})).toHaveCount(0);
  await page.screenshot({path:'test-results/search-results-desktop.png',fullPage:true});
});

test('manual Applied works without preparation',async({page})=>{
  const state=await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();
  for(const name of ['Tailor draft','Curate resume','Research company'])await expect(page.getByRole('button',{name,exact:true})).toHaveCount(0);
  expect(state.calls.some(c=>c.path.endsWith('/mark-applied'))).toBeFalsy();
  await page.getByRole('button',{name:'Mark as applied',exact:true}).click();
  await expect(page.getByText('Applied by your action')).toBeVisible();expect(state.job.status).toBe('applied');
  await page.reload();await expect(page.getByRole('region',{name:'Applied applications'}).locator('.tracker-card')).toHaveCount(1);
});

test('board and list views toggle and preference survives reload',async({page})=>{
  await fixtures(page);await page.goto('/tracker');await page.getByRole('button',{name:'List',exact:true}).click();await expect(page.locator('table')).toBeVisible();await page.reload();await expect(page.locator('table')).toBeVisible();await page.getByRole('button',{name:'Board',exact:true}).click();await expect(page.getByRole('region',{name:'Application pipeline'})).toBeVisible();
});

test('manual interview and offer outcomes update the tracker',async({page})=>{
  const state=await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();await page.getByRole('button',{name:'Mark as applied',exact:true}).click();
  await expect(page.getByLabel('Stage')).toBeVisible();await page.getByLabel('Stage').selectOption('interviewing');await page.getByRole('combobox',{name:'Outcome',exact:true}).selectOption('interview');await page.getByRole('button',{name:'Update stage',exact:true}).click();
  await expect(page.getByRole('region',{name:'Interviewing applications'}).locator('.tracker-card')).toHaveCount(1);
  await page.getByLabel('Stage').selectOption('resolved');await page.getByRole('combobox',{name:'Outcome',exact:true}).selectOption('offer');await page.getByRole('button',{name:'Update stage',exact:true}).click();
  await expect(page.getByRole('region',{name:'Resolved applications'}).locator('.tracker-card')).toHaveCount(1);expect(state.job.application.outcome).toBe('offer');
});

test('tracker has no interview research controls',async({page})=>{
  const state=await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();
  await expect(page.getByRole('button',{name:/Research company/})).toHaveCount(0);
  expect(state.calls.some(c=>c.path.endsWith('/research'))).toBeFalsy();
});

test('tracker has no deferred artifact export controls',async({page})=>{
  await fixtures(page);await page.goto('/tracker');await page.locator('.tracker-card').click();
  await expect(page.getByRole('button',{name:'Curate resume',exact:true})).toHaveCount(0);
  await expect(page.getByRole('link',{name:/Preview PDF|Download .tex/})).toHaveCount(0);
});

test('resume upload stays on Search jobs and enables search without a query',async({page})=>{
  const state=await fixtures(page,true,false,false);await page.goto('/');
  await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeDisabled();
  await expect(page.getByRole('link',{name:'Resume & facts',exact:true})).toHaveCount(0);
  await page.getByLabel('Upload resume').setInputFiles({name:'fictional-upload.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:Buffer.from('Built Java payment APIs.')});
  await expect(page.locator('.resume-chip')).toContainText('fictional-upload.docx');
  await page.getByText('Review resume details',{exact:true}).click();await expect(page.locator('.fact').getByText('Built Java payment APIs.',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.locator('.chat-job')).toHaveCount(1);
  expect(JSON.parse(state.calls.find(c=>c.path==='/search')!.body!)).toEqual(expect.objectContaining({query:'',mode:'resume',limit:15,request_key:expect.any(String)}));
  await page.getByRole('button',{name:'Remove resume',exact:true}).click();
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeDisabled();
  await expect(page.locator('.chat-job')).toHaveCount(1);
  await expect(page.getByText('Your resume changed since this search.',{exact:false})).toBeVisible();
  await expect(page.locator('.chat-job .score')).toHaveCount(0);
});

test('failed DOCX extraction keeps Add resume available and displays the error',async({page})=>{
  await fixtures(page,true,false,false);await page.route('**/api/resume',async route=>{
    if(route.request().method()==='POST')await route.fulfill({status:422,contentType:'application/json',body:JSON.stringify({detail:'We couldn’t read your resume details. Please upload the .docx file again to retry.'})});
    else await route.fallback();
  });await page.goto('/');
  await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toBeEnabled();
  await page.getByLabel('Upload resume').setInputFiles({name:'fictional-upload.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:Buffer.from('Mocked upload contents')});
  await expect(page.getByRole('alert')).toContainText('upload the .docx file again to retry');
  await expect(page.locator('.resume-chip')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toBeEnabled();
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeDisabled();
});

test('old resume bookmarks open the resume section on Search jobs',async({page})=>{
  await fixtures(page);await page.goto('/resume');
  await expect(page).toHaveURL('/#resume');
  await expect(page.getByRole('heading',{name:'Find your next role.'})).toBeVisible();
});

test('settings exposes preferences and service status without operator controls',async({page})=>{
  await fixtures(page);await page.goto('/settings');
  await expect(page.getByRole('heading',{name:'Service status'})).toBeVisible();
  await expect(page.getByRole('button',{name:/Add source|Save source changes|Check current free tool models/})).toHaveCount(0);
  await expect(page.getByText('Your data and control',{exact:true})).toBeVisible();
});

test('mobile pages fit the viewport and navigation stays usable',async({page})=>{
  await page.setViewportSize({width:390,height:844});await fixtures(page);
  for(const path of ['/','/tracker','/resume','/settings']){await page.goto(path);await expect(page.locator('h1')).toBeVisible();await expect(page.getByRole('navigation',{name:'Main navigation'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.screenshot({path:'test-results/mobile-'+(path==='/'?'search':path.slice(1))+'.png',fullPage:true});}
});

test('API failure is shown honestly without fabricated fallback content',async({page})=>{
  await fixtures(page,true,true,false);await page.route('**/api/search',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Free model temporarily unavailable'})}));await page.goto('/');await page.getByLabel('Describe the jobs you want').fill('Java jobs');await page.getByRole('button',{name:'Find jobs',exact:true}).click();await expect(page.getByRole('alert')).toHaveText('Free model temporarily unavailable');await expect(page.locator('.chat-job')).toHaveCount(0);
});


test('settings hides deferred learning controls',async({page})=>{
  const state=await fixtures(page);await page.goto('/settings');
  await expect(page.getByRole('checkbox')).toHaveCount(0);
  expect(state.calls.some(c=>c.path.startsWith('/personalization'))).toBeFalsy();
});

test('mobile chat accordion and composer fit the viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});await fixtures(page,true,true,false);await page.goto('/');await page.getByLabel('Describe the jobs you want').fill('Java backend jobs');await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.locator('.chat-job')).toHaveCount(1);await page.locator('.chat-job>summary').click();
  await expect(page.getByRole('button',{name:'Interested',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Interested',exact:true}).scrollIntoViewIfNeeded();
  await expect(page.getByRole('button',{name:'Interested',exact:true})).toBeInViewport();
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeInViewport();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.screenshot({path:'test-results/mobile-chat-results.png',fullPage:true});
});

test('successive chat searches survive reload and Enter submits the optional query',async({page})=>{
  await fixtures(page,true,true,false);await page.goto('/');
  await page.getByLabel('Describe the jobs you want').fill('Java backend jobs');
  await page.getByLabel('Describe the jobs you want').press('Enter');
  await expect(page.locator('.chat-turn')).toHaveCount(1);
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeEnabled();
  await page.getByLabel('Describe the jobs you want').fill('Remote Python jobs');
  await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.locator('.chat-turn')).toHaveCount(2);
  await page.reload();await expect(page.locator('.chat-turn')).toHaveCount(2);
  await expect(page.locator('.user-message').last()).toContainText('Remote Python jobs');
});

test('failed Interested action stays in chat and can be retried safely',async({page})=>{
  const state=await fixtures(page,true,true,false);let attempts=0;
  await page.route('**/api/jobs/1/interest',async route=>{
    if(++attempts===1)await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Could not save this job. Try again.'})});
    else await route.fallback();
  });await page.goto('/');await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.locator('.chat-job')).toHaveCount(1);await page.locator('.chat-job>summary').click();
  await page.getByRole('button',{name:'Interested',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Could not save this job');
  expect(state.job.status).toBe('discovered');
  await page.getByRole('button',{name:'Interested',exact:true}).click();
  await expect(page.getByRole('link',{name:'In Interested · Open tracker',exact:false})).toBeVisible();
  expect(state.job.status).toBe('interested');
});


test('Interested removal requires confirmation, persists and can be restored from chat',async({page})=>{
  const state=await fixtures(page,true,true,false);await page.goto('/');
  await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await page.locator('.chat-job>summary').click();await page.getByRole('button',{name:'Interested',exact:true}).click();
  await page.goto('/tracker');await page.locator('.remove-interest-icon').click();
  const dialog=page.getByRole('alertdialog');await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('Remove this job?');
  await dialog.getByRole('button',{name:'Cancel',exact:true}).click();
  expect(state.calls.filter(c=>c.method==='DELETE')).toHaveLength(0);
  await page.getByRole('button',{name:'List',exact:true}).click();
  await page.locator('.list-remove').click();await dialog.getByRole('button',{name:'Remove job',exact:true}).click();
  await expect(dialog).not.toBeVisible();await expect(page.locator('tbody tr')).toHaveCount(0);
  await page.reload();await expect(page.locator('tbody tr')).toHaveCount(0);
  await page.goto('/');await page.locator('.chat-job>summary').click();
  await page.getByRole('button',{name:'Interested again',exact:true}).click();
  expect(state.job.status).toBe('interested');
  await page.goto('/tracker');await expect(page.locator('tbody tr')).toHaveCount(1);
});

test('resume cross removes the current file and reveals the DOCX upload button',async({page})=>{
  const state=await fixtures(page);await page.goto('/');
  await expect(page.getByRole('button',{name:'Replace resume',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Remove resume',exact:true}).click();
  await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toBeEnabled();
  await expect(page.locator('.resume-chip')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Find jobs',exact:true})).toBeDisabled();
  expect(state.calls.filter(c=>c.path==='/resume'&&c.method==='DELETE')).toHaveLength(1);
  await page.reload();await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toBeVisible();
});

test('non DOCX files show the required format without uploading',async({page})=>{
  const state=await fixtures(page,true,false,false);await page.goto('/');
  await expect(page.getByRole('button',{name:'Add resume (.docx)',exact:true})).toBeEnabled();
  await expect(page.getByLabel('Upload resume')).toHaveAttribute('accept','.docx');
  for(const name of ['resume.pdf','resume.txt','resume.doc','resume.png']){
    await page.getByLabel('Upload resume').setInputFiles({name,mimeType:'application/octet-stream',buffer:Buffer.from('unsupported fixture')});
    await expect(page.getByRole('alert')).toContainText('Upload a .docx file');
  }
  expect(state.calls.filter(c=>c.path==='/resume'&&c.method==='POST')).toHaveLength(0);
});

test('tracker keeps four styled columns and removal dialog stays within mobile viewport',async({page})=>{
  await fixtures(page);await page.goto('/tracker');
  expect(await page.locator('.board').evaluate(e=>getComputedStyle(e).display)).toBe('grid');
  expect(await page.locator('.board').evaluate(e=>getComputedStyle(e).gridTemplateColumns.split(' ').length)).toBe(4);
  await page.screenshot({path:'test-results/tracker-restored-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.locator('.remove-interest-icon').click();
  await expect(page.getByRole('alertdialog')).toBeInViewport();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/tracker-remove-mobile.png',fullPage:true});
});


test('empty location search explains actual coverage and opens source notices',async({page})=>{
  await fixtures(page);
  await page.route('**/api/chat?**',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify([{
    id:1,query:'jobs around Delhi',mode:'resume',resume_filename:'fictional-fixture.docx',resume_changed:false,created_at:'2026-10-11T10:00:00Z',
    result:{jobs:[],query_spec:{hard_filters:{locations:['delhi ncr']}},relaxation_note:'Your filters were kept.',warnings:['Fictional source: unable to fetch a career page'],
      empty_message:'No new roles met your required location (Delhi NCR) and other filters in the checked company sources.',
      search_stats:{sources_searched:5,retrieved:200,tech_jobs:200,already_tracked:0,eligible:0,returned:0,hard_filter_excluded:{'Different required location':200}}}
  }])}));
  await page.goto('/');await expect(page.locator('.answer')).toContainText('Delhi NCR');
  await expect(page.locator('.search-coverage')).toContainText('200 postings across 5 company sources');
  await expect(page.locator('.answer')).not.toContainText('tracker');
  await expect(page.getByText('Fictional source: unable to fetch a career page',{exact:true})).toBeVisible();
  await page.reload();await expect(page.locator('.answer')).toContainText('Delhi NCR');
});

test('manual LinkedIn search is hidden in core',async({page})=>{
  await fixtures(page);await page.goto('/');
  await expect(page.getByRole('button',{name:'Search on LinkedIn',exact:true})).toHaveCount(0);
});

test('manual LinkedIn import is hidden in core',async({page})=>{
  await fixtures(page);await page.goto('/');
  await expect(page.getByRole('button',{name:'Import LinkedIn job',exact:true})).toHaveCount(0);
});

test('indexed leads without a JD show links without invented fit cards',async({page})=>{
  await fixtures(page);
  await page.route('**/api/chat?**',route=>route.fulfill({json:[{id:1,query:'Java jobs',mode:'resume',resume_filename:'fixture.docx',resume_changed:false,created_at:'2026-10-11T10:00:00Z',result:{jobs:[],warnings:[],relaxation_note:'Filters kept',query_spec:{},external_links:[{title:'Indexed LinkedIn fixture',url:'https://www.linkedin.com/jobs/view/12345',detail:'Job details unavailable.'}],search_stats:{sources_searched:0,retrieved:0,web_queries:3,web_pages_checked:2,tech_jobs:0,already_tracked:0,eligible:0,returned:0,hard_filter_excluded:{}}}}]}));
  await page.goto('/');await page.getByText('Other discovered links (1)',{exact:false}).click();
  await expect(page.getByRole('link',{name:'Indexed LinkedIn fixture'})).toBeVisible();
  await expect(page.locator('.chat-job')).toHaveCount(0);
  await expect(page.locator('.search-coverage')).toContainText('3 queries');
});


test('clicking fit opens saved inline points on desktop and mobile without tracker intake',async({page})=>{
  for(const width of [1280,390]){
    await page.setViewportSize({width,height:900});
    const state=await fixtures(page,true,true,false);
    Object.assign(state.job,{score_breakdown:{components:[
      {factor:'Resume similarity',value:.65,weight:.8,points:52,evidence:'Comparison with stored fictional resume statements.'},
      {factor:'Location preference',value:1,weight:.2,points:20,evidence:'Fictional fixture location inside 50 km.'}],
      raw_total:72,total:72,rounding_and_cap:0,location:{anchor:'Fixture City, Fixtureland',country:'Fixtureland',radius_km:50,mode:'preferred',distance_km:12,within_radius:true,evidence:'Fictional location fixture.'},resume_evidence:['Built Java payment APIs.'],notice:'Content match, not hiring probability.'}});
    await page.goto('/');
    await page.getByRole('button',{name:'Find jobs',exact:true}).click();
    const score=page.getByRole('button',{name:/Explain fit score 72/});
    await score.focus();await page.keyboard.press('Enter');
    await expect(page.getByRole('heading',{name:'Score breakdown',exact:true})).toBeVisible();
    await expect(page.getByRole('cell',{name:'52.00',exact:true})).toBeVisible();
    await expect(page.getByRole('cell',{name:'20.00',exact:true})).toBeVisible();
    await expect(page.getByText('Inside radius',{exact:false})).toBeVisible();
    expect(state.calls.some(c=>c.path.endsWith('/interest'))).toBeFalsy();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
    await page.screenshot({path:`test-results/score-breakdown-${width}.png`,fullPage:true});
    await page.reload();await page.getByRole('button',{name:/Explain fit score 72/}).click();
    await expect(page.getByRole('heading',{name:'Score breakdown',exact:true})).toBeVisible();
    await page.unroute('**/api/**');
  }
});


test('structured search memory saves only explicitly and resets without deleting history or defaults',async({page})=>{
  const state=await fixtures(page,true,true,false);await page.goto('/');
  await page.locator('.memory-panel>summary').click();
  await page.getByLabel('Saved search preferences',{exact:true}).fill('Jobs in India, prefer junior roles');
  expect(state.calls.some(c=>c.path==='/search/preferences'&&c.method==='PUT')).toBeFalsy();
  await page.getByRole('button',{name:'Save search preferences',exact:true}).click();
  await expect(page.getByText('Search preferences saved.',{exact:false})).toBeVisible();
  await page.locator('.memory-panel>summary').click();
  await page.getByRole('button',{name:'Find jobs',exact:true}).click();
  await expect(page.locator('.chat-turn')).toHaveCount(1);
  await page.reload();await page.locator('.memory-panel>summary').click();
  await expect(page.getByLabel('Saved search preferences',{exact:true})).toHaveValue('Jobs in India, prefer junior roles');
  await page.getByRole('button',{name:'New search',exact:true}).click();
  await expect(page.getByText('New search started.',{exact:false})).toBeVisible();
  await expect(page.locator('.chat-turn')).toHaveCount(1);
  await expect(page.getByLabel('Saved search preferences',{exact:true})).toHaveValue('Jobs in India, prefer junior roles');
  await page.getByRole('button',{name:'Remove saved preferences',exact:true}).click();
  await expect(page.getByLabel('Saved search preferences',{exact:true})).toHaveValue('');
  expect(state.calls.some(c=>c.path==='/chat'&&c.method==='DELETE')).toBeFalsy();
  await page.setViewportSize({width:390,height:900});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/search-memory-390.png',fullPage:true});
});


test('refresh recovers a running search and explicit cancellation preserves history',async({page})=>{
  const state=await fixtures(page);
  let run={id:'pending',query:'Python jobs',request_key:'key',status:'running',phase:'discovering',attempt:1,error:null,turn_id:null};
  await page.route('**/api/search/runs**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path.endsWith('/cancel'))run={...run,status:'cancelled',phase:'cancelled'};
    await route.fulfill({json:path.endsWith('/runs')?[run]:run});
  });
  await page.goto('/');await expect(page.getByRole('button',{name:'Cancel search',exact:true})).toBeVisible();
  await page.reload();await expect(page.getByRole('button',{name:'Cancel search',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Cancel search',exact:true}).click();
  await expect(page.getByText('Search cancelled.',{exact:false})).toBeVisible();
  expect(state.calls.filter(c=>c.path==='/search'&&c.method==='POST')).toHaveLength(0);
});

test('interrupted search retries only after user action',async({page})=>{
  await fixtures(page);let retries=0;
  let run={id:'interrupted',query:'Python jobs',request_key:'key',status:'interrupted',phase:'interrupted',attempt:1,error:'Server stopped',turn_id:null};
  await page.route('**/api/search/runs**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path.endsWith('/retry')){retries++;run={...run,status:'queued',phase:'queued',attempt:2};}
    await route.fulfill({json:path.endsWith('/runs')?[run]:run});
  });
  await page.goto('/');await expect(page.getByRole('button',{name:'Retry search',exact:true})).toBeVisible();expect(retries).toBe(0);
  await page.getByRole('button',{name:'Retry search',exact:true}).click();
  await expect(page.getByText('Search queued…',{exact:true})).toBeVisible();expect(retries).toBe(1);
});

test('older history loads without replacing recent conversation',async({page})=>{
  await fixtures(page);const result={jobs:[],warnings:[],query_spec:{},empty_message:'No eligible fixture jobs'};
  const turn=(id:number)=>({id,query:'Fixture search '+id,mode:'resume',resume_changed:false,resume_filename:'fixture.docx',created_at:'2026-10-16T10:00:00Z',result});
  await page.route('**/api/chat?**',async route=>{
    const before=new URL(route.request().url()).searchParams.get('before_id');
    await route.fulfill({json:before?[turn(1)]:Array.from({length:25},(_,i)=>turn(i+2))});
  });
  await page.goto('/');await expect(page.locator('.chat-turn')).toHaveCount(25);
  await page.getByRole('button',{name:'Load older messages',exact:true}).click();
  await expect(page.locator('.chat-turn')).toHaveCount(26);
  await expect(page.getByText('Fixture search 1',{exact:true})).toBeVisible();
  await expect(page.getByText('Fixture search 26',{exact:true})).toHaveCount(1);
});

test('login offers Google and passwordless email with processing notice',async({page})=>{
  await fixtures(page);
  await page.route('**/api/auth/config',route=>route.fulfill({json:{enabled:true,url:'https://fictional.supabase.co',publishable_key:'sb_publishable_fixture'}}));
  await page.goto('/login');
  await expect(page.getByRole('button',{name:/Google/})).toBeVisible();
  await expect(page.getByRole('textbox',{name:/Email/})).toBeVisible();
  await expect(page.getByRole('button',{name:/email|link/i})).toBeVisible();
});
