# Studium Labs corpus

Repositório documental usado pela pipeline de ingestão do Studium Labs.

Ele não é o banco normalizado de questões e não publica nada no catálogo sozinho. O objetivo é manter documentos, provenance, hashes, manifests e candidatos de ingestão reproduzíveis.

## Camadas

```text
fontes oficiais / espelhos / agregadores permitidos
                    ↓
             manifests de origem
                    ↓
      download + SHA-256 + empacotamento
                    ↓
              corpus release
                    ↓
       Studium Labs ingestion engine
                    ↓
      validação + revisão humana
                    ↓
                 catálogo
```

## Release atual

O release `corpus-latest` contém pacotes ZIP com PDFs e manifests internos. A auditoria automática abre os ZIPs reais, confere `manifest.json`, `SHA256SUMS.txt`, número de PDFs e SHA-256 dos bytes presentes.

A medição já registrada em `docs/release-inventory.md` encontrou 70 provas e 138 PDFs nos cinco pacotes militares históricos, todos com hashes internos conferentes naquela execução.

## UNESP

`sources/unesp.json` é o primeiro candidato novo construído pela pipeline genérica.

UNESP 2026, 1ª fase, versão 1:

- 90 questões objetivas;
- alternativas A–E;
- uma resposta por questão;
- prova recuperada de espelho público;
- gabarito recuperado de espelho público e conferido contra a URL canônica da VUNESP;
- provenance de mirror e authority oficial mantidas separadas;
- pacote `unesp.zip` reproduzível com hashes/tamanhos por PDF;
- gabarito 1..90 normalizado no manifest para uso em `reference-only`.

A presença no corpus não ativa automaticamente um provider.

## FATEC legado

O `fatec.zip` da raiz é material legado e **não** deve ser consumido diretamente.

`scripts/sanitize_fatec_legacy.py` abre os subarquivos ZIP/RAR e aceita apenas edições com uma prova e um gabarito válidos. `scripts/normalize_fatec_answers.py` extrai a camada de texto dos PDFs e exige um gabarito A–E completo.

Estado atual documentado em `docs/fatec-sanitization.md`:

- 8 edições saneadas;
- 454 questões objetivas esperadas;
- 2024.1 bloqueada por conter um PDF incorreto no lugar da prova;
- 2025.1 preserva somente o caderno Tipo A correspondente e ignora um edital do Prouni estranho ao corpus.

## Contratos

- `contracts/document-v1.json`: identidade documental mínima;
- `contracts/package-v1.json`: contrato de pacote resolvido usado pela ingestion.

O contrato separa:

- origem dos bytes;
- autoridade canônica;
- direitos/uso;
- SHA-256 e tamanho;
- edição/fase/variante;
- estado do gabarito;
- metadados objetivos necessários para ingestion em modo referência.

## Fontes não oficiais

Fontes não oficiais podem ser usadas como rota de bytes, descoberta ou evidência quando necessário.

Isso não muda a provenance: um mirror continua sendo mirror. Quando existe uma fonte oficial usada para conferência, ela é registrada separadamente como autoridade canônica.

## Escopo de resposta

O Studium Labs está, por decisão de produto, limitado a **múltipla escolha com uma única resposta canônica por questão**.

Não entram neste momento:

- somatória de proposições;
- múltiplas respostas corretas;
- questões abertas/discursivas.

Nenhuma prova deve ser convertida artificialmente para A–E apenas para caber no sistema.

## Workflows

### Audit corpus

Audita manifests, release atual, hashes, ZIPs e o legado FATEC.

### Build corpus packages

Reconstrói os pacotes a partir dos manifests versionados. Em pull requests gera artifacts de revisão; publicação no release continua separada e fail-closed.

### Validate corpus packages

Executa o builder com diagnóstico por pacote e preserva artifacts mesmo quando alguma coleção falha, permitindo identificar exatamente a URL/edição problemática.

### Sanitize FATEC legacy corpus

Extrai o legado, coloca edições contaminadas em quarentena, normaliza apenas múltipla escolha A–E e produz um candidato saneado para revisão.

## Regra principal

Um PDF existir e ser baixável não significa que ele está correto, que o gabarito é definitivo ou que a edição pode entrar no catálogo.

O caminho correto é sempre:

`documento → fingerprint → normalização → validação → ready-for-review → revisão humana → catálogo`.
