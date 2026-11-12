# Operação, custos e riscos - Vila Aurora

## Modelo de ameaças STRIDE

| Categoria | Falha no incidente | Controle e evidência | Limite |
|---|---|---|---|
| Spoofing | Página falsa e credenciais capturadas | MFA TOTP no painel; X.509 único; 25 testes | MFA resistente a phishing/WebAuthn ainda desejável; WireGuard não tem MFA humano |
| Tampering | Agendamento da bomba alterado por SQLi | Parâmetros, banco somente leitura, RBAC e aprovação | Sem hardware/PLC ligado |
| Repudiation | Logs espalhados e sobrescritos | JSONL central, sequência, SHA-256 e custódia | NTP não sincronizado; host único pode reescrever cadeia |
| Information disclosure | Tabela de usuários extraída | Separação de bancos e negação de leitura fora do histórico | Teste não equivale a auditoria completa da aplicação |
| Denial of service | Fibra cai e alarme depende da nuvem | Regras locais e outbox durável; teste de serviço >=30 min | Sem UPS ou redundância física testada |
| Elevation of privilege | Conta VPN abre acesso excessivo | Três segmentos e firewall preparados; permissões no painel | Linux/Docker e MFA administrativo ainda pendentes |

## Modo degradado e redundância

Sem conectividade, manter leitura e alarmes locais, colocar comandos remotos em espera e preservar os UUIDs em fila. O operador local decide sobre água/energia conforme procedimento; IA não libera portas nem para bombas. Não há acionamento crítico automático no protótipo. Um dispositivo violando ACL pode ter sua identidade revogada, com alerta para inspeção e emissão de novo certificado.

O escopo inicial aceita ponto único de falha no mini-PC de cada local, pois um cluster por instalação excede orçamento e manutenção voluntária. Mitigação projetada: UPS, imagem de recuperação, equipamento reserva compartilhado e visita técnica. Link 4G é opção futura; o requisito RT-03 também admite modo degradado justificado, que foi implementado logicamente. O host Windows único do laboratório não comprova resistência a falha de energia/disco.

Capacidade da fila: exemplo de planejamento, 20 sensores no conjunto x 1 leitura/10 s x 86400 s x 250 bytes = 43,2 MB/dia de payload; com margem 4x para índices/logs, cerca de 173 MB/dia. Reservar pelo menos 7 dias por espaço com verificação de disco e política de descarte prioritário. A fila do protótipo não tem limite/alarme de ocupação; testar disco cheio e recuperação é pendência.

## Custos (hipóteses de orçamento em reais, não cotações)

| Item | Quantidade | Unitário | Total |
|---|---:|---:|---:|
| Mini-PC/borda com armazenamento | 5 | 650,00 | 3.250,00 |
| UPS por local | 5 | 350,00 | 1.750,00 |
| Rede/caixa/cabeamento por local | 5 | 200,00 | 1.000,00 |
| Sensores e interfaces de laboratório por local | 5 | 250,00 | 1.250,00 |
| Equipamento de borda reserva | 1 | 650,00 | 650,00 |
| Instalação (12 h) | 12 | 60,00 | 720,00 |
| **Implantação estimada** | | | **8.620,00** |

Operação anual: hospedagem/backup R$60 x 12 = R$720; manutenção 2 h/mês x R$60 x 12 = R$1.440; energia estimada 5 x 15 W x 24 x 365 / 1000 x R$1,10/kWh = R$722,70. Total anual R$2.882,70; implantação + 12 meses = R$11.502,70. Reserva de 15% sobre o conjunto: R$1.725,41; orçamento com contingência R$13.228,11. Fibra comunitária já existente; 4G, certificação e adequação elétrica profissional não incluídos. Consumo de 15 W é hipótese, não medição do teste. Solicitar três cotações antes de comprar.

## Manutenção e responsabilidades propostas

- Operador local: conferir alertas/ocupação do disco diariamente; reportar mensagens suspeitas; nunca aprovar ação por áudio recebido.
- Técnico: revisão semanal de logs/filas; atualização mensal em homologação; backup diário e teste de restauração mensal; inventário de firmware e dependências; plano de retorno da versão anterior.
- Coordenação: aprovar ações de alto impacto, controlar admissões/desligamentos e revisar custos mensalmente.
- Auditor: revisão mensal de acessos e trilhas; conferência amostral dos hashes e restauração.
- PKI: certificados válidos 90 dias, renovar antes de 60 dias; revogação imediata por comprometimento; CA offline separada na implantação profissional. Na versão de desenvolvimento a CA fica privada no mesmo host.
- Logs propostos: telemetria 30 dias, segurança 90 dias e backup criptografado 90 dias; retenção de incidente suspensa mediante decisão formal. Esses períodos são política projetada; não há rotina automática de expurgo/backup no protótipo.

## RIPD simplificado

**Finalidade:** monitorar recursos e investigar falhas de segurança. **Dados atuais:** 100% sintéticos; nenhum paciente, morador ou voluntário real. Pessoas aparecem como p001-p003, contas fictícias em example.test; não há áudio/clonagem de pessoa real. **Dados futuros:** identificador pseudonimizado, horário e local do acesso; evitar biometria, prontuários e imagens na telemetria.

**Necessidade:** histórico mínimo para segurança do espaço e continuidade; separar a chave de pseudonimização do log. **Riscos:** reidentificação por rotina de horários, uso indevido por operador, vazamento de credenciais e retenção excessiva. **Controles:** RBAC, MFA, minimização, transporte autenticado, revisão de logs, expurgo e backup protegido. Não confundir pseudonimização com anonimização.

**Base legal de implantação:** deve ser definida pelo controlador conforme a finalidade e o vínculo institucional; para uma associação privada, legítimo interesse (art. 7º, IX) é apenas hipótese a avaliar com teste de necessidade/balanceamento, não autorização automática. Órgão público/saúde pode exigir outra hipótese legal e requisitos específicos. A solução não coleta dados de saúde. Consultar o texto vigente da LGPD: https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm .

**Responsáveis e prestação de contas:** associação/controlador valida finalidade, hipótese legal, canal de direitos e retenção antes de tratar pessoas reais. Auditoria acompanha evidências; técnico limita permissões. Risco residual da centralização em um único host e relógio sem NTP permanece registrado. Este RIPD é exercício acadêmico com dados sintéticos.

## Phishing e voluntários

Treinamento de 15 min: (1) reconhecer urgência e endereço; (2) não autenticar por link recebido; (3) abrir o endereço conhecido; (4) confirmar com telefone cadastrado previamente; (5) usar palavra-código definida fora do canal suspeito; (6) reportar antes de apagar. Áudio convincente e texto sem erros não provam identidade. Após reporte, coordenação confirma por outro canal e técnico preserva cabeçalhos/hash sem armazenar senhas.

Campanha atual mede a instrumentação com cinco agentes fictícios. Não fornece taxa real de vulnerabilidade humana. Uma campanha com pessoas exigiria escopo e consentimento institucionais, política de privacidade e avaliação ética compatível. Não produzir voz clonada sem autorização.

## Acessibilidade

Painel em português, texto de 18 px, rótulos associados, foco visível, link de salto, estado textual (sem depender só da cor), HTML sem imagens de texto e controles nativos. Teste de navegador validou login, cinco cartões e foco por Tab. Verificar contraste por cálculo, zoom 200%, leitor de tela e jornada completa antes de afirmar conformidade WCAG 2.1 AA. Referência: https://www.w3.org/WAI/WCAG21/quickref/ .
