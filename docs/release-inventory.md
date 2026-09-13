# Inventário medido do corpus

Medições executadas no GitHub Actions em 2026-09-13 pelos workflows de auditoria do corpus.

## `corpus-latest` publicado

O auditor baixou os ZIPs do release `corpus-latest`, abriu cada pacote e conferiu `manifest.json`, `SHA256SUMS.txt`, quantidade de PDFs e SHA-256 de cada PDF presente.

| Asset | Provas no pacote | PDFs | Tamanho |
|---|---:|---:|---:|
| `eear-pre2020.zip` | 15 | 30 | 11.204.790 bytes |
| `eear-2020-2022.zip` | 30 | 58 | 32.190.217 bytes |
| `eear-2023-2025.zip` | 19 | 38 | 19.721.604 bytes |
| `esa.zip` | 4 | 8 | 5.823.432 bytes |
| `espcex.zip` | 2 | 4 | 19.021.083 bytes |
| **Total** | **70** | **138** | **87.961.126 bytes** |

Todos os 138 PDFs presentes passaram na conferência de hash interno dessa execução.

## Candidatos versionados versus release

Com `sources/unesp.json`, existem agora **15 manifests**, **73 candidatos de prova** e **144 arquivos candidatos**.

A regra atual de empacotamento seleciona **71 provas / 140 arquivos** porque duas entradas ESA ficam fora pela regra histórica da Área Geral. O release público ainda contém 70 provas/138 PDFs porque a UNESP adicionada nesta branch ainda não foi publicada.

Assim, usamos três termos diferentes:

- **manifest candidates**: tudo que está descrito em `sources/`;
- **release assets**: o que realmente foi construído e publicado em ZIP;
- **normalized questions**: questões depois de ingestion, validação/evidence e review no `enemlab`.

Essas camadas não são equivalentes.

## UNESP 2026

A branch adiciona um candidato para a 1ª fase UNESP 2026, versão 1:

- caderno: espelho público, explicitamente marcado como `mirror`;
- gabarito: documento hospedado pela VUNESP, marcado como `official`;
- formato conhecido: 90 questões objetivas A–E;
- estado: candidato de corpus, ainda sem publicação automática no catálogo do Studium Labs.

O package builder genérico desta branch deve produzir `unesp.zip` em PR como artifact antes de qualquer publicação no release.

## `fatec.zip` legado

O arquivo raiz `fatec.zip` foi aberto recursivamente no runner. Ele tem:

- tamanho: **21.832.082 bytes**;
- SHA-256: `dcb3b4d67a9eacaaa4293d4d4276c9bb4767429d843e392f8e6b45f681c1ec7d`;
- 9 subpacotes: 7 ZIP e 2 RAR;
- todos os 9 subpacotes foram inventariados; os RARs foram abertos via `7z`.

### Conteúdo encontrado

| Edição/pacote | Conteúdo observado | Estado inicial |
|---|---|---|
| 2022.2 | `Prova.pdf` + `Gabarito.pdf` | candidato plausível |
| 2023.1 | `Prova.pdf` + `Gabarito.pdf` | candidato plausível |
| 2023.2 | `provas-fatecs-2023-2.pdf` + `gabarito-fatecs-2023-2.pdf` | candidato plausível |
| 2024.1 | `Gabarito.pdf` + `sisu-2024-termo-de-adesao-ufc.pdf` | **quarentena: caderno ausente/arquivo estranho** |
| 2024.2 | prova + gabarito FATEC | candidato plausível |
| 2025.1 | prova + gabarito + `edital-do-prouni-2025.pdf` | **quarentena: arquivo extra não relacionado** |
| 2025.2 | `Prova.pdf` + `Gabarito.pdf` | candidato plausível |
| 2026.1 | prova + gabarito FATEC | candidato plausível |
| 2026.2 | prova + gabarito FATEC | candidato plausível |

“Candidato plausível” significa somente que nomes/estrutura parecem compatíveis. Ainda não significa aprovação semântica do PDF ou do gabarito.

### Regra para FATEC

`fatec.zip` não entra como um todo na ingestion. Antes disso:

1. extrair cada edição para um manifest próprio;
2. excluir/quarentenar arquivos estranhos;
3. validar que o PDF de prova corresponde à edição declarada;
4. validar o gabarito e o domínio de respostas;
5. calcular SHA/tamanho por documento;
6. só então passar a edição pelo contrato corpus → ingestion → review.

2024.1 deve permanecer bloqueada até localizar o caderno correto. 2025.1 pode ter prova/gabarito aproveitáveis, mas o edital do Prouni deve ser descartado do corpus daquela edição.

## O que a auditoria de ZIP prova — e o que não prova

Ela prova que os arquivos existem, são archives legíveis, que os packages gerados têm manifests internos coerentes e, no release atual, que os hashes internos conferem para os bytes presentes.

Ela não prova sozinha:

- correspondência semântica do documento com a edição;
- correção do gabarito;
- autoridade oficial da origem;
- permissão de redistribuição;
- fidelidade de texto/matemática/imagem após extração.

Essas propriedades pertencem a provenance, validation/evidence e review da ingestion.
