# Fase 13C.4 — Consolidação da validação científica P0

**Projeto:** QE-Multiwfn
**Versão:** `0.3.0` (Python), MDM `1.1.0`, ABI nativa `0.2.0`
**Repositório:** `/home/fsia/Quimica/qe_multiwfn_030_dev`
**Commit inicial desta fase:** `9c47eafac7d9a8a54cca1b247d10c8d43ef29a62`
**Data:** 2026-11-15
**Status global:** **PARTIAL**

## 1. Objetivo

Resolver as pendências da auditoria 13C.3: fail-closed de unidades
geométricas, integração versionada do protocolo P0, classificação dos 115
testes ocultos por 20 skips de módulo, reconciliação de tolerâncias e
verificação meta/para do benzeno, preservando os resultados científicos, a
ABI de 44 símbolos, o vendor e a árvore frozen.

## 2. Pendências originais

| ID | Pendência 13C.3 | Estado nesta fase |
|---|---|---|
| U1 | `CoordinateUnits` ausente assumia Å | **Corrigido** no adaptador ORCA; testes adicionados |
| U2 | Suíte P0 de 223 testes externa e fora da CI | **Parcial**: protocolo P0 versionado + fixture manifest; 223 históricos continuam externos |
| U3 | 20 módulos/115 funções ocultos | **Classificado**; 14 testes independentes desbloqueados; 101 fixture-dependentes explícitos |
| U4 | Tolerâncias `1e-5` vs `1e-6` | **Reconciliado** em documentação; nenhum código/tolerância científica alterado |
| U5 | Rótulo meta/para do benzeno | **Esclarecido**: 0.115734 é para (1,4); 0.002046 é meta (1,3) |
| U6 | Origem histórica não confirmável pelo Git | **Mantida como limitação**; nenhuma proveniência inventada |
| U7 | Hash divergente do manifesto 0.2.0 | **Fora do escopo**; registrado |

## 3. Diagnóstico das unidades

| Entrada | Declaração de unidade | Comportamento atual | Decisão |
|---|---|---|---|
| ORCA `sp.json` | `CoordinateUnits` | Å/Bohr explícitos convertidos uma vez; ausente/desconhecida falha fechado | **Fail-closed** |
| cclib | `atomcoords` em Å (convenção cclib) | Å→Bohr explícito no adaptador | Preservado |
| ASE | `Atoms.positions` em Å (convenção ASE) | Å→Bohr explícito | Preservado |
| PySCF | `atom_coords(unit="Bohr")` | Bohr explícito | Preservado |
| `DatabaseRecord` | campo `coordinate_unit` obrigatório | `None`/desconhecida rejeitada | Preservado |
| `MolecularDataBuilder` | `set_geometry(unit=...)` obrigatório | ausente/desconhecida rejeitada | Preservado |
| `MolecularSystem.from_arrays` | `coordinates_unit` explícito; default Bohr documentado | Å converte; Bohr não converte | Contrato legado preservado |
| `MolecularSystem` direto | coordenadas em Bohr (contrato 0.1.1) | sem conversão | Contrato legado preservado |
| Pipeline P0 externo `run_validation.py` | `d.get("CoordinateUnits", "Angs")` | Ainda assume Å se ausente | **Limitação externa**; o harness versionado usa o adaptador fail-closed |

O caminho público `qe_multiwfn.adapters.orca` foi corrigido. O pipeline P0
histórico externo não foi alterado (não versionado); o protocolo P0
versionado usa o adaptador corrigido.

## 4. Correção do contrato de unidades

Alteração em `python/qe_multiwfn/adapters/orca.py`:

```python
def _unit_to_string(raw: Optional[str]) -> str:
    if raw is None:
        raise OrcaAdapterError(
            "ORCA sp.json is missing CoordinateUnits; refusing to infer a unit"
        )
```

- Unidade explícita `Angs`: converte Å→Bohr com `1.8897261246257702`.
- Unidade explícita `Bohr`: fator 1.0, sem conversão duplicada.
- Unidade ausente: `OrcaAdapterError`, sem assumir Å.
- Unidade desconhecida: `OrcaAdapterError`.
- A proveniência registra `coordinate_unit_source`, `conversion_factor` e
  hash das coordenadas convertidas.

Testes novos (`tests/python/test_geometry_units.py`, 10 testes):

1. ORCA Å explícito, conversão única.
2. ORCA Bohr explícito, sem conversão duplicada.
3. ORCA unidade ausente falha fechado.
4. ORCA unidade desconhecida falha fechado.
5. Builder sem unidade/desconhecida rejeita.
6. `DatabaseRecord` sem unidade/desconhecida rejeita.
7. Legado Bohr/Å equivalente; default Bohr documentado.
8. cclib Å→Bohr.
9. PySCF Bohr sem conversão.
10. ASE Å→Bohr (quando ASE disponível).

Nenhuma entrada já validada foi alterada; nenhuma conversão duplicada.

## 5. Integração da suíte P0

Foi adicionado o protocolo versionado:

| Item | Caminho |
|---|---|
| Teste P0 | `tests/python/test_p0_validation.py` |
| Manifesto de fixtures | `tests/python/p0_fixtures.json` |
| Executor | `scripts/run_p0_validation.sh` |

O teste:

- verifica SHA-256 de 16 arquivos externos (sp.json, sp.out,
  sp.property.txt, sp.molden.input, `qe_results/*/mayer.npy`,
  `validation_results.json`);
- reproduz H₂, H₂O e C₆H₆ com a biblioteca atual;
- verifica `CᵀSC`, `Tr(PS)`, `PSP=2P`, simetria, positividade de S;
- compara Mayer ao baseline histórico (≤1e-12) e ao Multiwfn histórico
  (≤1e-6);
- verifica energia ORCA e ordem p `pz,px,py → 4,2,3`.

Sem fixtures externas, os 5 testes de sistema/ordem são skipados com motivo
explícito; o teste de manifesto continua executando. A suíte histórica de
**223 testes** permanece externa (fixtures ORCA/Multiwfn não redistribuídas)
e foi reexecutada com **223/223 passed**.

## 6. Procedência e situação das fixtures

| Categoria | Exemplos | Situação |
|---|---|---|
| Código de teste do projeto | `tests/python/test_p0_validation.py`, manifesto, script | Versionado no repositório |
| Fixtures produzidas pelo projeto | estruturas intermediárias, manifests | Versionadas quando não contêm dados de terceiros |
| Saídas ORCA | `sp.out`, `sp.json`, `sp.property.txt`, `sp.molden.input` | Externas; não redistribuídas |
| Saídas Multiwfn | `bndmat.txt`, `multiwfn_results` | Externas; não redistribuídas |
| Binários ORCA/Multiwfn | ORCA 6.1.1, Multiwfn 2026.11.3 | Externos; não redistribuídos |
| Referências históricas | `qe_results/*/mayer.npy`, `validation_results.json` | Externas; hashes no manifesto |

Hashes verificados:

| Item | SHA-256 |
|---|---|
| ORCA `sp.json` H₂ | `6c9359d3…` |
| ORCA `sp.json` H₂O | `57731542…` |
| ORCA `sp.json` C₆H₆ | `62bb77f3…` |
| `qe_results/h2/mayer.npy` | `b7954252…` |
| `qe_results/h2o/mayer.npy` | `cf5f77b7…` |
| `qe_results/benzene/mayer.npy` | `7b280901…` |
| `validation_results.json` | `6fb8b315…` |
| ORCA 6.1.1 `orca` | `d65fe8fe…` |
| `orca_2json` | `6f190ba3…` |
| `orca_2mkl` | `422c5518…` |
| Multiwfn 2026.11.3 | `39a6c9e0…` |
| ZIP oficial Multiwfn | `a09ce82f…` |

O manifesto completo, com tamanho e hash de cada arquivo, está em
`tests/python/p0_fixtures.json`.

Para reproduzir localmente:

```bash
export QE_P0_FIXTURES=/caminho/autorizado/QE-Multiwfn-validation
./scripts/run_p0_validation.sh
```

A suíte histórica completa pode ser executada em cópia temporária com
`pytest "$QE_P0_FIXTURES/tests" -q`; ela exige o `qe_multiwfn_src` 0.1.1 e,
para os testes CLI, o binário Multiwfn.

## 7. Investigação dos 20 módulos

A classificação individual dos 115 nomes está em
`tests/python/skip_inventory.json`. Resumo:

| Módulo | Funções | Independentes | Fixture-dependentes | Tipo |
|---|---:|---:|---:|---|
| `test_ase_adapter` | 2 | 1 | 1 | integração |
| `test_ase_adapter_phase9c` | 2 | 2 | 0 | estrutural |
| `test_builder` | 11 | 5 | 6 | unitário/integração |
| `test_cache_invalidation` | 2 | 0 | 2 | integração |
| `test_cartesian_df` | 3 | 0 | 3 | científico |
| `test_cclib_adapter` | 4 | 0 | 4 | adaptador |
| `test_full_flow_mdm` | 8 | 0 | 8 | integração |
| `test_genp_integration` | 4 | 0 | 4 | integração |
| `test_genpprim_integration` | 4 | 0 | 4 | integração |
| `test_gensbas_integration` | 6 | 0 | 6 | integração |
| `test_mdm_1_1` | 3 | 1 | 2 | schema |
| `test_native_f_support` | 6 | 0 | 6 | científico |
| `test_normalization` | 9 | 2 | 7 | unitário/científico |
| `test_orca_adapter` | 13 | 0 | 13 | adaptador |
| `test_orca_angular_integration` | 12 | 0 | 12 | científico |
| `test_orca_mdm_1_2` | 7 | 3 | 4 | contrato |
| `test_orca_optimization` | 2 | 0 | 2 | integração |
| `test_pyscf_adapter` | 8 | 0 | 8 | adaptador |
| `test_rohf` | 4 | 0 | 4 | científico |
| `test_uhf` | 5 | 0 | 5 | científico |
| **Total** | **115** | **14** | **101** | |

Os 14 testes independentes são:

- `test_builder`: `test_builder_direct_numpy_rhf_and_array_ownership`,
  `test_builder_requires_explicit_unit_and_open_shell_method`,
  `test_builder_rejects_bad_arrays`,
  `test_engine_direct_path_uses_strict_validation`,
  `test_builder_accepts_noncontiguous_and_float32_arrays`.
- `test_mdm_1_1`: `test_legacy_roundtrip_still_bitwise`.
- `test_normalization`: `test_schema_1_1_and_unit_normalization`,
  `test_legacy_model_normalization_incomplete`.
- `test_ase_adapter`: `test_ase_geometry_only_cannot_run_mayer` (requer ASE).
- `test_ase_adapter_phase9c`: ambos os testes (requerem ASE).
- `test_orca_mdm_1_2`: `test_known_orca_f_convention_shape`,
  `test_unknown_program_fails_closed`,
  `test_phase_matrix_rejects_order_reordering`.

Sem pacotes opcionais (ASE), 11 dos 115 executam na CI build-test; com ASE,
14 executam no job optional. Os 101 restantes exigem fixtures externas
ORCA/Multiwfn e são skipados com motivo explícito.

## 8. Inventário das 115 funções

O arquivo `tests/python/skip_inventory.json` lista, para cada módulo:

- fase histórica;
- tipo (unitário, estrutural, integração, científico, adaptador);
- total de funções;
- nomes das funções independentes;
- nomes das funções fixture-dependentes;
- motivo do skip.

Totais verificados por `tests/python/test_skip_inventory.py`: 115 funções,
20 módulos, 14 independentes, 101 fixture-dependentes, 11 independentes sem
pacotes opcionais.

## 9. Política de skips

- Removidos skips de módulo de `test_builder`, `test_mdm_1_1`,
  `test_normalization`, `test_ase_adapter` e `test_orca_mdm_1_2`; testes
  independentes passaram a executar.
- `test_ase_adapter_phase9c` mantém skip por pacote ASE; o job optional
  executa quando ASE está presente.
- Os 14 módulos restantes são integralmente fixture-dependentes; o skip de
  módulo é mantido e documentado.
- Nenhum teste foi removido; nenhuma falha foi convertida em skip.
- CI usa `pytest -q -rs` para mostrar motivo de cada grupo de skip.
- Nenhum `continue-on-error`.

## 10. Resultados da CI

A CI hospedada **não foi executada** nesta fase porque não houve commit/push
(sem autorização). Foram feitas simulações locais exatas do workflow:

| Cenário | Resultado |
|---|---|
| Suíte local completa, com fixtures externas | **256 passed**, 1 warning |
| Build-test sem fixtures (pytest+numpy) | **109 passed, 50 skipped** |
| Optional-dependency job (PySCF/ASE/cclib, sem fixtures) | **114 passed, 46 skipped** |
| Suíte P0 histórica externa | **223/223 passed** |
| Protocolo P0 versionado (`QE_P0_FIXTURES`) | **6/6 passed** |
| Testes de unidades geométricas | **10/10 passed** |
| CTest | **7/7** |
| Exemplos | **3/3** |

Os skips restantes são de fixtures externas (ORCA/Multiwfn) e de pacotes
opcionais quando ausentes; não há PASS silencioso. A CI hospedada deve ser
executada após autorização de publicação.

## 11. Reconciliação das tolerâncias

| Grandeza | Sistema | Histórico | Atual | Medido | Justificativa |
|---|---|---:|---:|---:|---|
| `CᵀSC − I` | H₂/H₂O/C₆H₆ | `1e-5` em tabela histórica | `1e-10` | 6.66e-16 / 3.78e-15 / 7.77e-15 | Tabela histórica era aceitação frouxa; código é mais estrito; ambos atendidos |
| `Tr(PS) − Ne` | H₂/H₂O/C₆H₆ | `1e-5` | `1e-8` | 1.33e-15 / 1.60e-14 / 2.84e-14 | Idem |
| `PSP − 2P` | H₂/H₂O/C₆H₆ | `1e-5` | `1e-6·escala` | 8.88e-16 / 1.78e-14 / 2.23e-14 | Idem |
| Simetria P/S | H₂/H₂O/C₆H₆ | `1e-8` | `1e-10` | 0 / 0 / 0 | Código mais estrito |
| Positividade S | H₂/H₂O/C₆H₆ | `> 0` | `> 0` | 0.3219 / 0.3632 / 0.1672 | Autovalores positivos |
| QE × Multiwfn | H₂/H₂O/C₆H₆ | `1e-6` | `1e-6` | 1.33e-15 / 3.61e-9 / 4.98e-9 | Critério científico preservado |
| QE × ORCA | H₂/H₂O/C₆H₆ | não explícito | comparação | 0 / 9.99e-16 / 1.67e-15 | Referência ORCA property |
| Energia ORCA | H₂/H₂O/C₆H₆ | 7/12 casas | extração `1e-9` | valores exatos do `sp.out` | QE não calcula energia |
| Densidade P | H₂/H₂O/C₆H₆ | `1e-5` (teste) | `1e-6·escala` | idem | Código mais estrito |

Nenhuma tolerância científica foi relaxada. A tabela MDM 12.4 foi corrigida
de `1e-5`/`1e-8` para `1e-10`/`1e-10`, alinhada à seção 8.3. Relatórios
históricos externos permanecem como registros históricos; o relatório atual é
a referência de reconciliação.

## 12. Verificação meta/para do benzeno

Geometria do `sp.json` (Å), ordem C0..C5, H6..H11:

| Par | Distância (Å) | Mayer | Identificação |
|---|---:|---:|---|
| C0–C1 | 1.38681995 | 1.43520474 | orto (1,2) |
| C0–C2 | 2.40204262 | 0.00204554 | **meta (1,3)** |
| C0–C3 | 2.77363992 | 0.11573400 | **para (1,4)** |

Conclusão: o valor `0.115734` é a interação **para (1,4)**; o valor
`0.002046` é **meta (1,3)**. O relatório histórico rotula a tabela de
`0.115734` como “meta (1,3)”, mas lista pares C0–C3 (para). É erro de rótulo
documental, não de resultado. Nenhum número foi alterado.

## 13. Resultados científicos após correções

- Suíte P0 histórica: **223/223 passed**.
- Pipeline P0 atual com a biblioteca `b83308c2…`: **PASS**.
- Mayer atual vs baseline histórica: **bit a bit** para H₂, H₂O e C₆H₆.
- QE × Multiwfn: 1.33e-15 / 3.61e-9 / 4.98e-9 (critério 1e-6).
- QE × ORCA: 0 / 9.99e-16 / 1.67e-15.
- `CᵀSC`: 6.66e-16 / 3.78e-15 / 7.77e-15.
- `Tr(PS)`: erro 1.33e-15 / 1.60e-14 / 2.84e-14.
- `PSP−2P`: erro 8.88e-16 / 1.78e-14 / 2.23e-14.
- Ordem p: `pz,px,py`; códigos `4,2,3`.
- Conversão: Angs→Bohr, fator `1.8897261246257702`; `geometry_vs_property`
  3.31e-9 / 7.05e-9 / 2.30e-8 Bohr.

Nenhuma referência foi alterada.

## 14. Integridade nativa

| Item | Valor |
|---|---|
| Biblioteca | `b83308c228b787e6dbf4168bf688f3a5757a0a71091998f338ed968d388cb4f5` |
| Frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | 44 = 17 legados + 27 aditivos |
| Vendor | 74 arquivos; idêntico ao ZIP oficial `a09ce82f…` |
| `ldd -r` | limpo |
| RUNPATH | `$ORIGIN` |
| Rebuild nesta fase | nenhum |
| Alteração Fortran/ABI/vendor/frozen | nenhuma |

## 15. Arquivos modificados

Código/testes:

- `python/qe_multiwfn/adapters/orca.py` (unit fail-closed).
- `tests/python/test_builder.py`, `test_mdm_1_1.py`, `test_normalization.py`,
  `test_ase_adapter.py`, `test_orca_mdm_1_2.py` (skips por teste).
- `tests/python/test_geometry_units.py` (novo).
- `tests/python/test_p0_validation.py` (novo).
- `tests/python/test_skip_inventory.py` (novo).
- `tests/python/p0_fixtures.json` (novo).
- `tests/python/skip_inventory.json` (novo).
- `scripts/run_p0_validation.sh` (novo).

CI/documentação:

- `.github/workflows/ci.yml` (`-rs`; job optional executa pytest).
- `docs/CI.md`.
- `docs/ADAPTER_CONTRACT_AUDIT.md`.
- `docs/IMPLEMENTATION_STATUS.md`.
- `docs/LIMITATIONS.md`.
- `docs/MOLECULAR_DATA_MODEL_1.0.md` (MDM-030/MDM-033).
- `docs/ORCA_SUPPORTED_CONVENTIONS.md`.
- `docs/PHASE13C4_PHASE02_REMEDIATION.md` (este relatório).

Não modificados: `vendor/`, frozen 0.2.0, ABI, fontes Fortran, biblioteca
nativa.

## 16. Limitações

1. A suíte P0 histórica de 223 testes continua externa; apenas o protocolo
   versionado de três sistemas e o manifesto foram integrados.
2. 101 funções de teste continuam fixture-dependentes; 14 são independentes
   (11 sem pacotes opcionais, 3 adicionais com ASE).
3. A CI hospedada não foi executada nesta fase (sem commit/push autorizado).
   As contagens 109/50 e 114/46 são simulações locais do workflow.
4. O pipeline P0 histórico externo (`run_validation.py`) ainda usa
   `d.get("CoordinateUnits", "Angs")`; o harness versionado usa o adaptador
   fail-closed. O script externo não foi alterado.
5. Fixtures ORCA/Multiwfn não são redistribuídas; a auditoria definitiva de
   licenciamento permanece para a etapa final.
6. A origem histórica da Fase 2 não é confirmável pelo Git.
7. O hash divergente do `RELEASE_MANIFEST_0.2.0.txt` permanece fora do escopo.

## 17. Pendências remanescentes

1. Autorizar commit/push e executar a CI hospedada; registrar run/commit.
2. Decidir se a suíte P0 externa será versionada/publicada ou executada em job
   dedicado com fixtures autorizadas.
3. Auditar licenciamento/redistribuição das fixtures na etapa final.
4. Reconciliar o rótulo histórico meta/para nos relatórios externos, se
   desejado, sem alterar números.
5. Corrigir o default de unidade no pipeline P0 externo, se ele for mantido
   como ferramenta oficial; o harness versionado já falha fechado.
6. Reconciliar o hash do manifesto 0.2.0 fora do escopo P0.

## 18. Conclusão

**STATUS GLOBAL: PARTIAL.**

As pendências técnicas principais foram resolvidas: unidades ausentes falham
fechado; o protocolo P0 tem teste versionado, manifesto de hashes e executor;
os 115 testes foram individualmente classificados; 14 testes independentes
foram desbloqueados; tolerâncias e meta/para foram reconciliados; e os
resultados P0 permanecem bit a bit preservados.

A fase não é PASS integral porque a suíte P0 histórica de 223 testes e suas
fixtures continuam externas, 101 funções permanecem fixture-dependentes e a
CI hospedada não foi executada (sem autorização de publicação). Nenhuma
correção científica, de ABI, Fortran, vendor ou frozen foi feita.

A Fase 13C.5 não foi iniciada.

---

## Adendo 13C.5 — pipeline P0 externo

A Fase 13C.5 removeu o default `d.get("CoordinateUnits", "Angs")` do pipeline
P0 externo (`QE-Multiwfn-validation/run_validation.py`) e o fallback implícito
do bloco de geometria do `sp.property.txt`. Ambos agora exigem unidade
explícita e reutilizam `validation.coordinates.normalize_unit`; ausente ou
desconhecida falha antes de qualquer cálculo científico. Foram adicionados 3
testes externos de contrato de unidade (total externo 227 = 223 históricos +
4 novos). O adaptador público e o harness versionado já estavam corrigidos na
13C.4.

A CI hospedada continua não executada; as contagens locais permanecem
válidas. Ver `docs/PHASE13C5_PHASE02_FINALIZATION.md`.

---

**Fim do relatório — Fase 13C.4.**
