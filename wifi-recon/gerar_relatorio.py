#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_relatorio.py - Monta o relatorio da atividade de auditoria Wi-Fi.

Junta os dados extraidos pelo wifi_recon.py (JSON) com o resultado do ataque
(senha, metodo, PIN de WPS) e gera um relatorio em Markdown pronto para entrega.

Uso academico / autorizado.

Exemplos:
    # a partir do JSON gerado por: python wifi_recon.py --json dados.json
    python gerar_relatorio.py --json dados.json --target TP-Link \\
        --metodo wps --senha "senhaDoProf" --wps-pin 12345670 \\
        --ip 192.168.0.1 --autor "Seu Nome" --saida relatorio.md

    # sem JSON: preenche o que souber manualmente
    python gerar_relatorio.py --ssid RedeDoProf --bssid A4:2B:B0:11:22:33 \\
        --canal 6 --metodo handshake --senha "..." --saida relatorio.md
"""

import argparse
import datetime
import html as _html
import json
import os
import re


PLACEHOLDER = "_(preencher)_"


def carregar_json(caminho, alvo):
    """Le a lista de APs do JSON e devolve o AP que casa com `alvo`."""
    if not caminho or not os.path.exists(caminho):
        return None
    try:
        with open(caminho, encoding="utf-8") as f:
            redes = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(redes, list) or not redes:
        return None
    if alvo:
        a = alvo.lower()
        for r in redes:
            if a in r.get("ssid", "").lower() or a in r.get("bssid", "").lower():
                return r
    # sem alvo: pega o de maior sinal (ou o primeiro)
    def sinal(r):
        s = str(r.get("signal", "0")).rstrip("%")
        return int(s) if s.isdigit() else 0
    return max(redes, key=sinal)


def val(x, padrao=PLACEHOLDER):
    x = (str(x).strip() if x is not None else "")
    return x if x else padrao


METODOS = {
    "wps": "WPS Pixie Dust (reaver + pixiewps)",
    "handshake": "Captura de handshake WPA2 + ataque de dicionário (aircrack-ng)",
    "pmkid": "Captura de PMKID + ataque de dicionário (hashcat -m 22000)",
}


def montar(args, ap):
    ap = ap or {}
    ssid = args.ssid or ap.get("ssid")
    bssid = args.bssid or ap.get("bssid")
    canal = args.canal or ap.get("channel")
    freq = ap.get("freq_mhz")
    freq_txt = f"{freq} MHz" if freq else PLACEHOLDER
    banda = ap.get("band")
    cripto = ap.get("cipher") or ap.get("auth")
    sinal = ap.get("signal")
    metodo_txt = METODOS.get((args.metodo or "").lower(), val(args.metodo))
    hoje = datetime.date.today().strftime("%d/%m/%Y")

    senha_txt = f"`{args.senha}`" if args.senha else PLACEHOLDER
    pin_linha = (f"- **PIN do WPS recuperado:** `{args.wps_pin}`\n"
                 if args.wps_pin else "")

    return f"""# Relatório — Auditoria de Rede Wi-Fi

**Disciplina:** Segurança da Informação
**Atividade:** Quebra de senha e levantamento de parâmetros de rede sem fio
**Autor(es):** {val(args.autor)}
**Data:** {hoje}
**Equipamento alvo:** {val(args.modelo, "TP-Link AC750 (Archer C20)")}

> Atividade realizada em laboratório, sobre equipamento disponibilizado pelo
> professor **com autorização expressa** para fins didáticos. Nenhuma rede de
> terceiros foi auditada.

---

## 1. Parâmetros da rede (reconhecimento)

Dados coletados **sem conexão prévia** à rede (extraídos do beacon do roteador),
usando `wifi_recon.py` (`netsh` no Windows / `nmcli` no Linux).

| Parâmetro | Valor |
|---|---|
| SSID (nome da rede) | {val(ssid)} |
| BSSID (MAC do roteador) | {val(bssid)} |
| Canal | {val(canal)} |
| Frequência | {freq_txt} |
| Banda | {val(banda)} |
| Criptografia | {val(cripto)} |
| Sinal | {val(sinal)} |
| IP do roteador (gateway) | {val(args.ip)} |

> O **IP do roteador** só é obtido **após** conectar à rede (atribuição via
> DHCP); por isso é a última informação levantada, servindo também como prova
> de que a quebra teve sucesso.

---

## 2. Metodologia da quebra

- **Vetor utilizado:** {metodo_txt}
- **Ambiente:** Kali Linux (modo monitor em adaptador compatível)
- **Ferramentas:** `aircrack-ng`, `reaver`/`pixiewps`, `hcxdumptool`/`hashcat`
{pin_linha}
### Passos executados
1. Ativação do modo monitor na interface (`airmon-ng start`).
2. Varredura das redes ao alcance (`airodump-ng` / `wash`).
3. Execução do ataque pelo vetor acima.
4. Recuperação da senha e conexão à rede para confirmar o IP do gateway.

---

## 3. Resultado

- **Senha recuperada:** {senha_txt}
- **Tempo aproximado do ataque:** {val(args.tempo)}

---

## 4. Análise e recomendações de segurança

- Ataques de dicionário só funcionam se a senha estiver na wordlist — **senhas
  longas e aleatórias** inviabilizam esse vetor.
- Roteadores TP-Link antigos trazem **WPS ativo** e vulnerável a *Pixie Dust*;
  recomenda-se **desativar o WPS** no painel (`192.168.0.1`).
- Usar **WPA2 com senha forte** (ou WPA3, quando disponível) e trocar as
  credenciais padrão (`admin`/`admin`).

---

## 5. Evidências

{val(args.evidencias, "_(anexar prints do scan, da captura e da senha recuperada)_")}

---

_Relatório gerado automaticamente por `gerar_relatorio.py` — ferramenta da atividade._
"""


def markdown_para_html(md, titulo):
    """Converte o subconjunto de Markdown usado no relatorio em HTML estilizado."""
    linhas = md.splitlines()
    corpo = []
    i = 0
    while i < len(linhas):
        ln = linhas[i]
        # Tabelas (bloco contiguo que comeca e termina com '|')
        if ln.strip().startswith("|"):
            tbl = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                tbl.append(linhas[i]); i += 1
            corpo.append(_tabela_html(tbl))
            continue
        if ln.startswith("# "):
            corpo.append(f"<h1>{_inl(ln[2:])}</h1>")
        elif ln.startswith("## "):
            corpo.append(f"<h2>{_inl(ln[3:])}</h2>")
        elif ln.startswith("### "):
            corpo.append(f"<h3>{_inl(ln[4:])}</h3>")
        elif ln.startswith("> "):
            corpo.append(f'<blockquote>{_inl(ln[2:])}</blockquote>')
        elif ln.strip() == "---":
            corpo.append("<hr>")
        elif re.match(r"^\d+\.\s", ln):
            itens = []
            while i < len(linhas) and re.match(r"^\d+\.\s", linhas[i]):
                itens.append(f"<li>{_inl(re.sub(r'^\\d+\\.\\s', '', linhas[i]))}</li>")
                i += 1
            corpo.append("<ol>" + "".join(itens) + "</ol>")
            continue
        elif ln.startswith("- "):
            itens = []
            while i < len(linhas) and linhas[i].startswith("- "):
                itens.append(f"<li>{_inl(linhas[i][2:])}</li>"); i += 1
            corpo.append("<ul>" + "".join(itens) + "</ul>")
            continue
        elif ln.strip():
            corpo.append(f"<p>{_inl(ln)}</p>")
        i += 1

    return _PAGINA.format(titulo=_html.escape(titulo), corpo="\n".join(corpo))


def _inl(txt):
    """Formatacao inline: escapa HTML, depois aplica **negrito** e `codigo`."""
    txt = _html.escape(txt)
    txt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", txt)
    txt = re.sub(r"`(.+?)`", r"<code>\1</code>", txt)
    return txt


def _tabela_html(linhas):
    linhas = [l for l in linhas if set(l.strip()) - set("|-: ")]  # tira separador
    def celulas(l):
        return [c.strip() for c in l.strip().strip("|").split("|")]
    if not linhas:
        return ""
    cab = celulas(linhas[0])
    out = ["<table><thead><tr>"]
    out += [f"<th>{_inl(c)}</th>" for c in cab]
    out.append("</tr></thead><tbody>")
    for l in linhas[1:]:
        out.append("<tr>" + "".join(f"<td>{_inl(c)}</td>" for c in celulas(l)) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


_PAGINA = """<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<style>
  :root {{ --bg:#0d1117; --card:#161b22; --fg:#e6edf3; --mut:#8b949e;
           --acc:#1f6feb; --ok:#3fb950; --line:#30363d; --warn:#d29922; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
          font:16px/1.65 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:860px; margin:0 auto; padding:32px 20px 80px; }}
  h1 {{ font-size:1.9rem; margin:0 0 .2em; border-bottom:3px solid var(--acc);
        padding-bottom:.3em; }}
  h2 {{ font-size:1.3rem; margin:2em 0 .6em; color:#58a6ff; }}
  h3 {{ font-size:1.05rem; margin:1.4em 0 .4em; color:var(--fg); }}
  p {{ margin:.5em 0; }}
  code {{ background:#010409; color:#79c0ff; padding:.12em .4em; border-radius:6px;
          font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.9em; }}
  blockquote {{ margin:1em 0; padding:.8em 1.1em; background:#1c2128;
                border-left:4px solid var(--warn); border-radius:0 8px 8px 0;
                color:var(--mut); }}
  hr {{ border:0; border-top:1px solid var(--line); margin:2em 0; }}
  table {{ width:100%; border-collapse:collapse; margin:1em 0;
           background:var(--card); border-radius:10px; overflow:hidden; }}
  th,td {{ text-align:left; padding:.7em 1em; border-bottom:1px solid var(--line); }}
  th {{ background:#1f2630; font-weight:600; }}
  tr:last-child td {{ border-bottom:0; }}
  td code,strong {{ color:var(--ok); }}
  ul,ol {{ padding-left:1.4em; }}
  li {{ margin:.25em 0; }}
  @media print {{ body {{ background:#fff; color:#111; }}
    .wrap{{max-width:100%}} blockquote{{color:#555}}
    table,th,td{{border-color:#ccc}} th{{background:#eee}} code{{background:#eee;color:#06c}} }}
</style></head>
<body><div class="wrap">
{corpo}
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description="Gera o relatorio da auditoria Wi-Fi.")
    ap.add_argument("--json", help="JSON do wifi_recon.py")
    ap.add_argument("--target", help="SSID/BSSID alvo dentro do JSON")
    ap.add_argument("--ssid")
    ap.add_argument("--bssid")
    ap.add_argument("--canal")
    ap.add_argument("--ip", help="IP do roteador (gateway)")
    ap.add_argument("--metodo", help="wps | handshake | pmkid")
    ap.add_argument("--senha", help="senha recuperada")
    ap.add_argument("--wps-pin", dest="wps_pin", help="PIN do WPS recuperado")
    ap.add_argument("--tempo", help="tempo aproximado do ataque")
    ap.add_argument("--autor", help="nome do(s) autor(es)")
    ap.add_argument("--modelo", help="modelo do equipamento alvo")
    ap.add_argument("--evidencias", help="texto/legenda das evidencias")
    ap.add_argument("--saida", default="relatorio.md", help="arquivo de saida (.md)")
    ap.add_argument("--html", metavar="ARQ",
                    help="tambem gera versao HTML estilizada (imprimivel em PDF)")
    args = ap.parse_args()

    ap_dados = carregar_json(args.json, args.target)
    texto = montar(args, ap_dados)
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"[+] Relatorio gerado em: {args.saida}")
    if args.html:
        pagina = markdown_para_html(texto, "Relatorio - Auditoria Wi-Fi")
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(pagina)
        print(f"[+] Versao HTML gerada em: {args.html} "
              "(abra no navegador e use Imprimir > Salvar como PDF)")
    if ap_dados:
        print(f"[*] Dados do AP '{ap_dados.get('ssid')}' importados do JSON.")
    faltando = texto.count(PLACEHOLDER)
    if faltando:
        print(f"[!] {faltando} campo(s) ainda com '{PLACEHOLDER}' para completar.")


if __name__ == "__main__":
    main()
