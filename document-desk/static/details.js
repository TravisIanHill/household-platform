const DetailUI=(()=>{
const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function iso(value){if(/^\d{4}-\d\d-\d\d$/.test(value))return value;const d=new Date(value);return value&&!isNaN(d)?`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`:'';}
function fields(template,values,people,readonly){const e=escape;return (template?.fields||Object.keys(values)).map(f=>{const schema=template?.schema?.[f]||{},value=values[f]||'',disabled=readonly?'disabled':'',legacy=template?.legacy_fields?.includes(f);let control;
if(schema.type==='select'||schema.type==='person'){let options=schema.type==='person'?people.map(p=>p.name):schema.options||[];if(value&&!options.includes(value))options=[value,...options];control=`<select data-field="${e(f)}" ${disabled}><option value="">Choose…</option>${options.map(x=>`<option ${x===value?'selected':''} value="${e(x)}">${e(x)}</option>`).join('')}</select>`;}
else if(schema.type==='date'){const date=iso(value);control=`<input type="${value&&!date?'text':'date'}" data-field="${e(f)}" value="${e(date||value)}" ${disabled}>`;}
else control=`<input data-field="${e(f)}" value="${e(value)}" ${disabled}>`;
return `<label class="${legacy?'legacy-field':''}">${e(f)}${template?.required?.includes(f)?' *':''}${legacy?' (previous field · retained)':''}${control}</label>`;}).join('');}
return {escape,fields};})();
