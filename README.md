# Technical Documentation: Scripts & Notebooks

The workflow is organized into modular Python scripts 

---

## 1. Knowledge Graph 

**Files:** `config.py`, `database.py`, `loaders.py`, `KG_creation.py`


### config.py
- Centralizes environmental variables and file paths.
- Maps local JSON files for both 2014 and 2024 SRD editions.
- Includes manually integrated data (Subclasses, Spells, Feats) to fill gaps in standard APIs.

### database.py
- Implements the `Neo4jConnector` class.
- Manages Cypher queries to:
  - Create nodes
  - Create relationships 
- Enforces uniqueness constraints based on SRD version.

### loaders.py
- Contains the `DnDKnowledgeGraph` class.
- Maps raw JSON data into graph structures.
- Includes specialized logic for:

**Subclass Unlocks**
- Maps level-based unlocks (e.g., Level 1 for Clerics, Level 3 for Fighters).

**Spellcasting Mechanics**
- Distinguishes between:
  - "Known" casters
  - "Prepared" casters

**Equipment & Proficiencies**
- Links classes to starting gear and skills.

### KG_creation.py
- Execution script that initializes the graph.
- Applies constraints and runs the full loading pipeline.
- Generates:
  - **1,880 nodes**
  - **3,179 relationships**

---

## 2. Model Training & Inference

**File:** `Inf_&Training.ipynb`


### Fine-Tuning Pipeline
- Uses LoRA adapters for training (Qwen, Llama).
- Based on Alpaca/Chat templates.
- Includes merging adapters into 16-bit models 

### Constrained Inference
- Implements a RAG-enhanced inference loop:
  - Queries Neo4j graph
  - Injects "Rules Context" into prompts
- Uses Structured Outputs (Guided Decoding) to:
  - Restrict model choices
  - Enforce valid outputs:
    - Positive Candidates
    - Negative Distractors

---

## 3. Validation & Evaluation Pipeline

**File:** `validation.ipynb`


### Unified Fallback Parser
- extraction engine:
  - Attempts native JSON parsing
  - Falls back to Regex-based Markdown parsing

### Logical Validation Engine

**Mutation Check**
- Verifies that input data was not altered (no hallucinated changes).

**KG-Backed Rule Check**
- Cross-references generated entities (Subclass, Spell, Skill)
- Validates against Neo4j rules

### Master Reporting
- Aggregates results across models:
  - Baseline vs Fine-Tuned
- Produces:
  - Success rates
  - Partial successes
  - Failure types:
    - Stagnation
    - Loops
    - Mutations

---

## Directory Structure
/DnD_Project_Data
├── config.py / database.py / loaders.py 
├── KG_creation.py 
├── Inf_&Training.ipynb 
├── validation.ipynb 
├── processed_dataset/ 
└── inference_results/ 

## Output Data: