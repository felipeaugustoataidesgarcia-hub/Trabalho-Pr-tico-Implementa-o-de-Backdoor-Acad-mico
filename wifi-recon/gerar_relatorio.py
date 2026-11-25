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
import json
import os


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
    args = ap.parse_args()

    ap_dados = carregar_json(args.json, args.target)
    texto = montar(args, ap_dados)
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"[+] Relatorio gerado em: {args.saida}")
    if ap_dados:
        print(f"[*] Dados do AP '{ap_dados.get('ssid')}' importados do JSON.")
    faltando = texto.count(PLACEHOLDER)
    if faltando:
        print(f"[!] {faltando} campo(s) ainda com '{PLACEHOLDER}' para completar.")


if __name__ == "__main__":
    main()
