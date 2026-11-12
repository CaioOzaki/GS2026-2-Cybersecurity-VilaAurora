# Vila Aurora - Infraestrutura comunitária segura e resiliente

**GS 2026.2 | Cybersecurity | FIAP | 4ECA | RM552505**  
Caio Yudi Ozaki Godinho. Trabalho individual. Somente dados sintéticos.

## Estado verificável

- **25/25 testes locais aprovados**: mTLS MQTT/HTTPS, certificado ausente/CA inválida, ACL, rotação e revogação; cliente Paho QoS1; SQL Injection antes/depois; quatro perfis MFA; CSRF; aprovação de comando crítico; correlacionador e isolamento lógico automático.
- IA Isolation Forest: treino normal separado do teste, precisão 86,36%, revocação 63,33%, falsos positivos 2%. Não comanda atuadores. Não usa LLM.
- Campanha local automatizada com cinco contas fictícias, sem mensagens externas ou coleta de senhas. Assinatura DKIM verificada e adulteração rejeitada; SPF/DMARC documentados em zona fictícia offline.
- Experimento concluído do serviço coletor: **1802 s indisponível**, 3440 publicações no período sem falha, 3445 eventos locais/únicos na nuvem (inclui cinco leituras iniciais), **zero perda** e fila esvaziada em 26,015 s. Resultado integral: `evidence/chaos.json`. Relógio monotônico, cinco bordas lógicas e reconciliação por UUID.
- **Docker/WireGuard/segmentação: preparados, ainda não executados no computador de desenvolvimento.** O perfil Linux é um piloto da UBS; não equivale a cinco instalações físicas prontas.
- Windows sem sincronização NTP na consulta realizada. Horários UTC são os do host; a ordem causal e a duração têm contador monotônico. Energia física não medida.

Não apresentar esta versão como implantação de campo ou como cumprimento integral dos RT-06, RT-07, RT-12 e RT-23. O relatório separa execução local, configurações preparadas e limitações.

## 1. Executar o laboratório local

Requisitos: Python 3.12 de 64 bits, ambiente virtual e portas locais 8080, 8081 (opcional), 8883-8887 e 9443 livres. Nenhuma conexão com equipamento físico.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m aurora.demo --vulnerable
```

Abra `http://127.0.0.1:8080`. A comparação insegura está **somente em loopback** na porta 8081 e só inicia com `--vulnerable`. Para iniciar sem o alvo vulnerável, retire essa opção. Encerre com Ctrl+C. Não mude os endereços para 0.0.0.0 no modo nativo.

O primeiro início gera CA, identidades X.509 distintas e credenciais locais. Consulte **apenas em sua máquina** `.runtime/credentials.json` para a senha e a semente TOTP do perfil desejado. Cadastre a semente em um autenticador TOTP compatível (SHA-1, seis dígitos, período de 30 s). O mesmo código não pode ser reutilizado. **Não grave senha, semente ou QR na apresentação.** A sessão dura 15 minutos.

As regras locais sinalizam temperatura fora de 2-8 °C, nível abaixo de 15% e energia abaixo de 20%; são parâmetros didáticos do cenário, não prescrição para equipamentos reais. Dados entram por MQTT mTLS e chegam ao coletor por HTTPS mTLS. SQLite usa outbox durável e chave UUID única para reconciliar reenvios.

## 2. Reproduzir testes (ambientes separados)

Na raiz do repositório, PowerShell:

```powershell
$env:AURORA_RUNTIME="$PWD\.runtime\seguranca"
$env:PYTHONPATH="$PWD"
.\.venv\Scripts\python.exe tests/run_security.py
.\.venv\Scripts\python.exe -m aurora.ai
$env:AURORA_RUNTIME="$PWD\.runtime\campanha"
.\.venv\Scripts\python.exe -m aurora.phishing
```

Use um diretório novo para cada repetição dos testes de segurança; o teste modifica certificados e estado da bomba. Feche o demo antes de executar o teste longo. Para repetir a continuidade em estado limpo:

```powershell
$env:AURORA_RUNTIME="$PWD\.runtime\continuidade-nova"
.\.venv\Scripts\python.exe -m aurora.chaos
```

Espere cerca de 31 minutos. Não comprima o relógio. O coletor HTTPS é encerrado como processo e reiniciado após 1802 segundos; **isso é falha de serviço, não queda física da Internet**. As bordas continuam publicando, alarmando e persistindo. `evidence/chaos.json` só é criado ao terminar. A coleta não mede energia elétrica nem overhead TLS/TCP.

Os scripts substituem os resultados em `evidence/`; preserve uma cópia assinada por hash antes de repetir a coleta que será entregue.

## 3. Entender o código

| Arquivo | Função |
|---|---|
| `aurora/pki.py` | CA local, X.509, lista de bloqueio, contextos TLS |
| `aurora/mqtt.py` | Broker didático limitado MQTT 3.1.1 e cliente de teste |
| `aurora/edge.py` | Regras locais, SQLite, outbox e sincronização |
| `aurora/cloud.py` | Coletor HTTPS, checagem de identidade/site e deduplicação |
| `aurora/web.py` / `auth.py` | Painel, consultas seguras, versão legada isolada, RBAC, TOTP, CSRF |
| `aurora/defense.py` | Quatro regras de correlação e revogação automática por violação da ACL |
| `aurora/phishing.py` | Agentes fictícios e DKIM offline |
| `aurora/ai.py` | Dataset sintético, Isolation Forest e métricas de teste |
| `aurora/chaos.py` | Experimento longo e medições do processo |
| `docker/` / `compose.yaml` | Piloto Linux com Mosquitto, WireGuard e três segmentos |

O broker nativo NÃO é Mosquitto: implementa CONNECT com clean session, PUBLISH QoS0/1, PING e DISCONNECT, sem SUBSCRIBE, retained e last-will. Foi conferido por um cliente Paho independente. A versão Docker utiliza Mosquitto com assinante real. Cinco bordas nativas compartilham o host e o processo; não resistem à falha deste computador. SIEM é um correlacionador próprio, não Wazuh.

## 4. Linux/Docker - próxima validação obrigatória

Veja `docs/DOCKER_WINDOWS.md`. A configuração não tem portas publicadas. Piloto UBS: segmentos IoT, operadores e administração separados; borda permite MQTT apenas a IoT e painel aos outros dois; coletor aceita HTTPS apenas pelo túnel. Testes geram evidências somente quando executados:

```sh
python docker/prepare.py
docker compose up --build -d
sh docker/validate.sh
sh docker/chaos-wan.sh
docker compose logs --no-color > evidence/docker/containers.txt
docker compose down
```

No WSL, use Python/venv Linux para executar `prepare.py`. As bibliotecas de `requirements.txt` precisam estar instaladas. O script `chaos-wan.sh` derruba a interface do túnel, sem derrubar o tráfego IoT local; mede pelo menos 1802 s. Depois compare a fila, os UUIDs e o total da nuvem. Não publique um resultado como aprovado sem conferir esses arquivos.

WireGuard autentica máquinas por chave. O MFA implementado protege o painel, **não transforma o túnel em uma VPN com MFA de administrador**. Administração remota não é oferecida nesta versão (sem SSH/RDP). Uma implantação profissional precisa integrar um gateway de acesso administrativo com MFA, reduzir privilégios de containers, autenticar transporte central dos logs e testar renovação/revogação também no Mosquitto. O broker Docker usa root no piloto para evitar incompatibilidade de permissões dos bind-mounts Windows; isso deve ser corrigido antes de produção.

## 5. Proteção de segredos e evidências

`.runtime`, ambientes virtuais, chaves e bancos operacionais são ignorados pelo Git e pelo build Docker. Nunca publique essa pasta. `docker/prepare.py` distribui apenas os certificados de cada função; a chave da CA permanece no diretório privado de origem. Os logs de laboratório usam contas e pessoas fictícias. As chaves DKIM públicas e assinaturas de e-mail podem ser públicas; as chaves privadas não.

O manifesto SHA-256 e a custódia ficam em `evidence/forensics/`. Ele detecta alterações após a aquisição; uma cadeia de hashes sozinha não prova autoria nem impede que um administrador reescreva todo o conjunto. Preserve a versão entregue em repositório e mídia separada. Nenhuma imagem forense integral de disco ou memória foi adquirida.

Verifique a evidência entregue com `python tools/verify_evidence.py`. Para nova coleta, `python tools/acquire.py --security .runtime/seguranca --continuity .runtime/continuidade-nova`; isso atualiza as evidências públicas do seu ensaio, portanto preserve a versão anterior antes de repetir.

## 6. Entrega e vídeo

E1, E3 e E4 estão reunidos no relatório técnico identificado. E2 é este repositório. O vídeo deve mostrar demonstração real: SQLi corrigida, alarme local, fila/reconciliação, certificados, permissões e resultados de IA. O enunciado menciona vídeo na rubrica, mas não fixa sua duração. O roteiro sugere uma edição de aproximadamente 5 minutos, a confirmar com o professor. O link do vídeo ainda não existe.

## Uso de IA

OpenAI Codex/ChatGPT foi utilizado como apoio na estruturação da arquitetura, geração e revisão de código, automação dos testes, elaboração de gráficos e redação. As evidências são saídas das execuções descritas. O autor deve revisar o material, reproduzir os testes e dominar a explicação. Não foi usado LLM dentro do sistema operacional do projeto nem para comandar atuadores.
