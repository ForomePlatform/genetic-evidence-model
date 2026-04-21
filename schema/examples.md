# SHACL shape examples with commentary

This file is a reading companion for
[`genetic_evidence.shacl.ttl`](genetic_evidence.shacl.ttl), the
SHACL shapes file of the Genetic Evidence Model. It walks through the
shapes in order of increasing complexity and explains the idioms used,
in particular how SHACL expresses *conditional* required properties.

The shapes below use these prefixes:

```turtle
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix gem:  <https://w3id.org/genetic-evidence-model/> .
```

`gem:` is the Genetic Evidence Model namespace. Its long form resolves
via [w3id.org](https://w3id.org/genetic-evidence-model/) to this
repository.


## How to read these shapes

Every SHACL shape in this file declares itself with
`a sh:NodeShape` and attaches to `gem:GeneticEvidence` via
`sh:targetClass`. The validator applies each shape to every
`gem:GeneticEvidence` instance it encounters. A shape is *satisfied*
for a given instance if the conditions it declares all hold; it is
*violated* if any do not, and a violation produces a diagnostic whose
text comes from the `sh:message` field.

Two SHACL mechanisms are used:

- **`sh:property [ sh:path ... ; sh:minCount ... ; sh:class ... ]`**
  constrains a property directly: it says "the value along this path
  must exist (minCount), must come from this class (sh:class)". This
  is enough for ordinary required properties.

- **`sh:sparql [ sh:select """ ... """ ]`** expresses constraints
  that cannot be reduced to a single-property rule, for example
  "required only when another property takes a certain value". The
  convention is to write a `SELECT` that returns every instance which
  *violates* the condition; the validator reports those instances.
  The `FILTER NOT EXISTS` idiom inside the `WHERE` clause is how
  SHACL expresses "and does not have this other property".

The four examples below show the progression.


## 1. Ordinary required properties: the base shape

`gem:GeneticEvidenceShape` is the entry-point shape. It declares four
properties that every `gem:GeneticEvidence` instance must have,
regardless of its other values. These are the model's core dimensions
whose presence is non-negotiable.

```turtle
gem:GeneticEvidenceShape
  a sh:NodeShape ;
  sh:targetClass gem:GeneticEvidence ;

  sh:property [
    sh:path gem:knowledgeDomain ;
    sh:minCount 1 ;
    sh:class gem:KnowledgeDomain ;
    sh:message "GeneticEvidence must declare at least one knowledge_domain from the enumeration."
  ] ;

  sh:property [
    sh:path gem:method ;
    sh:minCount 1 ;
    sh:class gem:Method ;
    sh:message "GeneticEvidence must declare at least one method from the enumeration."
  ] ;

  sh:property [
    sh:path gem:targetType ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:class gem:TargetType ;
    sh:message "GeneticEvidence must declare exactly one target_type."
  ] ;

  sh:property [
    sh:path gem:phenotypeScale ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:class gem:PhenotypeScale ;
    sh:message "GeneticEvidence must declare exactly one phenotype_scale."
  ] .
```

**Reading the shape.** Each of the four `sh:property` blocks says: "a
value must exist along this path; the value must be from this class;
if these conditions fail, emit this message." `sh:minCount 1` alone
means "at least one value" (the multi-valued case, used here for
`knowledgeDomain` and `method`). `sh:minCount 1 ; sh:maxCount 1`
means "exactly one value" (the single-valued case, used here for
`targetType` and `phenotypeScale`).

Two other always-required dimensions from the model, `Resolution` and
`Credibility`, are not yet shaped here; they will be added as the
corpus grows and the enumerations for them settle.


## 2. A simple conditional: `variant_ascertainment`

The `variant_ascertainment` dimension is required only when
`target_type` is `VARIANT`. When the target is a gene, interval,
transcript, or segment, variant ascertainment is undefined and need
not be populated. SHACL expresses this with an `sh:sparql` constraint
whose `WHERE` clause is a single triple pattern.

```turtle
gem:VariantAscertainmentConditionalShape
  a sh:NodeShape ;
  sh:targetClass gem:GeneticEvidence ;
  sh:sparql [
    sh:message "When target_type is VARIANT, variant_ascertainment is required." ;
    sh:select """
      PREFIX gem: <https://w3id.org/genetic-evidence-model/>
      SELECT $this
      WHERE {
        $this gem:targetType gem:VARIANT .
        FILTER NOT EXISTS { $this gem:variantAscertainment ?v }
      }
    """
  ] .
```

**Reading the SELECT.** The query finds every `gem:GeneticEvidence`
instance (bound to `$this`) whose `targetType` is `VARIANT` **and**
which has no `variantAscertainment` value. These are the instances
that violate the rule.

There is also a separate shape, `gem:VariantAscertainmentShape`, that
validates the *values* of `variantAscertainment` against the
enumeration (`OBSERVED_IN_CASES`, `OBSERVED_IN_CONTROLS`,
`FROM_DATABASE`, `SYNTHETIC`) whenever the dimension is populated.
Required-presence and valid-value are orthogonal; both shapes are
needed.


## 3. A conjunction conditional: `mode_of_inheritance`

`mode_of_inheritance` is required when the Knowledge Domain contains
`HUMAN_GENETICS` **and** the Target Type is `GENE`. This is a
conjunction over two different axes of classification, and in SHACL
the conjunction is simply two triple patterns in the same `WHERE`
clause (implicit AND).

```turtle
gem:ModeOfInheritanceConditionalShape
  a sh:NodeShape ;
  sh:targetClass gem:GeneticEvidence ;
  sh:sparql [
    sh:message "When knowledge_domain contains HUMAN_GENETICS and target_type is GENE, mode_of_inheritance is required." ;
    sh:select """
      PREFIX gem: <https://w3id.org/genetic-evidence-model/>
      SELECT $this
      WHERE {
        $this gem:knowledgeDomain gem:HUMAN_GENETICS .
        $this gem:targetType      gem:GENE .
        FILTER NOT EXISTS { $this gem:modeOfInheritance ?moi }
      }
    """
  ] .
```

**Compact form.** In the paper we show only the `sh:sparql` body, as:

```turtle
sh:sparql [ sh:select """
  SELECT $this WHERE {
    $this gem:knowledgeDomain gem:HUMAN_GENETICS .
    $this gem:targetType      gem:GENE .
    FILTER NOT EXISTS { $this gem:modeOfInheritance ?m }
  }""" ] .
```

The outer `NodeShape` wrapper, the `sh:targetClass`, and the
`sh:message` are the same for every shape in this file and are
elided from the paper for space.

**On the conjunction.** Note that `gem:knowledgeDomain` is a
multi-valued property (a `gem:GeneticEvidence` may declare
`[HUMAN_GENETICS, POPULATION_GENETICS]` jointly), so the triple
`$this gem:knowledgeDomain gem:HUMAN_GENETICS` matches as long as
`HUMAN_GENETICS` is *among* the declared values. SPARQL's pattern
match handles this naturally; no explicit containment operator is
needed.


## 4. A cross-axis disjunction: `organism`

`organism` is required when the Method contains
`IN_VIVO_EXPERIMENT` **or** the Knowledge Domain contains
`MODEL_ORGANISM`. This is a disjunction expressed with SPARQL
`UNION`, and the two disjuncts refer to different axes (`method` vs
`knowledgeDomain`).

```turtle
gem:OrganismConditionalShape
  a sh:NodeShape ;
  sh:targetClass gem:GeneticEvidence ;
  sh:sparql [
    sh:message "When method contains IN_VIVO_EXPERIMENT or knowledge_domain contains MODEL_ORGANISM, organism is required." ;
    sh:select """
      PREFIX gem: <https://w3id.org/genetic-evidence-model/>
      SELECT $this
      WHERE {
        { $this gem:method gem:IN_VIVO_EXPERIMENT . }
        UNION
        { $this gem:knowledgeDomain gem:MODEL_ORGANISM . }
        FILTER NOT EXISTS { $this gem:organism ?org }
      }
    """
  ] .
```

**Compact form.** The paper's listing of this shape is:

```turtle
sh:sparql [ sh:select """
  SELECT $this WHERE {
    { $this gem:method          gem:IN_VIVO_EXPERIMENT . }
    UNION
    { $this gem:knowledgeDomain gem:MODEL_ORGANISM . }
    FILTER NOT EXISTS { $this gem:organism ?o }
  }""" ] .
```

**On the disjunction.** The `UNION` operator expresses "either
branch may match". Either a Method-axis condition fires the
requirement (a `STATISTICAL_GENETICS` paper that includes an in-vivo
experiment) or a Knowledge-Domain-axis condition does (a
`MODEL_ORGANISM` paper that reports only in-vitro assays). Either
way, an `organism` value must be populated.


## Why `FILTER NOT EXISTS` rather than a positive rule?

SHACL's SPARQL-based constraints report violations, not successes.
The `SELECT` query is written to return exactly the set of instances
that fail validation. For a required-when-condition rule, that set is
"instances that match the activation condition and lack the required
property", which in SPARQL is expressed most directly with
`FILTER NOT EXISTS` inside the `WHERE` clause.

The alternative (writing a positive rule: "for every instance matching
the condition, check that the required property exists") is not how
SHACL works. SHACL runs the query, looks at what comes back, and
treats the returned bindings as violations. If the query returns the
empty set, the shape is satisfied for every instance.


## Completeness and future shapes

The following shapes are still needed and are listed as `TODOs` at
the end of `genetic_evidence.shacl.ttl`:

- Enumerate `measurement_target` values for the Gene Function
  dimension.
- Enumerate `organism` values (the shape above requires *some*
  value but does not constrain it to an enumeration).
- A shape for `assertion.source_span` requiring both `page` and
  `key_phrase` fields to be populated.
- Shapes for the reviewer-flag fields (`reviewer_query`,
  `reviewer_suggestion`, `reviewer_disagreement`,
  `ai_uncertainty`, `ai_assumption`).

These will be added as the annotation corpus grows and the shapes'
enumerations stabilise. The file is intended to be incremental; a
shape is added when at least one annotation in the corpus would be
meaningfully validated by it.


## Candidate extensions not yet reflected in SHACL

The following candidate extensions are recorded in
[`dimensions.md`](dimensions.md) and in the relevant annotation
files, but have not yet been promoted to first-class dimensions and
therefore have no SHACL shape:

- `SCORE`, `WHOLE_GENOME_AGGREGATE`, `target_composition`, extended
  `measurement_target` for epidemiological quantities, structured
  cohort descriptor, and `derived_artifact` flag (CE-IN1 through
  CE-IN6, from the Inouye 2018 annotation).
- `direction_of_effect` (CE-DU1, from the Duerr 2006 annotation).
- `INTERACTION` and `COMPLEX` values for Target Type (from the
  Jossin 2017 annotation; commented as candidates in the SHACL
  file).

Promotion under the two-papers rule (see §5 of the paper) will move
these into the shapes file as they are confirmed by additional
annotations.
