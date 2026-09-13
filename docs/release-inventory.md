# Inventário medido do corpus-latest

Medição executada no GitHub Actions em 2026-09-13 pelo workflow `Audit corpus`.

O auditor baixou os ZIPs do release `corpus-latest`, abriu cada pacote e conferiu `manifest.json`, `SHA256SUMS.txt`, quantidade de PDFs e SHA-256 de cada PDF presente.

## Resultado do release

| Asset | Provas no pacote | PDFs | Tamanho |
|---|---:|---:|---:|
| `eear-pre2020.zip` | 15 | 30 | 11.204.790 bytes |
| `eear-2020-2022.zip` | 30 | 58 | 32.190.217 bytes |
| `eear-2023-2025.zip` | 19 | 38 | 19.721.604 bytes |
| `esa.zip` | 4 | 8 | 5.823.432 bytes |
| `espcex.zip` | 2 | 4 | 19.021.083 bytes |
| **Total** | **70** | **138** | **87.961.126 bytes** |

Todos os PDFs presentes nos cinco pacotes passaram na conferência de hash interno dessa execução.

## Manifests versus release

Os 14 manifests versionados descrevem 72 entradas de prova e 142 arquivos candidatos. O release contém 70 provas e 138 PDFs.

A diferença observada está na coleção `esa`: os manifests somam 6 entradas/12 arquivos, enquanto o pacote publicado contém 4 entradas/8 PDFs. A workflow de geração atual aplica um filtro antes de construir esse pacote.

Portanto, a partir deste ponto é importante usar termos distintos:

- **manifest candidates**: tudo que está descrito nos manifests de origem;
- **release assets**: o que realmente atravessou a regra de empacotamento e existe nos ZIPs publicados;
- **normalized questions**: conteúdo por questão depois de passar pela ingestion/validation do `enemlab`.

Essas três camadas não devem ser tratadas como equivalentes.

## O que esta medição prova

Ela prova que os ZIPs do release existem, são arquivos válidos, contêm os PDFs declarados em seus manifests internos e que os hashes internos conferem para os bytes presentes.

Ela não prova, sozinha, que cada PDF corresponde semanticamente à edição esperada, que o gabarito está correto, que a fonte é oficial ou que o documento pode ser redistribuído. Essas propriedades pertencem a provenance, validation/evidence e política de direitos.
