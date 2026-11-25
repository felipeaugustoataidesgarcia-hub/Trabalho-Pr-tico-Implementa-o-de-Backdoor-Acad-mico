# wifi-recon — Ferramenta de auditoria de redes Wi-Fi

Atividade prática de Segurança da Informação. Ferramenta para **extrair os dados
de uma rede Wi-Fi** (SSID, MAC/BSSID, canal, frequência, criptografia e IP do
roteador) e, de forma assistida, **auditar a senha WPA/WPA2** do equipamento
disponibilizado pelo professor em laboratório.

> ⚠️ **Uso autorizado apenas.** Rode somente contra o modem/roteador liberado
> para a aula. Acessar redes de terceiros sem autorização é crime no Brasil
> (Lei 12.737/2012 — invasão de dispositivo informático).

## Componentes

| Arquivo | Função | Onde roda |
|---|---|---|
| `wifi_audit.sh` | **Menu central** que une tudo, pré-configurado para o TP-Link AC750 | **Kali Linux** |
| `wifi_recon.py` | Extrai SSID, BSSID, canal, frequência, banda, criptografia e IP do gateway | **Windows e Linux** (Python 3, sem dependências externas) |
| `wifi_crack.sh` | Orquestra WPS (Pixie Dust) / handshake / PMKID + quebra por dicionário | **Kali Linux** (aircrack-ng/reaver/hashcat) |

## Início rápido (Kali)

```bash
sudo apt update && sudo apt install -y aircrack-ng hcxdumptool hcxtools \
     hashcat reaver pixiewps
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
sudo ./wifi_audit.sh          # abre o menu com a ordem de ataque recomendada
```

## Alvo da atividade: TP-Link AC750 (Archer C20)

| Característica | Valor padrão |
|---|---|
| Bandas | 2.4 GHz (canais 1–13) e 5 GHz (canais 36+) |
| Criptografia | WPA/WPA2-PSK (AES/CCMP) |
| Gateway | `192.168.0.1` (login `admin`/`admin`) |
| SSID de fábrica | `TP-Link_XXXX` |
| WPS | normalmente **ativo** e, em firmwares antigos, vulnerável a **Pixie Dust** (só na banda 2.4 GHz) |

**Ordem de ataque recomendada** (do mais rápido ao mais lento):

1. **WPS Pixie Dust** — `sudo ./wifi_crack.sh -i wlan0 -m wps` — recupera o PIN do WPS offline e, com ele, a senha WPA. Pode levar segundos. É o vetor clássico contra TP-Link; use o **BSSID de 2.4 GHz**.
2. **PMKID** — `sudo ./wifi_crack.sh -i wlan0 -m pmkid` — rápido e não precisa de cliente conectado.
3. **Handshake + dicionário** — `sudo ./wifi_crack.sh -i wlan0 -m handshake -b <BSSID> -c <canal>`.

> Firmwares mais novos do Archer C20 fazem *lockout* do WPS após algumas tentativas. Se o Pixie Dust travar (`WPS pin not found` / `rate limiting`), parta para PMKID/handshake.

---

## 1. Reconhecimento — `wifi_recon.py`

Extrai os dados que **não precisam de conexão** (ficam no beacon do roteador) e,
se você já estiver conectado, também o **IP do roteador**.

```bash
python wifi_recon.py                     # lista todas as redes ao alcance
python wifi_recon.py --target RedeDoProf # filtra por SSID ou BSSID
python wifi_recon.py --json r.json --csv r.csv   # exporta para o relatório
```

- **Windows:** usa `netsh wlan show networks mode=bssid` (funciona com Windows
  em português). Nenhuma instalação necessária.
- **Linux:** usa `nmcli` (ou `iw`). Também não exige modo monitor para o scan.

Saída de exemplo:

```
SSID                      BSSID (MAC)          CANAL   FREQ      BANDA     CRIPTO     SINAL
RedeDoProfessor           a4:2b:b0:11:22:33    6       2437 MHz  2.4 GHz   CCMP       92%

[*] IP do roteador: indisponivel - voce NAO esta conectado a nenhuma rede.
```

### O que precisa (ou não) de conexão

| Dado | Precisa estar conectado? |
|---|---|
| SSID, BSSID (MAC), canal, frequência, criptografia | ❌ Não — vem do beacon |
| IP do roteador (gateway) | ✅ Sim — só aparece após entrar na rede (DHCP) |

Por isso o **IP é a última etapa**: depois de quebrar a senha e conectar, rode
`wifi_recon.py` de novo e ele mostra o gateway (`ipconfig`/`ip route`) e
correlaciona com o MAC pela tabela ARP.

---

## 2. Quebra da senha — `wifi_crack.sh` (Kali)

A captura do handshake exige **modo monitor**, que o Windows não oferece
nativamente. Use o **Kali Linux** (Live USB na própria máquina, ou VM com um
adaptador Wi-Fi USB compatível — chipset Atheros/Ralink/Realtek).

Instale as dependências:

```bash
sudo apt update && sudo apt install -y aircrack-ng hcxdumptool hcxtools \
     hashcat reaver pixiewps
sudo gunzip /usr/share/wordlists/rockyou.txt.gz   # descompacta a wordlist
```

Use o menu (mais simples):

```bash
sudo ./wifi_audit.sh
```

Ou chame um vetor direto:

```bash
# WPS Pixie Dust (recomendado para TP-Link; use o BSSID de 2.4 GHz)
sudo ./wifi_crack.sh -i wlan0 -m wps -b AA:BB:CC:DD:EE:FF -c 6

# Handshake clássico (força reconexão de um cliente via deauth)
sudo ./wifi_crack.sh -i wlan0 -m handshake -b AA:BB:CC:DD:EE:FF -c 6

# PMKID — funciona mesmo SEM nenhum cliente conectado ao modem
sudo ./wifi_crack.sh -i wlan0 -m pmkid -b AA:BB:CC:DD:EE:FF -c 6
```

Cada vetor faz, em ordem: modo monitor → scan → ataque → recuperação da senha.
Ao sair, a interface é restaurada automaticamente (`trap`).

---

## Fluxo completo da atividade

| # | Etapa | Ferramenta | Conectado? |
|---|---|---|---|
| 1 | MAC, canal, frequência, criptografia | `wifi_recon.py` | ❌ |
| 2 | Capturar handshake / PMKID | `wifi_crack.sh` | ❌ |
| 3 | Quebrar a senha offline | `wifi_crack.sh` | ❌ |
| 4 | Conectar com a senha obtida | SO | ✅ |
| 5 | IP do roteador | `wifi_recon.py` | ✅ |

## Observações para o relatório

- O ataque de dicionário **só encontra a senha se ela estiver na wordlist** —
  senhas longas e aleatórias são inviáveis. Boa conclusão sobre a importância de
  senhas fortes.
- WPA3 (SAE) não é vulnerável à captura de handshake tradicional; o script é
  voltado a WPA/WPA2-PSK.
- Se o roteador tiver **WPS** ativo, vale testar `reaver`/`bully` (ataque ao PIN)
  como vetor adicional.
