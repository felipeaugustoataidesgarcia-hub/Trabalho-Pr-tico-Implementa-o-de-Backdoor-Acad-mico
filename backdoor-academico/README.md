# Trabalho Prático — Implementação de Backdoor Acadêmico

## Segurança da Informação — Engenharia de Software

### Objetivo

Este projeto demonstra, em ambiente controlado, o funcionamento de uma comunicação cliente/servidor TCP utilizando sockets e a execução remota de comandos do sistema operacional.

**Atenção:** o programa foi configurado para aceitar conexões somente em `127.0.0.1` (loopback), evitando exposição à rede. Utilize exclusivamente em equipamento próprio ou ambiente autorizado.

## Estrutura

```text
/
├── src/
│   ├── servidor.c
│   └── cliente.c
├── .gitignore
├── README.md
└── LICENSE
```

## Componentes

* Nome: Felipe Augusto Ataides Garcia
* Matrícula: 202312691

* Nome: Israel Philipe Guimarães Pereira
* Matrícula: 202312288




## Requisitos

Para compilar em Windows, é necessário um compilador C com suporte ao Winsock, como MinGW-w64.

Para Linux, utilize GCC.

## Compilação — Windows / MinGW

Na pasta raiz do projeto:

```bash
gcc src/servidor.c -o servidor.exe -lws2\_32
gcc src/cliente.c -o cliente.exe -lws2\_32
```

## Execução

Abra dois terminais.

### Terminal 1 — servidor

```bash
servidor.exe
```

O servidor ficará aguardando em:

```text
127.0.0.1:4444
```

### Terminal 2 — cliente

```bash
cliente.exe
```

Depois de conectado, podem ser utilizados comandos simples do sistema.

Exemplos no Windows:

```text
whoami
hostname
ver
ipconfig
dir
```

Para encerrar:

```text
exit
```

## Exemplo de demonstração

Cliente:

```text
Conectado.
Digite comandos do sistema. Use 'exit' para encerrar.

Comando> hostname

--- Saida ---
PC-EXEMPLO

Comando> whoami

--- Saida ---
PC-EXEMPLO\\usuario

Comando> exit
Conexao encerrada.
```

## Funcionamento técnico

O servidor:

1. Cria um socket TCP.
2. Utiliza `127.0.0.1:4444` para o serviço.
3. Executa `bind()` e `listen()`.
4. Aguarda uma conexão através de `accept()`.
5. Recebe comandos por `recv()`.
6. Executa o comando no shell do sistema.
7. Captura a saída.
8. Envia a saída ao cliente através de `send()`.
9. Encerra a sessão quando recebe `exit` ou `quit`.

O cliente:

1. Cria um socket TCP.
2. Conecta ao servidor através de `connect()`.
3. Lê comandos digitados pelo usuário.
4. Envia os comandos.
5. Recebe a resposta.
6. Exibe a saída.
7. Encerra a conexão com `exit` ou `quit`.

## Análise de Segurança — Visão Blue Team

Um backdoor que recebe comandos pela rede e executa processos no sistema apresenta comportamento que pode ser identificado por uma equipe de defesa. Entre as medidas estão o monitoramento de portas e conexões TCP, análise de processos em execução, regras de firewall, controle de aplicações e soluções EDR. A abertura inesperada de uma porta, especialmente associada a um processo que inicia um shell do sistema, pode ser um indicador de comprometimento. O princípio do menor privilégio também reduz o impacto, pois limita as permissões disponíveis ao processo. Em um ambiente corporativo, o tráfego de rede deve ser monitorado e conexões não autorizadas devem ser bloqueadas.

## Limitações e escopo acadêmico

Este projeto é propositalmente restrito ao endereço de loopback `127.0.0.1`, não implementa persistência, não tenta ocultar processos e não possui mecanismos de evasão. O objetivo é demonstrar conceitos de sockets TCP, comunicação cliente/servidor e interação controlada com o shell.

## Licença

Projeto acadêmico para fins educacionais.

