/* Pure catalog-list helpers; originals and stored names are never changed. */
const DeskQueue = (() => {
 const extension=d=>(d.original||'').match(/\.([^.]+)$/)?.[1].toLowerCase()||'';
 function title(d){
  let name=(d.source_relative_path||d.original||'Untitled').split(/[\\/]/).pop();
  // Flattened backup exports include this explicit separator. Retain full name in details.
  if(/_NOTARIZE-/i.test(name))name=name.split(/_NOTARIZE-/i).pop();
  return name.replace(/\.[^.]+$/,'').replace(/_/g,' ').replace(/([a-z])([A-Z])/g,'$1 $2').replace(/([A-Z])([A-Z][a-z])/g,'$1 $2').replace(/\s+/g,' ').trim()||d.original;
 }
 function size(value){if(value==null||!Number.isFinite(Number(value)))return 'Size unknown';let n=Number(value),i=0;const units=['B','KB','MB','GB','TB'];while(n>=1024&&i<4){n/=1024;i++;}return `${i?n.toFixed(1):n} ${units[i]}`;}
 function select(docs,{query='',status='review',filetype='all',sort='added-desc'}={}){
  const [key,direction]=sort.split('-'),sign=direction==='desc'?-1:1;
  const value=d=>({added:Date.parse(d.created),modified:d.source_modified?Date.parse(d.source_modified):null,size:d.size_bytes,name:title(d),category:d.type||'Unclassified',extension:extension(d)})[key];
  const missing=v=>v==null||(typeof v==='number'&&!Number.isFinite(v));
  return docs.filter(d=>(status==='all'||d.status===status)&&(filetype==='all'||extension(d)===filetype)&&JSON.stringify(d).toLowerCase().includes(query.trim().toLowerCase())).sort((a,b)=>{
   const av=value(a),bv=value(b);if(missing(av)!==missing(bv))return missing(av)?1:-1;
   let c=missing(av)?0:typeof av==='number'?av-bv:String(av).localeCompare(String(bv),undefined,{numeric:true,sensitivity:'base'});
   return c*sign||String(a.id).localeCompare(String(b.id));
  });
 }
 return {extension,title,size,select};
})();
if(typeof module!=='undefined')module.exports=DeskQueue;
