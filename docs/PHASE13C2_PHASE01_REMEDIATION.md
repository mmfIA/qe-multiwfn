# Fase 13C.2 — Consolidação corretiva da Fase 1

**Projeto:** QE-Multiwfn
**Versão:** `0.3.0` (Python), MDM `1.1.0`, ABI nativa `0.2.0`
**Escopo:** segurança de memória, validação ABI e testes negativos
**Repositório:** `/home/fsia/Quimica/qe_multiwfn_030_dev`
**Status global:** **PASS**
**Data:** 2026-11-15

## 1. Problemas identificados

A auditoria 13C.1 classificou a Fase 1 como `PARTIAL` e deixou três demandas
técnicas e duas documentais:

| ID | Problema | Severidade |
|---|---|---|
| P3 | Alocações do modelo/resultado sem tratamento explícito por `STAT=` | Média |
| P4 | Ausência de guarda de overflow em produtos de dimensões | Média |
| P5 | Testes negativos existiam apenas ad hoc | Média |
| P1 | Contagem histórica `32/32` divergente de `29/29` pytest | Média |
| P2 | Numeração histórica de fases divergente em `SOURCE_AUDIT.md` | Média |

## 2. Análise das causas

1. **P3:** as alocações foram escritas para o caminho feliz. `allocate` sem
   `stat=` aborta ou deixa arrays parcialmente alocados; não havia limpeza
   determinística do modelo/globais após falha.
2. **P4:** dimensões eram validadas como positivas, mas produtos como
   `nbasis*nbasis` e `ncenter*ncenter` eram calculados sem teste prévio. Um
   valor grande podia transbordar antes da alocação.
3. **P5:** as checagens negativas da auditoria eram chamadas `ctypes` externas
   ao suite; não havia teste versionado de `Tr(PS)`, NaN/Inf, capacidade,
   `NULL`, `result_id` ou overflow.
4. **P1/P2:** o CHECKPOINT 01 é uma reconstrução documental; `32/32` não é
   reproduzível como pytest. `SOURCE_AUDIT.md` usa uma numeração de fases
   anterior à do checkpoint.

## 3. Arquivos modificados

### Código e build

| Arquivo | Mudança |
|---|---|
| `src/bridge/qe_limits.f90` | **Novo.** Validação de dimensão, produto, soma e capacidade; erro de alocação; sem símbolos ABI |
| `src/bridge/qe_memory.f90` | Usa as guardas de dimensão/produto antes de `c_f_pointer` |
| `src/bridge/qe_c_api.f90` | Valida `ncenter` e `3*ncenter`; `xyz_bohr` com `stat=` |
| `src/state/qe_state_builder.f90` | Guardas no `begin`, setters transacionais, `prepare` com `stat=` e limpeza fail-closed |
| `src/state/qe_genp.f90` | Guardas de produto e `stat=` em todas as alocações |
| `src/state/qe_gensbas.f90` | Guardas de produto/soma, `stat=`, limpeza de todas as globais |
| `src/state/qe_genpprim.f90` | Guardas de produto, `stat=` em Ccart/CO/Sp |
| `src/analysis/qe_analysis_state.f90` | `qe_result_alloc` retorna status e usa `stat=` |
| `src/analysis/qe_mayer.f90` | `stat=` nos temporários; capacidade verificada |
| `CMakeLists.txt` | Inclui `qe_limits.f90` no objeto do bridge |

### Testes

| Arquivo | Mudança |
|---|---|
| `tests/native/test_abi_negative.c` | **Novo.** E3, E4, E5, E6 e falha de alocação |
| `tests/python/test_native_negative.py` | **Novo.** E1 e E2 no boundary Fortran |
| `tests/CMakeLists.txt` | Registra `abi_negative_c` no CTest |

### Binários e documentação

| Arquivo | Mudança |
|---|---|
| `python/qe_multiwfn/libqe_multiwfn.so` | Rebuild `b83308c2…` |
| `python/libqe_multiwfn.so` | Rebuild `b83308c2…` |
| `docs/PHASE13C1_PHASE01_RETROSPECTIVE_AUDIT.md` | Adendo de reconciliação 13C.2 |
| `docs/PHASE13C2_PHASE01_REMEDIATION.md` | Este relatório |

`vendor/` e a árvore frozen 0.2.0 não foram alterados.

## 4. Correções realizadas

1. **Módulo interno de limites** (`qe_limits`): `qe_check_dimension`,
   `qe_check_product`, `qe_check_sum`, `qe_check_capacity` e
   `qe_set_allocation_error`.
2. **Todas as 89 instruções `allocate` em `src/`** passaram a usar `stat=`
   (verificação automática: 89/89; nenhuma sem `stat=`).
3. **Setters transacionais:** shells, primitivas, AO map, normalização e
   orbitais alocam arrays temporários; em falha, os temporários são liberados
   e o estado anterior permanece intacto; em sucesso, `move_alloc` transfere.
4. **`qe_state_begin_system`:** valida todos os produtos antes de alocar;
   falha de alocação chama `qe_state_release()` e deixa o motor em
   `INITIALIZED`.
5. **`qe_state_prepare`:** todas as alocações de globais usam `stat=`; falha
   chama `qe_prepare_clear_globals()`, que libera `a`, `basstart`, `basend`,
   `Ptot`, `Palpha`, `Pbeta`, `Sbas`, limpa resultados e zera contadores.
   O modelo canônico é preservado para retry/release.
6. **Resultado Mayer:** `qe_result_alloc` retorna `status`; os três buffers
   temporários também usam `stat=` e são liberados em falha.
7. **Adaptadores nativos** (`genP`, `genSbas`, `genPprim`): guardas de
   produto/soma e `stat=`; falha limpa as globais do adaptador e não publica
   resultado científico.
8. **Getters de buffer:** usam `qe_check_capacity` antes de `c_f_pointer`,
   sem calcular `n*n` de forma insegura.

## 5. Tratamento de alocação

### 5.1 Inventário (Etapa A)

Todas as alocações controladas pelo wrapper estão em `src/`; as alocações
internas de `vendor/` permanecem sob o runtime Fortran original (ver §11).
A tabela abaixo agrupa as 89 instruções por rotina; cada célula “Arrays”
lista todas as alocações daquela rotina.

| Arquivo | Rotina | Arrays e dimensões | Origem das dimensões | Antes | Depois |
|---|---|---|---|---|---|
| `qe_state_builder.f90` | `qe_state_begin_system` | `atomic_numbers(ncenter)`, `coordinates(3,ncenter)`, `basis_center(nbasis)`, `basis_type(nbasis)`, `density_total(nbasis,nbasis)`, `density_alpha`, `density_beta`, `overlap`, `basstart(ncenter)`, `basend(ncenter)` | ABI `qe_begin_system` | sem `stat=`; falha abortava/parcial | `stat=` um a um; falha → release + `QE_ERROR_ALLOCATION` |
| `qe_state_builder.f90` | `qe_state_set_shells` | `shell_center`, `shell_l`, `shell_prim_start`, `shell_prim_end`, `shell_cartesian` (todos `nshell`) | v1 `qe_set_shells` | sem `stat=`; destruía estado anterior | temporários + `move_alloc`; falha preserva o anterior |
| `qe_state_builder.f90` | `qe_state_set_primitives` | `prim_center`, `prim_type`, `prim_shell`, `prim_exponent`, `prim_coefficient`, `prim_normalization` (`nprims`) | v1 `qe_set_primitives` | sem `stat=` | temporários + `move_alloc` |
| `qe_state_builder.f90` | `qe_state_set_ao_map` | `ao_shell`, `ao_multiwfn_type`, `ao_angular_type`, `ao_source_index` (`nbasis`) | v1 `qe_set_ao_map` | sem `stat=` | temporários + `move_alloc` |
| `qe_state_builder.f90` | `qe_state_set_ao_normalization` | `ao_source_self_overlap`, `ao_contraction_norm`, `ao_normalization_convention` (`nbasis`) | v1 `qe_set_ao_normalization` | sem `stat=` | temporários + `move_alloc` |
| `qe_state_builder.f90` | `qe_state_set_orbitals` | `orb_coefficients(m,n)`, `orb_energies(nmo)`, `orb_occupations(nmo)`, `orb_spin(nmo)` | v1 `qe_set_orbitals` | sem `stat=` | produto `m*n` verificado; temporários + `move_alloc` |
| `qe_state_builder.f90` | `qe_state_prepare` (RHF) | `psp(nbasis,nbasis)` | `the_mol%nbasis` | sem `stat=` | `qe_check_product` + `stat=` |
| `qe_state_builder.f90` | `qe_state_prepare` (UHF/ROHF) | `psp(nbasis,nbasis)` | `the_mol%nbasis` | sem `stat=` | `qe_check_product` + `stat=`; falha limpa globais |
| `qe_state_builder.f90` | `qe_state_prepare` (globais) | `a(ncenter)`, `basstart(ncenter)`, `basend(ncenter)`, `Ptot(nbasis,nbasis)`, `Palpha`, `Pbeta`, `Sbas` | modelo canônico | sem `stat=` | `stat=`; falha → `qe_prepare_clear_globals()` |
| `qe_analysis_state.f90` | `qe_result_alloc` | `mayer_total`, `mayer_alpha`, `mayer_beta` (`ncenter,ncenter`) | `ncenter` global | sem `stat=` e sem status | produto verificado; `stat=`; retorna `QE_ERROR_ALLOCATION` |
| `qe_mayer.f90` | `qe_mayer_calculate` | `bndmattot`, `bndmata`, `bndmatb` (`ncenter,ncenter`) | `ncenter` global | sem `stat=` | `stat=`; falha limpa resultado |
| `qe_c_api.f90` | `qe_v1_set_atoms` | `xyz_bohr(3,ncenter)` | v1 `qe_set_atoms` (Å) | sem `stat=` | `ncenter` conferido; `3*ncenter` e `stat=` |
| `qe_memory.f90` | `qe_copy_real2d`, `qe_copy_int1d` | `dest(m,n)`, `dest(n)` | chamador | já usava `stat=` | guardas de produto/dimensão antes do ponteiro |
| `qe_genp.f90` | `qe_genp_build_orbitals` | `CObasa(nbasis,nmo)`, `CObasb`, `MOocc(nmo)`, `MOtype(nmo)`, `alpha_idx(n)`, `beta_idx(n)`, `order(n)` | modelo/orbitais v1 | sem `stat=` | produtos verificados; `stat=`; falha limpa globais |
| `qe_gensbas.f90` | `qe_gensbas_build` | `a(ncenter)`, `b(nprims)`, `primstart/primend(nbasisCar)`, `primconnorm(nprims)`, `basshell/bascen/bastype(nbasis)`, `basstart/basend(ncenter)`, `shtype/shtypeCar/shcen/shcon(nshell)`, `primshexp/primshcoeff(nprimshell_total)` | modelo de base v1 | sem `stat=` | somas/produtos verificados; `stat=`; falha → `qe_gensbas_clear_all()` |
| `qe_gensbas.f90` | `qe_gensbas_generate_cartesian` | `Sbas_keep`, `Sbas(nbasisCar,nbasisCar)`, `Sbas_cart_saved` | `nbasisCar` | sem `stat=` | produto verificado; `stat=`; restaura Sbas ou falha fechado |
| `qe_genpprim.f90` | `qe_genpprim_generate`, `qe_genpprim_overlap` | `Ccart_a/Ccart_b(nbasisCar,nbasis)`, `CO(nmo,nprims)`, `Sp(nprims,nprims)` | modelo de base/orbitais | sem `stat=` | produtos verificados; `stat=`; falha limpa o adaptador |

### 5.2 Comportamento em falha

- Arrays cuja alocação falhou nunca são usados.
- Alocações parciais são liberadas; setores transacionais preservam o estado
  anterior.
- O erro é propagado como `QE_ERROR_ALLOCATION` (código 5), já mapeado para
  `QeAllocation` no Python.
- O motor permanece em `INITIALIZED` (falha no `begin`) ou `SYSTEM_LOADED`
  (falha em setter/prepare), nunca em estado que permita reutilizar dados
  inválidos.
- Resultados científicos não são publicados em caso de falha.

## 6. Proteções contra overflow

| Local | Verificação |
|---|---|
| `qe_begin_system` | `ncenter`, `nbasis`, `nprims` ≤ `huge(int32)`; `nbasis*nbasis`, `ncenter*ncenter`, `3*ncenter` antes de qualquer alocação |
| `qe_set_orbitals` | `nmo`, `ncoeff`, `m*n` verificados antes de mapear o buffer |
| `qe_set_shells` / primitives / AO map | dimensão positiva e ≤ limite |
| `qe_gensbas_build` | `ncart*nprim_comp`, `nbasisCar+ncart`, `nprims+nprim_add`, `nprimshell_total+nprim_add`, `nbasisCar*nbasisCar` |
| `qe_genp_build_orbitals` | `nbasis*nmo`, `2*nbasis`, `nbasis*nbasis` |
| `qe_genpprim_*` | `nbasisCar*nbasis`, `nmo*nprims`, `nprims*nprims` |
| `qe_mayer_get_result` / `qe_genp_get_density` / `qe_gensbas_get_*` / `qe_genpprim_get` | `qe_check_capacity` antes de `c_f_pointer` |
| `qe_pointer_to_real2d` | `m*n` antes de `c_f_pointer` |

A multiplicação só é executada depois do teste `a > QE_MAX_INDEX / b`; nunca
se calcula primeiro para depois verificar.

## 7. Mudanças nos testes

### 7.1 Novos testes C (`tests/native/test_abi_negative.c`)

| Grupo | Casos |
|---|---|
| E3 | capacidade 3 para resultado 2×2; sentinelas/guarda confirmam que nada foi escrito; capacidade 4 passa |
| E4 | `NULL` em `set_atomic_data`, `set_basis_data`, `set_density`, `set_overlap`, `get_mayer_dimensions`, `get_mayer_metadata`, `get_last_error`, `get_mayer_result` |
| E5 | `result_id=99` → `QE_ERROR_INVALID_ARGUMENT`; alpha em RHF → `QE_ERROR_NOT_AVAILABLE` |
| E6 | `ncenter` negativo/zero, `nbasis` zero, `nprims<nbasis`, produtos `50000²`, `ncenter²`, `INT_MAX²` — todos rejeitados antes de alocar; estado permanece `INITIALIZED`; sistema válido funciona em seguida |
| Alocação | `RLIMIT_AS=256 MB` + `nbasis=20000` (3,2 GB) → `QE_ERROR_ALLOCATION`, estado consistente, sistema válido posterior funciona |

### 7.2 Novos testes Python (`tests/python/test_native_negative.py`)

| Grupo | Casos |
|---|---|
| E1 | `P=I`, `S=2I`, `Ne=2` → `Tr(P*S)=4` rejeitado pelo Fortran; estado permanece `SYSTEM_LOADED`; getter de resultado falha |
| E2 | NaN na densidade; `+inf`, `-inf` e NaN no overlap → `QeInvalidArgument` |

### 7.3 Contagens

| Suite | Antes 13C.2 | Depois 13C.2 |
|---|---:|---:|
| Python local | 233 passed | **238 passed** (+5) |
| CTest | 6/6 | **7/7** (+1) |
| Exemplos | 3/3 | **3/3** |
| CI hospedada Python | 82 passed, 20 skipped | **87 passed, 20 skipped** |
| CI hospedada CTest | 6/6 | **7/7** |

A diferença de 5 testes Python na CI é exatamente `test_native_negative.py`.

## 8. Resultados de regressão

| Verificação | Antes | Depois |
|---|---|---|
| Suíte Python completa | 233 passed | 238 passed |
| CTest | 6/6 | 7/7 |
| Exemplos | 3/3 | 3/3 |
| Fluxos científicos alvo (H₂/H₂O/benzeno, H₂O/6-31G*, H₂S/def2-TZVP, O₂ UHF/ROHF, d cartesiano) | 28 passed | **28 passed** |
| Referências numéricas | inalteradas | inalteradas (comparações `array_equal`/`allclose` existentes) |
| `vendor/` | 74 arquivos | 74 arquivos, diff vazio |
| Frozen 0.2.0 | `9560c0fc…` | `9560c0fc…` |

Os 28 testes de regressão usam as mesmas fixtures e referências já
existentes; nenhuma tolerância ou valor esperado foi alterado.

## 9. Integridade científica

- `vendor/` não foi modificado; `calcMayerbndord` permanece byte a byte.
- Nenhuma fórmula, convenção angular, normalização, ocupação, ordem de
  orbitais ou tolerância científica foi alterada.
- As mudanças estão restritas ao wrapper Fortran/Python e ao tratamento de
  memória/dimensões.
- O rebuild não alterou os resultados das rotinas originais; as referências
  bitwise continuam passando.
- Alocações internas de `genP`, `genSbas`, `genSbas_curr` e `genPprim` ficam
  dentro do código original; o wrapper faz pré-checagem de dimensões e
  pós-condição (`allocated`, tamanho, trace/simetria). Não é possível
  interceptar `STAT=` dessas rotinas sem alterar `vendor/`, o que é proibido.

## 10. Integridade ABI

| Item | Valor |
|---|---|
| Símbolos exportados | **44** |
| Legados | **17** (`QE_MULTIWFN_0.1.1`) |
| Aditivos | **27** (`QE_MULTIWFN_0.2.0`) |
| Símbolos removidos/renomeados | **0** |
| Assinaturas públicas alteradas | **0** |
| Novos símbolos públicos | **0** (`qe_limits` é interno e oculto) |
| SONAME | `libqe_multiwfn.so.0` |
| RUNPATH | `$ORIGIN` |
| `ldd -r` | limpo |

O version script `cmake/qe_multiwfn.map` continua expondo apenas `qe_*`; o
novo módulo não aparece em `nm -D`.

## 11. Limitações remanescentes

1. Alocações internas das rotinas originais (`Sbas`, `Ptot`, `Ptot_prim`)
   permanecem sob o runtime Fortran; `vendor/` não pode ser alterado. A
   interface pré-valida dimensões e verifica pós-condições, mas não converte
   uma falha interna em `stat=` sem modificar o código original.
2. Não foi executado Valgrind/ASan (exigiria rebuild instrumentado).
3. O teste de falha de alocação usa `RLIMIT_AS` e cobre um caminho
   representativo; não injeta falha em cada uma das 89 alocações.
4. O estado global continua process-global e não thread-safe.
5. A origem histórica da Fase 1 continua não confirmável pelo Git (2 commits,
   sem tags); nenhuma data/tag/autor foi inventado.
6. A CI hospedada ignora 20 testes que dependem da árvore externa
   `QE-Multiwfn-validation`; localmente eles passam.
7. `RELEASE_MANIFEST_0.2.0.txt` mantém a divergência de hash já registrada na
   13C.1; não foi alterado nesta fase.

## 12. Histórico Git

| Commit | Mensagem | Conteúdo |
|---|---|---|
| `2ecaadb` | `docs: add Phase 13C.1 Phase 1 retrospective audit` | Relatório 13C.1 |
| `979ecfa` | `fix: harden native allocation/overflow handling and add negative tests (Phase 13C.2)` | Código, testes, rebuild e CMake |

O commit `979ecfa` foi publicado em `origin/main` sem force push. A árvore
frozen e o vendor não foram tocados.

## 13. Resultado da CI hospedada

| Item | Valor |
|---|---|
| Workflow | `qe-multiwfn-ci` |
| Run ID | `43711107774` |
| URL | https://github.com/mmfIA/qe-multiwfn/actions/runs/43711107774 |
| Commit | `979ecfa101746d3689f222f737839e69c9441315` |
| Conclusão | **success** |
| `build-test (3.12)` | success (11:53:41–11:58:57 UTC) |
| `optional-full` | success (11:58:59–11:59:33 UTC) |
| CTest | **7/7** |
| Python | **87 passed, 20 skipped** |
| Installed smoke | `PASS 0.3.0` |

O commit documental desta fase é publicado separadamente e dispara uma
execução adicional da CI; o resultado dessa execução é registrado no
checkpoint externo.

## 14. Conclusão

**STATUS GLOBAL: PASS.**

As três demandas técnicas prioritárias foram resolvidas: todas as 89
alocações controladas pelo wrapper usam `stat=`; os produtos de dimensão são
verificados antes de multiplicar/alocar; e os seis grupos de testes negativos
estão versionados e executados pela CI. A ABI permanece em 44 símbolos, o
vendor e a árvore frozen estão preservados e não houve regressão científica.

A documentação foi reconciliada: a contagem autoritativa é **29 pytest + 3
exemplos** no artefato 0.1.1 (não 32 pytest), e a origem histórica não
confirmável pelo Git foi registrada sem invenção.

A Fase 13C.3 não foi iniciada.

---

**Fim do relatório — Fase 13C.2.**
