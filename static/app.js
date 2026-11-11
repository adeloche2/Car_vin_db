const $=id=>document.getElementById(id);
const esc=s=>String(s??"—").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let timer=null,last="";
async function health(){try{const d=await(await fetch('/api/health')).json();$('dbstate').textContent=d.catalog_ready?d.catalog_models.toLocaleString()+" موديل محلي":"الكتالوج غير مستورد";if(d.catalog_ready)loadStats()}catch{$('dbstate').textContent="الخادم غير متصل"}}
function msg(text,kind="neutral"){$('progressive').className="message "+kind;$('progressive').textContent=text}
async function progressive(){
 const v=$('vinInput').value.toUpperCase().replace(/[\s-]/g,'');$('vinInput').value=v;last=v;
 $('counter').textContent=v.length+" / 17";$('progress').style.width=(v.length/17*100)+"%";
 $('stage').textContent=v.length===17?"VIN كامل":v.length>=3?"تحليل WMI":"إدخال أولي";$('decodeBtn').disabled=v.length!==17;$('decodeResult').innerHTML="";
 if(!v){msg("ابدأ بكتابة أول خانات رقم الهيكل.");return}
 try{const d=await(await fetch('/api/search?q='+encodeURIComponent(v))).json();if(last!==v)return;
 msg(d.message||"تم تحليل المدخل.",d.stage==="invalid"?"error":"neutral");
 if(d.wmi){const rows=(d.wmi.local_matches||[]).map(x=>"<div>"+esc(x.manufacturer)+" · "+esc(x.country)+" · "+esc(x.source)+"</div>").join("");const ext=(d.wmi.external_matches||[]).slice(0,4).map(x=>"<div>"+esc(x.Name||x.ManufacturerName||x.CommonName)+" · "+esc(x.Country)+"</div>").join("");$('decodeResult').innerHTML='<div class="card"><h3>رمز WMI: <span dir="ltr">'+esc(d.wmi.code)+'</span></h3>'+(rows||ext||"لم يتم العثور على سجل WMI مطابق.")+'<p class="muted">WMI يحدد جهة التصنيع غالبًا، ولا يحدد الموديل بمفرده.</p></div>'}
 }catch{msg("تعذر الاتصال بمحرك GVIDB المحلي.","error")}
}
$('vinInput').addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(progressive,350)});
$('clear').onclick=()=>{$('vinInput').value="";progressive()};
$('decodeBtn').onclick=async()=>{
 const v=$('vinInput').value.trim();$('decodeBtn').disabled=true;$('stage').textContent="جارٍ طلب بيانات VIN";
 try{const response=await fetch('/api/decode/'+encodeURIComponent(v));const d=await response.json();if(!response.ok)throw new Error(d.validation?.errors?.join(" ")||"تعذر تحليل الرقم");
 const veh=d.vehicle||{},colors=d.colors||{},year=d.year||{},source=d.source||{};
 const fields=[["الشركة المصنّعة",veh.manufacturer],["الموديل",veh.model],["سنة الطراز",veh.model_year],["الفئة",veh.trim],["السلسلة",veh.series],["نوع المركبة",veh.vehicle_type],["بلد التجميع",veh.plant_country],["مدينة المصنع",veh.plant_city],["المحرك",veh.engine],["الوقود",veh.fuel],["ناقل الحركة",veh.transmission]].filter(x=>x[1]);
 let html='<div class="card"><h3>نتيجة فك VIN</h3><div class="message '+(d.status==="decoded"?"success":"warning")+'">'+esc(d.user_message)+'</div><div class="grid">'+(fields.length?fields.map(x=>'<div class="cell"><span class="muted">'+esc(x[0])+'</span><br><b>'+esc(x[1])+'</b></div>').join(""):'<div class="cell">لم يتمكن المصدر من تحديد بيانات المركبة.</div>')+'</div><p class="muted">المصدر: '+esc(source.name)+' · مستوى الثقة: '+esc(d.confidence)+'</p></div>';
 html+='<div class="card"><h3>سنة الطراز</h3>'+esc(year.message)+(year.candidate_years?.length?'<p>احتمالات رمز السنة: '+year.candidate_years.join("، ")+'</p>':"")+'</div>';
 html+='<div class="card"><h3>الألوان</h3>'+esc(colors.message)+(colors.available?Object.entries(colors.values).map(([k,v])=>'<div>'+esc(k)+': '+esc(v)+'</div>').join(""):"")+'</div>';
 html+='<div class="card"><h3>فحص VIN</h3><p>'+esc(d.check_digit.explanation)+'</p><p class="muted">WMI: '+esc(d.positions.wmi)+' · VDS: '+esc(d.positions.vds)+'</p></div>';
 html+='<div class="card"><h3>حدود النتيجة</h3><ul>'+(d.limitations||[]).map(x=>'<li>'+esc(x)+'</li>').join("")+'</ul></div>';
 $('decodeResult').innerHTML=html;$('stage').textContent="اكتمل التحليل";
 }catch(e){msg(e.message,"error")}finally{$('decodeBtn').disabled=$('vinInput').value.length!==17}
};
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('vin').classList.toggle('hidden',b.dataset.tab!=="vin");$('catalog').classList.toggle('hidden',b.dataset.tab!=="catalog")});
async function loadStats(){try{const d=await(await fetch('/api/catalog/stats')).json();$('catalogStats').innerHTML='النسخة: '+esc(d.version||"—")+' · '+Number(d.models).toLocaleString()+' موديل · '+Number(d.makes).toLocaleString()+' علامة<br>'+(d.by_kind||[]).map(x=>esc(x.kind)+": "+x.count).join(" | ")}catch{}}
$('importBtn').onclick=async()=>{$('importBtn').disabled=true;$('importBtn').textContent="جارٍ تنزيل الكتالوج...";$('catalogStats').textContent="قد يستغرق التنزيل عدة دقائق.";try{const r=await fetch('/api/catalog/import',{method:"POST"});const d=await r.json();if(!r.ok)throw new Error(d.message||d.error);$('catalogStats').textContent='تم استيراد '+d.models_imported+' موديل من '+d.makes_imported+' علامة. الإصدار '+d.version;loadStats()}catch(e){$('catalogStats').textContent="فشل الاستيراد: "+e.message}finally{$('importBtn').disabled=false;$('importBtn').textContent="إعادة تنزيل / تحديث الكتالوج"}};
$('modelSearch').onclick=searchModels;$('modelQuery').addEventListener('keydown',e=>{if(e.key==="Enter")searchModels()});
async function searchModels(){const q=$('modelQuery').value.trim();if(q.length<2){$('modelResults').textContent="أدخل حرفين على الأقل.";return}try{const d=await(await fetch('/api/catalog/models?q='+encodeURIComponent(q))).json();$('modelResults').innerHTML=(d.results||[]).map(x=>'<div class="modelrow"><b>'+esc(x.make_name)+' '+esc(x.model_name)+'</b><br><span class="tag">'+esc(x.kind)+'</span><span class="muted"> '+esc(x.body_types||"نوع الهيكل غير محدد")+' · الأسواق: '+esc(x.countries||"غير محددة")+' · سنوات التسجيل: '+esc(x.registration_years||"غير متوفرة")+'</span></div>').join("")||"لا توجد نتائج."}catch{$('modelResults').textContent="تعذر البحث."}}
health();
