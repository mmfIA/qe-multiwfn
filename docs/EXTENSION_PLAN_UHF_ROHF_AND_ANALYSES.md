# Plano de extensão — UHF, ROHF e outras análises

> **Documento de planejamento histórico.** UHF e ROHF foram implementados e
> validados no 0.3.0-dev. PBC, pós-HF e ECP/EDF continuam pendentes; f/g/h
> permanece bloqueado no caminho de rotinas originais. Status atual:
> `docs/IMPLEMENTATION_STATUS.md` e `docs/LIMITATIONS.md`.

**Estado original:** planejamento (Fase 8).
**Base original:** QE-Multiwfn 0.1.1 + Molecular Data Model 1.0 (schema `1.0.0`),
P0 e M1 concluídas.

Este documento registra **o que falta**, **como implementar sem quebrar**
e **como validar** antes de declarar suporte. Nenhuma rotina científica será
substituída por aproximação.

---

## 1. Estado atual (verificado)

| Item | Estado |
|---|---|
| Modelo 1.0 em Python | Implementado (`model_v1.py`) |
| Shells/primitivas/AO map | Implementado (Python + Fortran v1 ABI) |
| Adaptador ORCA RHF | Implementado (`adapters/orca.py`) |
| P derivada no adaptador | Implementado e documentado (`P = 2 C_occ C_occ^T`) |
| Matrizes S/P/C/ocupações | Implementado (validação estrita) |
| UHF/ROHF no núcleo | **Implementado (opt-in) e validado**; pós-HF rejeitado |
| d/f no adaptador | **Implementado/validado** (esférico e cartesiano) |
| PBC/ECP-EDF executáveis | Não implementado |
| Outras análises | Não implementado |

A execução do Mayer continua sendo a rotina original
`calcMayerbndord` em `vendor/.../bondorder.f90`, sem modificação.

---

## 2. UHF e ROHF

### 2.1 Status (M1, 2026-11-14)

- **UHF: IMPLEMENTADO (opt-in) e VALIDADO** para O₂/STO-3G.
  - Ativação explícita: `load_molecule_v1(..., allow_open_shell=True)` ou
    `qe_v1_enable_open_shell(1)`.
  - Adaptador `from_orca_uhf_directory` divide os blocos α/β do `sp.json`.
  - P_alpha/P_beta derivadas no adaptador, com proveniência.
  - QE α/β × Multiwfn α/β: `1.22e−15` / `2.89e−15`.
  - QE total (Wiberg generalizado / mixed) × Multiwfn mixed: `3.16e−9`.
  - QE (α+β) × Multiwfn total: `4.0e−15`; × ORCA: `1.33e−15`.
  - UHF/ROHF sem a flag são rejeitados; pós-HF é rejeitado mesmo com a flag.
- **ROHF: IMPLEMENTADO (opt-in) e VALIDADO** para O₂/STO-3G.
  - P_alpha = Σ_{occ>0} C_i C_iᵀ; P_beta = Σ_{occ=2} C_i C_iᵀ.
  - QE α/β × Multiwfn α/β: `2.22e−16` / `2.22e−15`.
  - QE total × Multiwfn mixed: `2.22e−15`.
  - QE (α+β) × ORCA: `6.66e−16`.
- **Pós-HF (wfntype 3/4): NÃO implementado.**
- A API legada 0.1.1 continua **RHF-only**; UHF é um caminho v1 aditivo.

### 2.2 O que o núcleo faz no caminho UHF (implementado)

1. `qe_v1_enable_open_shell(1)` habilita somente `wfntype=1`.
2. `qe_state_begin_system` aceita UHF apenas sob a flag.
3. `qe_state_set_electronic_metadata` aceita multiplicidade ≥ 2 e Ne ímpar.
4. `qe_state_set_density` exige α/β, valida simetria e `Ptotal=Pα+Pβ`.
5. `qe_state_prepare` valida `Tr(PσS)=Nσ`, idempotência UHF
   `PσSPσ=Pσ` e empurra `Palpha/Pbeta/naelec/nbelec` para os globais.
6. `qe_mayer_calculate` chama a rotina original `calcMayerbndord` sob a flag.
7. `qe_analysis_state` devolve as três matrizes; `MayerResult` expõe
   `total`, `alpha`, `beta` e metadados.

Semântica preservada: para UHF, `total` é o Wiberg generalizado (densidade
mista) calculado pela rotina original, enquanto `alpha`/`beta` são as
contribuições de Mayer. `alpha+beta` corresponde ao total all-electron;
não sobrescrevemos `total` com a soma.

### 2.3 Pós-HF (planejado)

- Definir dados de estado multiconfiguracional e validação científica
  específica.
- Auditar `genP`/`wfnsanity` para wfntype 3/4 antes de qualquer execução.
- Não inferir densidades efetivas próprias.

### 2.4 Gates

| Gate | Critério | Status |
|---|---|---|
| G-UHF-1 | Modelo representa UHF e rejeita execução sem flag | PASS |
| G-UHF-2 | Núcleo não reimplementa matemática; usa `calcMayerbndord` | PASS |
| G-UHF-3 | Sistema com referência UHF externa (O₂/STO-3G) | PASS |
| G-UHF-4 | QE × Multiwfn ≤ 1e−6; QE × ORCA ≤ 1e−4 | PASS |
| G-UHF-5 | Três matrizes devolvidas com metadados | PASS |
| G-ROHF-1 | Convenção de ocupações documentada e validada | PASS |
| G-ROHF-2 | Referência independente ROHF + Multiwfn | PASS |
| G-ROHF-3 | Nenhuma regressão em RHF (84 testes + 223 do pipeline) | PASS |

---

## 3. d/f no adaptador ORCA

**Implementado e validado (M1, 2026-11-14): d/f esféricos.**

- ORCA emite d/f esféricos por padrão (5D/7F), na mesma ordem interna do
  Multiwfn:
  - d: `dz2, dxz, dyz, dx2y2, dxy` → `-5..-1`;
  - f: `f0, f+1, f-1, f+2, f-2, f+3, f-3` → `-12..-6`.
- Casos de referência: H₂O/6-31G* (18 funções, 35 primitivas, d esférico) e
  H₂S/def2-TZVP (49 funções, 79 primitivas, d+f esféricos).
- Validação científica: QE × Multiwfn ≤ 4.55e−9; QE × ORCA ≤ 8.88e−16.
- O adaptador detecta o número de componentes por shell a partir dos labels
  e rejeita inconsistências.

**d/f cartesianos: IMPLEMENTADOS e VALIDADOS.** ORCA 6.1.1 não emite
Cartesian 6D/10F, então a validação usa um fixture PySCF 2.15.0 real
(RHF/6-31G*, `mol.cart=True`) convertido ao esquema canônico ORCA-like. O
mapeamento por componente (`dxx,dyy,dzz,dxy,dxz,dyz`; f análogo) foi
verificado e o Mayer QE × Multiwfn deu `1.20e−9`. Componentes desconhecidos
são rejeitados.

---

## 4. Outras análises

Ordem recomendada, cada uma com dependências explícitas:

| Análise | Dependências mínimas | Backend | Observações |
|---|---|---|---|
| Mayer | geometry, AO→centro, P, S | `calcMayerbndord` | implementado (RHF) |
| Mulliken | geometry, P, S | rotina original | baixo risco; comparar com Multiwfn |
| Hirshfeld | densidade, grids, densidades atômicas, EDF | `genHirshfeld` | precisa de grade e validação de EDF |
| MBIS | densidade, progrid, convergência | `MBIS_frj` | rotina com menu; separar opções |
| NAO | base, C, ocupações | rotinas NAO | dependente de convenções de base |
| ESP | densidade, primitivas, LIBRETA | `eleesp2`/`eleesp2_slow` | inicialização do LIBRETA sob demanda |
| Topologia/bacias | densidade, grids, crítica | `topo_main`/`basinana` | fluxo interativo precisa ser isolado |

Regras:

1. Não implementar uma análise antes de auditar a rotina original e suas
   dependências.
2. Cada análise declara `AnalysisRequirement` (campos exigidos/opcionais).
3. Toda comparação com Multiwfn standalone usa o mesmo estado e tolerâncias
   centralizadas.
4. Falta de dado → `INCOMPLETE`, nunca `PASS`.

---

## 5. Estratégia de segurança

- Manter todas as funções `qe_*`/`qe_v1_*` atuais.
- Novas capacidades entram por flags de compilação/execução e por funções
  aditivas, nunca alterando a semântica RHF.
- `vendor/` permanece byte-idêntico.
- Nenhuma tolerância é relaxada; novos casos usam o perfil estrito.
- Cada fase atualiza `IMPLEMENTATION_STATUS`, `LIMITATIONS`, relatório e
  manifesto.

---

## 6. Definição de pronto para qualquer extensão

- código + documentação atualizados;
- build limpo;
- testes antigos e novos passando;
- evidência reproduzível (hashes, logs, proveniência);
- limitações remanescentes listadas;
- `vendor/` intacto;
- nenhuma funcionalidade declarada além do que foi testado.
