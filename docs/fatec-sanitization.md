# FATEC legado: saneamento e normalização

O arquivo `fatec.zip` da raiz é tratado como **legado bruto**, não como fonte pronta para ingestion.

## Regra

`scripts/sanitize_fatec_legacy.py` abre o ZIP externo e cada subarquivo ZIP/RAR. Uma edição só é aceita quando é possível provar a presença de exatamente:

- um PDF de prova;
- um PDF de gabarito.

Arquivos extras não entram no candidato saneado. Cada documento aceito recebe SHA-256 e tamanho em bytes.

Depois, `scripts/normalize_fatec_answers.py` usa a camada de texto dos PDFs, sem OCR, para:

- confirmar a quantidade de questões declarada na prova;
- extrair o gabarito completo;
- exigir sequência 1..N sem lacunas;
- aceitar somente respostas `A`, `B`, `C`, `D` ou `E`;
- identificar a variante quando necessária.

Qualquer conflito ou ausência faz o processo falhar fechado.

## Edições aceitas pelo saneamento

| Edição | Questões objetivas | Variante | Estado |
|---|---:|---|---|
| 2022.2 | 54 | única | saneada |
| 2023.1 | 54 | única | saneada |
| 2023.2 | 54 | única | saneada |
| 2024.2 | 54 | única | saneada |
| 2025.1 | 54 | Tipo A | saneada; arquivo estranho ignorado |
| 2025.2 | 64 | única | saneada |
| 2026.1 | 60 | única | saneada |
| 2026.2 | 60 | única | saneada |

Total esperado após normalização: **454 questões objetivas**.

### 2025.1

O arquivo legado contém prova Tipo A, gabaritos Tipo A e Tipo B e um PDF estranho de Prouni. O saneador preserva a prova e o gabarito; o normalizador usa somente a seção **PROVA TIPO A**, correspondente ao caderno presente. O edital do Prouni é registrado em `ignored_extras` e não participa do corpus saneado.

## Edição bloqueada

### 2024.1

O subarquivo possui um gabarito FATEC, mas o arquivo que deveria ser a prova é um documento do SISU/UFC. Essa edição permanece bloqueada até existir uma prova correta e verificável.

Não inferir questões a partir do gabarito e não reutilizar o PDF incorreto.

## Próximo gate

O resultado saneado ainda não é publicação automática no catálogo do Studium Labs. Para cada edição, o fluxo pretendido é:

`legacy archive -> sanitized documents -> normalized A-E key -> corpus evidence -> generic reference adapter -> ready-for-review -> human review -> catalog`

O produto permanece limitado a **múltipla escolha de resposta única**. Formatos de somatória ou resposta aberta não fazem parte deste pipeline.
