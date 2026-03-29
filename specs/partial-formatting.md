To support partial formatting across DOCX, PPTX, and XLSX without adding a new tool, I would adjust the existing mutation model so that formatting can target subranges inside an existing text-bearing object, instead of only whole objects or pre-existing runs.

Core Change

The main refactor is this: treat “text object” and “text segments within that object” as part of the same editing contract.

Today the surface is roughly split like this:

create_object creates high-level objects.
update_object replaces object text.
style_inline styles an already-addressable inline object, such as a run.
That works only when the inline segmentation already exists. To support partial formatting well, the system needs to be able to derive or rewrite that segmentation during normal update/style operations.

So I would refactor the existing tools around a shared text-fragment model:

Any text-bearing object can be updated either as plain text or as structured segments.
Any inline style operation can target either:
an existing inline object locator, or
a character range within a parent text object.
Format adapters become responsible for translating that range/segment intent into native structures:
DOCX runs
PPTX runs inside a text frame paragraph
XLSX rich text runs inside a cell
That lets you keep the current tools, but make them more capable.

What To Change

For update_object:
Expand it so it can accept either:

text: replace the whole object text, as today
segments: replace the text object with a list of text spans plus optional inline style metadata
optionally range + text or range + style for in-place partial edits
This makes update_object the main structural text-editing primitive.

Why this matters:

If the caller already knows the final formatting layout, it can send segments directly.
The adapter can rebuild native runs from those segments in one deterministic write.
This avoids needing a separate “split run” tool.
For style_inline:
Keep the tool, but broaden its target model. Right now it is effectively “style this existing run.” It should become “style inline content in this object,” where the target can be:

an inline object locator, as today
a parent text object locator plus character range
optionally a substring match selector, though range is cleaner and safer
Then the adapter does:

read the current inline fragments
split at the requested boundaries
apply style to the affected fragments
merge adjacent fragments with identical formatting
write back the normalized fragment list
That would make style_inline the equivalent of what Word/PowerPoint/Excel do interactively.

For create_object:
I would not make it create runs directly. That would leak too much format-specific structure into normal authoring. Keep it responsible for block-level creation. The useful refactor is:

allow optional segments on text-bearing created objects
if segments is present, the adapter creates the object with native inline fragments from the start
if only text is present, current behavior stays unchanged
That keeps the tool count stable and preserves backward compatibility.

Format-Specific Implications

DOCX:
The DOCX adapter already understands paragraphs and runs conceptually. The main missing behavior is rebuilding paragraph runs from segment data, and splitting runs by character range during style_inline.

Needed changes:

Extend paragraph update/write paths so they can rewrite a paragraph as multiple runs, not just one text blob.
Preserve paragraph-level properties and paragraph style while rebuilding runs.
Preserve non-text paragraph features where possible, or explicitly reject unsupported cases.
Normalize adjacent runs with identical formatting to avoid run explosion.
The current paragraph insertion path in docx_adapter.py:320 is the main place that would need to stop assuming one inserted run per paragraph.

PPTX:
PowerPoint text is more hierarchical:

text frame
paragraph
runs
For PPTX, partial formatting support should be applied within a paragraph of a text shape.

Needed changes:

Define which PPTX object locators are valid parent text targets for partial formatting.
Let style_inline target a paragraph or shape plus a character range.
In the adapter, flatten the visible text of the paragraph to a logical string, map range offsets back to runs, split runs as needed, then apply formatting.
Preserve paragraph-level properties and shape-level structure.
This is very similar to DOCX, just one level deeper.

XLSX:
This is the hardest one, because partial formatting in spreadsheets only makes sense for rich text cells, and support is less universal.

Needed changes:

Decide that partial inline formatting is only supported for string cells.
Represent a cell as either:
plain string
rich text segments
Extend update_object and style_inline so a cell can be rewritten as rich text when needed.
Reject partial formatting for formulas, numbers, booleans, and maybe merged-cell edge cases unless explicitly supported.
Keep style_block for cell-wide formatting and use style_inline only for rich text content.
The crucial architectural point is: XLSX partial formatting should not force every cell into a rich text model. Only promote a cell to rich text when partial inline formatting is requested.

Shared Adapter Refactor

The cleanest design is to introduce one internal cross-format abstraction, something like:

InlineFragment
text
style
TextContainerSnapshot
full text
fragments
parent metadata
adapter operations:
read text container as fragments
write text container from fragments
apply style to fragment range
normalize fragments
Then each adapter implements those operations in its own native way.

That gives you one editing algorithm across all three formats:

Resolve target text container.
Convert native structure to normalized fragments.
Apply range-based transformation.
Normalize fragments.
Rebuild native structure.
That is much better than scattering range logic separately into DOCX, PPTX, and XLSX code paths.

Tool-Surface Refactor

If you want to avoid adding another tool, I would reshape responsibilities like this:

create_object

creates block/container objects
optionally accepts segments for initial inline formatting
update_object

still supports whole-text replacement
additionally supports segment-based replacement for text-bearing objects
style_inline

still supports styling an existing inline object locator
additionally supports parent object + character range targeting
adapter performs run splitting internally
That is enough. No new tool needed.

Important Constraints

A few rules should be explicit:

Ranges must be based on the logical visible text of the target object, not raw XML/native indices.
Adapters must normalize fragments after every write.
Unsupported partial formatting cases should fail clearly, not silently degrade.
Existing callers using plain text updates should continue to work unchanged.
The current locator model should remain valid, but partial formatting should not depend on callers first creating run locators manually.
Recommended Direction

If I were advising the refactor, I would prioritize in this order:

Extend style_inline to accept parent-object range targeting.
Extend update_object to accept segments.
Refactor adapters around a shared fragment model.
Keep create_object block-oriented, with optional segments only where natural.
That gives you:

partial formatting on existing content
faithful creation of mixed-format paragraphs/cells/text blocks
no new tool
a cleaner, more uniform editing model
The real design goal is to stop treating inline structure as something that must already exist in the document. Instead, existing tools should be able to synthesize and rewrite that structure on demand.