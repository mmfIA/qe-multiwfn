# Molecular Data Model 1.0 — Especificação

> **Documento histórico de especificação.** O modelo 1.0 foi implementado no
> 0.2.0/M1 e estendido para MDM 1.1 no 0.3.0-dev. Contagens e referências à
> 0.1.1 neste documento descrevem o estado histórico. Status atual:
> `docs/IMPLEMENTATION_STATUS.md` e `docs/MOLECULAR_DATA_MODEL_1.1.md`.

**Projeto:** QE-Multiwfn (QuantumEngine-Multiwfn)
**Estado:** **ESPECIFICAÇÃO HISTÓRICA — IMPLEMENTADA DEPOIS EM 0.2.0/M1**
**Schema version:** `1.0.0`
**Data:** 2026-11-14
**Base:** QE-Multiwfn 0.1.1 (P0 concluída — ver
`QE-Multiwfn-validation/reports/P0_OPERATIONAL_VERIFICATION.md`)

> Este documento define o contrato canônico de dados moleculares que deve
> alimentar o núcleo Fortran do Multiwfn via RAM. Ele **não altera** a API
> 0.1.1 e **não implementa** o modelo. A implementação só começa após revisão
> deste esquema, da demonstração de compatibilidade retroativa (seção 9) e do
> plano de testes independentes (seção 12).

---

## 1. Objetivo e escopo

### 1.1 Objetivo

Definir um modelo molecular canônico, explícito e verificável que:

1. represente **geometria, base, função de onda, matrizes, correções de
   caroço (ECP/EDF), periodicidade e proveniência** sem perda de informação;
2. seja independente do formato/programa de origem (ORCA, cclib, ASE, FCH,
   WFN, WFX, Molden, MWFN, banco de dados);
3. preserve a matemática original do Multiwfn (o modelo prepara o estado; o
   cálculo continua em `calcMayerbndord` e futuras rotinas originais);
4. permita validar o que está presente, o que falta e o que foi derivado;
5. mantenha **compatibilidade retroativa total** com `MolecularSystem` 0.1.1.

### 1.2 Fora de escopo deste documento

- Implementação em Python/Fortran (será uma fase separada).
- Novos leitores nativos (ORCA/FCH/WFN/...).
- Cálculo de integrais, SCF, `genP`, `genSbas_curr`.
- UHF/ROHF/pós-HF, PBC e ECP/EDF como funcionalidades **executáveis**.
  Eles são modelados aqui, mas permanecem desabilitados até validação
  científica dedicada.
- Thread safety / múltiplas instâncias.

### 1.3 Princípios não negociáveis

1. **Núcleo Multiwfn intocado** (`vendor/` permanece byte-idêntico).
2. **Nenhuma matemática reimplementada** no adaptador; apenas preparação,
   validação e transporte.
3. **Unidades explícitas**; nunca inferir silenciosamente.
4. **Representação explícita** para coeficientes e matrizes.
5. **Tolerâncias centralizadas e fixas**; proibido relaxar por execução.
6. **PASS/FAIL/INCOMPLETE**: ausência de dado nunca vira PASS.
7. **Proveniência obrigatória** para todo dado importado ou derivado.
8. **RAM-to-RAM** no fluxo operacional; arquivos só em adaptadores/testes.

---

## 2. Convenções globais do modelo

| Convenção | Decisão |
|---|---|
| Índices atômicos e de AO no Fortran | **1-based** (como o Multiwfn) |
| Índices em Python/NumPy | 0-based na API pública, convertidos na fronteira |
| Unidade interna de comprimento | **Bohr**; entrada aceita Å ou Bohr com unidade declarada |
| Layout de matrizes na ABI | **column-major / Fortran order** |
| Layout lógico | sempre declarado (`layout`), nunca implícito |
| Ordenação canônica de AO | por centro → por shell → por componente (seção 6.2) |
| Precisão | `float64` (`real(c_double)`); inteiros `int32` (`integer(c_int)`) |
| Strings | UTF-8 na API Python; o Fortran recebe buffers/IDs, não strings livres |
| Dados ausentes | `None`/não alocado + flag de prontidão; nunca zero “válido” |
| Serialização | campos numéricos + metadados; arrays em `.npy`/JSON apenas em persistência |

### 2.1 Enums canônicos

| Enum | Valores |
|---|---|
| `WavefunctionType` | `0=RHF`, `1=UHF`, `2=ROHF`, `3=R-post-HF`, `4=U-post-HF` (espelha `wfntype`) |
| `LengthUnit` | `"bohr"`, `"angstrom"` |
| `BasisRepresentation` | `"cartesian"`, `"spherical"`, `"mixed"` |
| `CoefficientRepresentation` | `"contracted_basis"`, `"primitive_gtf"` |
| `MatrixRepresentation` | `"ao_current_basis"`, `"primitive_gtf"`, `"ao_cartesian"` |
| `DensityOrigin` | `"caller_supplied"`, `"derived_from_orbitals"`, `"post_hf"`, `"unknown"` |
| `SpinComponent` | `"total"`, `"alpha"`, `"beta"` |
| `EcpEdfStatus` (ver 5.8) | `"none"`, `"ecp_with_edf"`, `"ecp_without_edf"`, `"edf_reconstructed"`, `"incomplete"` |
| `PeriodicityType` | `0=isolated`, `1=1D`, `2=2D`, `3=3D` (espelha `ifPBC`) |
| `ProvenanceOrigin` | `"imported"`, `"derived"`, `"caller_supplied"`, `"reconstructed"` |

---

## 3. Versionamento e compatibilidade

- O modelo tem `schema_version = "1.0.0"` (SemVer próprio, independente da
  versão da biblioteca).
- A biblioteca 0.1.1 permanece congelada: **nenhuma assinatura existente
  muda**.
- O modelo ampliado entra por funções **aditivas** (seção 10) e por um
  construtor Python novo (`qe_multiwfn.molecular_v1`), mantendo
  `qe_multiwfn.MolecularSystem` 0.1.1 funcionando sem alteração.
- Regra de compatibilidade: qualquer estado representável em 0.1.1 deve ser
  representável em 1.0 **bit a bit**, sem conversão de unidades ou
  reordenação.

---

## 4. Visão geral da hierarquia

```
MolecularSystemV1
├── schema_version : str
├── provenance     : Provenance
├── atoms          : Atoms           (Z, símbolos, cargas nucleares/efetivas)
├── geometry       : Geometry        (coordenadas + unidade + célula)
├── electronic     : ElectronicState (carga, multiplicidade, Ne, wfntype)
├── basis          : BasisSet
│   ├── shells     : list[Shell]
│   ├── primitives : PrimitiveTable
│   └── aos        : list[AOFunction]
├── wavefunction   : Wavefunction   (opcional)
│   ├── orbitals   : OrbitalSet
│   └── coefficients
├── matrices       : MatrixBundle   (S, P_total, P_alpha, P_beta, ...)
├── core_correction: CoreCorrection (ECP/EDF, opcional)
├── periodicity    : Periodicity    (opcional; isolado por padrão)
└── readiness      : ReadinessFlags
```

Cada componente carrega:

- `present: bool` — existe;
- `origin: ProvenanceOrigin` — de onde veio;
- `validated: bool` — passou nas invariantes aplicáveis;
- `warnings: list[str]` — condições não fatais.

---

## 5. Componentes e campos

### 5.1 `MolecularSystemV1` (raiz)

| Campo | Tipo | Obrigatório | Invariante |
|---|---|---|---|
| `schema_version` | str | sim | `"1.0.0"` |
| `provenance` | Provenance | sim | `source_program` e `format` preenchidos |
| `atoms` | Atoms | sim | `len(z) == ncenter > 0` |
| `geometry` | Geometry | sim | `coords.shape == (ncenter, 3)`, finitas |
| `electronic` | ElectronicState | sim | `wfntype`, `nelectron > 0` |
| `basis` | BasisSet | sim | `nbasis >= 1`, `nprims >= nbasis` |
| `wavefunction` | Wavefunction? | condicional | exigido se análise precisar de C/ocupações |
| `matrices` | MatrixBundle | condicional | pode ser derivado de C se `genP` for permitido |
| `core_correction` | CoreCorrection? | não | se ECP presente, consistência obrigatória |
| `periodicity` | Periodicity | não | default isolado (`ifPBC=0`) |
| `readiness` | ReadinessFlags | sim (calculado) | derivado das presenças |

Dimensões derivadas: `ncenter`, `nbasis`, `nprims`, `nmo`, `nindbasis`.

---

### 5.2 `Provenance`

| Campo | Tipo | Obrigatório | Nota |
|---|---|---|---|
| `source_program` | str | sim | ex.: `"ORCA 6.1.1"`, `"python"` |
| `source_version` | str | sim | versão do programa/origem |
| `source_format` | str | sim | ex.: `"orca_json"`, `"molden"`, `"mwfn"`, `"arrays"` |
| `input_files` | list[FileRecord] | não | caminho relativo, SHA-256, role |
| `created_utc` | str | sim | ISO-8601 UTC |
| `adapter_name` / `adapter_version` | str | sim | responsável pela conversão |
| `coordinate_unit_source` | LengthUnit | sim | unidade do arquivo/origem |
| `conversion_factor` | float | condicional | ex.: Å→Bohr aplicado |
| `normalization_steps` | list[str] | sim | ordem, conversões, permutações |
| `warnings` | list[str] | não | ex.: truncamento de função f |
| `hashes` | dict[str,str] | sim | SHA-256 de S, C, P, geometria etc. |

`FileRecord`: `{role, relative_path, sha256, size, mtime_utc}`.

---

### 5.3 `Atoms` e `Geometry`

**Atoms**

| Campo | Tipo/forma | Obrigatório | Invariante |
|---|---|---|---|
| `z` | int32 `(ncenter,)` | sim | `1 <= z <= 118` |
| `symbols` | list[str] `(ncenter,)` | sim | coerente com `z` |
| `nuclear_charge` | float64 `(ncenter,)` | sim | default `z`; explícito se ECP |
| `effective_nuclear_charge` | float64? `(ncenter,)` | condicional | `z - core_electrons` |
| `labels` | list[str]? | não | rótulo de origem (para auditoria) |
| `residue` / `resname` | int32? / list[str]? | não | preserva informação PDB |
| `ghost` | bool `(ncenter,)` | não | átomos fantasma |

**Geometry**

| Campo | Tipo/forma | Obrigatório | Invariante |
|---|---|---|---|
| `coordinates` | float64 `(ncenter, 3)` | sim | finitas |
| `unit_internal` | `"bohr"` | sim | sempre Bohr no modelo |
| `unit_source` | LengthUnit | sim | unidade de entrada |
| `cell_vectors` | float64 `(3, 3)`? | condicional | Bohr; necessário se PBC |
| `cell_vectors_effective` | float64 `(3, 3)`? | derivado | preenchido por `init_PBC` |
| `periodic_directions` | bool `(3,)` | não | default `(F,F,F)` |

Regra: `geometry.coordinates` é copiado para `a(i)%x/y/z`; **nenhuma**
conversão de unidade ocorre no Fortran.

---

### 5.4 `ElectronicState`

| Campo | Tipo | Obrigatório | Invariante |
|---|---|---|---|
| `wfntype` | WavefunctionType | sim | 0..4 |
| `charge` | int | sim | consistente com Ne |
| `multiplicity` | int | sim | `>=1`; `1` para RHF |
| `nelectron` | int | sim | `>0`; `= ΣZ − charge` |
| `naelectron` / `nbelectron` | int | condicional | UHF/ROHF/pós-HF |
| `imodwfn` | int | não | default 0; 1 se função modificada |
| `total_energy` | float | não | proveniência, não usada por Mayer |
| `virial_ratio` | float | não | proveniência |
| `ecp_core_electrons` | int | condicional | total de elétrons de caroço |

Regras RHF 0.1.1 preservadas: `wfntype=0`, `multiplicity=1`, `nelectron`
positivo e par.

---

### 5.5 `BasisSet`

#### 5.5.1 Contadores

| Campo | Tipo | Invariante |
|---|---|---|
| `nbasis` | int | nº de funções de base contraídas (AO) |
| `nprims` | int | nº de primitivas gaussianas; `>= nbasis` |
| `nindbasis` | int? | nº de funções independentes (após dependência linear) |
| `nbasis_cartesian` | int? | dimensão cartesiana |
| `nbasis_spherical` | int? | dimensão esférica |
| `shell_count` | int | `len(shells)` |
| `representation` | BasisRepresentation | global ou por shell |
| `ao_order` | str | `"canonical"` ou `"source"` + permutação explícita |

#### 5.5.2 `Shell`

| Campo | Tipo | Obrigatório | Invariante |
|---|---|---|---|
| `index` | int (1-based) | sim | único |
| `center` | int (1-based) | sim | `1..ncenter` |
| `l` | int | sim | momento angular 0=s,1=p,2=d,... |
| `shell_type` | str | sim | `"s"`,`"p"`,`"sp"`,`"d"`,... (rótulo de origem) |
| `primitive_start` / `primitive_end` | int (1-based) | sim | intervalo em `primitives` |
| `exponents` | float64 `(nprim_shell,)` | sim | `>0`, finitos |
| `coefficients` | float64 `(nprim_shell,)` | sim | coeficientes de contração |
| `normalization` | float64 `(nprim_shell,)`? | condicional | normalização por primitiva |
| `contraction_normalization` | float64? | condicional | normalização da contração |
| `cartesian` | bool | sim | representação da shell |
| `spherical` | bool | sim | mutuamente exclusivo com `cartesian` |
| `source_label` | str? | não | rótulo original |
| `multipole` | bool | não | shell de multipolo (MWFN) |

Regra SP: uma shell `sp` deve ser decomposta em duas entradas (s e p) com
os mesmos expoentes e coeficientes apropriados; a correspondência com
`basshell`/`bastype` do Multiwfn deve ser explícita.

#### 5.5.3 `PrimitiveTable` (global)

| Campo | Tipo/forma | Invariante |
|---|---|---|
| `center` | int32 `(nprims,)` | 1-based |
| `type` | int32 `(nprims,)` | código de componente (ver 5.5.4) |
| `exponent` | float64 `(nprims,)` | `>0` |
| `coefficient` | float64 `(nprims,)` | contração |
| `normalization` | float64 `(nprims,)` | normalização |
| `shell_index` | int32 `(nprims,)` | 1-based, liga primitiva à shell |

Corresponde a `b(:)` (`primtype`: `center`, `type`, `exp`) + coeficientes
de contração.

#### 5.5.4 `AOFunction`

| Campo | Tipo | Invariante |
|---|---|---|
| `index` | int (1-based) | ordem canônica |
| `center` | int (1-based) | `1..ncenter` |
| `shell_index` | int (1-based) | shell que originou a AO |
| `l` | int | momento angular |
| `component` | str | ex.: `"s"`, `"pz"`, `"px"`, `"py"`, `"dz2"` |
| `multiwfn_type` | int | código de **componente** do Multiwfn |
| `angular_type` | int | código de **momento angular** (0=s,1=p,2=d,...) |
| `cartesian` | bool | representação da AO |
| `source_label` | str? | ex.: `"0C   1pz"` |

**Códigos de componente (`multiwfn_type`) — convenção real do Multiwfn
(`bastype`), confirmada em `vendor/.../define.f90:232-240` e
`vendor/.../fileIO.f90:422-439`:**

| Faixa `bastype` | Significado |
|---|---|
| `1` | S |
| `2`, `3`, `4` | p: X, Y, Z (isto é, px, py, pz) |
| `5..10` | d cartesiano: XX, YY, ZZ, XY, XZ, YZ |
| `11..20` | f cartesiano (ordem interna do Multiwfn: XXX, YYY, ZZZ, XXY, XXZ, YYZ, XYY, XZZ, YZZ, XYZ) |
| `21..35` | g cartesiano |
| `36..56` | h cartesiano |
| `-5..-1` | d esférico: D 0, D+1, D−1, D+2, D−2 (respectivamente) |
| `-12..-6` | f esférico |
| `-21..-13` | g esférico |
| `-32..-22` | h esférico |
| `0` | não usado (slot vazio) |

A tabela `s2f` de `fileIO.f90` mapeia `(shell_type, componente_j)` para esse
código. A ordem dos componentes **não** é a mesma de ORCA/Molden/FCH; em
particular, f cartesiano é reordenado (`s2f(3,1:10) =
11,12,13,17,14,15,18,19,16,20`).

> **Ambiguidade crítica a resolver:** a API 0.1.1 chama de `basis_type` um
> código por AO, mas:
> - o header `qe_multiwfn.h` sugere `0=S, 1=P, 2=D`;
> - o adaptador de validação grava o **momento angular** (`0=s,1=p,2=d,3=f`);
> - o Multiwfn usa o código de **componente** acima (`1=S, 2=px, ...`).
>
> `calcMayerbndord` **não usa** `basis_type` (confirmado em
> `vendor/.../bondorder.f90`: usa apenas `Ptot`, `Sbas`, `basstart`,
> `basend`, `wfntype`, `ncenter`, `nbasis`). Por isso a P0 não foi afetada.
> O modelo 1.0 separa `multiwfn_type` (componente) de `angular_type`
> (momento angular) e mantém `legacy_basis_type` apenas como alias
> documentado; qualquer análise orbital futura deve usar o código de
> componente correto, nunca o legado.

**Atualização M1 (2026-11-14):** a ordem esférica do ORCA foi confirmada
experimentalmente e é idêntica à ordem interna esférica do Multiwfn:

- d (5D): `dz2, dxz, dyz, dx2y2, dxy` → códigos `-5,-4,-3,-2,-1`;
- f (7F): `f0, f+1, f-1, f+2, f-2, f+3, f-3` → códigos `-12..-6`.

O adaptador implementa e valida d/f esféricos (H₂O/6-31G* e H₂S/def2-TZVP)
e d/f **cartesianos** (H₂O/6-31G* 6D via fixture PySCF convertida ao esquema
canônico). ORCA 6.1.1 não emite d/f cartesianos; a validação cartesiana usa
um fixture PySCF real e comparação com Multiwfn. Componentes desconhecidos
são rejeitados.

#### 5.5.5 Ordenação e permutação

- **Requisito funcional do Mayer:** cada centro deve ocupar um bloco
  contíguo de AOs (`basstart`/`basend`). Dentro do bloco, a ordem é
  preservada da origem e registrada.
- **Ordem canônica inicial (conservadora):**
  `centro (1..ncenter)` → `shell` (ordem de origem) → `componente`
  (ordem de origem). Cada AO carrega `source_ao_index` e `multiwfn_type`.
- Se a origem tiver centros intercalados, há duas opções:
  (a) rejeitar; (b) permutar para blocos por centro, aplicando a mesma
  permutação `P_ao` a `S`, `P`, `C`, `basis_center`, `basis_type` e
  registrando hashes antes/depois. A recomendação é (b), com
  `ao_order="source"` + `P_ao` explícita.
- Uma ordenação estritamente canônica por `multiwfn_type` (ex.: p em
  X,Y,Z) fica como opção futura, pois reordena todas as matrizes e exige
  nova validação. Ela **não** é obrigatória para o Mayer.

---

### 5.6 `Wavefunction` e `OrbitalSet`

| Campo | Tipo | Obrigatório | Invariante |
|---|---|---|---|
| `coefficients` | float64 `(n1, n2)` | sim | finitas; layout declarado |
| `coefficient_representation` | CoefficientRepresentation | sim | contraída ou primitiva |
| `coefficient_layout` | `"orbital_ao"` \| `"ao_orbital"` | sim | ex.: `CO(nmo,nprims)` vs `CObasa(nbasis,nmo)` |
| `energies` | float64 `(nmo,)` | sim | finitas |
| `occupations` | float64 `(nmo,)` | sim | `>=0`; soma = Ne |
| `spin` | list[SpinComponent] `(nmo,)` | sim | `alpha`/`beta`/`both` |
| `symmetry_labels` | list[str]? | não | `MOsym` |
| `orbital_indices` | int32 `(nmo,)` | sim | 1-based |
| `homo_index` / `lumo_index` | int? | não | derivável |
| `nocc` | int | condicional | `Σocc/2` para RHF |
| `irrep` / `state` | int? | não | proveniência |

Regras:

- Não inferir `multiplicity` a partir de ocupações quando o arquivo traz
  informação explícita.
- Manter `occupation`, `spin do orbital`, `wfntype` e `naelectron/nbelectron`
  como campos independentes.
- Para UHF, `coefficients_alpha` e `coefficients_beta` podem ser matrizes
  separadas **ou** uma única matriz com `spin` declarado por coluna
  (implementação M1: uma matriz `(nbasis, 2*nbasis)` com spin `alpha`/`beta`).
  A representação escolhida deve ser explícita; o `CᵀSC` é verificado por
  grupo de spin, não na matriz completa.
- **UHF/ROHF (M1):** o modelo e a ABI v1 suportam P_alpha/P_beta, traços
  `Tr(PσS)=Nσ`, idempotência `PσSPσ=Pσ` e `Ptotal=Pα+Pβ`. A execução é
  **opt-in** (`allow_open_shell=True` / `qe_v1_enable_open_shell(1)`) e foi
  validada para O₂/STO-3G em UHF e ROHF. Para ROHF:
  `Pα = Σ_{occ>0} C_i C_iᵀ` e `Pβ = Σ_{occ=2} C_i C_iᵀ`. Pós-HF continua
  rejeitado.

---

### 5.7 `MatrixBundle`

| Matriz | Forma | Representação | Obrigatória | Observações |
|---|---|---|---|---|
| `S` | `(nbasis, nbasis)` | `ao_current_basis` | sim (Mayer) | simétrica, positiva definida |
| `P_total` | `(nbasis, nbasis)` | `ao_current_basis` | sim (Mayer) | simétrica; RHF idempotente |
| `P_alpha` / `P_beta` | `(nbasis, nbasis)` | `ao_current_basis` | condicional | UHF/ROHF |
| `P_total_prim` | `(nprims, nprims)` | `primitive_gtf` | não | não substitui a anterior |
| `Dbas`, `DorbA`, ... | várias | `ao_current_basis` | não | derivadas; proveniência obrigatória |
| `Sbas_PBC` | `(nbasis, nbasis)` | `ao_current_basis` | condicional | PBC |

Cada matriz tem metadados:

```
MatrixRecord:
  data, representation, layout, symmetric, dimensions,
  origin (supplied/derived), derivation (ex.: "P = 2 C_occ C_occ^T"),
  tolerance_profile, sha256
```

Regras:

- `P_total` fornecida não é silenciosamente substituída por `genP`.
- Se derivada, registrar a fórmula e as tolerâncias usadas.
- `P_total` e `S` devem pertencer à **mesma** representação; dimensões
  iguais não bastam.
- Matrizes sempre em Fortran order na fronteira.

---

### 5.8 `CoreCorrection` (ECP/EDF)

| Campo | Tipo | Obrigatório | Nota |
|---|---|---|---|
| `status` | ECP/EDF status | sim | ver enum |
| `ecp_elements` | list[int] | condicional | Z com ECP |
| `effective_nuclear_charges` | float64 `(ncenter,)` | condicional | `Z - core` |
| `core_electrons_per_atom` | int32 `(ncenter,)` | condicional | `nEDFelecatm` |
| `core_electron_count` | int | condicional | `nEDFelec` |
| `edf_primitives` | PrimitiveTable | condicional | `b_EDF` |
| `edf_coefficients` | float64 `(nEDFprims,)` | condicional | `CO_EDF` |
| `source` | str | condicional | `"wfx"`, `"internal_library"`, `"caller"` |

Regras:

| Situação | Comportamento |
|---|---|
| sem ECP | seguir normalmente |
| ECP + EDF disponível | preparar estado com EDF |
| ECP sem EDF | marcar `ecp_without_edf`; só permitir análises que aceitem |
| EDF incompleta | rejeitar |
| EDF incompatível com átomos | rejeitar |

Ausência de EDF **não** é equivalente a EDF vazia válida.

---

### 5.9 `Periodicity`

| Campo | Tipo | Default | Nota |
|---|---|---|---|
| `ifPBC` | int 0..3 | 0 | isolado |
| `directions` | bool `(3,)` | `(F,F,F)` | eixos periódicos |
| `cell_vectors` | float64 `(3,3)`? | None | Bohr, originais |
| `cell_vectors_effective` | float64 `(3,3)`? | derivado | `init_PBC` pode alterar |
| `neighbor_cells` | int `(3,)` | 0 | `PBCn*_in` |
| `overlap_pbc` | MatrixRecord? | None | `Sbas_PBC` |

O modelo preserva vetores **originais** separados dos efetivos. O caminho
Mayer 0.1.1 **rejeita** `ifPBC > 0`.

---

### 5.10 `ReadinessFlags`

| Flag | Condição |
|---|---|
| `geometry_ready` | atoms + geometry válidos |
| `basis_ready` | shells + primitivas + AOs consistentes |
| `wavefunction_ready` | coefficients + occupations + spins válidos |
| `density_ready` | `P_total` presente ou derivável com validação |
| `overlap_ready` | `S` presente ou gerável por rotina autorizada |
| `ecp_ready` | status ECP/EDF coerente |
| `integrals_ready` | dependências de LIBRETA preparadas (futuro) |
| `analysis_ready(analysis)` | todas as dependências da análise satisfeitas |

Cada análise declara:

```
AnalysisRequirement:
  name, required (list), optional (list), backend, forbidden_states
```

Exemplos:

- **Mayer**: geometry, basis ownership (ou AO→centro), `P_total`, `S`;
  `wavefunction` opcional; LIBRETA não necessária.
- **Hirshfeld** (futuro): wavefunction/density evaluator, atomic reference
  densities, grid, EDF; LIBRETA conforme método.
- **Orbital analysis** (futuro): coefficients + energies + occupations +
  representação.

---

## 6. Pipeline de normalização

```
1. IMPORT      recebe dados e registra proveniência bruta
2. NORMALIZE   unidades, ordenação de AO, convenções angulares, layouts
3. VALIDATE    invariantes geométricas, eletrônicas, de base e matemáticas
4. BUILD       constrói estruturas canônicas (shells, primitivas, AOs)
5. DERIVE      calcula S/P somente com rotinas autorizadas e registra
6. PREPARE     inicializa apenas as dependências da análise
7. EXECUTE     chama a rotina científica original
8. EXPORT      devolve NumPy e metadados, sem ponteiros retidos
```

### 6.1 Normalização de unidades

- Toda entrada declara `unit_source`.
- Conversão Å→Bohr no importador, com fator registrado em
  `Provenance.conversion_factor`.
- Fortran recebe sempre Bohr.

### 6.2 Normalização de ordenação de AO

1. Determinar `ao_order` de origem.
2. Construir `source_ao_index`.
3. Definir ordem canônica (centro → shell → componente).
4. Aplicar a mesma permutação a `S`, `P`, `C`, `basis_center`, `basis_type`.
5. Registrar `P_ao` e os hashes antes/depois.
6. Validar `basstart`/`basend` e contiguidade (ou exigir ordem canônica).

### 6.3 Convenções angulares

- Declarar `cartesian` vs `spherical` por shell.
- Para conversões 5D/6D, 7F/10F, 9G/15G, 11H/21H, usar as matrizes do
  Multiwfn (`conv5d6d`, `conv7f10f`, ...) ou conversões equivalentes
  validadas; registrar qual foi usada.
- Coeficientes e matrizes devem estar na mesma convenção.

---

## 7. Estados de prontidão e invalidação

Estados globais propostos (não confundir com a máquina de estados da engine):

```
EMPTY
  → GEOMETRY_READY
  → BASIS_READY
  → WAVEFUNCTION_READY
  → DENSITY_READY
  → INTEGRALS_READY (opcional)
  → ANALYSIS_READY
```

Regras:

- Estados não são uma sequência rígida; análises diferentes exigem
  subconjuntos diferentes.
- Alterar um dado fundamental invalida todos os derivados dependentes.
- `release_analysis_cache()` libera apenas resultados temporários;
  `release_molecular_state()` libera o sistema.
- Estado anterior nunca contamina o próximo (`large → small`, ECP→sem ECP,
  PBC→isolado, representação cartesiana→esférica).

---

## 8. Regras de validação

### 8.1 Erros fatais (FAIL)

- dimensões/forma/dtype incorretos;
- NaN/Inf;
- `nbasis < 1`, `nprims < nbasis`, `ncenter < 1`;
- `ΣZ − charge != nelectron`;
- `wfntype`/multiplicidade incompatíveis com o suporte da versão;
- `basis_center` fora de `[1,ncenter]`;
- blocos não contíguos sem permutação declarada;
- `P`/`S` não simétricas (tolerância fixa);
- `Tr(PS) != Ne` (RHF) fora da tolerância central;
- `PSP != 2P` (RHF) fora da tolerância central;
- `CᵀSC != I` quando C estiver disponível e a análise exigir;
- representação de coeficientes/matrizes inconsistente;
- ECP sem EDF quando a análise exige EDF;
- unidade ausente ou inválida.

### 8.2 Avisos (WARN, não bloqueiam por si)

- arredondamento de origem (ex.: 6–8 casas);
- `nindbasis < nbasis` por dependência linear;
- funções acima de `h` truncadas pelo leitor de origem;
- ECP sem EDF em análise que não usa EDF;
- `basis_type` legado ambíguo.

### 8.3 Tolerâncias

- Centralizadas em um único módulo/constante versionada
  (`ToleranceProfile`).
- Nenhuma execução pode sobrescrever tolerâncias.
- **Perfil do modelo 1.0 (estrito, não relaxado).** Valores conferidos
  contra `validation/wavefunction_audit.py` e o contrato 0.1.1:

| Verificação | Modelo 1.0 | Observação |
|---|---|---|
| `CᵀSC = I` | 1e−10 | `TOL_ORTHONORM` |
| `Tr(PS) = Ne` | 1e−8 | `TOL_ELECTRON_COUNT` |
| `PSP = 2P` (RHF) | 1e−6 · escala | `IDEM_TOL_FACTOR` |
| simetria de P/S | 1e−10 | `TOL_SYMMETRY` |
| positividade de S | autovalor mín. > 0 | sem tolerância arbitrária |
| QE × Multiwfn | 1e−6 | critério científico mantido |
| QE × ORCA | 1e−4 | pares do `property.txt` |

- **Tolerâncias legadas do motor 0.1.1** (preservadas por compatibilidade,
  não relaxadas pelo modelo novo): `Tr(PS)` em
  `max(1e−3, 1e−6·|Ne|)`, simetria 1e−9, `PSP` 1e−6·escala. O modelo 1.0
  aplica o perfil estrito **antes** de entregar dados ao motor; o motor
  legado continua aceitando seus limites históricos.
- O limite de impressão do ORCA (6 casas) não é usado como desculpa para
  afrouxar: o adaptador lê `sp.json`, que carrega precisão plena.

---

## 9. Compatibilidade retroativa com `MolecularSystem` 0.1.1

### 9.1 Mapeamento campo a campo

| Campo 0.1.1 | Tipo/forma atual | Destino em 1.0 | Conversão |
|---|---|---|---|
| `ncenter` | int | `atoms.z.shape[0]` / `ncenter` | nenhuma |
| `nbasis` | int | `basis.nbasis` | nenhuma |
| `nprims` | int | `basis.nprims` | nenhuma |
| `wfntype` | int (só 0) | `electronic.wfntype` | nenhuma |
| `atomic_numbers` | int32 `(N,)` | `atoms.z` | nenhuma |
| `coordinates` | float64 `(N,3)`, Bohr | `geometry.coordinates` + `unit_internal="bohr"` | nenhuma |
| `basis_center` | int32 `(nbasis,)`, 1-based | `basis.aos[i].center` | nenhuma |
| `basis_type` | int32 `(nbasis,)`, 0/1/2/3 (momento angular) | `basis.aos[i].legacy_basis_type` + `angular_type` | nenhuma; **não** é o `bastype` do Multiwfn (1=S, 2..4=p) |
| `density_total` | float64 `(nbasis,nbasis)` | `matrices.P_total` (`ao_current_basis`, `caller_supplied`) | nenhuma |
| `overlap` | float64 `(nbasis,nbasis)` | `matrices.S` (`ao_current_basis`) | nenhuma |
| `density_alpha` / `density_beta` | não usados (RHF) | `matrices.P_alpha/P_beta` | reservado |
| `charge` | int | `electronic.charge` | nenhuma |
| `multiplicity` | int | `electronic.multiplicity` | nenhuma |
| `nelectron` | int | `electronic.nelectron` | nenhuma |
| `source_format` / `source_program` | str | `provenance.*` | mapear |

Campos 1.0 ausentes em 0.1.1 (`shells`, `primitives`, `coefficients`,
`ecp`, `pbc`) ficam `None`/`present=False` e **não bloqueiam** Mayer.

### 9.2 Construtores de compatibilidade

```python
# Proposto — não implementado
MolecularSystemV1.from_legacy(ms: MolecularSystem) -> MolecularSystemV1
MolecularSystemV1.to_legacy(self) -> MolecularSystem
MolecularSystemV1.is_legacy_representable(self) -> bool
```

Regras:

- `from_legacy` copia arrays **sem conversão** (bit a bit), marca
  `provenance.source_program="python"` e `legacy=True`.
- `to_legacy` só é permitido se:
  - `wfntype == 0`, `multiplicity == 1`, Ne positivo e par;
  - `P_total` e `S` estão em `ao_current_basis` e são as matrizes ativas;
  - não há dependência de ECP/PBC/orbitais para o resultado;
  - a ordem de AO é a canônica/Mayer-compatível.
  Caso contrário, levanta erro explícito (`NotLegacyRepresentable`).
- Round-trip obrigatório: `to_legacy(from_legacy(ms))` reproduz
  `ms` campo a campo e array a array (bit a bit).

### 9.3 Compatibilidade com o núcleo Fortran atual

- `calcMayerbndord` depende apenas de: `ncenter`, `nbasis`, `wfntype`,
  `Ptot`, `Sbas`, `basstart`, `basend`.
- O modelo 1.0 fornece exatamente esses dados no `qe_state_prepare()`.
- Dados adicionais (shells, C, ECP) são **opcionais** para Mayer e não
  alteram o resultado. Isso é a demonstração de compatibilidade: o caminho
  legado é um subconjunto do 1.0.
- A P0 já provou que o caminho 0.1.1 reproduz bit a bit os resultados
  validados; o caminho 1.0 deve reproduzir os mesmos hashes quando alimentado
  com os mesmos dados.

### 9.4 Compatibilidade ABI

- As 17 funções `qe_*` atuais permanecem com assinatura e semântica
  inalteradas.
- O modelo ampliado usa funções novas (seção 10); um chamador 0.1.1 não
  precisa saber que elas existem.
- Versão da biblioteca: propor `0.2.0` para o modelo aditivo; `1.0.0` só
  quando o modelo estiver estável e validado.

### 9.5 Demonstração de compatibilidade (checklist)

A compatibilidade é demonstrável sem reimplementar o modelo:

1. **Totalidade do mapeamento:** todos os campos obrigatórios de
   `MolecularSystem` 0.1.1 aparecem na tabela 9.1 e têm destino único em
   1.0; campos 1.0 novos são opcionais para Mayer.
2. **Preservação bit a bit:** `from_legacy` não converte unidades, não
   reordena AOs e não altera dtypes; logo `array_equal` deve valer para
   `z`, `coordinates`, `basis_center`, `basis_type`, `P` e `S`.
3. **Preservação das validações 0.1.1:** RHF fechado, `mult=1`, Ne par,
   `Tr(PS)`, `PSP=2P`, simetrias, contiguidade e `nprims>=nbasis`
   continuam obrigatórias no caminho legado.
4. **Fecho de dependência do Mayer inalterado:** `calcMayerbndord` usa
   apenas `ncenter`, `nbasis`, `wfntype`, `Ptot`, `Sbas`, `basstart`,
   `basend` (verificado no fonte original). O modelo 1.0 fornece esses
   mesmos dados; nada mais é necessário para o Mayer.
5. **ABI preservada:** os 17 símbolos `qe_*` e suas assinaturas não mudam;
   as funções `qe_v1_*` são aditivas.
6. **Evidência experimental:** a P0 já reproduziu bit a bit os resultados
   de H₂/H₂O/C₆H₆ com o caminho 0.1.1; o caminho 1.0 deve reproduzir os
   mesmos hashes com os mesmos dados (teste MDM-060/063).
7. **Ausência de dependência oculta:** nenhum campo novo (shells,
   primitivas, C, ECP) é consultado pelo caminho Mayer 0.1.1; portanto
   sua ausência não altera o resultado.

---

## 10. Evolução proposta da ABI (aditiva)

Manter as funções atuais. Adicionar, em um novo header
`include/qe_multiwfn_v1.h` (ou seção versionada no header atual):

```c
/* Ciclo de vida do modelo (mantém qe_initialize/finalize atuais) */
int qe_v1_model_begin(int ncenter, int nbasis, int nprims, int wfntype);
int qe_v1_model_commit(void);      /* valida e prepara */
int qe_v1_model_release(void);

/* Átomos e geometria */
int qe_v1_set_atoms(int ncenter, const int *z, const double *coords_3n,
                    int unit);     /* unit: 0=bohr, 1=angstrom */

/* Base */
int qe_v1_set_shells(int nshell, const int *center, const int *l,
                     const int *prim_start, const int *prim_end,
                     const int *is_cartesian);
int qe_v1_set_primitives(int nprims, const int *center, const int *type,
                         const double *exponent, const double *coefficient,
                         const double *normalization);
int qe_v1_set_ao_map(int nbasis, const int *center, const int *shell_index,
                     const int *multiwfn_type, const int *angular_type,
                     const int *source_ao_index);

/* Função de onda (opcional para Mayer) */
int qe_v1_set_orbitals(int nmo, int coeff_repr, int coeff_layout,
                       const double *coefficients, const double *energies,
                       const double *occupations, const int *spin);
int qe_v1_set_density(int nbasis, int representation, const double *p_total,
                      const double *p_alpha, const double *p_beta);
int qe_v1_set_overlap(int nbasis, int representation, const double *s);

/* ECP/EDF e periodicidade (opcionais) */
int qe_v1_set_ecp_edf(int status, int nprims, const int *center,
                      const int *type, const double *exponent,
                      const double *coefficient, const int *core_per_atom,
                      int core_total);
int qe_v1_set_periodicity(int ifPBC, const int *directions,
                          const double *cell_vectors);

/* Proveniência (strings como buffer + tamanho) */
int qe_v1_set_provenance(const char *json_utf8, int length);

/* Consulta */
int qe_v1_get_readiness(int *flags);
int qe_v1_get_analysis_requirements(int analysis_id, int *bitmask);
```

Regras:

- Toda função valida estado, ponteiro, dimensão e representação.
- Nenhum ponteiro Python é retido.
- Erros retornam códigos existentes; novos códigos só se necessários.
- `qe_v1_*` não substitui `qe_*`; o caminho legado continua válido.

---

## 11. Memória e propriedade

- Python é dono dos arrays de entrada; Fortran copia para memória própria.
- Fortran é dono do estado global do Multiwfn.
- Resultados são escritos em buffers alocados pelo chamador.
- Nenhum ponteiro é retido após o retorno.
- Matrizes sempre em Fortran order na fronteira.
- Liberação limpa estado molecular e resultados; nunca deixa resíduos.
- Uma instância/sistema ativo por processo nesta fase.

---

## 12. Plano de testes independentes

Legenda: **U** = unitário, **I** = integração, **N** = negativo,
**R** = regressão, **S** = científico (referência externa/independente).

### 12.1 Schema e construtores

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-001 | U | Campos obrigatórios e tipos | Rejeita ausência/tipo errado |
| MDM-002 | U | Formas e dtypes | Rejeita shape/dtype incorretos |
| MDM-003 | U | Unidades Bohr/Å | Conversão explícita e fator registrado |
| MDM-004 | U | Enums inválidos | Rejeitados com mensagem |
| MDM-005 | U | `schema_version` | Exige `1.0.0` |

### 12.2 Compatibilidade retroativa

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-010 | U | `from_legacy` copia bit a bit | Arrays idênticos (`array_equal`) |
| MDM-011 | U | Round-trip `legacy→v1→legacy` | Todos os campos idênticos |
| MDM-012 | N | `to_legacy` com ECP/PBC/representação não compatível | Erro explícito |
| MDM-013 | R | Os 29 testes Python da biblioteca continuam passando | 29/29 |
| MDM-014 | R | Os 223 testes de validação continuam passando | 223/223 |
| MDM-015 | R | CTest 4/4 | 4/4 |

### 12.3 Base e ordenação

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-020 | U | `basis_center` 1-based e intervalos | Consistente com `ncenter` |
| MDM-021 | U | Contiguidade por centro | Aceita contíguo; rejeita intercalado sem permutação |
| MDM-022 | U | Ordem canônica + permutação | `P_ao` aplicada a S/P/C |
| MDM-023 | S | Invariância por permutação | Mayer idêntico após permutação consistente |
| MDM-024 | U | `nprims >= nbasis` | Aceita e preserva contadores |
| MDM-025 | U | Shell SP decomposta | Soma de primitivas/coeficientes coerente |
| MDM-026 | S | Cartesiano vs esférico | Conversão validada contra referência |

### 12.4 Função de onda e matrizes

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-030 | S | `CᵀSC = I` | ≤ 1e−5 (fixtures ORCA) |
| MDM-031 | S | `Tr(PS) = Ne` | ≤ 1e−8·escala |
| MDM-032 | S | `PSP = 2P` (RHF) | ≤ 1e−6·escala |
| MDM-033 | U | Simetria de S/P | ≤ 1e−8 |
| MDM-034 | U | Positividade de S | autovalor mín. > 0 |
| MDM-035 | N | Representação de C inconsistente | Rejeita |
| MDM-036 | N | `occupations` somam Ne errado | Rejeita |
| MDM-037 | N | NaN/Inf em qualquer matriz | Rejeita |
| MDM-038 | U | `P` derivada vs fornecida | Registra origem; não substitui silenciosamente |

### 12.5 ECP/EDF e periodicidade (modelo)

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-040 | N | ECP sem EDF em análise que exige | Rejeita com status |
| MDM-041 | N | EDF incompatível com átomos | Rejeita |
| MDM-042 | U | `Periodicity` default isolado | `ifPBC=0` |
| MDM-043 | N | Mayer com `ifPBC>0` | Rejeita (0.1.1) |

### 12.6 ABI aditiva e ciclo de vida

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-050 | I | Funções antigas inalteradas | 17 símbolos e semântica |
| MDM-051 | I | Novas funções em estado inválido | Erro controlado |
| MDM-052 | I | Ponteiro nulo / dimensão inválida | Erro controlado, processo vivo |
| MDM-053 | I | Cópia na entrada | Modificar array Python não altera Fortran |
| MDM-054 | I | `large→small`, ECP→sem ECP, PBC→isolado | Sem resíduos |
| MDM-055 | I | Repetição com a mesma molécula | Resultados independentes |

### 12.7 Validação científica (fixtures existentes)

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-060 | S | H₂/H₂O/C₆H₆ via modelo 1.0 | Mayer idêntico ao baseline P0 |
| MDM-061 | S | Comparação QE × Multiwfn | ≤ 1e−6 |
| MDM-062 | S | Comparação QE × ORCA | ≤ 1e−4 |
| MDM-063 | S | Hashes das matrizes | Iguais aos da P0 |
| MDM-064 | S | Benzeno: 6 C–C iguais, 6 C–H iguais | σ dentro do esperado |

### 12.8 Robustez

| ID | Tipo | Teste | Critério |
|---|---|---|---|
| MDM-070 | U | Fuzzing de shapes/dtypes/NaN | Sem crash; erro controlado |
| MDM-071 | U | JSON de proveniência inválido | Rejeita |
| MDM-072 | U | Unidade implícita | Rejeita |
| MDM-073 | U | `legacy_basis_type` ambíguo | Aviso explícito |

Critério global: nenhum teste pode afrouxar tolerâncias; ausência de dado
externa gera `INCOMPLETE`, não `PASS`.

---

## 13. Critérios de aceitação da especificação

A especificação estará pronta para implementação quando:

1. todos os campos tiverem tipo, forma, unidade, obrigatoriedade e invariantes;
2. o mapeamento 0.1.1 → 1.0 estiver completo e o round-trip especificado;
3. a ambiguidade de `basis_type` estiver resolvida (componente vs angular);
4. a política de ordem/permutação de AO estiver fechada;
5. o plano de testes cobrir compatibilidade, invariantes, negativos e
   validação científica;
6. a evolução da ABI for aditiva e as 17 funções atuais permanecerem;
7. não houver promessa de UHF/ROHF/PBC/ECP/leitores antes da validação.

---

## 14. Decisões abertas (requerem aprovação)

| # | Decisão | Recomendação |
|---|---|---|
| D1 | `basis_type`: componente vs momento angular | separar os dois; `legacy_basis_type` como alias |
| D2 | Ordem de AO: exigir canônica ou permutar | permutar com `P_ao` registrada |
| D3 | C em base contraída vs primitiva | permitir ambas com `representation` explícita |
| D4 | Onde derivar P | só com rotina autorizada (`genP`) ou adaptador; registrar origem |
| D5 | ECP/EDF no primeiro modelo | modelar, mas desabilitar execução até validar |
| D6 | PBC no primeiro modelo | modelar, mas rejeitar em Mayer 0.1.x |
| D7 | Versão da biblioteca | `0.2.0` para o modelo aditivo; `1.0.0` após validação |
| D8 | Formato de proveniência | JSON UTF-8 com hashes e comandos |

---

## 15. Roteiro de implementação proposto (após aprovação)

| Fase | Entrega | Gate |
|---|---|---|
| M1 | `MolecularSystemV1` + `from_legacy`/`to_legacy` em Python | MDM-001..015 |
| M2 | Normalização de unidades, AO e representação | MDM-020..026 |
| M3 | Shells/primitivas/AOs no Fortran + ABI v1 | MDM-050..055 |
| M4 | Função de onda + derivação controlada de P | MDM-030..038 |
| M5 | ECP/EDF e PBC no modelo (sem execução) | MDM-040..043 |
| M6 | Fluxo 1.0 completo com Mayer | MDM-060..064 |
| M7 | Revisão de docs, release e manifesto | todos |

Cada fase exige: código + docs + build limpo + testes + evidência +
limitações + `vendor/` intacto.

---

## 16. Registro de auditoria da especificação (Fase 1)

Auditoria crítica realizada em 2026-11-14, comparando esta especificação com
o código 0.1.1, com `vendor/Multiwfn_2026.11.3_src_Linux/` e com os
artefatos da P0.

| # | Achado | Correção aplicada |
|---|---|---|
| A1 | `basis_type` estava ambíguo: header `0=S,1=P,2=D`, adaptador `0/1/2/3` (angular), Multiwfn `1=S,2..4=p,...` (componente) | Seção 5.5.4 reescrita com a tabela real de `define.f90`/`fileIO.f90`; separação `multiwfn_type` × `angular_type`; `legacy_basis_type` só como alias |
| A2 | Tabela de tolerâncias não refletia o código (usava 1e−5 para CᵀSC e 1e−8 para simetria) | Seção 8.3 alinhada: 1e−10 / 1e−8 / 1e−6·escala / 1e−10; perfil legado documentado separadamente |
| A3 | Ordem canônica de AO não especificava o que fazer com a ordem de origem (p. ex. pz,px,py do ORCA) | Seção 5.5.5 fixa: blocos por centro, ordem de origem preservada, `source_ao_index` explícito; reordenação canônica opcional e futura |
| A4 | Compatibilidade 0.1.1 afirmada, mas sem checklist verificável | Seção 9.5 adicionada com 7 critérios objetivos (totalidade, bit a bit, validações, fecho Mayer, ABI, evidência P0, ausência de dependência oculta) |
| A5 | Risco de `to_legacy` aceitar estado não representável | Regras de 9.2 explicitam as condições e o erro `NotLegacyRepresentable` |
| A6 | Fecho de dependência do Mayer precisava de confirmação no fonte | Confirmado em `vendor/.../bondorder.f90`: apenas `Ptot`, `Sbas`, `basstart`, `basend`, `wfntype`, `ncenter`, `nbasis` (mais `Palpha/Pbeta` para spin) |
| A7 | Especificação poderia ser confundida com implementação | Cabeçalho e seção 1 deixam explícito: **ESPECIFICAÇÃO — NÃO IMPLEMENTADO** |

**Estado da Fase 1:** concluída. Nenhuma alteração no núcleo, na ABI ou nos
fontes `vendor/`.

---

## Apêndice A — Mapa de símbolos atuais → modelo 1.0

| Símbolo 0.1.1 (Fortran/Python) | Modelo 1.0 |
|---|---|
| `the_mol%atomic_numbers` / `atomic_numbers` | `atoms.z` |
| `the_mol%coordinates` | `geometry.coordinates` (Bohr) |
| `the_mol%basis_center` | `basis.aos[i].center` |
| `the_mol%basis_type` | `basis.aos[i].legacy_basis_type`/`angular_type` |
| `the_mol%density_total` / `Ptot` | `matrices.P_total` |
| `the_mol%overlap` / `Sbas` | `matrices.S` |
| `basstart` / `basend` | derivados de `basis.aos[i].center` |
| `ncenter`, `nbasis`, `nprims`, `nmo` | dimensões do modelo |
| `wfntype`, `nelec`, `naelec`, `nbelec` | `electronic.*` |
| `MOocc`, `MOene`, `MOtype`, `MOsym` | `wavefunction.orbitals.*` |
| `CO`, `CObasa`, `CObasb` | `wavefunction.coefficients*` + layout/representação |
| `b(:)`, `b_EDF`, `CO_EDF`, `nEDF*` | `basis.primitives`, `core_correction.edf_*` |
| `basshell`, `bascen`, `bastype`, `primstart/end` | `basis.shells` + `basis.aos` |
| `ifPBC`, `cellv1/2/3`, `Sbas_PBC` | `periodicity.*` |
| `imodwfn` | `electronic.imodwfn` |

---

## Apêndice B — Exemplo canônico (benzeno RHF/STO-3G)

- `ncenter = 12` (6 C + 6 H), `nbasis = 36`, `nprims = 108`, `Ne = 42`.
- C: 5 AOs cada (1s, 2s, 2pz, 2px, 2py) → 30 AOs.
- H: 1 AO cada (1s) → 6 AOs.
- Ordem (preservada da origem ORCA): `C0{1s,2s,1pz,1px,1py}`, ...,
  `C5{...}`, `H6{1s}`, ..., `H11{1s}`.
- `basis.aos[i].center` = 1..6 para os 30 primeiros, 7..12 para os 6 últimos.
- `basstart/basend` por átomo: C0 (1,5), ..., C5 (26,30), H6 (31,31), ...,
  H11 (36,36).
- Representação: cartesiana (STO-3G p: pz, px, py), sem funções d.
- `angular_type`: `0=s` para 1s/2s e para H 1s; `1=p` para as três p.
- `multiwfn_type` (código real do Multiwfn): `1` para s; `4` para pz (Z),
  `2` para px (X), `3` para py (Y).
- Ordem interna preservada como `pz,px,py`; `source_ao_index` registra a
  posição original. Uma reordenação canônica para `px,py,pz` é opcional e
  exigiria permutar S, P e C.
- `P_total` e `S`: `(36,36)`, `ao_current_basis`, simétricas.
- Mayer resultante: 6 C–C = 1.435205; 6 C–H = 0.971834; diagonal C ≈ 3.979387;
  diagonal H ≈ 0.996041 (reproduzido na P0).

---

## Apêndice C — Glossário

- **AO**: função de base atômica contraída.
- **GTF**: primitiva gaussiana.
- **Shell**: agrupamento de primitivas com mesmo centro e momento angular.
- **Contração**: combinação linear de primitivas.
- **Representação**: base contraída, primitivas, cartesiana ou esférica.
- **Layout**: orientação lógica de uma matriz (orbital×AO ou AO×orbital).
- **Readiness**: estado de prontidão de um componente/análise.
- **Proveniência**: origem, versão, arquivos, hashes e transformações.
