# video-organizer

Varre uma biblioteca de vídeos (recursivamente, a partir de uma pasta definida no `config.yaml`)
e ajuda a organizá-la em duas etapas:

1. **Detecção de duplicados** — agrupa vídeos que são idênticos byte a byte ou *provavelmente*
   o mesmo clipe (duração parecida + um frame amostrado correspondente), e move cada grupo para
   uma pasta de revisão nomeada com base no arquivo que parece mais descritivo — os arquivos em
   si mantêm seus nomes originais, só a pasta é que leva esse nome de referência. Cada pasta de
   grupo também recebe um `duplicate_report.txt` com a pasta de origem completa de cada arquivo
   e o motivo da similaridade identificada.
2. **Detecção de vídeos curtos** — entre o que sobrou, encontra tudo que estiver abaixo de uma
   duração configurada e move para uma pasta de revisão separada. Essa pasta também recebe um
   `short_videos_report.csv` com uma linha por arquivo: `nome_arquivo`,
   `caminho_completo_origem`, `data_criacao_arquivo`, `tempo_video` (segundos) e
   `tamanho_arquivo` (bytes).

Toda movimentação é exibida como uma tabela e exige confirmação interativa antes de qualquer
alteração no disco (a menos que `--yes` ou `--dry-run` seja usado). Os arquivos são sempre
**movidos**, nunca copiados.

`source_folder` no `config.yaml` é opcional — se não for informado, a pasta atual (de onde o
comando for executado) é usada. Antes de começar a varredura, o programa sempre exibe a pasta
que será usada e um resumo de quais etapas de detecção estão ativas (`duplicates`,
`short_videos`), e pede confirmação explícita para prosseguir. Essa confirmação inicial acontece
sempre, mesmo com `--yes` ou `--dry-run` — o `--yes` só pula as confirmações de "mover estes
arquivos?" mais adiante.

## Requisitos

- Python 3.10+
- `ffmpeg` / `ffprobe` no PATH — usados para ler duração/resolução e para amostrar um frame na
  comparação de prováveis duplicados. Sem isso, a detecção de duplicados funciona apenas por
  hash exato de bytes, e a detecção de vídeos curtos não funciona.

## Configuração inicial

```
pip install -e ".[dev]"
cp config.example.yaml config.yaml
```

Edite o `config.yaml` — no mínimo, defina `source_folder`. Todo o resto (nomes das pastas de
revisão, os limites de similaridade de duplicados, o corte de vídeo curto) já tem um valor padrão
razoável e pode ser ajustado depois; veja os comentários em `config.example.yaml`.

## Uso

```
python -m video_organizer.cli --config config.yaml
python -m video_organizer.cli --config config.yaml --dry-run   # só mostra o plano, sem mover
python -m video_organizer.cli --config config.yaml --yes       # pula os prompts de confirmação
```

Ou, depois de `pip install -e .`, o script de console `video-organizer` também fica disponível.

## Testes

```
pytest
```
