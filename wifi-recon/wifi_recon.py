#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wifi_recon.py - Ferramenta de reconhecimento de redes Wi-Fi.

Extrai, para cada rede ao alcance, SEM precisar estar conectado:
    - SSID (nome da rede)
    - BSSID (endereco MAC do roteador)
    - Canal
    - Frequencia / Banda (2.4 GHz ou 5 GHz)
    - Autenticacao / Criptografia
    - Sinal

E, quando ja conectado a uma rede, descobre o IP do roteador (gateway)
e correlaciona esse IP com o MAC via tabela ARP.

Funciona em Windows (via 'netsh') e em Linux (via 'nmcli' ou 'iw'),
inclusive com Windows em portugues.

Uso academico - auditoria de redes autorizada (lab de seguranca).

Exemplos:
    python wifi_recon.py
    python wifi_recon.py --target MinhaRede
    python wifi_recon.py --json saida.json --csv saida.csv
"""

import argparse
import csv
import json
import platform
import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def run(cmd):
    """Executa um comando e devolve stdout (string), ou '' em caso de erro."""
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            timeout=60,
        )
        return out.stdout or ""
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        return ""


def canal_para_frequencia(canal):
    """Converte numero do canal em (frequencia_MHz, banda). Retorna (None, '')."""
    try:
        ch = int(canal)
    except (TypeError, ValueError):
        return None, ""
    if 1 <= ch <= 13:
        return 2407 + ch * 5, "2.4 GHz"
    if ch == 14:
        return 2484, "2.4 GHz"
    if 32 <= ch <= 177:          # faixa de 5 GHz
        return 5000 + ch * 5, "5 GHz"
    return None, ""


# ---------------------------------------------------------------------------
# Coleta - Windows (netsh)
# ---------------------------------------------------------------------------

# Rotulos aceitos em ingles e portugues (netsh e localizado).
_ROTULOS = {
    "ssid":   ("SSID",),
    "auth":   ("Authentication", "Autenticação", "Autenticacao"),
    "cipher": ("Encryption", "Criptografia"),
    "bssid":  ("BSSID",),
    "signal": ("Signal", "Sinal"),
    "radio":  ("Radio type", "Tipo de rádio", "Tipo de radio"),
    "band":   ("Band", "Banda"),
    "channel": ("Channel", "Canal"),
}


def _valor_apos_dois_pontos(linha):
    return linha.split(":", 1)[1].strip() if ":" in linha else ""


def _casa_rotulo(linha, chave):
    """True se a linha (antes do ':') comeca com algum rotulo da chave."""
    antes = linha.split(":", 1)[0].strip().lower()
    return any(antes.startswith(r.lower()) for r in _ROTULOS[chave])


def coletar_windows():
    saida = run(["netsh", "wlan", "show", "networks", "mode=bssid"])
    if not saida:
        return []

    redes = []
    rede_atual = None   # dados de SSID (compartilhados por varios BSSIDs)
    ap_atual = None     # um access point (uma linha BSSID)

    for linha in saida.splitlines():
        strip = linha.strip()
        if not strip:
            continue

        # Inicio de um novo SSID: "SSID 3 : NomeDaRede"
        if re.match(r"^SSID\s+\d+\s*:", strip):
            rede_atual = {
                "ssid": _valor_apos_dois_pontos(strip) or "<oculto>",
                "auth": "",
                "cipher": "",
            }
            ap_atual = None
            continue

        if rede_atual is None:
            continue

        if _casa_rotulo(strip, "auth"):
            rede_atual["auth"] = _valor_apos_dois_pontos(strip)
            continue
        if _casa_rotulo(strip, "cipher"):
            rede_atual["cipher"] = _valor_apos_dois_pontos(strip)
            continue

        # Inicio de um BSSID: "BSSID 1 : xx:xx:xx:xx:xx:xx"
        if re.match(r"^BSSID\s+\d+\s*:", strip):
            ap_atual = {
                "ssid": rede_atual["ssid"],
                "bssid": _valor_apos_dois_pontos(strip).lower(),
                "auth": rede_atual["auth"],
                "cipher": rede_atual["cipher"],
                "signal": "",
                "radio": "",
                "band": "",
                "channel": "",
                "freq_mhz": None,
            }
            redes.append(ap_atual)
            continue

        if ap_atual is None:
            continue

        if _casa_rotulo(strip, "signal"):
            ap_atual["signal"] = _valor_apos_dois_pontos(strip)
        elif _casa_rotulo(strip, "radio"):
            ap_atual["radio"] = _valor_apos_dois_pontos(strip)
        elif _casa_rotulo(strip, "band"):
            ap_atual["band"] = _valor_apos_dois_pontos(strip)
        elif _casa_rotulo(strip, "channel"):
            ap_atual["channel"] = _valor_apos_dois_pontos(strip)

    # Preenche frequencia/banda a partir do canal quando faltar.
    for ap in redes:
        freq, banda = canal_para_frequencia(ap["channel"])
        ap["freq_mhz"] = freq
        if not ap["band"]:
            ap["band"] = banda
    return redes


# ---------------------------------------------------------------------------
# Coleta - Linux (nmcli, com fallback para iw)
# ---------------------------------------------------------------------------

def coletar_linux():
    # nmcli nao precisa de modo monitor nem de root para escanear.
    campos = "SSID,BSSID,CHAN,FREQ,SECURITY,SIGNAL"
    saida = run(["nmcli", "-t", "-f", campos, "device", "wifi", "list"])
    redes = []
    if saida:
        for linha in saida.splitlines():
            # nmcli escapa ':' do BSSID como '\:' no modo -t
            partes = re.split(r"(?<!\\):", linha)
            partes = [p.replace("\\:", ":") for p in partes]
            if len(partes) < 6:
                continue
            ssid, bssid, chan, freq, sec, signal = partes[:6]
            freq_mhz = None
            m = re.search(r"\d+", freq)
            if m:
                freq_mhz = int(m.group())
            _, banda = canal_para_frequencia(chan)
            if not banda and freq_mhz:
                banda = "5 GHz" if freq_mhz >= 5000 else "2.4 GHz"
            redes.append({
                "ssid": ssid or "<oculto>",
                "bssid": bssid.lower(),
                "auth": sec,
                "cipher": sec,
                "signal": signal + "%" if signal.isdigit() else signal,
                "radio": "",
                "band": banda,
                "channel": chan,
                "freq_mhz": freq_mhz,
            })
    return redes


# ---------------------------------------------------------------------------
# Gateway (IP do roteador) + ARP
# ---------------------------------------------------------------------------

def descobrir_gateway():
    """Devolve (ip_gateway, mac_gateway) da rede atual, ou (None, None)."""
    sistema = platform.system()
    gw_ip = None

    if sistema == "Windows":
        saida = run(["ipconfig"])
        # Procura "Gateway Padrão" / "Default Gateway" seguido de um IPv4.
        m = re.search(
            r"(?:Default Gateway|Gateway Padr[ãa]o)[ .]*:\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})",
            saida,
        )
        if m:
            gw_ip = m.group(1)
    else:
        saida = run(["ip", "route"])
        m = re.search(r"default via ([0-9]{1,3}(?:\.[0-9]{1,3}){3})", saida)
        if m:
            gw_ip = m.group(1)

    if not gw_ip:
        return None, None

    # Correlaciona IP -> MAC pela tabela ARP.
    arp = run(["arp", "-a"]) if sistema == "Windows" else run(["ip", "neigh"])
    mac = None
    for linha in arp.splitlines():
        if gw_ip in linha:
            m = re.search(r"([0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5})", linha)
            if m:
                mac = m.group(1).replace("-", ":").lower()
                break
    return gw_ip, mac


# ---------------------------------------------------------------------------
# Saida
# ---------------------------------------------------------------------------

def imprimir_tabela(redes):
    if not redes:
        print("Nenhuma rede encontrada. "
              "Verifique se o Wi-Fi esta ligado e se ha permissao de scan.")
        return
    cab = ("SSID", "BSSID (MAC)", "CANAL", "FREQ", "BANDA", "CRIPTO", "SINAL")
    larg = [24, 19, 6, 8, 8, 14, 7]
    linha_fmt = "  ".join("{:<%d}" % w for w in larg)
    print(linha_fmt.format(*cab))
    print("-" * (sum(larg) + 2 * len(larg)))
    for r in sorted(redes, key=lambda x: x["ssid"].lower()):
        freq = f"{r['freq_mhz']} MHz" if r["freq_mhz"] else "-"
        cripto = (r["cipher"] or r["auth"] or "-")[:14]
        print(linha_fmt.format(
            r["ssid"][:24], r["bssid"][:19], str(r["channel"])[:6],
            freq[:8], (r["band"] or "-")[:8], cripto, str(r["signal"])[:7],
        ))


def main():
    ap = argparse.ArgumentParser(
        description="Reconhecimento de redes Wi-Fi (uso academico/autorizado)."
    )
    ap.add_argument("--target", help="filtra por SSID ou BSSID (substring)")
    ap.add_argument("--json", metavar="ARQ", help="salva resultado em JSON")
    ap.add_argument("--csv", metavar="ARQ", help="salva resultado em CSV")
    ap.add_argument("--no-gateway", action="store_true",
                    help="nao tenta descobrir o IP do roteador")
    args = ap.parse_args()

    sistema = platform.system()
    print(f"[*] Sistema detectado: {sistema}")

    if sistema == "Windows":
        redes = coletar_windows()
    elif sistema == "Linux":
        redes = coletar_linux()
    else:
        print(f"[!] Sistema '{sistema}' nao suportado diretamente.")
        sys.exit(1)

    if args.target:
        alvo = args.target.lower()
        redes = [r for r in redes
                 if alvo in r["ssid"].lower() or alvo in r["bssid"].lower()]

    print(f"[*] {len(redes)} access point(s) encontrado(s)\n")
    imprimir_tabela(redes)

    if not args.no_gateway:
        gw_ip, gw_mac = descobrir_gateway()
        print()
        if gw_ip:
            print(f"[*] IP do roteador (gateway) : {gw_ip}")
            print(f"[*] MAC do gateway (ARP)     : {gw_mac or 'nao resolvido'}")
            print("    (voce esta conectado a esta rede)")
        else:
            print("[*] IP do roteador: indisponivel - voce NAO esta conectado "
                  "a nenhuma rede.")
            print("    O IP so aparece depois de entrar na rede (DHCP); "
                  "o resto dos dados acima nao precisa de conexao.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(redes, f, ensure_ascii=False, indent=2)
        print(f"\n[+] JSON salvo em {args.json}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(redes[0].keys()) if redes else [])
            w.writeheader()
            w.writerows(redes)
        print(f"[+] CSV salvo em {args.csv}")


if __name__ == "__main__":
    main()
