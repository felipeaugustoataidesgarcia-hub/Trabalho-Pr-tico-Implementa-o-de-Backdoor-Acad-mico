#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webui.py - Painel de controle web do sistema de auditoria Wi-Fi.

Interface local (Flask) que une as ferramentas da atividade:
    - Reconhecimento (wifi_recon.py)  -> escaneia e lista as redes
    - Montador de comandos de ataque  -> WPS / WPS-BF / PMKID / Handshake
    - Gerador de relatorio             -> wifi_recon JSON + resultado -> HTML/MD

Por seguranca, os ataques (que exigem root/modo monitor) NAO sao disparados
pelo navegador: o painel monta o comando exato para voce copiar e rodar no
terminal. O reconhecimento e a geracao de relatorio rodam localmente.

Uso academico / autorizado.

Executar:
    pip install flask        # (uma vez)
    python webui.py          # abre em http://127.0.0.1:8000
"""

import json
import os
import subprocess
import sys

from flask import Flask, jsonify, render_template_string, request, send_file

AQUI = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python3"
app = Flask(__name__)


# --------------------------------------------------------------------- API
@app.post("/api/recon")
def api_recon():
    """Roda wifi_recon.py e devolve a lista de redes em JSON."""
    saida = os.path.join(AQUI, "dados.json")
    try:
        subprocess.run(
            [PY, os.path.join(AQUI, "wifi_recon.py"), "--json", saida, "--no-gateway"],
            capture_output=True, text=True, timeout=90, cwd=AQUI,
        )
        with open(saida, encoding="utf-8") as f:
            redes = json.load(f)
        return jsonify(ok=True, redes=redes)
    except FileNotFoundError:
        return jsonify(ok=False, erro="Nenhuma rede/arquivo. Scan indisponivel "
                       "neste ambiente (sem placa Wi-Fi?)."), 200
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, erro=str(e)), 200


@app.post("/api/relatorio")
def api_relatorio():
    """Gera relatorio .md + .html a partir dos campos enviados."""
    d = request.get_json(force=True, silent=True) or {}
    md = os.path.join(AQUI, "relatorio.md")
    htm = os.path.join(AQUI, "relatorio.html")
    cmd = [PY, os.path.join(AQUI, "gerar_relatorio.py"),
           "--saida", md, "--html", htm]
    for flag, chave in [("--target", "target"), ("--ssid", "ssid"),
                        ("--bssid", "bssid"), ("--canal", "canal"),
                        ("--ip", "ip"), ("--metodo", "metodo"),
                        ("--senha", "senha"), ("--wps-pin", "wps_pin"),
                        ("--tempo", "tempo"), ("--autor", "autor"),
                        ("--modelo", "modelo")]:
        v = (d.get(chave) or "").strip()
        if v:
            cmd += [flag, v]
    if os.path.exists(os.path.join(AQUI, "dados.json")):
        cmd += ["--json", os.path.join(AQUI, "dados.json")]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=AQUI)
        return jsonify(ok=True, log=r.stdout + r.stderr)
    except Exception as e:  # noqa: BLE001
        return jsonify(ok=False, erro=str(e)), 200


@app.get("/relatorio.html")
def ver_relatorio():
    p = os.path.join(AQUI, "relatorio.html")
    return send_file(p) if os.path.exists(p) else ("Gere o relatorio primeiro.", 404)


@app.get("/relatorio.md")
def baixar_md():
    p = os.path.join(AQUI, "relatorio.md")
    return send_file(p, as_attachment=True) if os.path.exists(p) else ("", 404)


@app.get("/")
def index():
    return render_template_string(PAGINA)


# --------------------------------------------------------------------- HTML
PAGINA = r"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auditoria Wi-Fi</title>
<style>
  :root{--bg:#0d1117;--card:#161b22;--fg:#e6edf3;--mut:#8b949e;--acc:#1f6feb;
        --ok:#3fb950;--warn:#d29922;--line:#30363d;--rad:12px;}
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--fg);
       font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
  header{padding:22px 20px;background:linear-gradient(90deg,#161b22,#0d1117);
         border-bottom:1px solid var(--line);display:flex;align-items:center;
         gap:14px;flex-wrap:wrap;}
  header h1{font-size:1.3rem;margin:0;}
  .chip{background:#1f2630;border:1px solid var(--line);color:#58a6ff;
        padding:.25em .7em;border-radius:999px;font-size:.8rem;}
  .wrap{max-width:960px;margin:0 auto;padding:24px 20px 80px;}
  .card{background:var(--card);border:1px solid var(--line);border-radius:var(--rad);
        padding:20px;margin:16px 0;}
  .card h2{margin:0 0 .3em;font-size:1.1rem;color:#58a6ff;}
  .card p.sub{margin:0 0 1em;color:var(--mut);font-size:.9rem;}
  button{background:var(--acc);color:#fff;border:0;border-radius:8px;
         padding:.6em 1.1em;font-size:.95rem;cursor:pointer;font-weight:600;}
  button:hover{filter:brightness(1.1);} button.ghost{background:#21262d;}
  label{display:block;font-size:.82rem;color:var(--mut);margin:.6em 0 .2em;}
  input,select{width:100%;background:#0d1117;border:1px solid var(--line);
         color:var(--fg);border-radius:8px;padding:.55em .7em;font-size:.95rem;}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;}
  table{width:100%;border-collapse:collapse;margin-top:12px;font-size:.9rem;}
  th,td{text-align:left;padding:.55em .6em;border-bottom:1px solid var(--line);}
  th{color:var(--mut);font-weight:600;} tr:hover td{background:#1c2128;}
  .cmd{background:#010409;border:1px solid var(--line);border-radius:8px;
       padding:.7em .9em;font-family:ui-monospace,Menlo,monospace;font-size:.82rem;
       color:#79c0ff;overflow-x:auto;display:flex;justify-content:space-between;gap:10px;}
  .cmd code{white-space:pre;}
  .copy{background:#21262d;color:#c9d1d9;border:1px solid var(--line);
        border-radius:6px;padding:.2em .6em;font-size:.75rem;cursor:pointer;flex:0 0 auto;}
  .tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;}
  .tabs .t{background:#21262d;border:1px solid var(--line);border-radius:999px;
           padding:.35em .9em;font-size:.82rem;cursor:pointer;}
  .tabs .t.on{background:var(--acc);color:#fff;border-color:var(--acc);}
  .muted{color:var(--mut);font-size:.85rem;}
  .ok{color:var(--ok);} .warn{color:var(--warn);}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px;}
  a{color:#58a6ff;}
  pre.log{background:#010409;border:1px solid var(--line);border-radius:8px;
          padding:.8em;font-size:.8rem;white-space:pre-wrap;color:var(--mut);display:none;}
</style></head>
<body>
<header>
  <h1>🛰️ Sistema de Auditoria Wi-Fi</h1>
  <span class="chip">Alvo: TP-Link AC750 (Archer C20)</span>
  <span class="chip">uso acadêmico / autorizado</span>
</header>
<div class="wrap">

  <div class="card">
    <h2>1 · Reconhecimento</h2>
    <p class="sub">Extrai SSID, BSSID (MAC), canal, frequência e criptografia — sem precisar estar conectado.</p>
    <div class="row">
      <button onclick="escanear()">🔍 Escanear redes</button>
      <span id="reconMsg" class="muted"></span>
    </div>
    <div id="reconTbl"></div>
  </div>

  <div class="card">
    <h2>2 · Vetores de ataque</h2>
    <p class="sub">Monte o comando com seu alvo e rode no terminal do Kali (precisa de root + modo monitor).</p>
    <div class="grid">
      <div><label>Interface</label><input id="iface" value="wlan0"></div>
      <div><label>BSSID do alvo</label><input id="bssid" placeholder="AA:BB:CC:DD:EE:FF"></div>
      <div><label>Canal</label><input id="canal" placeholder="6"></div>
    </div>
    <div class="tabs" id="tabs">
      <span class="t on" data-m="wps">WPS Pixie Dust</span>
      <span class="t" data-m="wps-bf">WPS Bruteforce PIN</span>
      <span class="t" data-m="pmkid">PMKID</span>
      <span class="t" data-m="handshake">Handshake + dict</span>
    </div>
    <div class="cmd"><code id="cmd"></code><button class="copy" onclick="copiar('cmd')">copiar</button></div>
    <p class="muted" id="dica"></p>
  </div>

  <div class="card">
    <h2>3 · Relatório</h2>
    <p class="sub">Junta os dados do recon com o resultado do ataque e gera o relatório formatado.</p>
    <div class="grid">
      <div><label>Autor(es)</label><input id="autor" placeholder="Seu nome"></div>
      <div><label>SSID alvo (filtro no JSON)</label><input id="target" placeholder="TP-Link"></div>
      <div><label>Método</label><select id="metodo">
        <option value="wps">WPS Pixie Dust</option>
        <option value="wps-bf">WPS Bruteforce</option>
        <option value="pmkid">PMKID</option>
        <option value="handshake">Handshake + dicionário</option>
      </select></div>
      <div><label>Senha recuperada</label><input id="senha" placeholder="ex.: 12345678"></div>
      <div><label>PIN do WPS</label><input id="wps_pin" placeholder="8 dígitos"></div>
      <div><label>IP do roteador</label><input id="ip" placeholder="192.168.0.1"></div>
      <div><label>Tempo do ataque</label><input id="tempo" placeholder="ex.: 2 min"></div>
    </div>
    <div class="row">
      <button onclick="gerar()">📄 Gerar relatório</button>
      <a id="verLink" href="/relatorio.html" target="_blank" style="display:none">abrir HTML ↗</a>
      <a id="mdLink" href="/relatorio.md" style="display:none">baixar .md ↓</a>
      <span id="relMsg" class="muted"></span>
    </div>
    <pre class="log" id="log"></pre>
  </div>

</div>
<script>
let modo="wps";
const dicas={
  "wps":"Mais rápido em TP-Link. Use o BSSID de 2.4 GHz (WPS não existe em 5 GHz).",
  "wps-bf":"Fallback do Pixie Dust: bruteforce do PIN. Lento e sujeito a lockout.",
  "pmkid":"Não precisa de cliente conectado ao modem.",
  "handshake":"Precisa de um cliente para o deauth; depende da wordlist."
};
function cmdFor(m){
  const i=val("iface")||"wlan0", b=val("bssid"), c=val("canal");
  const alvo=(b?` -b ${b}`:"")+(c?` -c ${c}`:"");
  if(m==="handshake") return `sudo ./wifi_crack.sh -i ${i} -m handshake${alvo}`;
  if(m==="pmkid") return `sudo ./wifi_crack.sh -i ${i} -m pmkid${alvo}`;
  if(m==="wps-bf") return `sudo ./wifi_crack.sh -i ${i} -m wps-bf${alvo}`;
  return `sudo ./wifi_crack.sh -i ${i} -m wps${alvo}`;
}
function val(id){return document.getElementById(id).value.trim();}
function refresh(){document.getElementById("cmd").textContent=cmdFor(modo);
  document.getElementById("dica").textContent=dicas[modo];}
document.getElementById("tabs").addEventListener("click",e=>{
  if(!e.target.dataset.m)return;
  document.querySelectorAll(".tabs .t").forEach(t=>t.classList.remove("on"));
  e.target.classList.add("on"); modo=e.target.dataset.m; refresh();
});
["iface","bssid","canal"].forEach(id=>document.getElementById(id).addEventListener("input",refresh));
refresh();
function copiar(id){navigator.clipboard.writeText(document.getElementById(id).textContent);}
async function escanear(){
  const m=document.getElementById("reconMsg"); m.textContent="escaneando...";
  try{
    const r=await fetch("/api/recon",{method:"POST"}); const j=await r.json();
    if(!j.ok){m.innerHTML='<span class="warn">'+j.erro+'</span>';return;}
    if(!j.redes.length){m.textContent="nenhuma rede encontrada.";return;}
    m.innerHTML='<span class="ok">'+j.redes.length+' rede(s) encontrada(s)</span>';
    let h='<table><tr><th>SSID</th><th>BSSID</th><th>Canal</th><th>Freq</th><th>Cripto</th><th>Sinal</th><th></th></tr>';
    j.redes.forEach(r=>{h+=`<tr><td>${esc(r.ssid)}</td><td>${esc(r.bssid)}</td><td>${esc(r.channel)}</td>`
      +`<td>${r.freq_mhz?r.freq_mhz+' MHz':'-'}</td><td>${esc(r.cipher||r.auth||'-')}</td>`
      +`<td>${esc(r.signal||'-')}</td><td><button class="copy" onclick="usar('${esc(r.bssid)}','${esc(r.channel)}','${esc(r.ssid)}')">usar alvo</button></td></tr>`;});
    document.getElementById("reconTbl").innerHTML=h+'</table>';
  }catch(e){m.innerHTML='<span class="warn">erro: '+e+'</span>';}
}
function usar(b,c,s){document.getElementById("bssid").value=b;
  document.getElementById("canal").value=c;document.getElementById("target").value=s;refresh();}
function esc(x){return (x==null?'':(''+x)).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
async function gerar(){
  const m=document.getElementById("relMsg"); m.textContent="gerando...";
  const body={};["autor","target","metodo","senha","wps_pin","ip","tempo"].forEach(k=>body[k]=val(k));
  body.bssid=val("bssid");body.canal=val("canal");
  const r=await fetch("/api/relatorio",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const j=await r.json();
  const log=document.getElementById("log");
  if(j.ok){m.innerHTML='<span class="ok">relatório gerado</span>';
    document.getElementById("verLink").style.display="inline";
    document.getElementById("mdLink").style.display="inline";
    log.style.display="block"; log.textContent=j.log;}
  else{m.innerHTML='<span class="warn">'+(j.erro||'falhou')+'</span>';}
}
</script>
</body></html>
"""


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", "8000"))
    print(f"[*] Painel em http://127.0.0.1:{porta}  (Ctrl+C para sair)")
    app.run(host="127.0.0.1", port=porta, debug=False)
