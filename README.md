# Vila Aurora - Infraestrutura comunitária segura e resiliente

**GS 2026.2 | Cybersecurity | FIAP | 4ECA | RM552505**  
Caio Yudi Ozaki Godinho. Trabalho individual. Somente dados sintéticos.

## Estado verificável

- **25/25 testes locais aprovados**: mTLS MQTT/HTTPS, certificado ausente/CA inválida, ACL, rotação e revogação; cliente Paho QoS1; SQL Injection antes/depois; quatro perfis MFA; CSRF; aprovação de comando crítico; correlacionador e isolamento lógico automático.
- IA Isolation Forest: treino normal separado do teste, precisão 86,36%, revocação 63,33%, falsos positivos 2%. Não comanda atuadores. Não usa LLM.
- Campanha local automatizada com cinco contas fictícias, sem mensagens externas ou coleta de senhas. Assinatura DKIM verificada e adulteração rejeitada; SPF/DMARC documentados em zona fictícia offline.
- Experimento concluído do serviço coletor: **1802 s indisponível**, 3440 publicações no período sem falha, 3445 eventos locais/únicos na nuvem (inclui cinco leituras iniciais), **zero perda** e fila esvaziada em 26,015 s. Resultado integral: `evidence/chaos.json`. Relógio monotônico, cinco bordas lógicas e reconciliação por UUID.
- **Piloto Linux validado em Ubuntu 24.04/WSL2 e Docker Desktop:** 9/9 verificações de rede/privilégios, seis cenários Mosquitto de TLS/ACL/CRL e 25/25 testes de segurança repetidos em Linux. Interface WireGuard desligada durante **1802.000 s**, 1328 novas leituras e 41 novos alarmes locais; **zero mensagens perdidas**, fila recuperada em **28.914 s**. A revisão com CRL/processos UID 1000 teve regressão curta complementar e teste real do painel. O perfil é um piloto UBS; não equivale a cinco instalações físicas.
- Windows sem sincronização NTP na consulta original. Linux contactou servidor NTP, mas timedatectl ainda indicou relógio não sincronizado. Horários UTC são os do host; a ordem causal e a duração têm contador monotônico. Energia física não medida.

O relatório distingue as fases nativa e Linux. Acesso administrativo remoto SSH/RDP não é oferecido; MFA protege o painel. Persistem limitações de sincronismo absoluto, coleta central autenticada de logs entre hosts, energia e operação física. Não apresentar o laboratório como instalação em campo.

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

## 4. Linux/Docker - reprodução do piloto validado

Veja `docs/DOCKER_WINDOWS.md`. Clone no diretório pessoal do Ubuntu; não use um bind-mount Windows para os segredos. O piloto possui segmentos IoT, operadores e administração separados, além da rede de transporte do túnel. Apenas o visualizador publica **127.0.0.1:8088**, sem exposição na LAN/Internet.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python docker/prepare.py
docker compose up --build -d
python3 docker/validate.py
python3 docker/chaos.py
```

O teste longo demora pelo menos 30 minutos reais e substitui seu resultado em `evidence/docker/`; preserve a coleta entregue antes de repetir. A interface WireGuard é desligada, mantendo MQTT, regras locais e SQLite. Ao retornar, os UUIDs locais e remotos são comparados. O gerador é congelado brevemente somente na reconciliação para tornar essa comparação estável e depois retomado.

Abra `http://127.0.0.1:8088/`. Consulte a senha e semente TOTP **somente localmente** em `.runtime/docker/edge/credentials.json`. Não as grave nem publique. O painel usa HTTP no segmento isolado e em loopback; uma implantação distribuída exige HTTPS também na interface humana. Não há SSH/RDP remoto. WireGuard autentica máquinas; MFA TOTP protege as contas do painel.

Para repetir TLS/ACL, construa a imagem de teste e execute o probe somente na rede própria:

```sh
docker compose --profile tests build probe
docker compose run --rm --no-deps --user 1000:1000 --entrypoint python probe /app/docker/probe_mqtt.py before
.venv/bin/python docker/rotate_probe.py
docker compose restart edge
# Aguarde o broker voltar antes do próximo comando.
docker compose run --rm --no-deps --user 1000:1000 --entrypoint python probe /app/docker/probe_mqtt.py after
python3 docker/short_regression.py
```

O primeiro probe confere certificado válido, ausência de certificado, CA estrangeira e publicação em tópico indevido. A estação emissora revoga o certificado de teste, assina uma CRL e emite outro serial para o mesmo dispositivo. O reinício controlado do broker força reconexão: o serial antigo é recusado e o novo aceito. A CRL não é a lista JSON do broker didático. A chave da CA permanece fora dos containers.

`prepare.py` gera novas chaves WireGuard e redistribui arquivos privados: execute com o perfil parado, nunca durante o ensaio. A inicialização precisa de root/NET_ADMIN para a rede; os cinco processos principais passam a UID 1000. O host Docker continua sendo uma fronteira de confiança. Mantenha a CRL renovada antes de sete dias. Para parar, `docker compose down`; os dados privados são preservados.

## 5. Proteção de segredos e evidências

`.runtime`, ambientes virtuais, chaves e bancos operacionais são ignorados pelo Git e pelo build Docker. Nunca publique essa pasta. `docker/prepare.py` distribui apenas os certificados de cada função; a chave da CA permanece no diretório privado de origem. Os logs de laboratório usam contas e pessoas fictícias. As chaves DKIM públicas e assinaturas de e-mail podem ser públicas; as chaves privadas não.

O manifesto SHA-256 e a custódia ficam em `evidence/forensics/`. Ele detecta alterações após a aquisição; uma cadeia de hashes sozinha não prova autoria nem impede que um administrador reescreva todo o conjunto. Preserve a versão entregue em repositório e mídia separada. Nenhuma imagem forense integral de disco ou memória foi adquirida.

Verifique a evidência entregue com `python tools/verify_evidence.py`. Para nova coleta, `python tools/acquire.py --security .runtime/seguranca --continuity .runtime/continuidade-nova`; isso atualiza as evidências públicas do seu ensaio, portanto preserve a versão anterior antes de repetir.

## 6. Entrega e vídeo

E1, E3 e E4 estão reunidos no relatório técnico identificado. E2 é este repositório. O vídeo deve mostrar demonstração real: SQLi corrigida, alarme local, fila/reconciliação, certificados, permissões e resultados de IA. O enunciado menciona vídeo na rubrica, mas não fixa sua duração. O roteiro sugere uma edição de aproximadamente 5 minutos, a confirmar com o professor. O link do vídeo ainda não existe.

## Revisão complementar do escopo e da interface

O enunciado (página 10) permite containers e simuladores; hardware real é diferencial, não obrigatório. Não é necessário montar placa ou sensor externo para esta entrega. RT-06 exige VPN borda-nuvem e MFA quando houver administração remota. O piloto usa WireGuard e MFA no painel; SSH/RDP remoto não é oferecido. Isso não transforma WireGuard em um protocolo de login humano com TOTP.

- `evidence/energy-scenario.json`: cenário energético sintético calculado, sem wattímetro. Hipótese de 15 W × 1802 s / 3600 = 7,5083 Wh por borda; cenários de 8/25 W mostram sensibilidade. Não são medições elétricas. Reproduzir: `python tools/estimate_energy.py`.
- `evidence/email-policy-tests.json`: 9/9 verificações offline de SPF (pyspf), DKIM e alinhamento DMARC estrito. Nenhum envio SMTP ou DNS público. Reproduzir: `python tests/run_email_auth.py` após instalar requirements.
- `evidence/review/accessibility.json`: 9/9 verificações de navegador, incluindo login por teclado, rótulos explícitos, foco visível, contraste selecionado, refluxo em 320 CSS px e zoom CSS 200%. Não é certificação integral WCAG nem teste com leitor de tela/usuários.
- O horário absoluto segue pendente: W32Time está parado e a sessão não tem permissão administrativa para iniciá-lo. `docs/AJUSTAR_HORARIO_WINDOWS.ps1` contém os comandos para o usuário executar como administrador. As evidências anteriores não foram reescritas; eventual nova coleta deve ser separada.

Para repetir a acessibilidade, instale Playwright em ambiente de testes Node separado e disponibilize o módulo em NODE_PATH. O teste foi executado no Edge/Chromium pelo Playwright do ambiente de desenvolvimento. Execute `python tools/run_accessibility.py --credentials .runtime/docker/edge/credentials.json`; forneça `--browser CAMINHO_DO_CHROMIUM` se usar navegador próprio, ou instale o Chromium pelo Playwright. O processo recebe a credencial por stdin e nunca a imprime; não use captura de tela do arquivo privado.

## Uso de IA

OpenAI Codex/ChatGPT foi utilizado como apoio na estruturação da arquitetura, geração e revisão de código, automação dos testes, elaboração de gráficos e redação. As evidências são saídas das execuções descritas. O autor deve revisar o material, reproduzir os testes e dominar a explicação. Não foi usado LLM dentro do sistema operacional do projeto nem para comandar atuadores.
