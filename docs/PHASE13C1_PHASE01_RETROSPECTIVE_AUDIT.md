# Fase 13C.1 — Auditoria retrospectiva da Fase 1

**Projeto:** QE-Multiwfn
**Versão atual do tree:** `0.3.0` (Python), MDM `1.1.0`, ABI nativa `0.2.0`
**Fase auditada:** Fase 1 — fundação da ponte nativa (marco histórico `0.1.1`)
**Repositório:** `/home/fsia/Quimica/qe_multiwfn_030_dev`
**Commit de referência:** `f113cdf2143494c01277abbd644be9d6dc0b8aef`
**Data da auditoria:** 2026-11-15
**Natureza:** auditoria somente-leitura; nenhum código, biblioteca, teste, ABI,
workflow ou documento existente foi alterado.

## Status global desta auditoria

**PARTIAL.**

A ponte nativa da Fase 1 existe, funciona e é reprodutível no tree atual:
a ABI legada de 17 símbolos foi preservada, o núcleo Fortran original continua
sendo chamado, os testes legados passam (29/29 Python e 4/4 C) e os três
exemplos executam. Entretanto, a auditoria encontrou lacunas não críticas, mas
reais: tratamento de falha de alocação incompleto, ausência de guarda explícita
contra overflow de produtos de dimensões, cobertura negativa insuficiente no
conjunto versionado de testes e uma divergência documental reproduzível
(`32/32` no CHECKPOINT 01 contra `29/29` nos artefatos de 0.1.1). Não foi
encontrada falha comprovada em requisito essencial; por isso não há `FAIL`.

| Classificação | Quantidade |
|---|---:|
| PASS | 22 |
| PARTIAL | 3 |
| FAIL | 0 |
| NOT VERIFIED | 3 |
| SUPERSEDED | 4 |
| **Total de linhas da matriz** | **32** |

---

## 1. Objetivo da auditoria

Confrontar o escopo declarado no CHECKPOINT 01 com o código efetivamente
presente no repositório atual, distinguindo:

1. o que a Fase 1 pretendia implementar;
2. o que foi implementado;
3. o que permanece no código atual;
4. o que foi modificado, ampliado ou substituído;
5. o que está comprovadamente testado;
6. o que não possui evidência suficiente;
7. o que precisa ser corrigido, complementado ou documentado.

A referência primária foi o código real do repositório e o artefato histórico
`qe_multiwfn-0.1.1-fullsource.zip`, que representa o marco `0.1.1` descrito pelo
CHECKPOINT 01. O checkpoint externo foi usado como declaração de escopo, não
como prova de implementação.

---

## 2. Fontes examinadas

### 2.1 Checkpoint

| Item | Caminho | Situação |
|---|---|---|
| CHECKPOINT 01 — Fase 1 | `/home/fsia/Quimica/CHECKPOINTS/PHASE1_CHECKPOINT.md` | Presente; 175 linhas; lido integralmente |
| Pasta citada no enunciado | `/home/fsia/Quimica/CHECKPOINT` | **Não existe**; a pasta real é `CHECKPOINTS`, conforme a instrução final do responsável |

O CHECKPOINT 01 declara explicitamente (§7) que não preserva inventário
completo de arquivos, nomes/assinaturas da interface inicial, fixtures,
tolerâncias ou hashes dos artefatos originais. Essas ausências foram tratadas
como limitações históricas, não como falhas de implementação.

### 2.2 Repositório atual

- `src/` — 16 fontes Fortran (`bridge`, `engine`, `state`, `analysis`).
- `include/` — `qe_multiwfn.h` (ABI legada) e `qe_multiwfn_v1.h` (ABI aditiva).
- `python/qe_multiwfn/` — 18 módulos Python, incluindo adaptadores.
- `tests/` — 29 arquivos Python de teste, 6 testes C nativos.
- `docs/` — arquitetura, limitações, status, auditorias e relatórios históricos.
- `reports/build/` — evidências do build `0.1.1` (símbolos exportados, `ldd -r`,
  sumário de testes).
- `vendor/Multiwfn_2026.11.3_src_Linux/` — 74 arquivos do núcleo original.
- `.git` — dois commits, sem tags.

### 2.3 Artefato histórico 0.1.1

`/home/fsia/Quimica/qe_multiwfn-0.1.1-fullsource.zip` foi extraído somente em
`/tmp/audit13c1/src011/qe_multiwfn_src` (fora do repositório) e usado para
comparação byte a byte. Ele contém:

- 12 fontes Fortran do bridge;
- 8 módulos Python;
- 1 header C;
- 5 arquivos de teste Python (29 funções `test_`);
- 4 testes C;
- 3 exemplos;
- `docs/BUILD_VERIFICATION_0.1.1.md`, `docs/RELEASE_NOTES_0.1.1.md`,
  `docs/SOURCE_AUDIT.md`, `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`,
  `docs/IMPLEMENTATION_STATUS.md`, `docs/FINAL_REPORT_0.1.0.md`;
- `reports/build/test_summary.md` com `29 passed` e CTest 4/4;
- a biblioteca compartilhada `python/libqe_multiwfn.so`.

### 2.4 Git

```
f113cdf2143494c01277abbd644be9d6dc0b8aef  docs: add Phase 13B Git publication audit and checkpoint
0c4b65f37a4696940d9030e07e6c8ce64191c3c2  Initial release: QE-Multiwfn 0.3.0
```

Não há commit, tag ou ramo da Fase 1. O histórico Git começa na publicação de
2026-11-14; a origem histórica dos arquivos da Fase 1 **não é confirmável pelo
Git** e foi inferida apenas pelo artefato 0.1.1 e pelos relatórios internos.

---

## 3. Resumo da Fase 1 original

Segundo o CHECKPOINT 01, a Fase 1 tinha como objetivo estabelecer a primeira
integração funcional entre as rotinas científicas originais do Multiwfn
(Fortran) e uma camada externa de programação, permitindo acesso programático
sem interação com a interface original.

Atividades registradas:

1. estruturação inicial da ponte nativa;
2. preparação da comunicação Fortran ↔ camada externa;
3. validação de entradas;
4. correções de alocação;
5. verificação de dimensões e limites;
6. proteções contra overflow;
7. tratamento do estado global Fortran;
8. consistência entre densidade eletrônica e matriz de overlap (`Tr(PS)`);
9. localização e carregamento da biblioteca compartilhada;
10. primeiros testes automatizados.

Resultados declarados no checkpoint:

| Verificação | Resultado declarado |
|---|---|
| Build Release | PASS |
| CTest | 4/4 |
| Testes Python | 32/32 |
| `ldd -r` | sem símbolos indefinidos |
| Integridade do código vendor | preservada |

Decisões arquiteturais declaradas:

- preservação do núcleo científico nas rotinas Fortran originais;
- fronteira nativa controlada, sem expor estruturas internas/variáveis globais;
- validação antes da execução;
- independência do ambiente, sem caminhos absolutos.

**Materialização concreta encontrada:** a Fase 1, no artefato 0.1.1, é a ponte
Multiwfn → Fortran `bind(C)` → C ABI de 17 símbolos → `ctypes`/NumPy, com a
rotina original `calcMayerbndord` (Mayer RHF) como primeira capacidade
científica. O checkpoint não nomeia “Mayer”, mas o código e os documentos 0.1.1
identificam essa como a capacidade exercitada.

---

## 4. Arquitetura original encontrada

### 4.1 Camadas em 0.1.1

| Camada | Arquivos | Papel |
|---|---|---|
| Python de alto nível | `engine.py`, `molecular.py`, `results.py`, `analysis/bond_order.py` | `Engine`, `MolecularSystem`, `MayerResult`, cálculo one-shot |
| Python de ligação | `native.py`, `exceptions.py`, `__init__.py` | carregamento da `.so`, `argtypes`/`restype`, status → exceção |
| C ABI | `include/qe_multiwfn.h`, `src/bridge/qe_c_api.f90` | 17 funções `bind(C)` |
| Suporte C-interop | `qe_c_types.f90`, `qe_status.f90`, `qe_error_handler.f90`, `qe_memory.f90` | tipos, códigos, última mensagem, `c_f_pointer`/cópia |
| Máquina de estados | `qe_engine_state.f90`, `qe_engine_lifecycle.f90` | estados, `initialize`/`finalize` |
| Estado molecular | `qe_molecular_state.f90`, `qe_state_builder.f90` | modelo canônico e push para `defvar` |
| Análise | `qe_analysis_state.f90`, `qe_mayer.f90` | buffers de resultado e chamada a `calcMayerbndord` |
| Núcleo científico | `vendor/Multiwfn_2026.11.3_src_Linux/` | fontes originais; closure mínimo `define.f90`, `util.f90`, `bondorder.f90` |
| Stub | `qe_hyp2f2_stub.f90` | `hyp2F2` sem flint/arb; não usado pelo caminho Mayer |

### 4.2 Propriedade de memória

| Dado | Proprietário | Ciclo de vida |
|---|---|---|
| Arrays NumPy de entrada | Python | até o retorno de cada `qe_set_*`; Fortran copia |
| `the_mol` (modelo canônico) | Fortran | até `qe_release_system()` |
| Globais do Multiwfn (`Ptot`, `Sbas`, `basstart`, ...) | Fortran (`defvar`) | até `qe_release_system()` |
| Buffers de resultado (`mayer_total`, ...) | Fortran (`qe_analysis_state`) | até novo cálculo ou release |
| Buffer NumPy de saída | Python | controlado pelo chamador |

Regra central: a ABI não retém ponteiros Python após o retorno; toda entrada é
copiada para memória Fortran.

### 4.3 Máquina de estados

```
UNINITIALIZED --qe_initialize--> INITIALIZED --qe_begin_system--> SYSTEM_LOADED
SYSTEM_LOADED --qe_prepare_system--> SYSTEM_PREPARED --qe_calculate_mayer--> RESULT_AVAILABLE
SYSTEM_PREPARED/RESULT_AVAILABLE --qe_release_system--> INITIALIZED
INITIALIZED --qe_finalize--> UNINITIALIZED
```

Os setters são aceitos apenas em `SYSTEM_LOADED`; mutação após preparo é
rejeitada; o release limpa o resultado em cache.

---

## 5. Análise da implementação nativa

### 5.1 Wrappers `ISO_C_BINDING` e ABI

- Todos os 17 pontos de entrada legados usam
  `bind(C, name="...")` (`src/bridge/qe_c_api.f90:101-290`).
- Tipos usados: `integer(c_int)` para escalares e status,
  `real(c_double)` para matrizes, `type(c_ptr), value` para buffers.
- `qe_status.f90` espelha os 13 códigos `QE_ERROR_*` e os 5 estados.
- `qe_error_handler.f90` mantém a última mensagem (1024 bytes) e implementa
  `qe_get_last_error` sem depender de alocação dinâmica.
- `qe_memory.f90` converte `c_ptr` em ponteiros Fortran com `c_f_pointer`,
  valida `c_associated` e dimensões, e copia para arrays alocáveis.
- `qe_analysis_state.f90` mantém as matrizes de resultado e o estado
  `mayer_available`/`mayer_has_spin`.
- `qe_mayer.f90:70` chama diretamente
  `calcMayerbndord(bndmattot, bndmata, bndmatb)` — a rotina original — sem
  reimplementação em Python.

### 5.2 Entradas, cópias e buffers

- `qe_set_atomic_data`: `int32[ncenter]` + `double[3*ncenter]` em ordem
  Fortran; valida números atômicos e copia.
- `qe_set_basis_data`: `int32[nbasis]` para centro e tipo; valida
  `basis_center` em `[1, ncenter]`.
- `qe_set_density` e `qe_set_overlap`: matrizes `(nbasis, nbasis)` em ordem
  coluna; validam forma, finitude e simetria (`1e-9`).
- `qe_prepare_system` deriva `basstart`/`basend` de `basis_center`, rejeita
  blocos intercalados, valida `Tr(P·S)=N_e` e a idempotência `P·S·P=2P`
  (`src/state/qe_state_builder.f90:845-870`).
- `qe_get_mayer_result` valida `capacity >= ncenter*ncenter`, checa ponteiro
  nulo e só então escreve no buffer do chamador.

### 5.3 Estado global e liberação

- O estado do motor é process-global (`qe_engine_state.f90`), documentado como
  não thread-safe.
- `qe_state_prepare` aloca e preenche `a(:)`, `basstart`, `basend`, `Ptot`,
  `Sbas` e, quando aplicável, `Palpha`/`Pbeta`.
- `qe_state_release` libera apenas o que o wrapper alocou, limpa o resultado
  em cache e zera os contadores; não chama `dealloall()`.
- Testes sequenciais (2→3 átomos, 3→2 átomos) confirmam que não há vazamento
  de estado entre sistemas.

### 5.4 Ausência de entrada interativa

`calcMayerbndord` foi inspecionada em
`vendor/Multiwfn_2026.11.3_src_Linux/bondorder.f90:285-345`: ela calcula
`PS = matmul_blas(Ptot, Sbas)` e acumula bond orders; não lê `stdin`, não
imprime menu e não chama `ask_sbas_pbc`/`readinfile`. O binário contém rotinas
interativas de `bondorder.f90`, mas elas não são alcançáveis pela ABI e estão
ocultas pelo version script.

### 5.5 Pontos frágeis encontrados

| Item | Evidência | Efeito |
|---|---|---|
| Alocação sem `stat=` | `src/state/qe_state_builder.f90:116-140`; `qe_analysis_state.f90` | falha de alocação aborta o processo em vez de retornar `QE_ERROR_ALLOCATION` |
| Produtos de dimensão sem guarda | `qe_mayer.f90` calcula `expected = n*n`; `qe_state_builder` aloca `(nbasis,nbasis)` | overflow de `int32`/tamanho excessivo não é rejeitado explicitamente |
| `qe_state_transition` sem uso | declarada em `qe_engine_state.f90:25` e definida em `:75`; nenhuma chamada | código morto de baixa severidade |
| Mensagem de número atômico | diz `1..118`, mas aceita `0..118` | inconsistência documental menor |

---

## 6. Análise da camada Python

### 6.1 Carregamento e declarações `ctypes`

`native.py:60-97` procura a biblioteca em:

1. `QE_MULTIWFN_LIBRARY` (prioridade máxima);
2. diretório do pacote (`libqe_multiwfn.so`);
3. `../libqe_multiwfn.so`;
4. `bin/libqe_multiwfn.so`;
5. `build/libqe_multiwfn.so` relativo ao projeto;
6. caminho do sistema.

Não há caminho absoluto de máquina de desenvolvimento. A carga usa
`ctypes.CDLL(..., RTLD_GLOBAL)` para resolver BLAS.

As 17 funções legadas têm `argtypes`/`restype` explícitos. A camada v1 é
opcional: `hasattr(_lib, "qe_v1_model_begin")` evita quebra com uma `.so`
0.1.1 sem os símbolos aditivos. `_check_status` converte código em exceção e
consulta `qe_get_last_error`.

### 6.2 Modelo e validação

`molecular.py` (inalterado desde 0.1.1) valida:

- dimensões positivas e `nprims >= nbasis`;
- RHF apenas (`wfntype == 0`) no caminho legado;
- formas e faixas de `atomic_numbers`, `coordinates`, `basis_center`,
  `basis_type`;
- forma, finitude e simetria de `density_total` e `overlap`;
- multiplicidade 1 e contagem eletrônica positiva/par;
- idempotência `P·S·P=2P`.

O caminho aditivo v1 (`model_v1.py`, `engine.load_molecule_v1`) acrescenta
UHF/ROHF opt-in, shells, primitivas, AO map, normalização e orbitais, sem
alterar o comportamento legado por padrão.

### 6.3 Ciclo de vida e resultados

`engine.py` implementa `initialize`, `finalize`, `load_molecule`,
`prepare`, `calculate_mayer`, `release_molecule` e o protocolo de contexto. O
`finalize` libera o sistema e tolera falha de release; `__del__` é protegido.
`results.py` expõe `total`, `alpha`, `beta`, `metadata`, `has_spin_components`,
`total_semantics`, `mixed`, `mayer_total` e `as_dict`.

### 6.4 Separação e ausência de processos externos

Busca em `python/qe_multiwfn/**/*.py` não encontrou `subprocess`, `os.system`,
`Popen`, `tkinter`, `PyQt`, `PySide`, `curses`, `readline` ou `input(`. Não há
simulação de menus, backend de terminal ou chamada ao executável Multiwfn.

---

## 7. Análise da integração entre camadas

O caminho completo exercitado é:

```
NumPy (F-order) → ctypes → C ABI → qe_state_builder → globais defvar
→ calcMayerbndord (bondorder.f90) → qe_analysis_state → buffer C
→ NumPy (ncenter,ncenter) → MayerResult
```

Evidências de integração real (não apenas importação):

- `tests/python/test_memory_layout.py` monta H2 2×2 com
  `P = [[2/3,2/3],[2/3,2/3]]`, `S = [[1,0.5],[0.5,1]]`, verifica
  `Tr(PS)=2`, resultado todo `1.0`, `has_spin=False` e metadados.
- `tests/python/test_mayer_reference.py` compara 2×2 e 3×3 contra uma
  implementação NumPy independente da fórmula, além de recarregar sistemas
  em ordens diferentes e verificar ausência de resíduo.
- `tests/native/test_memory_transfer.c` envia uma matriz 3×3, executa o
  pipeline, verifica resultado zero para átomo sem base e rejeita
  `QE_MAYER_ALPHA` em RHF com `QE_ERROR_NOT_AVAILABLE`.
- `tests/native/test_mayer.c` verifica a matriz esperada, rejeita mutação
  após preparo e confirma que o resultado não sobrevive ao release.
- `tests/native/test_error_handling.c` cobre dimensões inválidas, estado
  incompleto, chamada antes do preparo, `NULL` no buffer de erro e estado
  inválido.
- `tests/native/test_lifecycle.c` cobre inicialização, re-inicialização,
  finalização, re-finalização e estado.

A matriz de layout é consistente: coordenadas viajam como `(3,ncenter)`,
densidade/overlap como `(nbasis,nbasis)` em ordem coluna, e o resultado é
simétrico (a distinção linha/coluna é irrelevante para Mayer).

---

## 8. Matriz completa de requisitos

> Legenda: **C** = requisito derivado do CHECKPOINT 01; **D** = característica
> documentada do marco 0.1.1, usada para detectar substituição/ampliação;
> **A** = item de verificação exigido pela auditoria (§5.6/§7) que não é um
> requisito funcional do checkpoint.

| ID | Requisito da Fase 1 | Implementação encontrada | Arquivos envolvidos | Evidência | Teste executado | Resultado | Classificação |
|---|---|---|---|---|---|---|---|
| C01 | Acesso programático às capacidades científicas sem a interface interativa do Multiwfn (§1) | ABI C + `Engine` Python; apenas `calcMayerbndord` é chamada; sem `stdin`/menu | `src/bridge/qe_c_api.f90`; `src/analysis/qe_mayer.f90:70`; `python/qe_multiwfn/engine.py` | Inspeção de `bondorder.f90:285-345`; 17 `bind(C)`; testes de execução | 29 pytest legados; 4 testes C; 3 exemplos | Cumprido | PASS |
| C02 | Estruturação inicial da ponte nativa (§2.1) | 12 fontes Fortran em 5 camadas; 17 símbolos `bind(C)`; header C | `src/bridge`; `src/engine`; `src/state`; `src/analysis`; `include/qe_multiwfn.h` | `nm -D` do artefato 0.1.1: 17 símbolos `qe_*`; `reports/build/exported_symbols.txt` | 4 binários C; 29 pytest | Cumprido | PASS |
| C03 | Preparação da comunicação Fortran ↔ camada externa (§2.2) | `c_f_pointer` + cópia para arrays Fortran; retorno por buffer do chamador | `qe_memory.f90`; `qe_state_builder.f90`; `native.py` | `test_memory_transfer` e `test_memory_layout` passam; cópia confirmada | 1 teste C; 5 testes Python de layout | Cumprido | PASS |
| C04 | Validação de entradas antes da execução (§2.3, §6.3) | Validação Python + validação Fortran; setters gated; rejeição de NaN/assimetria/dimensões | `molecular.py`; `qe_state_builder.f90`; `qe_memory.f90` | `test_invalid_inputs.py` (11 testes); `test_error_handling.c` | 11 pytest; 1 teste C; 6 checagens ad hoc | Cumprido | PASS |
| C05 | Correções de alocação e limites de alocação (§2.4, §3, §4) | Arrays de posse passaram a `nbasis`; `nprims` independente; `qe_copy_*` usa `stat=`; porém alocações do modelo/resultado não usam `stat=` | `qe_state_builder.f90:116-140`; `qe_state_builder.f90:862`; `qe_analysis_state.f90`; `qe_memory.f90:125-157` | `RELEASE_NOTES_0.1.1.md` itens 1–2; inspeção estática; testes sequenciais | `test_memory_transfer`; `test_memory_layout`; `test_mayer_reference` | Parcial: correção histórica confirmada, falha de alocação não tratada | PARTIAL |
| C06 | Verificação de dimensões e limites (§2.5, §3) | `ncenter>0`, `nbasis>0`, `nprims>=nbasis`, `basis_center` em faixa, formas de matrizes, capacidade de saída | `qe_state_builder.f90`; `qe_c_api.f90`; `molecular.py` | Testes de entrada inválida; checagem ad hoc de capacidade | 11 pytest; 1 teste C; 2 checagens ad hoc | Cumprido | PASS |
| C07 | Proteções contra overflow (§2.6, §4) | Há checagem de dimensões e finitude, mas não há multiplicação verificada para `nbasis*nbasis` nem `ncenter*ncenter` | `qe_mayer.f90`; `qe_state_builder.f90` | Inspeção estática; nenhuma guarda `huge`/`int64` para produtos | Não executado (caminho destrutivo/OOM) | Parcial: guarda explícita ausente | PARTIAL |
| C08 | Tratamento do estado global Fortran (§2.7, §4) | Máquina de estados; setters só em `SYSTEM_LOADED`; release limpa resultado e globais | `qe_engine_state.f90`; `qe_engine_lifecycle.f90`; `qe_state_builder.f90`; `qe_c_api.f90` | `test_mayer.c` (mutação rejeitada, resultado limpo); testes sequenciais | 4 testes C; 4 pytest de referência | Cumprido | PASS |
| C09 | Consistência densidade–overlap `Tr(PS)` (§2.8, §3) | `Tr(P·S)` comparado a `N_e`; idempotência `P·S·P=2P`; versão aberta adiciona `Tr(PαS)`/`Tr(PβS)` | `qe_state_builder.f90:845-870`; `:938-951` | Código; todos os testes válidos passam; checagem ad hoc com `P=I`, `S=2I`, `N_e=2` retorna código 1 | 29 pytest; 4 C; 1 checagem ad hoc negativa | Cumprido; não há teste negativo versionado | PASS |
| C10 | Localização e carregamento da biblioteca compartilhada (§2.9, §4) | Busca por env, pacote, `../`, `bin/`, projeto e sistema; `CDLL` com `RTLD_GLOBAL` | `native.py:60-97` | `test_import.py`; `NATIVE_LIBRARY_PATH`; 3 exemplos | 2 pytest de importação; 3 exemplos | Cumprido | PASS |
| C11 | Estruturação dos primeiros testes automatizados (§2.10) | 5 arquivos Python (29 funções) e 4 testes C | `tests/python/*`; `tests/native/*`; `tests/CMakeLists.txt` | `reports/build/test_summary.md`: CTest 4/4, pytest 29 | 29 pytest; 4 C | Cumprido | PASS |
| C12 | Consistência dos buffers (§3) | Entradas copiadas; saída só após `capacity`; ponteiro nulo rejeitado | `qe_memory.f90`; `qe_mayer.f90`; `native.py` | `test_memory_transfer`; checagens ad hoc de capacidade e `NULL` | 1 C; 2 ad hoc | Cumprido | PASS |
| C13 | Tratamento de entradas inválidas (§3) | Rejeita NaN/Inf, assimetria, formas erradas, `basis_center` inválido, `wfntype` inválido, estado incompleto | `molecular.py`; `qe_state_builder.f90`; `qe_c_api.f90` | `test_invalid_inputs.py`; `test_error_handling.c` | 11 pytest; 1 C | Cumprido | PASS |
| C14 | Controle do estado interno (§3) | `qe_state_set`/`qe_state_require`; transições efetivas; `qe_state_transition` não é usada | `qe_engine_state.f90`; `qe_c_api.f90` | `test_lifecycle.c`; `test_lifecycle.py`; `test_error_handling.c` | 1 C; 7 pytest; 1 C | Cumprido; código morto residual | PASS |
| C15 | RUNPATH para localizar dependências (§4) | `INSTALL_RPATH "$ORIGIN"`; SONAME `libqe_multiwfn.so.0` | `CMakeLists.txt:117-141` | `readelf -d`: RUNPATH `$ORIGIN`; SONAME correto | `readelf`; `ldd -r` | Cumprido | PASS |
| C16 | Independência de caminhos absolutos específicos da máquina (§4, §6.4) | Nenhum caminho absoluto no carregador; env/relativo/sistema | `native.py:60-97` | Busca textual; `RUNPATH=$ORIGIN` | 3 exemplos; 2 import | Cumprido | PASS |
| C17 | Build Release (§5) | `CMAKE_BUILD_TYPE=Release`; biblioteca e testes construídos | `CMakeLists.txt`; `build/CMakeCache.txt`; `reports/build/` | `CMAKE_BUILD_TYPE:STRING=Release`; logs de build | Não reexecutado (proibido rebuild) | Cumprido historicamente | PASS |
| C18 | CTest 4/4 (§5) | 4 testes C legados presentes e executáveis | `tests/native/*.c`; `build/tests/*` | Saídas `PASS` dos 4 binários | 4/4 binários, exit 0 | Cumprido | PASS |
| C19 | Testes Python 32/32 (§5) | 29 funções pytest + 3 exemplos = 32 execuções; `32/32` como pytest não reproduz | `tests/python/*`; `examples/*` | `RELEASE_MANIFEST.txt` e `reports/build/test_summary.md` dizem 29/29; checkpoint diz 32/32 | 29 pytest + 3 exemplos | Parcial: contagem documental divergente | PARTIAL |
| C20 | `ldd -r` sem símbolos indefinidos (§5) | Dependências resolvidas; sem diagnósticos | `python/qe_multiwfn/libqe_multiwfn.so` | `ldd -r` limpo; `reports/build/packaged_ldd_r.txt` | `ldd -r` | Cumprido | PASS |
| C21 | Integridade do código vendor preservada (§5) | 74 arquivos; idênticos ao artefato 0.1.1 | `vendor/Multiwfn_2026.11.3_src_Linux/` | `diff -rq` vazio; digest de árvore `6c669e...` | `diff -rq`; contagem 74 | Cumprido | PASS |
| C22 | Preservação do núcleo científico em Fortran (§6.1) | `calcMayerbndord` original chamada; vendor não modificado; sem fórmula Python substituta | `vendor/.../bondorder.f90`; `qe_mayer.f90:70` | Fonte original; `diff` do vendor vazio | 29 pytest; 4 C | Cumprido | PASS |
| C23 | Fronteira nativa controlada, sem expor estruturas/globais (§6.2) | ABI expõe escalares, arrays e status; `defvar` é interno; version script oculta o resto | `qe_multiwfn.h`; `qe_c_api.f90`; `cmake/qe_multiwfn.map` | `nm -D`: apenas `qe_*`; nenhum struct do Multiwfn no header | `nm -D`; testes de execução | Cumprido | PASS |
| D01 | ABI inicial de 17 símbolos legados preservada | 17 nomes idênticos ao artefato 0.1.1, nó `QE_MULTIWFN_0.1.1` | `cmake/qe_multiwfn.map`; `.so` atual | Comparação de listas; `nm -D` | 29 pytest legados na `.so` atual | Cumprido | PASS |
| D02 | Pacote Python 0.1.1 (8 módulos) como estado final | Hoje 18 módulos, com v1/adaptadores; API legada preservada | `python/qe_multiwfn/` | `find` 18 módulos vs 8; `MolecularSystem` e `Engine` mantidos | 29 pytest legados | Substituído/ampliado; compatibilidade preservada | SUPERSEDED |
| D03 | Pipeline Mayer restrito a RHF em 0.1.1 | Legado continua RHF-only; v1 aditivo permite UHF/ROHF opt-in | `molecular.py`; `qe_mayer.f90`; `model_v1.py` | `molecular.py` rejeita `wfntype != 0`; `qe_mayer.f90` aceita 1/2 com flag | Testes legados RHF | Substituído por escopo aditivo | SUPERSEDED |
| D04 | Build 0.1.0 com 59 fontes do núcleo | 0.1.1 já usava closure mínimo; tree atual usa 17 fontes | `cmake/FortranSources.cmake`; `docs/FINAL_REPORT_0.1.0.md`; `RELEASE_NOTES_0.1.1.md` | `QE_MULTIWFN_COUNT=17`; vendor completo preservado | Não reexecutado | Substituído já em 0.1.1 | SUPERSEDED |
| D05 | Versão nativa `0.1.1` | `qe_get_version()` retorna `0.2.0`; ABI legada mantém nó 0.1.1 | `qe_c_api.f90`; `include/qe_multiwfn.h`; `test_import.py` | Saída `0.2.0`; header `VERSION 0.2.0` | 2 pytest de importação | Substituído por 0.2.0 | SUPERSEDED |
| D06 | Conjunto de testes 0.1.1 reproduzível (29 pytest, 4 C, 3 exemplos) | Reprodutível no artefato e no tree atual | `tests/`; `examples/` | 29 passed no artefato em `/tmp` e 29 passed no tree; 4/4 C; 3/3 exemplos | 29+29 pytest; 4 C; 3 exemplos | Cumprido | PASS |
| A01 | Determinar a origem histórica dos componentes da Fase 1 pelo Git (§5.6) | Repositório tem apenas 2 commits (2026-11-14), sem tags; nada da Fase 1 | `.git` | `git log`: `0c4b65f`, `f113cdf`; sem tags | `git log`, `git tag` | Não confirmável pelo Git | NOT VERIFIED |
| A02 | Verificar o vendor contra o ZIP oficial do Multiwfn (§5.6/§7) | ZIP oficial não está presente nesta máquina; apenas o artefato 0.1.1 | `vendor/`; `~/Quimica/qe_multiwfn-0.1.1-fullsource.zip` | `find` não encontrou `Multiwfn_2026.11.3_src_Linux.zip` | Comparação não executada | Não verificável nesta auditoria | NOT VERIFIED |
| A03 | Recuperar fixtures, tolerâncias e hashes originais da Fase 1 (§7 do checkpoint) | O checkpoint declara que esses dados não foram preservados; o artefato 0.1.1 contém apenas os testes e o build report | `CHECKPOINTS/PHASE1_CHECKPOINT.md` §7; artefato 0.1.1 | Declaração explícita do checkpoint; ausência de manifesto 0.1.1 | Busca no artefato | Não verificável | NOT VERIFIED |

---

## 9. Testes executados e resultados

### 9.1 Comandos e resultados

| # | Alvo | Comando (resumo) | Resultado |
|---|---|---|---|
| 1 | Testes legados Python no tree atual | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=python QE_MULTIWFN_LIBRARY=... pytest -p no:cacheprovider test_import test_lifecycle test_memory_layout test_invalid_inputs test_mayer_reference -q` | **29 passed** em 2,33 s |
| 2 | Testes do artefato 0.1.1 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/.../python pytest ... tests/python -q` | **29 passed** em 0,29 s |
| 3 | Testes C legados | Execução direta de `build/tests/test_lifecycle_c`, `test_memory_transfer_c`, `test_error_handling_c`, `test_mayer_c` | **4/4 PASS**, exit 0 |
| 4 | Exemplos | `example_lifecycle.py`, `example_memory_transfer.py`, `example_mayer_rhf.py` | **3/3 PASS**, exit 0 |
| 5 | Checagens negativas ad hoc | `ctypes` direto na `.so`: `Tr(PS)` divergente, densidade NaN, capacidade insuficiente, buffer nulo, `result_id` inválido, ponteiro atômico nulo em `SYSTEM_LOADED` | Códigos esperados: 1, 1, 3, 4, 1, 4 |

### 9.2 O que cada teste legado realmente valida

| Arquivo | Valida | Executa a camada nativa? | Verifica números? |
|---|---|---|---|
| `test_import.py` | import do pacote; caminho da `.so`; versão `0.2.0` | Carrega a `.so`; não executa análise | Não |
| `test_lifecycle.py` | estados, dupla inicialização, finalização, context manager, preparo/cálculo sem sistema | Sim (estado) | Não |
| `test_memory_layout.py` | H2 2×2, `Tr(PS)`, resultado todo 1.0, metadados, unidades Å/Bohr, entradas inválidas | Sim (pipeline Mayer) | Sim (matriz 2×2) |
| `test_invalid_inputs.py` | dimensões, `nprims`, NaN, `basis_center`, forma, unidade, estado, RHF não idempotente, bloco não contíguo | Sim (exceto validações Python puras) | Não (foco em rejeição) |
| `test_mayer_reference.py` | 2×2 e 3×3 contra fórmula NumPy; sistemas sequenciais; 3→2 átomos | Sim | Sim (`atol 1e-10`) |
| `test_lifecycle.c` | estados, re-init/re-finalize, preparo sem sistema, versão | Sim | Não |
| `test_memory_transfer.c` | matriz 3×3, cópia, resultado zero, alpha indisponível | Sim | Sim (zero) |
| `test_error_handling.c` | `NULL`, dimensões, `wfntype`, estado incompleto, cálculo prematuro, buffer de erro nulo | Sim | Não |
| `test_mayer.c` | matriz esperada 1.0, mutação pós-preparo, resultado limpo no release | Sim | Sim (`atol 1e-9`) |

### 9.3 Cobertura científica

Os testes da Fase 1 validam a ponte RAM-to-RAM, o contrato de dimensões, as
transições de estado e a fórmula de Mayer contra uma expressão NumPy
independente. **Eles não constituem validação científica externa**: não há
cálculo SCF independente (ORCA/PySCF/Psi4) nem execução separada do Multiwfn
original no conjunto 0.1.1. Essa validação veio depois, na etapa P0, fora do
escopo da Fase 1. O próprio `RELEASE_NOTES_0.1.1.md` registra essa ressalva.

### 9.4 Testes não executados e justificativa

| Item | Motivo |
|---|---|
| `ctest` completo (6/6) | Os 4 testes da Fase 1 foram executados diretamente; `v1_abi_c` e `uhf_abi_c` estão fora do escopo 0.1.1. `ctest` gravaria logs no tree, contrariando a regra de não modificação |
| Suíte Python completa atual (196 funções) | Inclui fases posteriores, fixtures externas e skips; fora do escopo desta auditoria |
| Rebuild 0.1.1 | Proibido pelo enunciado; toolchain original (gfortran 16.2/conda) não está disponível |
| Valgrind/ASan | Exigiria rebuild/instrumentação; proibido |
| Falha de alocação e overflow | Testes destrutivos/OOM; não executados |
| Comparação com ZIP oficial do Multiwfn | ZIP oficial ausente |
| Atribuição histórica via Git | Não há commits da Fase 1 |

---

## 10. Integridade científica e ABI

### 10.1 Hashes verificados

| Artefato | SHA-256 | Onde foi verificado |
|---|---|---|
| Biblioteca de desenvolvimento atual | `e9ac3a733f974a7fab88956f394ebc50c901cf400459c80068992424dbfd5119` | `python/libqe_multiwfn.so`, `python/qe_multiwfn/libqe_multiwfn.so`, `build/libqe_multiwfn.so.0.2.0` |
| Biblioteca frozen 0.2.0 | `9560c0fc6705f7618d1738f392f72c795881e15eb2a15182abdd4ef6d2c3fa72` | `/home/fsia/Quimica/qe_multiwfn_src/python/libqe_multiwfn.so` e `.../build/libqe_multiwfn.so.0.2.0` |
| Biblioteca histórica 0.1.1 | `b950b0d94cbcbb2f1c0255349857a78bddb03ee031fcf507c47241bbbc1ff608` | `qe_multiwfn-0.1.1-fullsource.zip` (`python/libqe_multiwfn.so`) |
| Header legado `qe_multiwfn.h` | `a3c7eab10df9f61ac63313654020548c8fadda81944045eb01eaed829d775929` | `include/qe_multiwfn.h` |
| Header aditivo `qe_multiwfn_v1.h` | `d99b67d41e701be9e3a41d1879011618685fe43e4cbd6d1ee1fc094b8559fb17` | `include/qe_multiwfn_v1.h` |
| Árvore vendor (74 arquivos) | `6c669ecf48c69e82fbf96237b94e92b00807318aa882acbbeb21df700a18e06a` | Digest determinístico dos hashes SHA-256 dos 74 arquivos em `vendor/Multiwfn_2026.11.3_src_Linux` |

Os valores `e9ac3a73...` e `9560c0fc...` coincidem com as referências
históricas do projeto. O valor `9560c0fc...` é o hash da **biblioteca
compartilhada frozen 0.2.0**, não um digest de árvore; o `RELEASE_MANIFEST_0.2.0.txt`
menciona `ecc7852a...` para o “artefato”, o que é uma inconsistência documental
a esclarecer fora desta fase.

### 10.2 ABI

| Item | Valor |
|---|---|
| Símbolos totais exportados | **44** |
| Símbolos legados | **17**, nó de versão `QE_MULTIWFN_0.1.1` |
| Símbolos aditivos | **27**, nó de versão `QE_MULTIWFN_0.2.0` |
| Símbolos legados removidos | **0** |
| Símbolos internos exportados | Nenhuma função interna; apenas os nós de versão (`QE_MULTIWFN_0.1.1`, `QE_MULTIWFN_0.2.0`); `local: *` no version script |
| SONAME | `libqe_multiwfn.so.0` |
| RUNPATH | `$ORIGIN` |
| `ldd -r` | Sem símbolos indefinidos |

Lista aditiva (27): `qe_v1_build_electronic_state`,
`qe_v1_enable_open_shell`, `qe_v1_generate_cartesian_overlap`,
`qe_v1_generate_density`, `qe_v1_generate_overlap`,
`qe_v1_generate_primitive_density`,
`qe_v1_get_generated_cartesian_overlap`, `qe_v1_get_generated_density`,
`qe_v1_get_generated_density_dimensions`, `qe_v1_get_generated_overlap`,
`qe_v1_get_generated_primitive_density`, `qe_v1_get_overlap_dimensions`,
`qe_v1_get_primitive_density_dimensions`, `qe_v1_get_primitive_overlap`,
`qe_v1_get_readiness`, `qe_v1_model_begin`, `qe_v1_model_commit`,
`qe_v1_model_release`, `qe_v1_set_angular_canonical`, `qe_v1_set_ao_map`,
`qe_v1_set_ao_normalization`, `qe_v1_set_atoms`, `qe_v1_set_density`,
`qe_v1_set_orbitals`, `qe_v1_set_overlap`, `qe_v1_set_primitives`,
`qe_v1_set_shells`.

### 10.3 Estado dos fontes, headers e wrappers

| Item | 0.1.1 | Atual |
|---|---:|---:|
| Fontes Fortran do bridge (`src/**/*.f90`) | 12 | 16 |
| Headers C | 1 | 2 |
| Módulos Python no pacote | 8 | 18 |
| Arquivos de teste Python | 5 | 29 |
| Testes C | 4 | 6 |

Arquivos da Fase 1 **inalterados** desde 0.1.1:

- `src/bridge/qe_c_types.f90`
- `src/bridge/qe_status.f90`
- `src/bridge/qe_error_handler.f90`
- `src/bridge/qe_hyp2f2_stub.f90`
- `src/analysis/qe_analysis_state.f90`
- `python/qe_multiwfn/molecular.py`
- `python/qe_multiwfn/exceptions.py`
- os 4 testes C legados
- `test_lifecycle.py`, `test_memory_layout.py`, `test_invalid_inputs.py`,
  `test_mayer_reference.py`

Arquivos da Fase 1 **modificados** desde 0.1.1 (16):

- `include/qe_multiwfn.h` (somente versão 0.1.1 → 0.2.0);
- `python/libqe_multiwfn.so` (novo build);
- `python/qe_multiwfn/{__init__,native,engine,results}.py`;
- `python/qe_multiwfn/analysis/bond_order.py`;
- `src/bridge/qe_c_api.f90` (v1 aditivo);
- `src/bridge/qe_memory.f90` (helpers 1-D);
- `src/engine/qe_engine_lifecycle.f90`;
- `src/engine/qe_engine_state.f90` (flag open-shell);
- `src/state/qe_molecular_state.f90` (campos v1);
- `src/state/qe_state_builder.f90` (v1, open-shell, cache);
- `tests/CMakeLists.txt` (2 testes novos);
- `tests/python/test_import.py` (versão esperada 0.2.0).

### 10.4 Integridade científica

- O núcleo `vendor/` está completo (74 arquivos) e idêntico ao artefato 0.1.1.
- `bondorder.f90::calcMayerbndord` não foi modificado; o adaptador apenas o
  chama.
- `hyp2F2` continua um stub documentado; não é exercitado pelo caminho Mayer.
- Não há fórmula Python substituindo a rotina científica.
- Não há rebuild nesta auditoria; todos os hashes vêm de artefatos existentes.

---

## 11. Diferenças entre o checkpoint e o código atual

| Dimensão | CHECKPOINT 01 / 0.1.1 | Código atual | Natureza |
|---|---|---|---|
| Versão nativa | `0.1.1` | `0.2.0` (ABI legada versionada em 0.1.1) | Evolução |
| Python | `0.1.1`, 8 módulos | `0.3.0`, 18 módulos + adaptadores | Ampliação |
| ABI | 17 símbolos | 44 = 17 + 27 | Aditiva |
| Fontes Fortran do bridge | 12 | 16 | Ampliação |
| Científica | Mayer RHF | Mayer RHF + UHF/ROHF opt-in + `genP`/`genPprim`/`genSbas`/`genSbas_curr` | Ampliação |
| Build | closure mínimo (0.1.1) | mesmo closure mínimo ampliado (17 fontes) | Evolução |
| Testes Python | 5 arquivos / 29 funções | 29 arquivos / 196 funções | Ampliação |
| Testes C | 4 | 6 | Ampliação |
| Biblioteca | `b950b0d9...` (0.1.1) | `e9ac3a73...` (0.3.0-dev) | Novo build |
| Documentação 0.1.1 | 7 documentos originais | Todos os 7 modificados com notas históricas/apêndices P0/M1 | Revisão documental |
| Contagem “32/32” | Declarada no checkpoint | 29/29 pytest + 3/3 exemplos | Divergência documental |
| Escopo “Fase 1” | CHECKPOINT 01 = ponte nativa 0.1.1 | `SOURCE_AUDIT.md` chama a auditoria de fontes de “Phase 1” e o CMake de “Phase 2” | Ambiguidade histórica |

A comparação confirma que a **funcionalidade** da Fase 1 foi preservada, mas o
**texto** do checkpoint não corresponde integralmente aos artefatos: a contagem
32/32 não é reproduzível como pytest, e a numeração de fases em
`SOURCE_AUDIT.md` difere da usada no CHECKPOINT 01.

---

## 12. Funcionalidades substituídas ou ampliadas

1. **Build de 0.1.0 com 59 fontes** → já em 0.1.1, closure mínimo
   (`define.f90`, `util.f90`, `bondorder.f90`); no tree atual, closure de 17
   fontes para `genP`/`genPprim`/`genSbas`/`genSbas_curr`. O vendor completo
   permanece.
2. **ABI de 17 símbolos** → 44 símbolos, com 27 aditivos e nenhum legado
   removido.
3. **Mayer RHF-only** → UHF/ROHF opt-in no caminho v1; o caminho legado
   continua RHF-only por padrão.
4. **Pacote Python de 8 módulos** → 18 módulos, incluindo
   `model_v1`, `builder`, `normalization`, `angular` e adaptadores
   ORCA/ASE/cclib/PySCF/database; `Engine`, `MolecularSystem` e `MayerResult`
   continuam disponíveis.
5. **`qe_get_version()` 0.1.1** → `0.2.0`.
6. **Documentos 0.1.1** → receberam avisos de documento histórico e apêndices
   P0/M1; o conteúdo original foi preservado, mas o estado atual está nos
   documentos de 0.3.0.
7. **`qe_state_transition`** → permanece declarada e não usada; não foi
   substituída nem removida.
8. **`hyp2F2` stub** → permanece; nenhuma implementação flint/arb foi
   adicionada.

---

## 13. Limitações encontradas

1. **Proveniência histórica:** o Git não contém a Fase 1; a atribuição depende
   do artefato 0.1.1 e de relatórios internos.
2. **Ambiente original:** o build 0.1.1 não foi reproduzido; o toolchain
   original (gfortran 16.2/conda) não está disponível. A `.so` 0.1.1
   pré-compilada funciona no host atual.
3. **ZIP oficial do Multiwfn ausente:** a identidade byte a byte do vendor
   contra o upstream não pôde ser reexecutada; a preservação contra o artefato
   0.1.1 foi confirmada.
4. **Sem rebuild:** todos os hashes são de artefatos existentes; não foi
   possível provar que a `.so` atual corresponde exatamente a cada fonte no
   instante da auditoria. Exceto `include/qe_multiwfn_v1.h` (18:37), nenhum
   fonte/header é mais novo que a `.so` (17:00).
5. **Testes destrutivos não executados:** falha de alocação e overflow não
   foram provocados.
6. **Cobertura negativa incompleta no suite:** `Tr(PS)` divergente, `NaN` em
   overlap, overlap assimétrico, ponteiro nulo em `SYSTEM_LOADED`,
   `capacity` insuficiente e `result_id` inválido foram verificados apenas
   ad hoc, não em testes versionados.
7. **Validação científica externa:** a Fase 1 não a possuía; os testes 0.1.1
   comparam com uma fórmula NumPy, não com SCF/ORCA/Multiwfn independente.
8. **Escopo nativo:** estado global, uma instância por processo, sem
   thread-safety, PBC, ECP/EDF, leitores de arquivo ou geração de S/P no
   caminho legado.
9. **Documentação:** a contagem 32/32 e a numeração de fases em
   `SOURCE_AUDIT.md` precisam de reconciliação.
10. **Manifesto 0.2.0:** `RELEASE_MANIFEST_0.2.0.txt` cita
    `ecc7852a...` para o artefato, enquanto a biblioteca frozen verificada é
    `9560c0fc...`; fora do escopo 0.1.1, mas relevante para integridade.

---

## 14. Problemas que exigem correção

> Nenhuma correção foi aplicada nesta fase. A lista é para decisão do
> responsável do projeto.

| ID | Severidade | Problema | Ação sugerida |
|---|---|---|---|
| P1 | Média | Checkpoint declara `32/32` testes Python; os artefatos 0.1.1 e o tree atual produzem `29/29` pytest + `3/3` exemplos | Corrigir o checkpoint para `29/29 pytest + 3/3 exemplos`, ou documentar explicitamente que 32 = 29+3 |
| P2 | Média | `docs/SOURCE_AUDIT.md` chama a auditoria de fontes de “Phase 1” e o CMake de “Phase 2”; o CHECKPOINT 01 chama a ponte nativa de “Fase 1” | Reconciliar a numeração histórica em uma nota única |
| P3 | Média | Alocações do modelo/resultado sem `stat=` (`qe_state_builder.f90:116-140`, `qe_analysis_state.f90`) | Usar `stat=` e retornar `QE_ERROR_ALLOCATION`; teste de falha de alocação |
| P4 | Média | Sem multiplicação verificada para `nbasis*nbasis`/`ncenter*ncenter` | Guarda de overflow e limite máximo explícito antes de alocar |
| P5 | Média | Cobertura negativa ausente no suite versionado | Adicionar testes para `Tr(PS)` divergente, `NaN`/assimetria de overlap, `NULL` em estado carregado, `capacity` insuficiente e `result_id` inválido |
| P6 | Baixa | `qe_state_transition` não é usada | Remover ou integrar às transições |
| P7 | Baixa | Mensagem de número atômico diz `1..118`, mas aceita `0..118` | Alinhar mensagem e validação |
| P8 | Baixa | Comentário de `test_mayer.c` diz `BO(1,1)=0.64`, mas o esperado/real é `1.0` | Corrigir o comentário |
| P9 | Baixa | `RELEASE_MANIFEST_0.2.0.txt` cita hash diferente do frozen verificado | Reconciliar o manifesto (fora do escopo 0.1.1) |
| P10 | Baixa | Sem manifesto imutável do artefato 0.1.1 (fonte + `.so` + testes + hashes) | Criar manifesto histórico e arquivar |

---

## 15. Recomendações para a Fase 13C.2

1. **Auditar a Fase 2** com o mesmo método: reconstruir o escopo a partir do
   CHECKPOINT 02, confrontar com o artefato 0.1.1/0.2.0 e verificar se a
   validação científica foi realmente executada ou apenas planejada.
2. **Corrigir a documentação da Fase 1** (P1/P2) antes de usar o checkpoint
   como baseline de rastreabilidade.
3. **Fortalecer a robustez nativa** (P3/P4) com `stat=`, multiplicação
   verificada e limites máximos; só depois considerar testes de fault
   injection.
4. **Fechar a cobertura negativa** (P5) no suite versionado, para que as
   validações de `Tr(PS)`, buffers e ponteiros não dependam de checagem ad hoc.
5. **Registrar a baseline histórica** (P10) e o hash do ZIP oficial do
   Multiwfn (A02), para que auditorias futuras não dependam de suposição.
6. **Não alterar a ABI legada** durante essas correções; qualquer mudança deve
   ser aditiva e versionada.
7. **Não iniciar a Fase 13C.2** antes da avaliação deste relatório pelo
   responsável do projeto.

---

## 16. Conclusão e status global

A Fase 1, conforme reconstruída pelo CHECKPOINT 01, **está implementada e
funcional no código atual** naquilo que é essencial: a ponte Fortran `bind(C)`
→ C ABI → Python existe, a ABI legada de 17 símbolos foi preservada, o núcleo
`calcMayerbndord` é chamado sem modificação, a comunicação é RAM-to-RAM, as
validações de dimensão/estado/`Tr(PS)` funcionam, o carregamento não depende de
caminho absoluto e os testes legados passam.

Entretanto, a auditoria **não confirma** o status histórico “CONCLUÍDA” sem
ressalvas:

- a contagem `32/32` não é reproduzível como pytest (são 29/29 + 3 exemplos);
- a origem histórica não é confirmável pelo Git;
- a comparação com o ZIP oficial do Multiwfn não pôde ser refeita;
- falha de alocação e overflow não têm tratamento/guarda explícitos;
- parte das validações negativas existe apenas em checagem ad hoc.

Não há evidência de falha em requisito essencial, portanto **FAIL = 0**. O
resultado global é **PARTIAL**, com 22 PASS, 3 PARTIAL, 4 SUPERSEDED e 3 NOT
VERIFIED. A Fase 13C.2 não foi iniciada.

---

## Adendo de reconciliação — Fase 13C.2

Este relatório é o registro histórico da auditoria 13C.1 e mantém a
classificação **PARTIAL** de C19 como evidência da divergência então
encontrada. A reconciliação documental foi concluída na Fase 13C.2:

- a contagem autoritativa do artefato 0.1.1 é **29 testes pytest**, não 32;
- o valor histórico “32/32” corresponde a **29 pytest + 3 exemplos**, e não
  a 32 testes pytest;
- os testes C são **4** no artefato 0.1.1 (e **7** no tree após a 13C.2);
- a origem histórica de componentes continua **não confirmável pelo Git**
  disponível (2 commits, sem tags), e nenhuma data, tag, commit ou autor foi
  inventado.

A correção e os resultados finais estão em
`docs/PHASE13C2_PHASE01_REMEDIATION.md`.

---

**Fim do relatório técnico — Fase 13C.1.**
