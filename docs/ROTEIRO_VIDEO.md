# Roteiro da demonstração - versão local

**Duração sugerida: 4min50s.** Confirmar com o professor, pois o PDF não informa um limite. Gravar somente após revisar o protótipo e, se possível, concluir a validação Docker. Não exibir senhas, sementes TOTP, chaves ou QR do autenticador.

## Antes de gravar

1. Abrir o painel em `127.0.0.1:8080` com `python -m aurora.demo --vulnerable`. Fazer login antes da captura. Abrir também os resultados em `evidence/security.json`, `ai.json` e `chaos.json`.
2. Separar uma captura do teste de continuidade já finalizado: duração, crescimento da fila e reconciliação. O vídeo pode resumir os 30 minutos por cortes; a evidência original deve permanecer disponível.
3. Não afirmar que a VPN foi validada até executar o perfil Docker e conferir `evidence/docker/`. O material atual comprova a parte local.

## 0:00-0:40 - Problema e entrega

**Mostrar:** diagrama do relatório, depois painel.

**Dizer:** “Sou Caio Yudi Ozaki Godinho, RM 552505, da turma 4ECA. A Rede Vila Aurora reúne cinco espaços comunitários e precisa continuar monitorando água, energia e condições ambientais quando a conexão falha. Desenvolvi um laboratório com identidade por dispositivo, regras na borda, armazenamento local e sincronização posterior. A demonstração utiliza dados sintéticos e mostra as funcionalidades efetivamente testadas.”

## 0:40-1:10 - Arquitetura e limites

**Mostrar:** cinco cartões e componentes no diagrama.

**Dizer:** “Cada espaço tem uma borda lógica com broker MQTT e SQLite. Os dispositivos possuem certificados individuais e usam TLS mútuo. A nuvem recebe lotes por HTTPS, também com certificado, e evita duplicação pelo UUID. Nesta execução, as cinco bordas compartilham um computador. A configuração Linux com Mosquitto, WireGuard e segmentos separados está preparada; a comprovação dessa etapa depende dos testes no Docker.”

Se Docker já tiver sido testado e o relatório atualizado, substituir a última frase por uma explicação que mostre o handshake real e os bloqueios de tráfego, sem ocultar a ausência de MFA no túnel administrativo.

## 1:10-2:00 - SQL Injection antes e depois

**Mostrar:** em `127.0.0.1:8081`, buscar `p001` na versão legada. Depois buscar `' OR 1=1 --` na mesma versão e na corrigida. Mostrar dois registros extraídos por UNION em `security.json`.

**Dizer:** “A consulta legada concatena a entrada e permite que uma busca devolva outros registros. O ataque ocorre apenas neste banco descartável local. Na versão corrigida, o mesmo texto é tratado como valor. A proteção combina parâmetros, limite de entrada, banco aberto para leitura e autorização restrita à tabela de histórico. A resposta não revela detalhes do banco.”

## 2:00-2:40 - Identidade, perfis e aprovação

**Mostrar:** testes aprovados de certificado ausente, CA inválida, ACL, revogação/rotação; solicitar parada da bomba como operador. Mostrar o estado pendente. Usar sessão de coordenação em outra janela, com login feito fora da gravação, para aprovar.

**Dizer:** “Um certificado válido não permite publicar por outro sensor. Uma violação da ACL dispara o bloqueio lógico daquela identidade. No painel, auditor consulta, operador solicita e somente coordenação aprova a ação de alto impacto. A bomba aqui é um estado lógico; não há acionamento de equipamento físico.”

## 2:40-3:35 - Continuidade e reconciliação

**Mostrar:** `evidence/chaos.json` e gráfico do relatório; destacar duração real, cinco filas antes, filas após, total local e total único recebido.

**Dizer:** “Este experimento desligou o processo coletor por mais de 30 minutos reais. Os sensores continuaram publicando e os alarmes foram decididos localmente. As mensagens ficaram persistidas no SQLite. Com o retorno do serviço, os lotes foram reenviados e reconciliados. O contador monotônico mediu a duração. Este teste é uma falha de serviço local; o ensaio do túnel virtual está separado no Docker.”

Ler os números reais exibidos no resultado, sem usar um valor previsto. Se houver perda ou falha, explicar e corrigir antes da entrega.

## 3:35-4:15 - Detecção, IA e phishing

**Mostrar:** quatro regras em `detections.json`, matriz de confusão e métricas da campanha.

**Dizer:** “O correlacionador identifica SQL Injection, falha de certificado e comando fora do perfil; a regra de login VPN foi testada com um evento sintético identificado. O Isolation Forest foi treinado somente com leituras normais. No teste separado, encontrou 38 de 60 anomalias, com 6 falsos positivos entre 300 leituras normais. Por isso ele complementa as regras determinísticas e não comanda atuadores. A campanha com cinco agentes fictícios validou abertura, clique, submissão e reporte sem coletar senhas. A assinatura DKIM passou e uma mensagem adulterada foi recusada.”

## 4:15-4:50 - Forense, pendências e fechamento

**Mostrar:** manifesto de hashes, cronologia e repositório.

**Dizer:** “A reprodução gerou evidências com SHA-256, registro de aquisição e linha do tempo. A alteração do agendamento ocorreu somente no banco vulnerável; o banco corrigido permaneceu intacto. As limitações registradas são NTP ainda não sincronizado no host, energia física não medida e validação de VPN e segmentação ainda necessária. O repositório inclui os testes e a configuração para reproduzir o laboratório. A prioridade é manter o serviço local, restringir a atuação e preservar evidências verificáveis.”

## Publicação e entrega

Publicar como público ou não listado, conferir o vídeo em uma janela sem login e manter acessível até as notas. Enviar o link para atualizar a identificação de entrega. Não inventar link ou capturas. E2 exige o repositório acessível ao professor. O roteiro não substitui a gravação.
