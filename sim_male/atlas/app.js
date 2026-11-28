"use strict";
const data = JSON.parse(document.getElementById("data").textContent);
const byId = id => document.getElementById(id);
const fmt = n => n.toLocaleString("en-US");
const pct = n => (100*n).toFixed(1) + "%";
const colors = {Support:"#16805e", Oppose:"#b55c42", Undecided:"#687781"};
const dotColors = {Support:"#8ce7ac", Oppose:"#ff9877", Undecided:"#d3dce3"};
const all = "Greater Malé";
let area = all, mode = 0, opened = false, page = 0;
const cardCount = 3;
function el(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}
function svg(tag, attrs, parent) {
  const node = document.createElementNS("http://www.w3.org/2000/svg",tag);
  for (const [key,value] of Object.entries(attrs)) node.setAttribute(key,value);
  parent.append(node);
  return node;
}
function groupRows(key) {return key === all ? data.rows : data.rows.filter(r => r.area === key);}
function changed(r) {return r.answers[0][0] !== r.answers[1][0];}
function share(rows,m,choice) {
  const total = rows.reduce((s,r) => s+r.weight,0);
  return total ? rows.reduce((s,r) => s+(r.answers[m][0]===choice ? r.weight : 0),0)/total : null;
}
function rings(g) {
  if (g.type==="Polygon") return g.coordinates;
  if (g.type==="MultiPolygon") return g.coordinates.flat();
  if (g.type==="GeometryCollection") return g.geometries.flatMap(rings);
  return [];
}
function filtered() {
  const rows = groupRows(area);
  return mode===2 && byId("changed").checked ? rows.filter(changed) : rows;
}
function selectArea(key) {area=key; byId("area").value=key; page=0; redraw();}
function mapDraw() {
  const map=byId("map");
  map.replaceChildren();
  const shapes = area===all ? Object.values(data.masks) : [data.masks[area]];
  const coords=shapes.flatMap(g=>rings(g).flat());
  const xs=coords.map(([x])=>x), ys=coords.map(([,y])=>y);
  const west=Math.min(...xs),east=Math.max(...xs),south=Math.min(...ys),north=Math.max(...ys);
  const w=650,h=320,scale=Math.min(550/Math.max(.001,east-west),268/Math.max(.001,north-south));
  const project=([x,y])=>[w/2+(x-(west+east)/2)*scale*.997,h/2-(y-(north+south)/2)*scale];
  map.setAttribute("viewBox","0 0 650 320");
  function path(g,attrs) {
    const d=rings(g).map(r=>r.map((p,i)=>(i?"L":"M")+project(p).map(v=>v.toFixed(2)).join(" ")).join("")+"Z").join("");
    return svg("path",{d,"fill-rule":"evenodd",...attrs},map);
  }
  data.shores.forEach(g=>path(g,{class:"land"}));
  for (const [name,g] of Object.entries(data.masks)) {
    const group=groupRows(name), rate=share(group,mode===0?0:1,"Support");
    const fill=opened && rate!==null ? "hsl(154,32%,"+(83-48*rate)+"%)" : "#7da99b";
    const n=path(g,{class:"zone",fill,opacity:area===all||area===name?1:.32});
    n.onclick=()=>selectArea(name);
    svg("title",{},n).textContent=name+(opened && rate!==null?" · "+pct(rate)+" support":"");
  }
  for (const r of groupRows(area)) {
    const [x,y]=project([r.lon,r.lat]);
    const m=mode===0?0:1;
    const n=svg("circle",{cx:x,cy:y,r:area===all?1.65:3.6,class:"dot",fill:opened?dotColors[r.answers[m][0]]:"#d3efcb"},map);
    svg("title",{},n).textContent=r.id+" · "+r.area+(opened?" · "+r.answers[m][0]:"");
    n.onclick=()=>{
      opened=true; area=r.area; byId("area").value=area; byId("changed").checked=false;
      page=Math.floor(filtered().findIndex(item=>item.id===r.id)/cardCount);
      redraw(); byId("responses").scrollIntoView({block:"start"});
      document.getElementById("card-"+r.id)?.focus({preventScroll:true});
    };
  }
  if(area===all) {
    for(const [label,x,y,anchor] of [["Villimalé",73.437,4.177,"start"],["Malé",73.51,4.161,"middle"],["Hulhumalé",73.526,4.222,"end"]]) {
      const [px,py]=project([x,y]);
      svg("text",{x:Math.max(5,px),y:Math.min(h-4,py),"text-anchor":anchor,class:"map-label"},map).textContent=label;
    }
  }
  byId("mapTitle").textContent=area;
  const population=area===all?data.n:data.counts[area]||0;
  byId("mapCaption").textContent=fmt(population)+" synthetic residents · "+groupRows(area).length+" sampled";
  byId("mapKey").textContent=opened?"Darker green areas = higher support"+(mode===2?" with same fare":""):"Dots show sampled residents";
}
function scoreDraw(rows) {
  const box=byId("scores"); box.replaceChildren();
  if (!rows.length) {box.append(el("p","No sampled responses in this area."));return;}
  for (const opt of data.options) {
    if(mode===2) {
      const row=el("div","","compareRow");row.append(el("span",opt),el("b",pct(share(rows,0,opt))+" → "+pct(share(rows,1,opt))));
      box.append(row);continue;
    }
    const row=el("div","","score"), track=el("span","","track"), fill=el("i","");
    const s=share(rows,mode,opt);fill.style.width=pct(s);fill.style.background=colors[opt];track.append(fill);
    row.append(el("span",opt),track,el("b",pct(s)));box.append(row);
  }
  const note=mode===2 ? rows.filter(changed).length+" of "+rows.length+" changed their answer. Baseline → same fare."
    : rows.length+" synthetic responses · "+area;
  box.append(el("p",note,"muted"));
}
function listDraw() {
  const rows=filtered(), list=byId("cards");list.replaceChildren();
  const pages=Math.max(1,Math.ceil(rows.length/cardCount));page=Math.min(Math.max(0,page),pages-1);
  byId("listSummary").textContent=area+" · "+fmt(rows.length)+" matching responses";
  for (const r of rows.slice(page*cardCount,(page+1)*cardCount)) {
    const card=el("article","","person");card.id="card-"+r.id;card.tabIndex=-1;
    card.append(el("strong",r.area),el("small",r.id+" · "+r.age+" · "+r.occupation));
    for(const i of mode===2?[0,1]:[mode]) {
      const [vote,reason]=r.answers[i];
      card.append(el("p",(mode===2?(i?"Same fare · ":"Baseline · "):"")+vote,"vote"),el("p",reason));
    }
    list.append(card);
  }
  if(!rows.length) list.append(el("p","No responses match this selection."));
  byId("pageInfo").textContent=(page+1)+" / "+pages;
  byId("prev").disabled=page===0;byId("next").disabled=page+1>=pages;
}
function redraw() {
  const rows=groupRows(area);
  byId("result").hidden=!opened;byId("runBox").hidden=opened;byId("responses").hidden=!opened;
  byId("fareNote").hidden=!opened||mode===0;
  byId("changedWrap").hidden=mode!==2;
  document.querySelectorAll("[data-mode]").forEach(b=>b.setAttribute("aria-pressed",Number(b.dataset.mode)===mode));
  mapDraw(); if(opened){scoreDraw(rows);listDraw();}
}
function download(name,content,type) {
  const a=document.createElement("a"),url=URL.createObjectURL(new Blob([content],{type}));
  a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
byId("download").onclick=()=>{
  const cols=["resident_id","area","weight","baseline","baseline_reason","same_fare","same_fare_reason","method","run_utc"];
  const quote=v=>'"'+String(v).replace(/^[=+@-]/,"'$&").replaceAll('"','""')+'"';
  const rows=data.rows.map(r=>[r.id,r.area,r.weight,...r.answers[0],...r.answers[1],data.method,data.date]);
  download("ask-male-paired.csv",[cols,...rows].map(row=>row.map(quote).join(",")).join("\r\n"),"text/csv;charset=utf-8");
};
byId("survey").onclick=()=>download("evening-bus-pilot.txt",[
  "Greater Malé evening bus service | anonymous pilot","Record area of residence: "+data.areas.join(" / "),"",
  "1. "+data.question, data.options.join(" / "), "Reason (optional):","",
  "2. "+data.question+" "+data.fare,data.options.join(" / "),"Reason (optional):","",
  "Keep both answers on one form. Summarise recruitment, area and respondent counts alongside any comparison."
].join("\n"),"text/plain;charset=utf-8");
for(const key of [all,...data.areas]) byId("area").add(new Option(key,key));
byId("area").onchange=e=>selectArea(e.target.value);
byId("question").textContent=data.question;byId("fareNote").textContent=data.fare;
byId("methodName").textContent=data.method;
byId("startInfo").textContent=data.rows.length+" sampled residents answer two versions of the proposal.";
byId("demoNote").textContent=data.live?"AI-generated responses from a fixed cohort.":"Offline demo with scripted synthetic answers.";
byId("methodText").textContent=data.live?"Each sampled profile answered both prompts through the displayed model. The map and results use those individual responses.":"The demo assigns an initial preference and fare sensitivity reproducibly from each synthetic ID. Its templates illustrate how to compare a fixed cohort. The assumed fare effect and area differences provide no evidence of real preferences.";
byId("runInfo").textContent="Run "+data.date+" · Sample seed "+data.seed+" · "+data.rows.length+" of "+fmt(data.n)+" residents. Shares use the supplied voter weights; response counts are unweighted.";
byId("sourceNote").textContent="Map colours use the displayed area's sampled support share. Dot colours show each sampled response. Reclaimed land and parcel status follow the source map editions.";
byId("run").onclick=()=>{opened=true;redraw();};
document.querySelector('a[href="#responses"]').onclick=()=>{opened=true;redraw();};
document.querySelector('a[href="#method"]').onclick=()=>{byId("method").open=true;};
document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>{mode=Number(b.dataset.mode);page=0;redraw();});
byId("changed").onchange=()=>{page=0;listDraw();};
byId("prev").onclick=()=>{page--;listDraw();};byId("next").onclick=()=>{page++;listDraw();};
redraw();
