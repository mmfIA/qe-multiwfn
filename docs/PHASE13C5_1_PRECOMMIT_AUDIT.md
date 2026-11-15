# Fase 13C.5.1 — Auditoria pré-commit e preparação da CI hospedada

**Projeto:** QE-Multiwfn
**Fase:** 13C.5.1 — auditoria somente-leitura e preparação
**Repositório:** `/home/fsia/Quimica/qe_multiwfn_030_dev`
**REMOTE:** `git@github.com:mmfIA/qe-multiwfn.git`
**Branch:** `main`
**Commit base:** `9c47eafac7d9a8a54cca1b247d10c8d43ef29a62`
**Data:** 2026-11-15
**Status global:** **PASS** (auditoria pré-commit)
**Publicação:** nenhum commit, push, tag ou release executado

---

## 1. Estado do repositório principal

| Comando | Resultado |
|---|---|
| `git status --branch` | `main`, up to date with `origin/main` |
| `git status --short` | 14 modificados; 9 não rastreados (antes deste relatório) |
| `git diff --stat` | 14 files, 138 insertions(+), 36 deletions(-) |
| `git diff --check` | sem erros |
| `git diff --cached --stat` | vazio (nada staged) |
| `git log --oneline -10` | 5 commits; HEAD `9c47eaf` |
| `git remote -v` | `origin` fetch/push `git@github.com:mmfIA/qe-multiwfn.git` |
| `git branch -vv` | `* main 9c47eaf [origin/main]` |

Arquivos ignorados presentes: `build/`, `build_13c2/`, `build_audit/`,
`.pytest_cache/`, `python/qe_multiwfn.egg-info/`, `dist-phase11/`,
`dist-phase12/`. Não entram no commit. `build_13c2/` está em
`.git/info/exclude`.

Nenhum arquivo staged; nenhuma alteração de Git foi feita nesta fase.

## 2. Arquivos modificados (tracked)

Todos pertencem ao **Commit B** (correções/validação P0), salvo indicação.

| # | Arquivo | Natureza | Commit |
|---|---|---|---|
| 1 | `.github/workflows/ci.yml` | `-rs`; job optional executa pytest | B |
| 2 | `docs/ADAPTER_CONTRACT_AUDIT.md` | unidade ORCA obrigatória | B |
| 3 | `docs/ARCHITECTURE.md` | contrato de unidades/camadas P0 | B |
| 4 | `docs/CI.md` | estado 13C.4/13C.5 e jobs | B |
| 5 | `docs/IMPLEMENTATION_STATUS.md` | contagens 256/109/50/114/46; P0 | B |
| 6 | `docs/LIMITATIONS.md` | fixtures externas, skips, Git externo | B |
| 7 | `docs/MOLECULAR_DATA_MODEL_1.0.md` | MDM-030/033 para 1e-10 | B |
| 8 | `docs/ORCA_SUPPORTED_CONVENTIONS.md` | `CoordinateUnits` obrigatório | B |
| 9 | `python/qe_multiwfn/adapters/orca.py` | fail-closed de unidade | B |
| 10 | `tests/python/test_ase_adapter.py` | skip por teste | B |
| 11 | `tests/python/test_builder.py` | skip por teste | B |
| 12 | `tests/python/test_mdm_1_1.py` | skip por teste | B |
| 13 | `tests/python/test_normalization.py` | skip por teste | B |
| 14 | `tests/python/test_orca_mdm_1_2.py` | skip por teste | B |

Nenhum binário tracked modificado; `vendor/`, frozen 0.2.0, ABI, Fortran e
biblioteca nativa permanecem intocados.

## 3. Arquivos não rastreados

| # | Arquivo | Tamanho | Tipo | Commit | Observação |
|---|---|---:|---|---|---|
| 1 | `docs/PHASE13C3_PHASE02_RETROSPECTIVE_AUDIT.md` | 33.105 B | texto | **A** | Auditoria 13C.3; completo |
| 2 | `docs/PHASE13C4_PHASE02_REMEDIATION.md` | 18.397 B | texto | **A** | Remediação 13C.4 + adendo 13C.5 |
| 3 | `docs/PHASE13C5_PHASE02_FINALIZATION.md` | 14.819 B | texto | **B** | Fechamento 13C.5 + adendo 13C.5.1 |
| 4 | `scripts/run_p0_validation.sh` | 796 B | shell | **B** | Executor P0; sem dados |
| 5 | `tests/python/p0_fixtures.json` | 2.433 B | JSON | **B** | 16 hashes; **não é fixture** |
| 6 | `tests/python/skip_inventory.json` | 15.266 B | JSON | **B** | 115 nomes/metadados |
| 7 | `tests/python/test_geometry_units.py` | 7.126 B | Python | **B** | 10 testes sintéticos |
| 8 | `tests/python/test_p0_validation.py` | 5.329 B | Python | **B** | Harness P0 |
| 9 | `tests/python/test_skip_inventory.py` | 1.353 B | Python | **B** | Consistência do inventário |
| 10 | `docs/PHASE13C5_1_PRECOMMIT_AUDIT.md` | este arquivo | texto | **B** | Auditoria pré-commit |

Nenhum contém matrizes, coordenadas ORCA, `bndmat`, binários ou fixtures
externas. `p0_fixtures.json` contém somente caminhos relativos, tamanhos e
SHA-256; `skip_inventory.json` contém nomes de testes e metadados. Nenhum
arquivo externo foi copiado.

## 4. Separação proposta dos commits

### Commit A — documentação retrospectiva

Mensagem proposta:

```
docs: document Phase 2 retrospective audits
```

Arquivos:

- `docs/PHASE13C3_PHASE02_RETROSPECTIVE_AUDIT.md`
- `docs/PHASE13C4_PHASE02_REMEDIATION.md`

Escopo inequívoco: relatórios históricos/retrospectivos. Não inclui código,
testes, CI ou fixtures.

### Commit B — correções e validação P0

Mensagem proposta:

```
fix: enforce explicit geometry units and finalize P0 validation
```

Arquivos:

- todos os 14 tracked modificados da seção 2;
- `docs/PHASE13C5_PHASE02_FINALIZATION.md`;
- `docs/PHASE13C5_1_PRECOMMIT_AUDIT.md`;
- `scripts/run_p0_validation.sh`;
- `tests/python/p0_fixtures.json`;
- `tests/python/skip_inventory.json`;
- `tests/python/test_geometry_units.py`;
- `tests/python/test_p0_validation.py`;
- `tests/python/test_skip_inventory.py`.

Não inclui `QE-Multiwfn-validation/` nem qualquer dado ORCA/Multiwfn.
Não usar `git add .`.

A separação é coerente: A é somente documentação retrospectiva; B contém
mudanças funcionais/testes/CI e a documentação da fase corrente. O relatório
13C.5.1 fica em B por depender do estado de B.

## 5. Estado do projeto externo

Diretório real: `/home/fsia/Quimica/QE-Multiwfn-validation`.

| Item | Resultado |
|---|---|
| Repositório Git próprio | **Não** (`fatal: not a git repository`) |
| Remote | inexistente |
| Branch | inexistente |
| Últimos commits | inexistentes |
| Arquivos modificados/não rastreados | não aplicável |
| `run_validation.py` | modificado em 13C.5 (unidade obrigatória) |
| Testes externos | 223 históricos + 4 novos = 227 |
| Fixtures locais | `orca/` 13 MB, `multiwfn_results/` 1,2 MB, etc. |
| Dados não redistribuíveis | ORCA/Multiwfn outputs, binários, `qe_results`, `comparisons` |

### Revisão lógica do código externo que produziu 227/227

Sem Git, a revisão é identificada por hashes:

| Item | SHA-256 |
|---|---|
| Code tree digest (código/testes/validation) | `0eedfba6071de5799bdd9a2c965fa0508ff8af24848c6ccab8518bb8ae0befd1` |
| `run_validation.py` | `1425a3c1e8e175d020d140e6523e36133562a6dc17f469bcd70d246e025997b9` |
| `tests/test_unit_contract_p0.py` | `ce193005c2fa3a55848a2bc33a3307733d940ea5443db6bc0795140f59813e7f` |
| `validation/coordinates.py` | `69b9e617702925d15dc99ad82dfa5aa597dc5ccda4b57f4e3864e71b7b957d9e` |
| `validation/wavefunction_audit.py` | `900c9d72f2d79ee9db7cf6eaf424aeaaf88506109a9c7065d79c3befff8642bd` |
| `orca_extractor.py` | `996b45e62067066f63df6f1f75896f056abdb1c7a03f430986be3eb06e5b63b7` |
| `comparisons/validation_results.json` | `6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70` |
| `SHA256SUMS.txt` | `6aff745e05feee71f9c2c9a6e47a854093353d50ad0dbcb059feaa1869fb97e6` |

O run 227/227 foi feito na cópia `/tmp/audit13c3/valcopy13c5b`; os hashes de
código/teste são idênticos aos do diretório externo atual.

### Observação de ambiente do 227/227

- 223 históricos + 4 novos; `QE_ROOT` apontou para
  `/home/fsia/Quimica/qe_multiwfn_src` (frozen 0.2.0, lib `9560c0fc…`).
- O resultado P0 arquivado (`validation_results.json`, `6fb8b315…`) referencia
  a lib histórica 0.1.1 `b950b0d9…`.
- O pipeline P0 atual usou a lib 0.3.0 `b83308c2…` e passou.
- Os três níveis devem constar do registro de rastreabilidade.

### `SHA256SUMS.txt` externo

Está **defasado**:

- `run_validation.py` no manifesto: hash `55661678…`, tamanho 55.650;
- `run_validation.py` atual: hash `1425a3c1…`, tamanho 55.938;
- `tests/test_unit_contract_p0.py` não aparece no manifesto;
- manifesto gerado em `2026-11-14T17:08:46Z`, antes das mudanças 13C.5.

Deve ser regenerado antes de um commit externo; não foi alterado nesta
auditoria.

### Proposta de versionamento externo

1. Criar repositório Git independente em `QE-Multiwfn-validation` (local ou
   remoto privado).
2. Commitar apenas código/testes/validation/docs/manifests produzidos pelo
   projeto.
3. Excluir do Git: `orca/`, `multiwfn_results/`, `qe_results/`,
   `comparisons/`, `fixtures/`, `df_results/`, `cartesian_results/`,
   `uhf_results/`, `rohf_results/`, `database/`, `extracted/`, `structures/`,
   `backup/`, `__pycache__/`, `.pytest_cache/`, `QE-Multiwfn-validation.zip`,
   `qe_multiwfn_src/` (binário/header histórico; tratar separadamente).
4. Regenerar um manifesto de fixtures apenas com hashes, sem redistribuir
   dados.
5. Registrar a commit SHA externa e o code digest; sem remote público de
   fixtures.

Não copiar o pipeline externo para o repositório principal.

## 6. Rastreabilidade entre os projetos

Registro proposto (versionável em documentação, sem dados):

```json
{
  "protocol": "p0-13c5",
  "qe_multiwfn": {
    "commit": "<sha após Commit B>",
    "library_sha256": "b83308c228b787e6dbf4168bf688f3a5757a0a71091998f338ed968d388cb4f5",
    "frozen_0_2_0_sha256": "9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72"
  },
  "p0_validation": {
    "commit": "<sha após commit externo>",
    "code_digest": "0eedfba6071de5799bdd9a2c965fa0508ff8af24848c6ccab8518bb8ae0befd1",
    "run_validation_sha256": "1425a3c1e8e175d020d140e6523e36133562a6dc17f469bcd70d246e025997b9",
    "unit_test_sha256": "ce193005c2fa3a55848a2bc33a3307733d940ea5443db6bc0795140f59813e7f"
  },
  "fixtures": {
    "manifest": "tests/python/p0_fixtures.json",
    "manifest_sha256": "ed81e41a69c30ed9c1d778590250dee9944b2dc3c2880dab792cac4316660fcb",
    "historical_results_sha256": "6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70"
  },
  "results": {
    "external_227": "227/227",
    "historical_223": "223/223 (arquivo b950b0d9)",
    "versioned_p0": "6/6 local",
    "current_pipeline": "PASS (b83308c2)",
    "main_suite": "256 passed"
  },
  "environment": {
    "host": "Ubuntu 26.04.1 x86_64",
    "fortran": "GNU Fortran 15.2.0",
    "cmake": "4.2.3",
    "python": "3.12.16",
    "orca": "6.1.1",
    "multiwfn": "2026.11.3",
    "openblas": "sistema"
  }
}
```

Nenhum campo contém matrizes ou dados de terceiros; somente hashes,
caminhos e resultados.

## 7. Auditoria do workflow

Arquivo: `.github/workflows/ci.yml`.

| Item | Estado |
|---|---|
| Eventos | `push`, `pull_request` (sem filtro de branch) |
| Branch monitorada | todas; `main` é a principal |
| Jobs | `build-test` e `optional-full` (`needs: build-test`) |
| Build-test | system deps, wheel/sdist, CMake, CTest 7/7, pytest 109/50, venv, smoke |
| Optional | system deps, wheel, wheel+PySCF/ASE/cclib, import check, pytest 114/46 |
| Dependências opcionais | PySCF 2.15.0, ASE 3.29.0, cclib 1.8.1 |
| Artefatos | wheel/sdist em `dist`; **não** há upload de artifact |
| Relatórios | logs do Actions; `-rs` mostra skips |
| Skips | 50 no build-test; 46 no optional (simulações locais) |
| P0 versionado | 1 teste de manifesto executa; 5 sistema/ordem skipam sem fixtures |
| `continue-on-error` | ausente |
| Permissões | nenhum bloco `permissions`; não há operação de escrita |
| Riscos | 223 P0 externos não rodam; 101 testes fixture-dependentes; sem artifact; Node/Ubuntu warnings |

Recomendação opcional de hardening: adicionar `permissions: contents: read`
ao workflow. Não foi alterado nesta fase.

## 8. Comandos preparados para publicação

> **Não executados.** Apresentados apenas como proposta.

### Commit A

```bash
cd /home/fsia/Quimica/qe_multiwfn_030_dev
git add docs/PHASE13C3_PHASE02_RETROSPECTIVE_AUDIT.md \
        docs/PHASE13C4_PHASE02_REMEDIATION.md
git diff --cached --stat
git diff --cached --check
git commit -m "docs: document Phase 2 retrospective audits"
```

### Commit B

```bash
git add .github/workflows/ci.yml \
        docs/ADAPTER_CONTRACT_AUDIT.md \
        docs/ARCHITECTURE.md \
        docs/CI.md \
        docs/IMPLEMENTATION_STATUS.md \
        docs/LIMITATIONS.md \
        docs/MOLECULAR_DATA_MODEL_1.0.md \
        docs/ORCA_SUPPORTED_CONVENTIONS.md \
        docs/PHASE13C5_PHASE02_FINALIZATION.md \
        docs/PHASE13C5_1_PRECOMMIT_AUDIT.md \
        python/qe_multiwfn/adapters/orca.py \
        scripts/run_p0_validation.sh \
        tests/python/p0_fixtures.json \
        tests/python/skip_inventory.json \
        tests/python/test_ase_adapter.py \
        tests/python/test_builder.py \
        tests/python/test_geometry_units.py \
        tests/python/test_mdm_1_1.py \
        tests/python/test_normalization.py \
        tests/python/test_orca_mdm_1_2.py \
        tests/python/test_p0_validation.py \
        tests/python/test_skip_inventory.py
git diff --cached --stat
git diff --cached --check
git commit -m "fix: enforce explicit geometry units and finalize P0 validation"
```

### Push e CI

```bash
git push origin main
git ls-remote origin refs/heads/main
gh run list --limit 5 --json databaseId,headSha,status,conclusion,url,createdAt
gh run watch <RUN_ID> --exit-status
gh run view <RUN_ID> --json conclusion,status,headSha,url,jobs
gh run view --job <BUILD_TEST_JOB_ID> --log
gh run view --job <OPTIONAL_JOB_ID> --log
```

Sem force push. Sem tag/release.

## 9. Pendências

1. Autorização explícita para Commit A e Commit B.
2. Autorização para push e execução da CI hospedada.
3. Criar/decidir o repositório Git externo para `QE-Multiwfn-validation`.
4. Regenerar o `SHA256SUMS.txt` externo após as mudanças 13C.5.
5. Auditar licenciamento/redistribuição das fixtures.
6. Decidir se o pipeline externo será versionado ou permanecerá externo.
7. Reconciliar o hash do `RELEASE_MANIFEST_0.2.0.txt` fora do escopo P0.
8. Registrar a proveniência histórica da Fase 2 como não confirmável pelo Git.

## 10. Riscos identificados

| ID | Risco | Mitigação |
|---|---|---|
| R1 | Projeto externo sem Git; revisão só por hashes | Criar repo externo e registrar commit/digest |
| R2 | `SHA256SUMS.txt` externo defasado | Regenerar antes do commit externo |
| R3 | 223 P0 externos não rodam na CI | Manter externo e documentar; job autorizado/self-hosted |
| R4 | 101 testes fixture-dependentes | Inventário explícito; não declarar cobertura integral |
| R5 | Optional job testa source (`PYTHONPATH`) e não wheel instalado | Smoke instalado cobre wheel; documentar distinção |
| R6 | P0 versionado skipa 5 testes na CI | Manifesto executa; `-rs` transparente |
| R7 | Caminhos absolutos `/home/fsia` em docs | Proveniência, não segredo; decidir redaction futura |
| R8 | Sem artifact upload | Logs do Actions; adicionar artifact se necessário |
| R9 | Node 20/`ubuntu-latest` warnings | Não bloqueante; acompanhar migração |
| R10 | Fixtures de terceiros com licença não auditada | Não redistribuir; auditoria final |

## 11. Recomendação final

**PASS** para a auditoria pré-commit. Os arquivos estão classificados, os
commits A/B têm escopo inequívoco, nenhuma fixture externa está incluída, o
estado do projeto externo foi esclarecido e os comandos/CI estão preparados.
Nenhuma publicação foi realizada.

Recomenda-se:

1. revisar este relatório e autorizar Commit A e Commit B;
2. autorizar push e execução da CI hospedada;
3. criar o repositório externo independente e regenerar seu manifesto;
4. manter a Fase 13C.6 bloqueada até a avaliação da CI.

---

**Fim do relatório — Fase 13C.5.1.**
