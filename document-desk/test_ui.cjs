const fs=require('fs');
const {JSDOM}=require('jsdom');
const assert=require('node:assert/strict');
const root=__dirname;
const data={user:{id:'admin',role:'admin',name:'Owner'},people:[{id:'sam',name:'Sam',aliases:[],user_id:null}],organization:{folders:['Family_Records/Vital_Records'],tags:[],collections:[]},templates:[{name:'Birth Certificate',fields:['Person','Date of birth','Country','State or territory'],schema:{Person:{type:'person'},'Date of birth':{type:'date'},Country:{type:'select',options:['United States','Other']},'State or territory':{type:'select',options:['Oregon','Arizona']}}}],docs:[{id:'doc',filename:'Birth.pdf',original:'Birth.pdf',folder:'Family_Records/Vital_Records',type:'Birth Certificate',status:'archived',fields:{Person:'Sam','Date of birth':'2010-01-01'},person_ids:['sam'],text:'BIRTH CERTIFICATE',history:[],visibility:'private',can_edit:true,can_share:true}]};
const dom=new JSDOM(fs.readFileSync(root+'/templates/finder.html','utf8').replace('{{csrf}}','fixture'),{url:'http://desk/',runScripts:'outside-only'});const w=dom.window;
w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};w.confirm=()=>true;
w.fetch=async(url,opts={})=>{let result;
if(url==='/api/state')result=JSON.parse(JSON.stringify(data));
else if(url==='/api/users')result={users:[{id:'admin',name:'Owner',username:'owner',role:'admin',active:1,adult:1}]};
else if(url==='/api/policies')result={policies:[]};
else if(url==='/api/batches')result={batches:[]};
else if(url==='/api/docs/doc/suggest')result={type:'Birth Certificate',message:'Confirm suggestions',fields:{Country:{value:'United States',evidence:'STATE OF OREGON'}},person_ids:[]};
else if(url==='/api/docs/doc'&&opts.method==='PUT'){const v=JSON.parse(opts.body);Object.assign(data.docs[0],v);result=data.docs[0];}
else if(url==='/api/docs/doc/organization'){Object.assign(data.docs[0],JSON.parse(opts.body));result=data.docs[0];}
else throw Error('Unexpected URL '+url);
return {ok:true,status:200,json:async()=>result};};
const turn=()=>new Promise(resolve=>setTimeout(resolve,15));
(async()=>{w.eval(fs.readFileSync(root+'/static/details.js','utf8')+'\n'+fs.readFileSync(root+'/static/finder.js','utf8'));await turn();assert(w.document.querySelector('[data-id="doc"]'));
w.document.querySelector('[data-id="doc"]').click();await turn();assert(w.document.querySelector('#preview iframe'));assert.equal(w.document.querySelector('[data-field="Date of birth"]').type,'date');assert.equal(w.document.querySelector('[data-field="State or territory"]').tagName,'SELECT');
w.document.querySelector('#suggest').click();await turn();w.document.querySelector('[data-accept="Country"]').click();assert.equal(w.document.querySelector('[data-field="Country"]').value,'United States');w.document.querySelector('#detailform').dispatchEvent(new w.Event('submit',{cancelable:true}));await turn();assert.equal(data.docs[0].fields.Country,'United States');
w.document.querySelector('#settings').click();await turn();assert(w.document.querySelector('[data-adult="admin"]'));assert(w.document.querySelector('[data-personform="sam"]'));w.document.querySelector('#addrule').click();assert(w.document.querySelector('[data-rule]'));
data.user={id:'parent',role:'member',name:'Parent'};data.docs[0].can_edit=false;data.docs[0].can_share=false;await w.eval('refresh()');w.document.querySelector('[data-id="doc"]').click();assert(!w.document.querySelector('#suggest'));assert(w.document.querySelector('#doctype').disabled);assert(w.document.querySelector('#settings').hidden);
console.log('PASS: Finder list/preview/details, typed controls, accept suggestion and save, adult/person/policy settings, viewer controls disabled. DOM simulation; no visual browser QA.');w.close();})().catch(err=>{console.error(err);process.exit(1);});
