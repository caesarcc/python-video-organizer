# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral do projeto

video-organizer é uma CLI em Python que varre uma biblioteca de vídeos (recursivamente, a partir
de uma pasta definida no `config.yaml`) e a organiza em duas etapas:

1. **Detecção de duplicados** — agrupa vídeos que são idênticos byte a byte (SHA-256) ou
   *provavelmente* o mesmo clipe (duração parecida + hash perceptual de um frame amostrado, via
   ffmpeg/ffprobe), move cada grupo para uma pasta de revisão e renomeia as cópias com base no
   nome de arquivo julgado mais descritivo (o mais longo).
2. **Detecção de vídeos curtos** — entre os vídeos restantes, encontra tudo que estiver abaixo de
   uma duração configurada e move para uma pasta de revisão separada.

Toda movimentação é exibida como uma tabela e exige confirmação interativa antes de qualquer
alteração no disco (a menos que `--yes` ou `--dry-run` seja usado). Os arquivos são sempre
**movidos**, nunca copiados.

`source_folder` é opcional no `config.yaml`: se ausente, `Config.source_folder_from_default` fica
`True` e a pasta atual (`Path.cwd()`) é usada. Por isso, antes de escanear qualquer coisa,
`cli.py:confirm_target` sempre exibe a pasta resolvida e um resumo de quais etapas de detecção
estão ativas (`duplicates`, `short_videos`), e pede confirmação explícita — esse gate roda mesmo
com `--yes` ou `--dry-run` (só o `--yes` posterior, nas confirmações de "mover estes arquivos?",
é que é ignorado).

## Comandos

Configuração inicial:
```
pip install -e ".[dev]"
```

Copie o config de exemplo antes da primeira execução — `config.yaml` está no `.gitignore` porque
contém um caminho local real:
```
cp config.example.yaml config.yaml   # depois edite source_folder
```

Executar:
```
python -m video_organizer.cli --config config.yaml
python -m video_organizer.cli --config config.yaml --dry-run   # só mostra o plano, sem mover
python -m video_organizer.cli --config config.yaml --yes       # pula os prompts de confirmação
```

Testes:
```
pytest
pytest tests/test_duplicates.py -k exact_hash   # um teste específico
```

Requer `ffmpeg`/`ffprobe` no PATH para extração de metadados e hash perceptual — sem isso, a
detecção de duplicados cai para apenas hash exato (ver `metadata.FFProbeNotFoundError`), e a
detecção de vídeos curtos não funciona, já que depende da duração.

## Arquitetura

Pipeline, orquestrado de ponta a ponta a partir de `video_organizer/cli.py:main`:

```
confirm_target()  ->  scanner.find_videos()  ->  duplicates.find_duplicate_groups()  ->  mover (exibe/confirma/executa)
                                              ->  short_videos.find_short_videos()    ->  mover (exibe/confirma/executa)
```

- `config.py` — carrega e valida o `config.yaml` em um dataclass `Config`. Todos os parâmetros
  ajustáveis (pasta de origem, nomes das pastas de revisão, limite de distância de hash,
  tolerância de duração, limite de vídeo curto) vivem aqui; novos parâmetros devem começar por
  aqui.
- `scanner.py` — descoberta recursiva de arquivos; sempre exclui os nomes de pasta de revisão
  configurados, para que reexecuções não reescaneiem o que já foi organizado.
- `metadata.py` — encapsula o `ffprobe` (saída em JSON) para obter duração/resolução; é o único
  ponto onde a ausência do ffmpeg é detectada e sinalizada (`FFProbeNotFoundError`).
- `hashing.py` — `sha256_file` para comparação de duplicados exatos; `perceptual_hash` extrai um
  frame via `ffmpeg` no meio do clipe e o compara com `imagehash.phash` para prováveis
  duplicados.
- `duplicates.py` — agrupamento em duas passagens: primeiro os SHA-256 exatos, depois uma
  passagem de agrupamento por tolerância de duração + distância de hash perceptual sobre o que
  não foi reivindicado na primeira passagem. `pick_reference_name` escolhe o nome de arquivo mais
  longo do grupo como base para a renomeação (usado como heurística para "o arquivo com mais
  informação no título").
- `short_videos.py` — filtra os vídeos restantes (não duplicados) por
  `duration_seconds < max_duration_seconds`.
- `mover.py` — o único módulo que toca o sistema de arquivos para mover arquivos. `MovePlan` é um
  objeto de dados puro; `show_plan`/`confirm` são o ponto de confirmação humana;
  `execute_moves` usa `shutil.move` (funciona entre drives) e `unique_destination` evita
  sobrescrever arquivos existentes na pasta de revisão.

Invariante importante: nada em `duplicates.py` ou `short_videos.py` move um arquivo diretamente —
eles só retornam dados (`DuplicateGroup`, listas de `Path`). O `cli.py` transforma isso em
`MovePlan`s, e o `mover.py` é o único lugar onde `shutil.move` é chamado. Ao adicionar novas
regras de detecção, mantenha essa mesma separação "detectar -> planejar -> confirmar -> executar".
