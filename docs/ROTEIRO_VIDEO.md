# Roteiro da demonstração - laboratório validado

Vídeo final publicado pelo autor: https://youtu.be/NxUQMSvv-xU

**Duração sugerida: 4min50s.** O enunciado não fixa duração; confirmar com o professor. Este roteiro acompanha as evidências reais e não substitui o vídeo. Não mostrar senhas, sementes TOTP, QR ou chaves privadas.

## Preparação

Deixar Docker Desktop ativo. No Ubuntu: `cd ~/GS2026-2-Cybersecurity-VilaAurora` e `docker compose ps`. Abrir http://127.0.0.1:8088/ e fazer login antes de iniciar a captura. Separar o relatório, `evidence/docker/network.json`, `mqtt-before.json`, `mqtt-after.json` e `chaos-tunnel.json`. Para a comparação SQLi, iniciar o laboratório nativo separado com `python -m aurora.demo --vulnerable`, em runtime próprio; abrir 127.0.0.1:8081. Evitar executar suites de teste durante a gravação.

## 0:00-0:35 - Problema e entrega

**Mostrar:** diagrama do relatório e painel da UBS.

**Dizer:** “Sou Caio Yudi Ozaki Godinho, RM 552505, da turma 4ECA. A Rede Vila Aurora reúne cinco espaços comunitários que precisam acompanhar água, energia e condições ambientais mesmo quando a conexão falha. Desenvolvi um laboratório com certificados por dispositivo, decisões locais, armazenamento durável e sincronização posterior. Vou mostrar os recursos testados, com telemetria sintética.”

## 0:35-1:05 - Arquitetura em funcionamento

**Mostrar:** Docker com cinco serviços; `wireguard.txt` e diagrama das redes.

**Dizer:** “O piloto Linux representa uma UBS. Quatro geradores publicam no Mosquitto por TLS mútuo; a borda guarda as leituras no SQLite e envia lotes por HTTPS através do WireGuard. As redes IoT, operação e administração são separadas por regras de firewall. O operador acessa o painel, mas não o broker. A chave da autoridade certificadora fica fora dos containers. Os cinco processos principais executam sem root após a configuração da rede.”

## 1:05-1:45 - SQL Injection antes e depois

**Mostrar:** na página local 8081, consultar `p001`, depois `' OR 1=1 --` na busca vulnerável e na parametrizada. Mostrar resultado de UNION em `evidence/security.json`.

**Dizer:** “No banco legado descartável, a concatenação permite que a entrada altere o significado da consulta e exponha outros registros. Na versão corrigida, o mesmo texto vira apenas um valor. A proteção usa parâmetros, limite de entrada, conexão somente leitura e autorização restrita ao histórico. A tentativa de alterar o agendamento ocorreu exclusivamente no alvo vulnerável do próprio laboratório.”

## 1:45-2:20 - Certificados e decisões humanas

**Mostrar:** resultados MQTT: válido, ausência de certificado, CA estrangeira, tópico indevido, serial revogado e serial novo. Mostrar uma solicitação pendente no painel e a aprovação em sessão de coordenação previamente autenticada.

**Dizer:** “O certificado identifica o dispositivo, e a ACL restringe seu tópico. A CRL assinada recusou o serial antigo após reinício controlado do broker, enquanto o novo foi aceito. No painel, senha e TOTP protegem quatro perfis. O operador solicita uma intervenção; somente a coordenação aprova. A bomba é um estado lógico, sem acionamento de máquina física. Não há administração remota SSH ou RDP.”

## 2:20-3:35 - Continuidade e retorno da conexão

**Mostrar:** painel online; iniciar `python3 docker/short_regression.py` no Ubuntu. Durante os 45 s de corte, voltar ao painel para mostrar “VPN desligada”, leituras e fila crescendo. Depois mostrar VPN ligada e fila zero. Sobrepor os números do ensaio longo e o gráfico do relatório; usar cortes na edição, sem apresentar os 45 s como 30 minutos.

**Dizer:** “Agora o teste desliga a interface WireGuard, mantendo a rede local ativa. As leituras continuam chegando, os alarmes continuam sendo calculados e a fila cresce no disco. No ensaio longo registrado, o túnel ficou desligado por 1802.000 segundos: foram 1328 novas leituras e 41 novos alarmes locais. Depois da recuperação, a fila zerou em 28.914 segundos. A comparação dos UUIDs confirmou zero mensagens ausentes. O teste longo usou a versão-base; esta demonstração é a regressão curta da revisão final.”

## 3:35-4:10 - Detecção, IA e phishing

**Mostrar:** quatro regras em `detections.json`, matriz de confusão e campanha fictícia.

**Dizer:** “O correlacionador trata SQL Injection, certificado inválido, atuação fora do perfil e um evento sintético de acesso VPN. O Isolation Forest acertou 38 de 60 anomalias, com seis falsos positivos em 300 leituras normais. Por isso complementa regras e não comanda atuadores. A campanha usou cinco agentes fictícios: quatro aberturas, três cliques, duas submissões e dois reportes, sem pessoas reais ou coleta de senhas. DKIM foi verificado offline; a mensagem adulterada foi recusada.”

## 4:10-4:50 - Evidências e fechamento

**Mostrar:** manifesto SHA-256, linha do tempo, 25/25 testes locais e Linux, nove verificações de rede e repositório.

**Dizer:** “Os arquivos de teste foram adquiridos logicamente, registrados em custódia e conferidos por SHA-256. Os 25 testes de segurança passaram tanto na execução nativa quanto no Linux. O piloto também passou nas nove verificações de rede e privilégios. Os limites estão documentados: não há instalação física, energia medida nem confirmação de sincronismo absoluto dos relógios. O código e as evidências permitem reproduzir os resultados. A solução mantém a operação local, restringe os acessos e exige aprovação para ações de alto impacto.”

## Publicação

Publicar no YouTube como público ou não listado e testar o link sem login. Mantê-lo acessível até a divulgação das notas. Enviar o link para inclusão na identificação de entrega; não inventar endereço. Repositório E2: https://github.com/CaioOzaki/GS2026-2-Cybersecurity-VilaAurora .

## Complemento após revisão do escopo

Se perguntarem sobre hardware, explicar: “O enunciado permite um laboratório com dispositivos em containers; hardware real é um diferencial. Nosso projeto foi executado nesse formato.”

Se citar energia, dizer: “Para dimensionamento, usamos um cenário sintético de 15 W por borda, equivalente a aproximadamente 7,51 Wh durante o intervalo de 30 minutos. Essa é uma estimativa calculada, não uma medição elétrica.” CPU, memória, filas e perdas apresentados no vídeo continuam sendo as medições reais registradas.

Os testes adicionais de e-mail e acessibilidade passaram 9/9 cada. Evitar afirmar conformidade integral WCAG ou DNS publicado na Internet. O serviço de horário do Windows foi iniciado após autorização administrativa, mas o sincronismo NTP não foi confirmado; essa limitação permanece registrada no relatório.
