You are acting as a senior API and tool-surface architect. Your task is not to write code. Your task is to perform a deep architectural analysis and produce a concrete simplification proposal for an Office-document MCP/tooling system.

Context

We have Office-agent style system that currently exposes two broad capability families:

1. Search and retrieval over document contents
2. Direct access to, and modification of, document structures through document-library APIs

The supported document families are:
- PowerPoint via python-pptx
- Word via python-docx
- Excel via openpyxl

The system now contains both higher-level and lower-level interfaces.

Current capability shape

A. Search model
The system supports indexing and search over documents.
There are at least two search modes:
- textual / lexical / indexed search
- vector / embedding-based semantic search

A search hit can be resolved back to a concrete location in the document model, for example:
- presentation -> slide -> shape/text box
- document -> paragraph/table/run
- workbook -> sheet -> row/cell/range

The current unit of indexing/search may vary by document type and implementation detail, but for now it is effectively hardwired in the model.

B. Access model
The system also exposes direct object-level access to the underlying document structures through the Python libraries.
This includes reading, modifying, and creating document elements through the APIs of python-pptx, python-docx, and openpyxl.


Verify all these capabilities as implemented in /src/office-agent and specified in /openspec.


The goal

I want a full architectural analysis of how to simplify the API and the exposed tool set as much as possible without losing functional power.

The simplified design must preserve all core use cases:
- indexing documents
- textual search
- vector search
- resolving hits to exact document locations
- reading document structures and content
- modifying existing items
- creating new items
- supporting the natural object models of PowerPoint, Word, and Excel

Important constraints

- Do not write implementation code
- Do not propose vague abstractions without consequences
- Do not default to “just expose everything”
- Do not remove important power merely for elegance
- Do not assume that all three libraries can be flattened into one naïve universal model
- Be critical about over-abstraction
- Distinguish clearly between what should be unified and what should remain document-type-specific
- Assume this is intended for an MCP-style tool surface consumed by an AI agent
- Assume the AI agent benefits from a smaller, clearer, more orthogonal tool set
- Assume some use cases require high-level semantic operations and some require low-level precise access

Your task

Produce a rigorous analysis and proposal that answers the following.

1. Problem framing
Explain the architectural tension between:
- search/retrieval as a discovery mechanism
- object access/modification as an operational mechanism

Clarify why these are related but not identical concerns.

2. Current conceptual model
Infer and describe the likely current model from the context above.
Identify where duplication, fragmentation, accidental complexity, leaky abstraction, or awkward tool proliferation are likely to exist.

3. Design principles
Define a compact set of design principles for simplification.
Examples of the kind of principles I expect:
- orthogonality
- stable identifiers and addressability
- separation of discovery from mutation
- capability layering
- minimal but expressive primitives
- explicit type-specific escape hatches

Do not just list principles. Explain how each principle affects the API/tool design.

4. Search model analysis
Analyze how the search side should be modeled.

Specifically address:
- Whether textual and vector search should be separate top-level tools or two modes of one search abstraction
- Whether indexing should be explicit or implicit
- Whether reindexing, incremental indexing, and index metadata should be first-class concepts
- What the “search unit” should be conceptually
- Whether the search unit should be standardized across formats or allowed to differ by format
- How a search hit should reference the original document location
- Whether search results should return snippets, structured locations, opaque handles, stable IDs, or all of these
- How filters/scopes should work across documents, document types, and substructures

5. Access model analysis
Analyze how the direct access side should be modeled.

Specifically address:
- Whether access should revolve around object paths, typed handles, stable IDs, or library-shaped operations
- Whether reads and writes should be separated
- Whether mutation should be generic or strongly type-specific
- How to expose create/update/delete operations without reproducing the entire raw Python library surface in a chaotic way
- How to support both high-level operations and low-level escape hatches
- How to preserve power while still dramatically simplifying the agent-facing surface

6. Unified conceptual architecture
Propose a target conceptual architecture for the whole system.

At minimum, address whether the system should be organized around concepts such as:
- document
- node / element / object
- location / address
- search index
- hit / match
- selection / scope
- mutation command
- typed capability adapters

Be explicit. Show the concepts and the relations between them.

7. Tool-surface proposal
Propose a simplified MCP/tool API surface.

Do not give code. Instead, define the tool families and their semantics.

For each proposed tool or tool family, provide:
- name
- purpose
- required inputs
- important optional inputs
- output shape
- when an agent should use it
- what it replaces from the likely current design

I want you to be opinionated here. Reduce the number of tools aggressively, but not foolishly.

8. Unification boundary
State clearly what should be unified across Word, PowerPoint, and Excel, and what should remain format-specific.

For example, discuss whether these should be unified:
- addressing
- search semantics
- metadata access
- content extraction
- mutation verbs
- structural traversal

And discuss where format-specific APIs are justified or necessary.

9. Search-to-access bridge
This is crucial.

Explain how a search hit should transition into an access or mutation operation.
The bridging model must be explicit and robust.

For example, discuss:
- stable location descriptors
- resolvable handles
- path-based references
- typed references
- provenance of search hits
- how an agent can safely go from “find me the relevant text box” to “edit that text box”

10. Layering strategy
Propose a layered model, for example:
- discovery layer
- structural inspection layer
- mutation layer
- advanced/raw layer

But do not assume these exact names.
Explain what belongs in each layer and why.

11. Naming strategy
Propose a naming system for tools and entities that is:
- compact
- regular
- agent-friendly
- unsurprising
- extensible

Show a few examples of good and bad naming.

12. Trade-offs and rejected alternatives
Discuss the main alternative simplification strategies and why you reject them.
Examples:
- one giant universal CRUD API
- complete exposure of raw library methods
- separate fully independent APIs per file type
- search-only with no structural bridge
- ultra-high-level only with no low-level access

13. Recommended target design
Give your final recommendation.

This section must include:
- the preferred conceptual model
- the preferred simplification strategy
- the recommended balance between generic and document-specific tools
- the minimum core tool set
- the advanced escape-hatch model
- the key invariants the API should guarantee

14. Migration guidance
Assume an existing richer, messier tool surface already exists.
Explain how to migrate toward the simplified model without breaking capability.

Include:
- what to deprecate first
- what compatibility shims may exist
- what old concepts should map to new concepts
- what documentation the agent would need

15. Deliverable format
Structure your answer in the following sections:

A. Executive architectural judgment  
B. Core problem decomposition  
C. Simplification principles  
D. Search model proposal  
E. Access and mutation model proposal  
F. Unified tool-surface proposal  
G. Format-specific boundaries  
H. Recommended end-state architecture  
I. Migration path  
J. Final concise recommendation

Additional instructions

- Be concrete and analytical
- Challenge hidden assumptions
- Prefer small sets of strong primitives over broad vague surfaces
- Where useful, propose 2 or 3 candidate models and then choose one
- Call out ambiguities or risks explicitly
- Do not write code
- Do not generate pseudocode unless strictly needed to explain a model
- Treat this as an API architecture review for a serious long-lived system
- Optimize for clarity, agent usability, maintainability, and expressive power

Write your analysis and proposal in a clear, structured format, using headings and subheadings as needed to organize the content. The file should be stored as a markdown file with appropriate formatting for readability. The name should reflect the content, for example: `tool-simplification-analysis.md`.