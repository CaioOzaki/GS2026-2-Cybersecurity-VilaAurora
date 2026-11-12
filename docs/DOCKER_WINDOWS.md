# Ubuntu/WSL2 e Docker - reprodução e gravação

O piloto desta entrega foi executado no Ubuntu 24.04/WSL2 com Docker Desktop. A instalação é necessária apenas em outro computador; neste computador ela já foi concluída.

1. No PowerShell administrador: `wsl --install -d Ubuntu-24.04`. Reinicie se solicitado, abra o Ubuntu e crie usuário/senha. Não compartilhe a senha.
2. Instale Docker Desktop pelo site oficial, use o mecanismo WSL2 e habilite Ubuntu em Settings > WSL integration. Confirme `docker version` no Ubuntu.
3. Clone o repositório no diretório pessoal Linux. Instale Python/venv e siga a seção 4 do README. Não prepare as chaves com os containers em execução.
4. `docker compose ps` deve mostrar cinco serviços em execução. `python3 docker/validate.py` gera nove verificações de fluxo e privilégios. O handshake está em `evidence/docker/wireguard.txt`; o HTTPS mTLS via túnel faz parte de `network.json`.
5. O painel está em http://127.0.0.1:8088/ . Credenciais privadas: `.runtime/docker/edge/credentials.json`. Cadastre o TOTP em autenticador SHA-1, seis dígitos, 30 s. O código é de uso único. Faça login antes de gravar; não filme senha, semente ou QR.
6. `python3 docker/chaos.py` realiza 1802 s reais de corte da interface WireGuard. Não execute outro teste ou reinício em paralelo. `chaos-progress.json` permite acompanhar a fila; `chaos-tunnel.json` só confirma o resultado final. O corte é de rede virtual, não de fibra física.
7. Para demonstrar uma interrupção curta em vídeo, rode `python3 docker/short_regression.py` e atualize o painel. Ele desliga o túnel por 45 s, restaura e confere a reconciliação. Essa regressão não substitui o teste longo.
8. No README estão os probes de Mosquitto: certificado válido, certificado ausente, CA estrangeira, tópico indevido, serial revogado e serial novo. O procedimento de rotação reinicia a borda e produz uma breve interrupção controlada.
9. Antes de repetir coletas, preserve os arquivos de evidência da entrega. Para encerrar o laboratório: `docker compose down`. Nunca envie `.runtime/`, credenciais, chaves privadas ou bancos operacionais ao GitHub.

## Limites preservados no relatório

O corte longo foi medido na versão-base; depois a revisão acrescentou CRL, processos sem root e visualizador, com regressão curta e repetição dos testes. São fases distintas. Sensores são geradores de telemetria, não hardware físico. Os cinco espaços foram exercitados logicamente na versão nativa; o piloto Linux é uma UBS. Não há SSH/RDP remoto nem MFA humano no protocolo WireGuard. A aplicação oferece MFA no painel. O painel HTTP está restrito ao laboratório/loopback; instalar HTTPS antes de disponibilizá-lo em ambiente distribuído. O relógio absoluto ainda requer verificação NTP e a energia física não foi medida.

Fontes oficiais: https://docs.docker.com/desktop/setup/install/windows-install/ ; https://docs.docker.com/desktop/features/wsl/ ; https://learn.microsoft.com/windows/wsl/install ; https://www.wireguard.com/quickstart/ ; https://mosquitto.org/man/mosquitto-conf-5.html .
