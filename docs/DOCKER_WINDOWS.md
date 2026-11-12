# Instalar Docker no Windows e validar o piloto

Esta etapa depende de instalação e possível reinicialização. Salve seus trabalhos antes. Não foi executada automaticamente.

1. Abra PowerShell **como administrador** e execute `wsl --install`. Reinicie se solicitado. Abra Ubuntu e conclua a criação de um usuário Linux. A senha não aparece enquanto você digita; não a compartilhe.
2. No PowerShell, execute `wsl --update` e `wsl --list --verbose`. Confirme a distribuição na versão 2.
3. Baixe Docker Desktop somente em https://docs.docker.com/desktop/setup/install/windows-install/ . Escolha o mecanismo WSL 2. Abra o Docker Desktop e aguarde o mecanismo ficar ativo. Em Settings > Resources > WSL Integration, habilite Ubuntu se essa opção estiver disponível.
4. No terminal Ubuntu, confirme `docker version`, `docker compose version` e `docker run --rm hello-world`. Se aparecer erro de virtualização, verifique a virtualização de hardware/WSL conforme a documentação oficial; não altere BIOS sem entender o procedimento do fabricante.
5. Clone o repositório no diretório pessoal do Ubuntu (melhor desempenho de disco que a pasta Windows):

```sh
git clone https://github.com/CaioOzaki/GS2026-2-Cybersecurity-VilaAurora.git
cd GS2026-2-Cybersecurity-VilaAurora
sudo apt-get update
sudo apt-get install -y python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python docker/prepare.py
docker compose config
docker compose up --build -d
docker compose ps
sh docker/validate.sh
```

Se `docker compose ps` mostrar serviço encerrado, pare aqui e veja `docker compose logs --tail=80`. Ainda não há comprovação de funcionamento neste ambiente. O script verifica túnel e tráfego autorizado/negado e salva saídas em `evidence/docker/`.

6. Confirme `latest handshake` recente no `wireguard.txt`. Em `tunnel-https.txt` deve haver 200; `segments.txt` deve indicar painel permitido ao operador e MQTT/painel proibidos às origens indevidas. Não confunda o endereço privado 10.77.0.1 com um endereço de Internet.
7. Rode `sh docker/chaos-wan.sh` e mantenha por pelo menos 30 minutos. Observe no log da borda os alarmes e a fila. O script testa o corte do túnel virtual da UBS; não simula cinco links físicos nem perda de energia. Após retornar, compare leituras únicas na borda e na nuvem e confirme fila zero.
8. Pare com `docker compose down`. Os bind-mounts preservam a fila e as credenciais locais. Nunca envie `.runtime/` ao repositório.

Fontes: Docker Desktop Windows e backend WSL 2, https://docs.docker.com/desktop/features/wsl/ ; Microsoft, https://learn.microsoft.com/windows/wsl/install ; WireGuard, https://www.wireguard.com/quickstart/ . Consulte as versões atuais e requisitos do seu Windows.

## Pendências após a instalação

- Validar o piloto e corrigir eventuais incompatibilidades do kernel WireGuard/iptables.
- Revisar identidades e revogação no Mosquitto (a lista de bloqueio Python não é automaticamente uma CRL Mosquitto).
- Tornar os serviços sem privilégios após preparar a rede; root e NET_ADMIN estão restritos ao laboratório.
- Sincronizar o relógio do host por NTP e repetir a coleta; containers herdam o relógio do host.
- Capturar a comprovação real da VPN, segmentação e caos; atualizar o relatório.
- Se administração remota for habilitada futuramente, implementar portal/ZTNA/bastion com MFA antes de expor acesso.
