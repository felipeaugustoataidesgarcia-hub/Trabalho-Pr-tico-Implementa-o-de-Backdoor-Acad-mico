/*
 * Trabalho Pratico - Backdoor Academico
 * Cliente TCP para laboratorio local.
 *
 * Uso EXCLUSIVO em 127.0.0.1 ou ambiente autorizado.
 *
 * Compilacao (Windows MinGW):
 *   gcc src/cliente.c -o cliente.exe -lws2_32
 *
 * Execucao:
 *   cliente.exe
 */

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")
typedef SOCKET socket_t;
#define CLOSESOCK closesocket
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int socket_t;
#define INVALID_SOCKET (-1)
#define CLOSESOCK close
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SERVER_IP "127.0.0.1"
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

int main(void) {
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "Erro ao iniciar Winsock.\n");
        return 1;
    }
#endif

    socket_t cliente = socket(AF_INET, SOCK_STREAM, 0);
    if (cliente == INVALID_SOCKET) {
        fprintf(stderr, "Erro ao criar socket.\n");
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    struct sockaddr_in servidor;
    memset(&servidor, 0, sizeof(servidor));
    servidor.sin_family = AF_INET;
    servidor.sin_port = htons(PORT);
    inet_pton(AF_INET, SERVER_IP, &servidor.sin_addr);

    printf("Conectando a %s:%d...\n", SERVER_IP, PORT);

    if (connect(cliente, (struct sockaddr *)&servidor, sizeof(servidor)) < 0) {
        fprintf(stderr, "Nao foi possivel conectar. Execute primeiro o servidor.\n");
        CLOSESOCK(cliente);
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    printf("Conectado.\n");
    printf("Digite comandos do sistema. Use 'exit' para encerrar.\n\n");

    char comando[BUFFER_SIZE];
    char buffer[BUFFER_SIZE];

    while (1) {
        printf("Comando> ");
        fflush(stdout);

        if (!fgets(comando, sizeof(comando), stdin)) break;

        if (!enviar_tudo(cliente, comando, strlen(comando))) {
            fprintf(stderr, "Erro ao enviar comando.\n");
            break;
        }

        char copia[BUFFER_SIZE];
        strncpy(copia, comando, sizeof(copia) - 1);
        copia[sizeof(copia) - 1] = '\0';

        size_t len = strlen(copia);
        while (len > 0 && (copia[len - 1] == '\n' || copia[len - 1] == '\r')) {
            copia[--len] = '\0';
        }

        if (strcmp(copia, "exit") == 0 || strcmp(copia, "quit") == 0) {
            printf("Conexao encerrada.\n");
            break;
        }

        printf("\n--- Saida ---\n");

        int recebido;
        while ((recebido = recv(cliente, buffer, sizeof(buffer) - 1, 0)) > 0) {
            buffer[recebido] = '\0';
            fputs(buffer, stdout);

            /* O servidor envia uma resposta por comando.
               Para comandos comuns, uma leitura com pequeno timeout
               permite detectar o fim da resposta sem manter conexao aberta. */
#ifdef _WIN32
            DWORD timeout = 150;
            setsockopt(cliente, SOL_SOCKET, SO_RCVTIMEO, (const char *)&timeout, sizeof(timeout));
#else
            struct timeval tv = {0, 150000};
            setsockopt(cliente, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
#endif
            break;
        }

        if (recebido <= 0) {
            printf("\n[Sem resposta ou conexao encerrada.]\n");
        }

        printf("\n-------------\n\n");
    }

    CLOSESOCK(cliente);

#ifdef _WIN32
    WSACleanup();
#endif

    return 0;
}
