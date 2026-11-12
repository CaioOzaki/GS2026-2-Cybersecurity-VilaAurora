"""Cenário energético sintético: calcula hipóteses, não lê um medidor físico."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
    duration=json.loads((ROOT/'evidence/docker/chaos-tunnel.json').read_text())['duration_monotonic_seconds']
    rows=[]
    for power in [8,15,25]:
        rows.append(dict(assumed_average_watts=power,outage_seconds=duration,
            energy_one_node_wh=round(power*duration/3600,4),energy_five_independent_nodes_wh=round(5*power*duration/3600,4),
            annual_one_node_kwh=round(power*24*365/1000,3),annual_five_nodes_kwh=round(5*power*24*365/1000,3)))
    result=dict(classification='Cenário sintético calculado; NÃO é medição de energia elétrica',physical_measurement=False,
        model='E(Wh) = potência média hipotética (W) × duração (s) / 3600',
        assumptions='Sensibilidade de 8, 15 e 25 W para uma futura borda física; 15 W é a hipótese do orçamento. Cinco nós são uma extrapolação do produto, não cinco máquinas físicas medidas.',
        measured_input='Apenas a duração monotônica do ensaio foi medida; potência não foi medida nem inferida da CPU.',scenarios=rows,
        limitation='Docker/CPU/RAM não fornecem consumo elétrico confiável do nó. RT-22 mantém essa ressalva; hardware real é opcional no enunciado.')
    (ROOT/'evidence/energy-scenario.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
