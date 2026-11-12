// Requer Playwright e navegador Chromium. Entrada privada por stdin, nunca por argumento/log.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'evidence/review');fs.mkdirSync(out,{recursive:true});
function otp(secret,when){const a='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';let n=0,bits=0,b=[];for(const c of secret.replace(/=/g,'')){n=(n<<5)|a.indexOf(c);bits+=5;if(bits>=8){bits-=8;b.push((n>>bits)&255);}}const ctr=Buffer.alloc(8);ctr.writeBigUInt64BE(BigInt(Math.floor(when/30)));const h=crypto.createHmac('sha1',Buffer.from(b)).update(ctr).digest(),o=h[19]&15;return String((h.readUInt32BE(o)&0x7fffffff)%1000000).padStart(6,'0');}
function luminance(rgb){const v=rgb.match(/[\d.]+/g).slice(0,3).map(Number).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;});return .2126*v[0]+.7152*v[1]+.0722*v[2];}
function ratio(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
(async()=>{
 const secret=JSON.parse(fs.readFileSync(0,'utf8')),start=Date.now(),checks=[];
 const browser=await chromium.launch({headless:true,...(process.env.AURORA_BROWSER?{executablePath:process.env.AURORA_BROWSER}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:1000}});
  await page.goto(process.env.AURORA_URL||'http://127.0.0.1:8088/',{waitUntil:'networkidle'});
  checks.push({test:'Idioma português e título identificável',passed:await page.getAttribute('html','lang')==='pt-BR'&&(await page.title()).includes('Vila Aurora')});
  checks.push({test:'Rótulos nativos dos três campos',passed:await page.getByLabel('Perfil',{exact:true}).count()===1&&await page.getByLabel('Senha',{exact:true}).count()===1&&await page.getByLabel('Código do autenticador',{exact:true}).count()===1});
  await page.keyboard.press('Tab');const skip=await page.evaluate(()=>document.activeElement.classList.contains('skip'));
  const focus=await page.evaluate(()=>{const s=getComputedStyle(document.activeElement);return {outline:s.outlineStyle,width:s.outlineWidth};});
  await page.keyboard.press('Enter');checks.push({test:'Link de salto alcançável por Tab e ativa conteúdo',passed:skip&&await page.evaluate(()=>document.activeElement.id==='conteudo')});
  checks.push({test:'Foco visível por teclado',...focus,passed:focus.outline==='solid'&&parseFloat(focus.width)>=3});
  const visited=[];let submitted=false;
  for(let i=0;i<25;i++){
   await page.keyboard.press('Tab');const element=await page.evaluate(()=>({tag:document.activeElement.tagName,name:document.activeElement.name||'',form:document.activeElement.form?.id}));visited.push(element.name||element.tag);
   if(element.name==='username'){await page.keyboard.press('Home');for(let j=0;j<3;j++)await page.keyboard.press('ArrowDown');}
   if(element.name==='password')await page.keyboard.type(secret.user.password);
   if(element.name==='otp')await page.keyboard.type(otp(secret.user.totp_secret,secret.epoch+(Date.now()-start)/1000));
   if(element.tag==='BUTTON'&&element.form==='login'){await page.keyboard.press('Enter');submitted=true;break;}
  }
  if(submitted)await page.waitForFunction(()=>document.querySelector('#authstate').textContent.includes('Conectado como auditor'));
  checks.push({test:'Login MFA concluído somente com teclado',visited,passed:submitted&&await page.locator('#login').isHidden()});
  await page.waitForSelector('.card');
  const pairs=await page.evaluate(()=>{const items=[['Texto principal','body','body'],['Texto secundário','small','body'],['Link','nav a','body'],['Texto de seção','#acesso','#acesso'],['Texto do botão','#refresh','#refresh'],['Texto do cartão','.card','.card']];return items.map(([label,fg,bg])=>({label,foreground:getComputedStyle(document.querySelector(fg)).color,background:getComputedStyle(document.querySelector(bg)).backgroundColor}));});
  const contrast=pairs.map(p=>({...p,ratio:Number(ratio(p.foreground,p.background).toFixed(2))}));checks.push({test:'Contraste mínimo 4,5:1 nos seis pares selecionados',contrast,passed:contrast.every(x=>x.ratio>=4.5)});
  await page.setViewportSize({width:320,height:900});await page.waitForTimeout(300);
  const narrow=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));
  checks.push({test:'Refluxo a 320 CSS px sem rolagem horizontal',...narrow,passed:narrow.scrollWidth<=narrow.clientWidth});
  await page.screenshot({path:path.join(out,'panel-320.png'),fullPage:true});
  await page.setViewportSize({width:1280,height:1000});await page.evaluate(()=>document.body.style.zoom='2');await page.waitForTimeout(300);
  const zoom=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));
  checks.push({test:'Ampliação CSS 200% sem rolagem horizontal',...zoom,passed:zoom.scrollWidth<=zoom.clientWidth});
  await page.evaluate(()=>document.body.style.zoom='1');
  const statuses=await page.evaluate(()=>['authstate','totals','commandstate'].map(id=>{const e=document.getElementById(id);return {id,role:e.getAttribute('role'),live:e.getAttribute('aria-live')};}));
  checks.push({test:'Mensagens de estado com anúncio acessível',statuses,passed:statuses.every(e=>e.role==='status'||e.live==='polite')});
  const result={scope:'Verificações selecionadas de WCAG 2.1 AA em navegador real; não certifica toda a norma nem substitui teste com leitor de tela e usuários.',browser:browser.version(),utc_host:new Date().toISOString(),tests:checks,passed:checks.filter(x=>x.passed).length,total:checks.length};
  fs.writeFileSync(path.join(out,'accessibility.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({passed:result.passed,total:result.total}));if(result.passed!==result.total)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
