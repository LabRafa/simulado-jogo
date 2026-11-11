"""Locutor do Sisão do simulado: grava (edge-tts, mesma voz do Show do Sisão original, pt-BR-AntonioNeural)
uma fala por pergunta do simulado (bancos.js) e por alternativa, e escreve sisao/locutor.js.
As falas fixas (valendo, certa, errada...) são as do original, já copiadas em sisao/audio/locutor/.
Uso: python sisao/gerar_locutor_simulado.py   (refaz só o que falta). Rodar de novo quando o banco mudar."""
import asyncio, hashlib, json, subprocess, time
from pathlib import Path
import edge_tts

AQUI = Path(__file__).resolve().parent          # simulado-jogo/sisao
RAIZ = AQUI.parent                              # simulado-jogo
SAIDA = AQUI / 'audio' / 'locutor'
SAIDA.mkdir(parents=True, exist_ok=True)
VOZ = 'pt-BR-AntonioNeural'
NODE = r'C:\Users\rafar\AppData\Local\hermes\tools\node-26.7.0-win32-x64\node.exe'
V = time.strftime('%Y%m%d%H%M')

js = "global.window={};require('./bancos.js');const out=[];for(const k of ['bases','carie','inter']){const m=window.BANCOS[k];if(!m)continue;for(const q of m.q){if(!q||!q.p||!Array.isArray(q.o))continue;out.push({q:(q.ctx?q.ctx+'\\n\\n':'')+q.p,o:q.o.map(String)})}}process.stdout.write(JSON.stringify(out))"
dados = json.loads(subprocess.check_output([NODE, '-e', js], cwd=RAIZ, text=True, encoding='utf-8'))
h = lambda s: hashlib.sha1(s.encode('utf-8')).hexdigest()[:12]

async def main():
    fixas = {p.stem: f'sisao/audio/locutor/{p.name}?v={V}' for p in SAIDA.glob('*.mp3') if not p.stem.startswith(('q_', 'o_'))}
    mapa = {'fixas': fixas, 'perguntas': {}, 'opcoes': {}}
    sem = asyncio.Semaphore(8)
    feitos = [0]
    async def um(texto, arq):
        async with sem:
            if arq.exists() and arq.stat().st_size > 1000:
                return
            for t in range(4):
                try:
                    await edge_tts.Communicate(texto, VOZ, rate='+14%', pitch='-18Hz', volume='+15%').save(str(arq))
                    feitos[0] += 1
                    if feitos[0] % 50 == 0: print('gravadas', feitos[0], flush=True)
                    return
                except Exception:
                    await asyncio.sleep(2 + t)
    tarefas = []
    for d in dados:
        arq = SAIDA / f'q_{h(d["q"])}.mp3'
        tarefas.append(um(d['q'].replace('\n\n', ' '), arq)); mapa['perguntas'][d['q']] = f'sisao/audio/locutor/{arq.name}?v={V}'
        for o in d['o']:
            arq = SAIDA / f'o_{h(o)}.mp3'
            if o not in mapa['opcoes']:
                tarefas.append(um(o + '.', arq)); mapa['opcoes'][o] = f'sisao/audio/locutor/{arq.name}?v={V}'
    await asyncio.gather(*tarefas)
    falt = [k for k, v in list(mapa['perguntas'].items()) + list(mapa['opcoes'].items()) if not (AQUI.parent / v.split('?')[0]).exists()]
    for k in falt:
        mapa['perguntas'].pop(k, None); mapa['opcoes'].pop(k, None)
    (AQUI / 'locutor.js').write_text('/* gerado por sisao/gerar_locutor_simulado.py */\nwindow.LOCUTOR = ' + json.dumps(mapa, ensure_ascii=False) + ';\n', encoding='utf-8')
    print('ok', len(mapa['perguntas']), 'perguntas,', len(mapa['opcoes']), 'alternativas, faltaram', len(falt), flush=True)

asyncio.run(main())
