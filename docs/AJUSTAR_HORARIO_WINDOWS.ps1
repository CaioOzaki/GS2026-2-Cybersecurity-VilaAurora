# Executar em PowerShell aberto como administrador. Não define hora manualmente.
# A sincronização atual não valida retroativamente a hora das coletas anteriores.
$ErrorActionPreference = 'Stop'
Start-Service -Name W32Time
& w32tm.exe /resync /rediscover
if ($LASTEXITCODE -ne 0) { throw 'A sincronização não foi confirmada. Preserve a mensagem para diagnóstico.' }
& w32tm.exe /query /status
