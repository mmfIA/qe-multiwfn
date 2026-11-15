# Fase 13C.3 — Auditoria retrospectiva da Fase 2

## Validação científica P0 — QE-Multiwfn 0.3.0

**Projeto:** QE-Multiwfn
**Fase auditada:** Fase 2 — P0: validação científica inicial
**Versão histórica:** QE-Multiwfn `0.1.1`
**Versão atual:** `0.3.0` (Python), MDM `1.1.0`, ABI nativa `0.2.0`
**Repositório:** `/home/fsia/Quimica/qe_multiwfn_030_dev`
**Commit de referência:** `9c47eafac7d9a8a54cca1b247d10c8d43ef29a62`
**Data:** 2026-11-15
**Natureza:** auditoria somente-leitura; nenhum código, teste, biblioteca, ABI, CI ou documento existente foi alterado.

## Status global desta auditoria

**PARTIAL.**

Os requisitos científicos centrais da P0 são reproduzíveis e numericamente
corretos: H₂, H₂O e C₆H₆ foram validados com ORCA, as relações
`CᵀSC=I`, `P=2CoccCoccᵀ`, `Tr(PS)=Nₑ` e `PSP=2P` fecham em precisão de
máquina, a ordem p `pz,px,py` é preservada e a biblioteca atual reproduz
bit a bit as matrizes Mayer históricas.

A classificação é **PARTIAL** por três lacunas reais:

1. o adaptador ORCA atual (e o pipeline P0 histórico) assume silenciosamente
   `Å` quando `CoordinateUnits` está ausente, contrariando a decisão de
   unidades explícitas;
2. a suíte P0 de 223 testes é externa ao repositório e **não** é executada
   pela CI hospedada; os 20 skips da CI pertencem a fases posteriores;
3. os registros históricos completos (comandos, resíduos/teste, inventário
   original) não foram preservados, e a origem da Fase 2 não é confirmável
   pelo Git.

Não há falha científica comprovada nos sistemas de referência; por isso
**FAIL = 0**.

| Classificação | Quantidade |
|---|---:|
| PASS | 29 |
| PARTIAL | 2 |
| FAIL | 0 |
| NOT VERIFIED | 2 |
| SUPERSEDED | 1 |
| **Total de linhas da matriz** | **34** |

---

## 1. Objetivo

Determinar se os critérios científicos da Fase 2 (P0) continuam satisfeitos
pela implementação atual, confrontando o CHECKPOINT 02, o código publicado, os
testes, as referências numéricas, as convenções de orbitais/base e a extração
ORCA. A auditoria não se limita a compilar/importar: verifica as relações
matemáticas e a correspondência entre coeficientes, overlap, densidade, base e
geometria.

## 2. Fontes históricas

| Fonte | Caminho | SHA-256 / observação |
|---|---|---|
| CHECKPOINT 02 | `~/Quimica/CHECKPOINTS/PHASE02_CHECKPOINT.md` | `5107dba478aab990a10c69ab8e19980347970e39d5765f5128efa84b4e6f8282`; 209 linhas, lido integralmente |
| Relatório P0 operacional | `~/Quimica/P0_audit_20261114_153054/reports/P0_OPERATIONAL_VERIFICATION.md` e cópia em `QE-Multiwfn-validation/reports/` | ambos `4b88d0386a5f0f0ff0c298f1d74451c0ec0da605f60f0ad1c5c5dd007dacc78a` |
| Resultados P0 armazenados | `QE-Multiwfn-validation/comparisons/validation_results.json` | `6fb8b315c8d7d3911e8c020a8e1a22d0b2b8701f4a820cc1da66c25e11061f70` |
| Suíte P0 | `QE-Multiwfn-validation/tests/` (13 arquivos) | 223 testes; executada em cópia temporária |
| Relatórios científicos | `QE-Multiwfn-validation/reports/` | H₂/H₂O, benzeno, proveniência, execução Multiwfn, test report |
| Código atual | `src/`, `python/`, `tests/` do repositório | commit `9c47eaf` |
| Git | `.git` | 5 commits; nenhum commit/tag da Fase 2 |

A árvore `QE-Multiwfn-validation` **não está versionada no repositório**. Ela
é a fonte operacional da P0 e foi executada apenas em cópia temporária
(`/tmp/audit13c3/valcopy`) para não alterar artefatos canônicos.

## 3. Resumo da Fase 2 original

O CHECKPOINT 02 descreve uma reconstrução documental da P0:

- sistemas H₂, H₂O e C₆H₆ em RHF/STO-3G, com referência ORCA;
- matriz de overlap, coeficientes orbitais, ocupações, densidade e ordem de
  funções de base;
- verificação de `CᵀSC=I`, `P=2CoccCoccᵀ` e `Tr(PS)=Nₑ`;
- identificação de incompatibilidade de ordenação p no parser cclib;
- adoção de `orca_2json` para extração confiável;
- exigência de unidades geométricas explícitas (`angstrom` ou `bohr`);
- validação antes das rotinas nativas, com comparação a programa de referência.

O próprio checkpoint registra a ausência de comandos completos, arquivos
individuais, resíduos por comparação e inventário exato de testes. O status
histórico declarado é “CONCLUÍDO”, mas esta auditoria o confronta com o código
e os artefatos atuais, não o aceita por declaração.

## 4. Requisitos P0 identificados

| ID | Requisito |
|---|---|
| P01 | H₂ RHF/STO-3G como sistema de referência |
| P02 | H₂O RHF/STO-3G como sistema de referência |
| P03 | C₆H₆ RHF/STO-3G como sistema de referência |
| P04 | Cálculos ORCA como referência independente |
| P05 | Energias de referência preservadas |
| P06 | Comparação energética não substitui matrizes/orbitais/densidade |
| P07 | Correspondência base/AO/primitivas/coeficientes/S/P/ocupações/ordem |
| P08 | Ortogonalidade `CᵀSC=I` |
| P09 | Densidade RHF `P=2CoccCoccᵀ` |
| P10 | Densidade só com ocupações/orientação identificadas |
| P11 | Contagem eletrônica `Tr(PS)=Nₑ` independente |
| P12 | Identificação da incompatibilidade de ordenação p (cclib) |
| P13 | Correspondência explícita AO/componente/centro/coeficiente/posição |
| P14 | Adoção de `orca_2json` para extração confiável |
| P15 | Unidades geométricas explícitas (`angstrom`/`bohr`) |
| P16 | Conversão controlada e documentada |
| P17 | Não inferir silenciosamente unidade ausente/ambígua |
| P18 | Validar dados científicos antes das rotinas nativas |
| P19 | Ordenação das funções de base explícita |
| P20 | Comparação com referência considerando convenções |
| P21 | Incompatibilidades de parser tratadas no adaptador, não no núcleo |
| P22 | Validação inclui propriedades matemáticas, não só energias |
| P23 | Registros históricos completos (comandos, arquivos, resíduos, testes) |
| P24 | Referências não alteradas sem nova validação |
| P25 | Nenhuma reordenação arbitrária para forçar concordância |
| P26 | Densidade não construída sem ocupações conhecidas |
| P27 | Alterações futuras exigem testes e documentação próprios |
| D01 | Mapa AO→primitiva explícito no modelo (evolução posterior) |
| A01 | Suíte P0 reproduzível localmente |
| A02 | Biblioteca atual reproduz a P0 histórica |
| A03 | Biblioteca atual vs Multiwfn standalone fresco |
| A04 | Suíte P0 executada pela CI hospedada |
| A05 | Origem histórica da Fase 2 confirmável pelo Git |
| A06 | Integridade da ABI, biblioteca, vendor e frozen |

## 5. Sistemas de referência

| Sistema | Método/base | ncenter | nbasis | nprims | Nₑ | Referência |
|---|---|---:|---:|---:|---:|---|
| H₂ | RHF/STO-3G | 2 | 2 | 6 | 2 | ORCA 6.1.1 |
| H₂O | RHF/STO-3G | 3 | 7 | 21 | 10 | ORCA 6.1.1 |
| C₆H₆ | RHF/STO-3G | 12 | 36 | 108 | 42 | ORCA 6.1.1 |

Esses valores foram extraídos dinamicamente do `sp.json`/`sp.out`, não
impostos por dicionário. A carga é 0 e a multiplicidade é 1 nos três casos.

## 6. Análise de energias

### 6.1 Valores recuperados

| Sistema | `FINAL SINGLE POINT ENERGY` (Eh) | Checkpoint | Consistência |
|---|---:|---:|---|
| H₂ | `-1.117505885114` | `-1.1175059` | arredondamento a 7 casas |
| H₂O | `-74.965901192193` | `-74.9659012` | arredondamento a 7 casas |
| C₆H₆ | `-227.891360374421` | `-227.891360374421` | exato |

`Total Energy` do ORCA também foi extraído:
H₂ `-1.11750588511423`, H₂O `-74.96590119219337`, C₆H₆
`-227.89136037442066`. SCF convergiu e a terminação foi normal nos três casos.

### 6.2 Limite da comparação energética

A biblioteca QE-Multiwfn **não calcula energia eletrônica**. A energia ORCA é
usada como referência de proveniência/integridade do cálculo, não como saída
da biblioteca. A validação científica da P0 é feita por propriedades
matemáticas (S, C, P) e pela matriz Mayer comparada a ORCA e Multiwfn. Isso é
compatível com o checkpoint, que alerta que a energia não substitui a
validação das matrizes.

## 7. Análise de ortogonalidade

Critério efetivo no código: `TOL_ORTHONORM = 1e-10` em
`validation/wavefunction_audit.py` e no adaptador ORCA.

| Sistema | `max(abs(CᵀSC − I))` | Limite | Resultado |
|---|---:|---:|---|
| H₂ | `6.66e-16` | `1e-10` | PASS |
| H₂O | `3.78e-15` | `1e-10` | PASS |
| C₆H₆ | `7.77e-15` | `1e-10` | PASS |

As dimensões são `(nbasis, nbasis)`: 2, 7 e 36. `C` é
`(nbasis, nmo)` com `nmo=nbasis` para RHF; a orientação é
“linhas = AO, colunas = MO”. O erro está na precisão de máquina.

O checkpoint não informa tolerância. Os relatórios históricos exibem
`1e-5` em algumas tabelas, mas o código de auditoria usa `1e-10`; os resíduos
reais são muito menores que ambos. A divergência de documentação é registrada
em §19/§20; não foi alterada.

## 8. Análise das matrizes de densidade

Implementação verificada em `validation/wavefunction_audit.py`
(`build_density_rhf`) e no adaptador ORCA atual:

```
P = 2 * C_occ @ C_occ.T
```

com ocupações RHF exclusivamente 0 ou 2, `nocc = Nₑ/2` e `C_occ` formado
pelas colunas ocupadas. O adaptador atual rejeita ocupação fracionária ou
aberta antes de construir P.

| Sistema | nocc | Ocupações | Simetria `max(abs(P−Pᵀ))` | Resultado |
|---|---:|---|---:|---|
| H₂ | 1 | 2, 0 | 0.0 | PASS |
| H₂O | 5 | 2×5, 0×2 | 0.0 | PASS |
| C₆H₆ | 21 | 2×21, 0×15 | 0.0 | PASS |

A densidade não é construída a partir de `occ > 0` sem validação: a função
`build_density_rhf` rejeita ocupações diferentes de 0/2. A matriz P é simétrica
e é passada à biblioteca junto com S na mesma ordem de AO.

## 9. Contagem eletrônica

Critério efetivo: `Tr(PS)` comparado a `Nₑ` com `TOL_ELECTRON_COUNT = 1e-8`.

| Sistema | `Tr(PS)` | `Nₑ` | Erro | Resultado |
|---|---:|---:|---:|---|
| H₂ | `2.0000000000000013` | 2 | `1.33e-15` | PASS |
| H₂O | `10.000000000000016` | 10 | `1.60e-14` | PASS |
| C₆H₆ | `42.00000000000003` | 42 | `2.84e-14` | PASS |

A verificação é independente da energia: usa P e S reais, não a energia ORCA.
A origem de P é a construção RHF acima; a origem de S é `S-Matrix` do
`sp.json` ORCA, na mesma ordem de AO de C.

## 10. Ordenação das funções de base e convenção p

### 10.1 Ordem observada

Para C₆H₆, os primeiros labels ORCA são:

```
0C 1s, 0C 2s, 0C 1pz, 0C 1px, 0C 1py, 1C 1s, 1C 2s, ...
```

O adaptador atual preserva a ordem de origem e atribui os códigos de
componente do Multiwfn:

| Label | Componente | `multiwfn_type` |
|---|---|---:|
| `1s` | s | 1 |
| `1pz` | pz | 4 |
| `1px` | px | 2 |
| `1py` | py | 3 |

A ordem p `pz, px, py` é preservada em C, S, P e no mapa de AO. O teste
`test_pyscf_adapter.py::test_pyscf_p_components_are_distinct_and_ordered`
verifica explicitamente `["pz","px","py"] → [4,2,3]`; ele é skipado na CI por
falta de PySCF (ver §14), mas passa localmente.

### 10.2 Incompatibilidade histórica do cclib

O documento `orca_extractor.py` registra que cclib 1.8.1 reordena funções p
(`pz,px,py`) ao ler ORCA, quebrando a correspondência C/S. A solução histórica
foi ler S e C da mesma fonte, preservando a ordem, e adotar `orca_2json` como
caminho de extração confiável. O adaptador atual lê `S-Matrix`, `MOs` e
`OrbitalLabels` do `sp.json`, todos na mesma ordem; o adaptador cclib atual
falha fechado para o parser ORCA real e, sem base explícita, produz modelo
incompleto que não executa Mayer.

Não houve reordenação arbitrária para fazer resultados coincidirem. A
correspondência é sustentada por `CᵀSC` e pela comparação bit a bit de S/P/C
com as matrizes históricas.

### 10.3 `basis_type` histórico

O pipeline P0 usa `basis_type` grosseiro `0=s,1=p,2=d`, não o código de
componente real do Multiwfn. `calcMayerbndord` não usa `basis_type`; a
correspondência de posição C/S é o que importa para Mayer. O MDM 1.0/1.1
posterior substituiu esse mapeamento por códigos de componente, shells,
primitivas e `source_ao_index` (D01, SUPERSEDED).

A ordem canônica cartesiana declarada em `angular.py` para transformações
explícitas de d/f (`px,py,pz`) não é aplicada ao caminho P0: a canonicalização
angular trata l=0/1 como identidade e o MDM preserva a ordem de origem
`pz,px,py`; o adaptador PySCF mapeia explicitamente para essa ordem.

## 11. Tratamento das unidades

### 11.1 Conversão nos dados válidos

Todos os `sp.json` históricos declaram `"CoordinateUnits": "Angs"`.
A conversão usa `1 Å = 1.8897261246257702 Bohr` e é registrada como
`coordinate_units_source=Angs`, `target=bohr`.

| Sistema | Fonte | Fator | `geometry_vs_property` |
|---|---|---|---:|
| H₂ | Angs | `1.8897261246257702` | `3.31e-09` Bohr |
| H₂O | Angs | `1.8897261246257702` | `7.05e-09` Bohr |
| C₆H₆ | Angs | `1.8897261246257702` | `2.30e-08` Bohr |

Não há conversão duplicada: o pipeline P0 converte para Bohr e passa
`coordinates_unit="bohr"` ao `MolecularSystem`; o adaptador atual armazena
Bohr em `Geometry` e o Engine envia `QE_V1_UNIT_BOHR`.

### 11.2 Comportamento com unidade ausente

O código atual `_unit_to_string(mol.get("CoordinateUnits"))` retorna
`"angstrom"` quando o campo é `None`. O pipeline P0 histórico faz o mesmo com
`d.get("CoordinateUnits", "Angs")`.

Teste executado em cópia temporária: removendo `CoordinateUnits` do `sp.json`
de H₂, o adaptador **aceitou** o modelo e converteu as coordenadas como Å
(fator `1.8897261246257702`). Isso contraria a decisão do checkpoint de não
inferir silenciosamente unidades. Não há teste versionado para unidade
ausente no adaptador ORCA.

Classificação específica: **PARTIAL**. A unidade explícita funciona e é
validada nos três sistemas, mas a ausência não falha de forma controlada.

## 12. Auditoria ORCA e cclib

### 12.1 Caminho ORCA atual

O adaptador `python/qe_multiwfn/adapters/orca.py` lê `sp.json` produzido por
`orca_2json`. Campos obrigatórios: `Atoms`, `S-Matrix`, `MolecularOrbitals`,
`Charge`, `Multiplicity`, `HFTyp`. Ele:

- exige RHF fechado e multiplicidade 1;
- lê Z, coordenadas e unidade;
- constrói shells, primitivas e mapa AO→centro/shell/componente;
- lê S, C, energias e ocupações;
- valida finitude, simetria, positividade de S, `CᵀSC`, `Tr(PS)`, `PSP`;
- deriva `P=2CoccCoccᵀ` no adaptador;
- registra hashes e proveniência.

Testes locais de adaptador: 73 passaram nos módulos ORCA/P0/full-flow/UHF/ROHF/
f/Cartesian (ver §13).

### 12.2 cclib

O adaptador cclib atual:

- `from_cclib` falha fechado para o parser ORCA 6.1.1 real (cclib 1.8.1
  `orcaparser.py:2799` `IndexError` documentado);
- `from_cclib_data` aceita dados sintéticos com base canônica explícita e
  valida `CᵀSC`/`Tr(PS)` no modelo;
- sem base, cria modelo `unspecified` sem AO map e não executa Mayer.

Portanto, o suporte cclib atual **não é equivalente** ao parser ORCA JSON e
não substitui a extração `orca_2json`. Isso é consistente com o checkpoint e
com `docs/LIMITATIONS.md`.

## 13. Testes e fixtures

### 13.1 Suíte P0 externa

Executada em cópia temporária `/tmp/audit13c3/valcopy` com
`QE_ROOT=~/Quimica/qe_multiwfn_src`, `MULTIWFN_BIN` real e
`PYTHONDONTWRITEBYTECODE=1`:

```
223 passed in 2.55s
```

Cobertura por arquivo (do `reports/TEST_REPORT.md`): 19 basis mapping, 32
benzene, 16 benzene basis, 6 CLI, 9 coordinates, 15 dynamic extraction, 7
energy extraction, 12 manifest, 13 Multiwfn isolation, 14 regression, 42
regression all, 13 status, 25 wavefunction. Total 223.

### 13.2 Testes atuais do repositório

| Conjunto | Resultado |
|---|---:|
| `test_orca_adapter`, `test_full_flow_mdm`, `test_native_f_support`, `test_uhf`, `test_rohf`, `test_cartesian_df`, `test_orca_angular_integration`, `test_orca_mdm_1_2` | **73 passed** |
| Suíte Python completa do repositório | **238 passed**, 1 warning |
| CTest | **7/7** |
| Exemplos | **3/3** |

### 13.3 Pipeline P0 contra a biblioteca atual

Executado em `/tmp` com `QE_MULTIWFN_LIBRARY` apontando para a biblioteca
atual `b83308c2…` e Multiwfn 2026.11.3 fresco:

```
STATUS GLOBAL: PASS
H2: PASS   max|Δ QE−MW| = 1.33e-15
H2O: PASS  max|Δ QE−MW| = 3.61e-09
C6H6: PASS max|Δ QE−MW| = 4.98e-09
```

Cada molécula passou 34/34 verificações obrigatórias (23 matemáticas, 4 de
execução, 4 de comparação, 3 de proveniência).

## 14. Análise dos 20 testes ignorados

A CI `build-test` reporta **87 passed, 20 skipped** (run `43711807880`, commit `9c47eaf`). Reproduzindo o ambiente
da CI em venv com apenas `pytest` e `numpy`, obteve-se exatamente
**87 passed, 20 skipped**. Os 20 skips são entradas de módulo (não 20 funções
individuais); juntos eles escondem **115 funções de teste**.

| # | Arquivo | Motivo do skip | Funções | Fase | Relação com P0 |
|---|---|---|---:|---|---|
| 1 | `test_ase_adapter.py` | fixtures indisponíveis | 2 | 4/9C | não |
| 2 | `test_ase_adapter_phase9c.py` | `ase` ausente | 2 | 9C | não |
| 3 | `test_builder.py` | fixtures científicas ausentes | 11 | 9B/10 | não |
| 4 | `test_cache_invalidation.py` | fixtures ausentes | 2 | 6 | não |
| 5 | `test_cartesian_df.py` | fixture Cartesian ausente | 3 | 8B/10 | não |
| 6 | `test_cclib_adapter.py` | fixtures ausentes | 4 | 4/6 | parcial (cclib histórico) |
| 7 | `test_full_flow_mdm.py` | fixtures ausentes | 8 | 6E | posterior, mesma base |
| 8 | `test_genp_integration.py` | fixtures ausentes | 4 | 6A | não |
| 9 | `test_genpprim_integration.py` | fixtures ausentes | 4 | 6B | não |
| 10 | `test_gensbas_integration.py` | fixtures ausentes | 6 | 6C/6D | não |
| 11 | `test_mdm_1_1.py` | fixtures ausentes | 3 | MDM 1.1 | não |
| 12 | `test_native_f_support.py` | fixture H₂S ausente | 6 | 8B | não |
| 13 | `test_normalization.py` | fixtures ausentes | 9 | 5/10 | não |
| 14 | `test_orca_adapter.py` | fixtures ORCA ausentes | 13 | 4/6/7 | parcial (H₂/H₂O/C₆H₆) |
| 15 | `test_orca_angular_integration.py` | fixtures ausentes | 12 | 7C | não |
| 16 | `test_orca_mdm_1_2.py` | fixtures ausentes | 7 | 7C | não |
| 17 | `test_orca_optimization.py` | fixtures ausentes | 2 | 9 | não |
| 18 | `test_pyscf_adapter.py` | `pyscf` ausente | 8 | 9C/10 | não |
| 19 | `test_rohf.py` | fixtures ROHF ausentes | 4 | 6/8C | não |
| 20 | `test_uhf.py` | fixtures UHF ausentes | 5 | 6 | não |

Conclusões:

- **Nenhum dos 20 skips é a suíte P0 de 223 testes.** A P0 está fora do
  repositório e não é executada pela CI.
- Todos os 20 módulos passam localmente quando as fixtures e pacotes
  opcionais estão presentes, como parte dos 238 passed.
- A CI `optional-full` instala PySCF/ASE/cclib, mas só faz import check; não
  executa pytest. Portanto, os 115 testes ocultos e a P0 não são cobertos
  pela CI.
- A ausência compromete a **cobertura de regressão hospedada**, não a
  validade científica local da P0.

## 15. Comparação científica independente

### 15.1 Biblioteca atual vs baseline histórica

Comparação da matriz Mayer do pipeline P0 atual (biblioteca `b83308c2…`) com
`QE-Multiwfn-validation/qe_results/<mol>/mayer.npy`:

| Sistema | `np.array_equal` | `max(abs(Δ))` |
|---|---|---:|
| H₂ | True | 0.0 |
| H₂O | True | 0.0 |
| C₆H₆ | True | 0.0 |

A reprodução é bit a bit, não apenas dentro de tolerância.

### 15.2 QE vs Multiwfn standalone fresco

| Sistema | `max(abs(Δ))` | Critério | Resultado |
|---|---:|---:|---|
| H₂ | `1.33e-15` | `1e-6` | PASS |
| H₂O | `3.61e-09` | `1e-6` | PASS |
| C₆H₆ | `4.98e-09` | `1e-6` | PASS |

As diferenças de ~1e-9 são compatíveis com o arredondamento de 8 casas da
saída textual do Multiwfn, como documentado no relatório P0.

### 15.3 QE vs ORCA

| Sistema | Pares | `max(abs(QE−ORCA))` |
|---|---:|---:|
| H₂ | 1 | `0.0` |
| H₂O | 2 | `9.99e-16` |
| C₆H₆ | 15 | `1.67e-15` |

### 15.4 Matrizes S, C, P

Os testes `test_orca_matrices_are_bitwise_reproducible` e
`test_orca_v1_engine_reproduces_baseline_mayer` comparam S, P e Mayer com
`np.array_equal` contra os artefatos históricos; passaram localmente para os
três sistemas. A suíte P0 também verifica S positivo, P simétrico, P
idempotente e `Tr(PS)`.

## 16. Matriz de requisitos

> C = requisito do CHECKPOINT 02; D = característica histórica ampliada
> posteriormente; A = item de verificação desta auditoria.

| ID | Requisito histórico | Implementação atual | Arquivos | Evidência científica | Teste | Resultado | Classificação |
|---|---|---|---|---|---|---|---|
| P01 | H₂ RHF/STO-3G | Sistema validado | `QE-Multiwfn-validation/orca/h2`; `validation/` | nbasis=2, nprims=6, Ne=2, CᵀSC=6.66e-16, TrPS=2 | P0 223; pipeline atual | PASS | PASS |
| P02 | H₂O RHF/STO-3G | Sistema validado | `.../orca/h2o`; `validation/` | nbasis=7, nprims=21, Ne=10, CᵀSC=3.78e-15 | P0 223; pipeline atual | PASS | PASS |
| P03 | C₆H₆ RHF/STO-3G | Sistema validado | `.../orca/benzene`; `validation/` | nbasis=36, nprims=108, Ne=42, CᵀSC=7.77e-15 | P0 223; pipeline atual | PASS | PASS |
| P04 | Referência ORCA | ORCA 6.1.1; JSON e property | `orca/*/sp.json`, `sp.out`, `sp.property.txt` | SCF convergido, terminação normal, 10 arquivos por molécula | P0 223; pipeline atual | PASS | PASS |
| P05 | Energias de referência | Extraídas de `sp.out` | `run_validation.py:extract_orca_energies` | H₂ −1.117505885114; H₂O −74.965901192193; C₆H₆ −227.891360374421 | P0 223; pipeline atual | PASS | PASS |
| P06 | Energia não substitui matrizes | Auditoria matemática independente | `validation/wavefunction_audit.py` | 23 checks matemáticos por molécula | P0 223; pipeline atual | PASS | PASS |
| P07 | Correspondência base/AO/C/S/P/ocupações/ordem | Labels, ordem fonte, C/S/P alinhados | `orca_extractor.py`; `adapters/orca.py` | CᵀSC e comparação bit a bit de S/P/C | P0 223; 73 testes repo | PASS | PASS |
| P08 | `CᵀSC=I` | Auditoria e adaptador | `wavefunction_audit.py`; `adapters/orca.py` | 6.66e-16 / 3.78e-15 / 7.77e-15 | P0 223; pipeline atual | PASS | PASS |
| P09 | `P=2CoccCoccᵀ` | `build_density_rhf`; adaptador | `wavefunction_audit.py`; `adapters/orca.py` | nocc=1/5/21; ocupações 0/2; P simétrico | P0 223; 73 testes repo | PASS | PASS |
| P10 | Densidade só com ocupações/orientação | Rejeita ocupação fracionária/aberta | `wavefunction_audit.py`; `adapters/orca.py` | `confirm_rhf_closed_shell`; `build_density_rhf` | `test_wavefunction`; 73 repo | PASS | PASS |
| P11 | `Tr(PS)=Nₑ` | Auditoria independente | `wavefunction_audit.py` | 1.33e-15 / 1.60e-14 / 2.84e-14 | P0 223; pipeline atual | PASS | PASS |
| P12 | Incompatibilidade p do cclib | Documentada e contornada | `orca_extractor.py`; `adapters/cclib.py` | cclib reordena p; S/C da mesma fonte; cclib atual fail-closed | P0 223; 73 repo | PASS | PASS |
| P13 | Correspondência AO/componente/centro/coeficiente/posição | Labels + ordem fonte + mapa AO atual | `adapters/orca.py`; `basis_mapping.py` | pz→4, px→2, py→3; blocos contíguos; C/S alinhados | 73 repo; P0 223 | PASS | PASS |
| P14 | `orca_2json` adotado | `sp.json` como fonte | `run_validation.py`; `adapters/orca.py` | S, C, ocupações, labels, unidades do JSON | P0 223; pipeline atual | PASS | PASS |
| P15 | Unidades explícitas | `CoordinateUnits` + conversão | `coordinates.py`; `adapters/orca.py` | Angs→Bohr fator 1.8897261246257702 | P0 223; pipeline atual | PASS | PASS |
| P16 | Conversão controlada/documentada | Fator e proveniência registrados | `coordinates.py`; `model_v1.py` | geometry_vs_property 3.31e-9/7.05e-9/2.30e-8 Bohr | P0 223; pipeline atual | PASS | PASS |
| P17 | Não inferir unidade ausente | Default silencioso `angstrom` | `adapters/orca.py:_unit_to_string`; `run_validation.py:load_orca_json` | JSON sem `CoordinateUnits` aceito e convertido como Å | Teste ad hoc em `/tmp` | Parcial: falta fail-closed | PARTIAL |
| P18 | Validar antes das rotinas nativas | Auditoria antes do Engine | `run_validation.py`; `wavefunction_audit.py` | 34 checks antes de Mayer; status FAIL/INCOMPLETE | P0 223; pipeline atual | PASS | PASS |
| P19 | Ordenação de base explícita | Ordem fonte preservada | `adapters/orca.py`; `basis_mapping.py` | pz,px,py; source_index; contiguidade | 73 repo; P0 223 | PASS | PASS |
| P20 | Comparação considerando convenções | QE×MW, QE×ORCA, sem reordenação | `run_validation.py`; `comparison.py` | max 1.33e-15/3.61e-9/4.98e-9; ORCA ≤1.67e-15 | P0 223; pipeline atual | PASS | PASS |
| P21 | Parser no adaptador, não no núcleo | Extração em Python; vendor intocado | `orca_extractor.py`; `adapters/` | `vendor/` 74/74 idêntico ao ZIP oficial | diff vendor; 73 repo | PASS | PASS |
| P22 | Validar propriedades, não só energia | S, C, P, ortogonalidade, idempotência | `wavefunction_audit.py` | 23 checks matemáticos | P0 223; pipeline atual | PASS | PASS |
| P23 | Registros históricos completos | Checkpoint declara ausência; Git sem Fase 2 | `CHECKPOINTS/PHASE02_CHECKPOINT.md` §7/§9 | Comandos/resíduos/inventário original não preservados | Busca documental e Git | Não verificável | NOT VERIFIED |
| P24 | Referências não alteradas | Nenhum valor/tolerância alterado | `validation/`; `tests/` | Energias e matrizes históricas preservadas | 223; 238; 73 | PASS | PASS |
| P25 | Sem reordenação arbitrária | Ordem fonte; transformações explícitas | `adapters/orca.py`; `angular.py` | pz,px,py; phase d/f com manifesto | 73 repo; P0 223 | PASS | PASS |
| P26 | Densidade sem ocupações não é construída | Rejeita ocupações inválidas | `wavefunction_audit.py`; `adapters/orca.py` | 0/2 apenas; nocc=Ne/2 | `test_wavefunction`; 73 repo | PASS | PASS |
| P27 | Alterações futuras exigem testes/docs | Política refletida nos artefatos | `docs/`; `tests/` | Nenhuma alteração nesta auditoria; documentação presente | Revisão documental | PASS | PASS |
| D01 | Mapa AO→primitiva explícito | P0 usa labels/tipo grosseiro; MDM 1.0/1.1 adicionou shells/primitivas/AO map | `adapters/orca.py`; `model_v1.py` | P0 calcula nprims; MDM tem PrimitiveTable/AO map | 73 repo (MDM) | Ampliado posteriormente; impacto nulo em Mayer P0 | SUPERSEDED |
| A01 | Suíte P0 reproduzível | 223 testes externos | `QE-Multiwfn-validation/tests` | 223 passed em cópia temporária | P0 223 | PASS | PASS |
| A02 | Biblioteca atual reproduz P0 | b83308c2… | `python/qe_multiwfn/libqe_multiwfn.so` | Mayer bit a bit igual ao baseline | pipeline atual; 73 repo | PASS | PASS |
| A03 | Atual vs Multiwfn fresco | Multiwfn 2026.11.3 | `run_validation.py` | 1.33e-15/3.61e-9/4.98e-9 ≤1e-6 | pipeline atual | PASS | PASS |
| A04 | P0 na CI hospedada | CI roda 87/20, sem P0 | `.github/workflows/ci.yml`; `tests/python` | P0 externa não versionada; 20 skips de fases posteriores | CI 43711807880; venv 87/20 | Parcial: cobertura hospedada ausente | PARTIAL |
| A05 | Origem histórica pelo Git | Sem commit/tag da Fase 2 | `.git` | 5 commits, nenhum da Fase 2 | `git log` | Não verificável | NOT VERIFIED |
| A06 | Integridade ABI/biblioteca/vendor/frozen | b83308c2; 44 símbolos; vendor 74; frozen 9560 | `src/`, `python/`, `vendor/`, `~/Quimica/qe_multiwfn_src` | `ldd -r` limpo; RUNPATH `$ORIGIN`; 74/74 ZIP oficial | `nm`, `ldd`, `diff` | PASS | PASS |

## 17. Integridade nativa

| Item | Valor |
|---|---|
| Biblioteca atual | `b83308c228b787e6dbf4168bf688f3a5757a0a71091998f338ed968d388cb4f5` |
| Biblioteca frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` |
| ABI | 44 símbolos = 17 legados (`QE_MULTIWFN_0.1.1`) + 27 aditivos (`QE_MULTIWFN_0.2.0`) |
| Vendor | 74 arquivos; `diff` vazio contra o ZIP oficial `a09ce82f…` |
| Header legado | `a3c7eab1…`; header v1 `d99b67d4…` |
| `ldd -r` | limpo |
| RUNPATH | `$ORIGIN` |
| SONAME | `libqe_multiwfn.so.0` |
| Rebuild nesta auditoria | nenhum |
| Modificações nesta auditoria | nenhuma |

## 18. Diferenças históricas

| Dimensão | Fase 2 / 0.1.1 | Estado atual | Natureza |
|---|---|---|---|
| Biblioteca | `b950b0d9…` (distribuída) / `b981c10b…` (rebuild P0) | `b83308c2…` | Evolução 0.3.0 |
| ABI | 17 símbolos | 44 símbolos | Aditiva |
| Fluxo P0 | `MolecularSystem` legado com S/P prontos | Mantido; MDM adiciona caminho completo | Preservado/ampliado |
| Parser ORCA | `sp.json` via `orca_2json` | Mesmo caminho; adaptador MDM | Preservado |
| cclib | Reordenação p identificada | Fail-closed para ORCA real; base explícita | Preservado/fail-closed |
| p order | `pz,px,py` | Preservado; MDM 1.2 identity para s/p | Preservado |
| Unidades | Declaração explícita exigida | Declaração explícita; default silencioso no adaptador | Lacuna atual |
| Suíte P0 | 223 testes no projeto de validação | 223 reproduzidos; fora do repo/CI | Não versionada |
| CI | Inexistente na Fase 2 | 87 passed, 20 skipped; P0 não executada | Cobertura parcial |
| Tolerâncias | Checkpoint não informa | Código 1e-10/1e-8/1e-6; relatórios exibem 1e-5 | Divergência documental |

## 19. Limitações

1. O CHECKPOINT 02 é uma reconstrução; não preserva comandos, arquivos
   individuais, resíduos por comparação ou inventário original de testes.
2. O Git não contém a Fase 2; a origem histórica não é confirmável.
3. A suíte P0 (223 testes) e as fixtures ORCA estão fora do repositório e não
   são executadas pela CI.
4. A CI reporta 20 skips de módulos, que escondem 115 funções de teste de
   fases posteriores; nenhum é a suíte P0.
5. O adaptador ORCA atual assume `angstrom` quando `CoordinateUnits` está
   ausente; não há teste versionado desse caso.
6. Os relatórios históricos exibem tolerância `1e-5` em tabelas, enquanto o
   código usa `1e-10`/`1e-8`/`1e-6`; os resíduos reais são muito menores.
7. O relatório do benzeno rotula a interação `0.115734` como “meta (1,3)”,
   mas os pares listados (C0–C3 etc.) são para (1,4); o P0 já registrou a
   correção documental.
8. A biblioteca não calcula energia; a comparação energética é uma checagem
   de proveniência do ORCA, não uma saída QE.
9. A validação P0 usa S/P fornecidos; a geração nativa de S/P por
   `genSbas`/`genP` veio em fases posteriores e não é requisito da Fase 2.

## 20. Problemas encontrados

| ID | Severidade | Problema | Ação sugerida |
|---|---|---|---|
| U1 | Média | Unidade ausente é inferida como Å no adaptador ORCA e no pipeline P0 | Falhar fechado quando `CoordinateUnits` estiver ausente; teste negativo |
| U2 | Média | Suíte P0 de 223 testes não está versionada nem é executada pela CI | Versionar fixtures/redistribuição permitida ou job CI dedicado |
| U3 | Média | 20 skips da CI escondem 115 testes de fases posteriores | Documentar por módulo e criar job opcional com fixtures/pacotes |
| U4 | Baixa | Tolerâncias em relatórios (`1e-5`) divergem do código (`1e-10`/`1e-8`/`1e-6`) | Reconciliar tabelas com os limites efetivos |
| U5 | Baixa | Relatório do benzeno rotula 0.115734 como meta (1,3), mas os pares são para (1,4) | Corrigir o rótulo |
| U6 | Baixa | Origem histórica da Fase 2 não confirmável pelo Git | Registrar como limitação; não inventar proveniência |
| U7 | Baixa | `RELEASE_MANIFEST_0.2.0.txt` mantém hash divergente já registrado | Reconciliar fora do escopo P0 |

Nenhuma correção foi aplicada nesta fase.

## 21. Recomendações

1. **Unidades:** alterar o adaptador ORCA para exigir `CoordinateUnits`
   explícito e falhar com `OrcaAdapterError` quando ausente; adicionar teste
   negativo. Não alterar as fixtures válidas.
2. **Cobertura P0:** decidir se a árvore `QE-Multiwfn-validation` será
   versionada ou publicada como artefato de validação; enquanto isso, criar um
   job CI que execute a suíte P0 quando as fixtures estiverem disponíveis.
3. **Skips:** documentar os 20 módulos/115 funções e criar um job opcional com
   PySCF/ASE/cclib e a árvore de validação para reduzir a lacuna.
4. **Tolerâncias:** reconciliar as tabelas dos relatórios com os limites
   efetivos do código, sem relaxar nenhum limite.
5. **Documentação:** corrigir o rótulo meta/para do benzeno e registrar que a
   energia ORCA não é saída da biblioteca.
6. **Integridade:** preservar ABI de 44 símbolos, vendor e frozen; não
   reconstruir sem necessidade.
7. **Próxima fase:** não iniciar a 13C.4 sem avaliação do responsável.

## 22. Status global

**PARTIAL.**

A Fase 2 P0 está **cientificamente reproduzida** nos três sistemas: as
relações matemáticas fecham em precisão de máquina, a ordem p é preservada, a
conversão de unidades está correta nos dados válidos, o pipeline atual
reproduz bit a bit as matrizes históricas e a comparação com Multiwfn/ORCA
permanece dentro do critério. Não há `FAIL`.

A classificação é `PARTIAL` porque:

- a unidade ausente não falha de forma controlada (P17);
- a suíte P0 não é executada pela CI (A04);
- os registros históricos completos e a origem Git da Fase 2 não são
  verificáveis (P23/A05).

A Fase 13C.4 não foi iniciada.

---

**Fim do relatório — Fase 13C.3.**
