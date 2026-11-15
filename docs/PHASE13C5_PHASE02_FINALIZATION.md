# Fase 13C.5 — Fechamento da validação P0 e preparação da CI hospedada

**Projeto:** QE-Multiwfn
**Versão:** `0.3.0` (Python), MDM `1.1.0`, ABI nativa `0.2.0`
**Repositório:** `/home/fsia/Quimica/qe_multiwfn_030_dev`
**Commit inicial:** `9c47eafac7d9a8a54cca1b247d10c8d43ef29a62`
**Data:** 2026-11-15
**Status global:** **PASS** no escopo local e de preparação
**CI hospedada:** não executada (sem commit/push autorizado)

## 1. Status global

**PASS** para os critérios autorizados desta fase:

- o pipeline P0 externo não aceita unidade ausente silenciosamente;
- todos os caminhos de geometria auditados têm contrato de unidade coerente;
- os testes correspondentes passam;
- a estratégia P0 está versionada, documentada e reproduzível;
- os skips estão justificados e inventariados;
- os workflows estão tecnicamente preparados;
- a regressão científica P0 permanece estável;
- a integridade nativa, a ABI, o vendor e o frozen foram preservados.

A CI hospedada **não foi executada** e não é declarada como PASS. A execução
depende de autorização para commit/push. Este relatório separa claramente o
que foi executado localmente do que permanece condicionado à publicação.

## 2. Default implícito e correção

Foram encontrados dois pontos no pipeline P0 externo
(`QE-Multiwfn-validation/run_validation.py`):

1. `load_orca_json`: `units = d.get("CoordinateUnits", "Angs")`.
2. `_check_geometry_vs_property`: `unit = "bohr" if "bohr" in unit_raw else "angstrom"`.

Correções:

- `CoordinateUnits` passou a ser obrigatório; ausente levanta
  `CoordinateUnitError` antes de retornar S/C.
- A unidade é validada imediatamente com
  `validation.coordinates.normalize_unit`, a mesma função usada na conversão.
- Unidade desconhecida é rejeitada pela mesma função.
- No bloco `sp.property.txt`, `normalize_unit(unit_raw)` substituiu o fallback
  binário; unidade desconhecida faz a verificação falhar, não assumir Å.
- Não há nova implementação independente de normalização: o pipeline reutiliza
  `normalize_unit`; o adaptador público mantém sua implementação equivalente.

Testes externos novos (`QE-Multiwfn-validation/tests/test_unit_contract_p0.py`):

1. `CoordinateUnits` ausente rejeitada.
2. `CoordinateUnits` desconhecida rejeitada.
3. Å e Bohr explícitos convertem exatamente uma vez e produzem a mesma
   geometria interna.
4. `sp.property.txt` com unidade desconhecida falha a verificação, sem
   assumir Å.

Resultado externo: **227 passed** = 223 testes históricos + 4 novos testes de
contrato de unidade. O pipeline P0 completo com os três sistemas: **PASS**.

## 3. Auditoria do contrato de unidades

| Origem | Unidade de entrada | Unidade interna | Conversão | Comportamento sem unidade |
|---|---|---|---|---|
| ORCA `sp.json` | `CoordinateUnits` (`Angs`/`Bohr`) | Bohr | Å→Bohr uma vez; Bohr fator 1 | **Rejeita** (`OrcaAdapterError`) |
| Pipeline P0 externo | `CoordinateUnits` obrigatório | Bohr | Reutiliza `normalize_unit`/`convert_to_bohr` | **Rejeita** (`CoordinateUnitError`) |
| cclib | `atomcoords` em Å (convenção cclib) | Bohr | Å→Bohr explícito | Convenção documentada da biblioteca |
| ASE | `Atoms.positions` em Å (convenção ASE) | Bohr | Å→Bohr explícito | Convenção documentada da biblioteca |
| PySCF | `atom_coords(unit="Bohr")` | Bohr | Nenhuma | Unidade explícita na chamada |
| `DatabaseRecord` | `coordinate_unit` obrigatório | Bohr | Å→Bohr ou fator 1 | **Rejeita** |
| `MolecularDataBuilder` | `set_geometry(unit=...)` obrigatório | Bohr | Å→Bohr ou fator 1 | **Rejeita** |
| `MolecularSystem.from_arrays` | `coordinates_unit` explícito; default Bohr documentado | Bohr | Å→Bohr; Bohr fator 1 | Contrato legado documentado |
| `MolecularSystem` direto | Coordenadas em Bohr (contrato 0.1.1) | Bohr | Nenhuma | Contrato legado documentado |
| Harness P0 versionado | ORCA `sp.json` via adaptador corrigido | Bohr | Uma vez | **Rejeita** no adaptador |
| Pipeline P0 histórico externo | Corrigido em 13C.5 | Bohr | Uma vez | **Rejeita** |

Nenhuma conversão duplicada foi encontrada. O caso legado

`MolecularSystem` mantém a convenção Bohr documentada; não há inferência por
magnitude. Nenhum contrato público incompatível foi introduzido.

## 4. Auditoria dos workflows de CI

Arquivo: `.github/workflows/ci.yml`.

| Item | Situação |
|---|---|
| `pytest -q -rs` no build-test | Correto; motivos de skip aparecem |
| Build-test descobre testes independentes | Sim: 109 passed, 50 skipped na simulação sem fixtures |
| Job optional instala PySCF/ASE/cclib | Sim: `pyscf==2.15.0`, `ase==3.29.0`, `cclib==1.8.1` |
| Job optional executa testes | Sim: `pytest -q -rs`, não apenas import check |
| Skips transparentes | Sim: `-rs` mostra arquivo, linha e motivo |
| Ausência de fixtures não gera falha artificial | Sim: skips explícitos |
| Falhas reais convertidas em skip | Não |
| `continue-on-error` | Ausente |
| Fixtures artificiais | Não foram criadas |
| P0 versionado descoberto | Sim; manifesto executa, sistemas skipam sem fixtures |
| CTest | 7/7 no build-test |

Simulações locais exatas do workflow:

| Cenário | Resultado |
|---|---|
| Build-test sem fixtures (pytest+numpy) | **109 passed, 50 skipped** |
| Optional-dependency (PySCF/ASE/cclib, sem fixtures) | **114 passed, 46 skipped** |

A CI hospedada não foi executada. As contagens acima são locais e não
substituem a execução no GitHub Actions.

## 5. Situação dos testes P0

Os conjuntos são mantidos distintos:

| Conjunto | Quantidade | Onde | Estado |
|---|---:|---|---|
| P0 histórico | 223 | `QE-Multiwfn-validation/tests` externo | **223/223 passed** |
| Contrato de unidade do pipeline P0 | 4 | externo, novo | **4/4 passed** |
| Protocolo P0 versionado | 6 | `tests/python/test_p0_validation.py` | **6/6 passed** local |
| Testes independentes desbloqueados | 14 | repo | 11 sem pacotes opcionais; 14 com ASE |
| Fixture-dependentes | 101 | repo | skip explícito sem fixtures |
| Suíte geral do repo | 256 | `tests/python` | **256 passed** local |

O protocolo versionado usa:

- `tests/python/test_p0_validation.py`;
- `tests/python/p0_fixtures.json` (16 arquivos externos, SHA-256);
- `scripts/run_p0_validation.sh`.

O manifesto foi verificado; os hashes correspondem. As fixtures externas
ORCA/Multiwfn não são redistribuídas. A ausência é informada por skip com
motivo. Nenhuma referência numérica foi alterada.

## 6. Inventário de skips

`tests/python/skip_inventory.json` lista os 20 módulos e as 115 funções
originais, com:

- módulo, fase e tipo;
- total de funções;
- nomes das funções independentes;
- nomes das funções fixture-dependentes;
- dependência necessária;
- fixture necessária;
- motivo do skip;
- condição para executar.

Totais: **20 módulos, 115 funções, 14 independentes, 101 fixture-dependentes,
11 independentes sem pacotes opcionais**. O teste
`tests/python/test_skip_inventory.py` valida totais, nomes e campos.

Cinco módulos tiveram skips de módulo substituídos por skips por teste:
`test_builder`, `test_mdm_1_1`, `test_normalization`, `test_ase_adapter`,
`test_orca_mdm_1_2`. Os 15 módulos restantes são integralmente
fixture-dependentes ou dependentes de ASE; nesses casos o skip de módulo é
justificado e documentado. Nenhum teste foi removido.

## 7. Resultados dos testes locais

| Alvo | Resultado |
|---|---|
| Suíte local completa com fixtures | **256 passed**, 1 warning |
| Build-test simulado sem fixtures | **109 passed, 50 skipped** |
| Optional simulado sem fixtures | **114 passed, 46 skipped** |
| P0 histórico externo | **223/223 passed** |
| P0 externo com novos testes de unidade | **227/227 passed** |
| Protocolo P0 versionado | **6/6 passed** |
| Unidades geométricas | **10/10 passed** |
| CTest | **7/7** |
| Exemplos | **3/3** |

## 8. Resultados científicos

| Critério | H₂ | H₂O | C₆H₆ |
|---|---:|---:|---:|
| CᵀSC − I | 6.66e-16 | 3.78e-15 | 7.77e-15 |
| Tr(PS) − Nₑ | 1.33e-15 | 1.60e-14 | 2.84e-14 |
| PSP − 2P | 8.88e-16 | 1.78e-14 | 2.23e-14 |
| QE × Multiwfn | 1.33e-15 | 3.61e-9 | 4.98e-9 |
| QE × ORCA | 0 | 9.99e-16 | 1.67e-15 |

- Mayer atual vs baseline histórica: **bit a bit**.
- Energias ORCA: −1.117505885114 / −74.965901192193 / −227.891360374421 Eh.
- Ordem p: `pz,px,py`; códigos `4,2,3`.
- Angs→Bohr: `1.8897261246257702`; geometria vs property 3.31e-9 / 7.05e-9 /
  2.30e-8 Bohr.
- Meta/para: C0–C3 é para (1,4), Mayer 0.115734; C0–C2 é meta (1,3),
  Mayer 0.002046. O rótulo histórico foi corrigido documentalmente; números
  inalterados.

## 9. Integridade da ABI e da biblioteca nativa

| Item | Valor |
|---|---|
| Biblioteca | `b83308c228b787e6dbf4168bf688f3a5757a0a71091998f338ed968d388cb4f5` |
| Frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | **44 = 17 legados + 27 aditivos** |
| Vendor | **74/74** idêntico ao ZIP oficial `a09ce82f…` |
| SONAME | `libqe_multiwfn.so.0` |
| RUNPATH | `$ORIGIN` |
| `ldd -r` | limpo |
| Rebuild nesta fase | nenhum |
| Símbolos legados removidos/renomeados | nenhum |

## 10. Arquivos modificados

### Repositório (tracked)

- `.github/workflows/ci.yml`
- `docs/ADAPTER_CONTRACT_AUDIT.md`
- `docs/ARCHITECTURE.md`
- `docs/CI.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/LIMITATIONS.md`
- `docs/MOLECULAR_DATA_MODEL_1.0.md`
- `docs/ORCA_SUPPORTED_CONVENTIONS.md`
- `python/qe_multiwfn/adapters/orca.py`
- `tests/python/test_ase_adapter.py`
- `tests/python/test_builder.py`
- `tests/python/test_mdm_1_1.py`
- `tests/python/test_normalization.py`
- `tests/python/test_orca_mdm_1_2.py`

### Repositório (novos, não rastreados)

- `docs/PHASE13C3_PHASE02_RETROSPECTIVE_AUDIT.md` (13C.3)
- `docs/PHASE13C4_PHASE02_REMEDIATION.md` (13C.4)
- `docs/PHASE13C5_PHASE02_FINALIZATION.md` (este relatório)
- `scripts/run_p0_validation.sh`
- `tests/python/p0_fixtures.json`
- `tests/python/skip_inventory.json`
- `tests/python/test_geometry_units.py`
- `tests/python/test_p0_validation.py`
- `tests/python/test_skip_inventory.py`

### Externo ao repositório (não versionado)

- `QE-Multiwfn-validation/run_validation.py` (unidade obrigatória; 2 pontos).
- `QE-Multiwfn-validation/tests/test_unit_contract_p0.py` (4 testes novos).

Não modificados: `vendor/`, frozen 0.2.0, ABI, fontes Fortran, biblioteca
nativa.

## 11. Diff resumido

Repositório:

- 14 arquivos rastreados modificados; 9 arquivos novos não rastreados
  (incluindo os relatórios 13C.3/13C.4 pendentes de versionamento).
- Código de biblioteca alterado: apenas
  `python/qe_multiwfn/adapters/orca.py` (fail-closed de unidade).
- Sem alteração Fortran/ABI/vendor/frozen.
- Workflow: `-rs` e execução real de pytest no job optional.

Externo:

- `run_validation.py`: remoção de `d.get("CoordinateUnits", "Angs")` e do
  fallback binário no `sp.property.txt`; reutilização de `normalize_unit`.
- Novo `tests/test_unit_contract_p0.py` com 4 testes.
- Total externo: 223 históricos + 4 = **227 passed**.

## 12. Pendências

1. Autorização para commit/push e execução da CI hospedada.
2. Definição da estratégia definitiva para as fixtures P0 externas
   (repositório privado, artefato autorizado ou runner self-hosted).
3. Auditoria de licenciamento/redistribuição das fixtures na etapa final.
4. Decidir se o pipeline P0 externo será versionado ou permanecerá externo.
5. Reconciliar o manifesto 0.2.0 (`ecc7852a…` vs frozen `9560c0fc…`) fora do
   escopo P0.
6. A origem histórica da Fase 2 continua não confirmável pelo Git.

## 13. Proposta de commit

Nenhum commit foi executado. Proposta para autorização:

**Commit 1 — documentação histórica pendente**

```
docs: add Phase 13C.3 and Phase 13C.4 audit reports
```

Arquivos:
- `docs/PHASE13C3_PHASE02_RETROSPECTIVE_AUDIT.md`
- `docs/PHASE13C4_PHASE02_REMEDIATION.md`

**Commit 2 — fechamento P0/13C.5**

```
fix: enforce explicit geometry units and finalize P0 validation (Phase 13C.5)
```

Arquivos:
- `.github/workflows/ci.yml`
- `docs/ADAPTER_CONTRACT_AUDIT.md`
- `docs/ARCHITECTURE.md`
- `docs/CI.md`
- `docs/IMPLEMENTATION_STATUS.md`
- `docs/LIMITATIONS.md`
- `docs/MOLECULAR_DATA_MODEL_1.0.md`
- `docs/ORCA_SUPPORTED_CONVENTIONS.md`
- `docs/PHASE13C5_PHASE02_FINALIZATION.md`
- `python/qe_multiwfn/adapters/orca.py`
- `scripts/run_p0_validation.sh`
- `tests/python/p0_fixtures.json`
- `tests/python/skip_inventory.json`
- `tests/python/test_ase_adapter.py`
- `tests/python/test_builder.py`
- `tests/python/test_geometry_units.py`
- `tests/python/test_mdm_1_1.py`
- `tests/python/test_normalization.py`
- `tests/python/test_orca_mdm_1_2.py`
- `tests/python/test_p0_validation.py`
- `tests/python/test_skip_inventory.py`

Não usar `git add .`; os arquivos externos do `QE-Multiwfn-validation` não
entram no commit do repositório sem decisão específica de versionamento.

## 14. Condições para executar a CI hospedada

1. Autorização explícita para commit e push.
2. Push sem force; manter `main`.
3. Confirmar que os arquivos externos de validação não serão publicados.
4. Executar o workflow e registrar run/commit:
   - build-test esperado: **109 passed, 50 skipped** sem fixtures;
   - optional esperado: **114 passed, 46 skipped** sem fixtures;
   - CTest **7/7**; exemplos **3/3**; smoke **PASS**.
5. O protocolo P0 versionado continuará com 1 teste de manifesto executando e
   5 testes de sistema/ordem skipados na CI pública sem fixtures. A suíte P0
   de 223/227 testes exige o tree externo e não roda na CI pública.
6. Não declarar CI hospedada PASS antes da execução real.
7. A Fase 13C.6 não deve ser iniciada antes da avaliação deste relatório.

---

## Adendo 13C.5.1 — auditoria pré-commit

A auditoria pré-commit confirmou: repositório principal limpo de staged
changes; 14 arquivos rastreados modificados e 9 novos não rastreados; nenhuma
fixture/binário externo entre os novos arquivos. O pipeline externo **não
possui repositório Git**; sua revisão lógica atual é identificada pelo code
digest `0eedfba6071de5799bdd9a2c965fa0508ff8af24848c6ccab8518bb8ae0befd1`
e pelos hashes de `run_validation.py` (`1425a3c1…`) e
`tests/test_unit_contract_p0.py` (`ce193005…`). O `SHA256SUMS.txt` externo
está defasado e deve ser regenerado antes de um commit externo.

Os 227/227 testes externos foram reexecutados com `QE_ROOT` apontando para a
árvore frozen 0.2.0 (lib `9560c0fc…`); o resultado histórico arquivado da P0
(223) referencia a lib 0.1.1 `b950b0d9…`; o pipeline P0 atual usa a lib 0.3.0
`b83308c2…`. Os três níveis estão registrados na auditoria 13C.5.1. Nenhum
commit/push/tag foi executado. Ver `docs/PHASE13C5_1_PRECOMMIT_AUDIT.md`.

---

**Fim do relatório — Fase 13C.5.**
