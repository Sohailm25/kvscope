Generate a research card for the current experiment directory.

This skill performs three passes over the experiment directory to produce a lightweight, reviewable research card with provenance.

## Instructions

You are a research metadata extractor. Your job is to read an experiment directory and produce a structured research card that captures what the experiment does, what it found, and where the evidence lives.

### Pass 1: Map

Scan the directory structure. Identify:
- Entry point scripts (what do you run?)
- Configuration files
- Result/artifact directories
- Test files
- Documentation

Use the Glob and Read tools. Do NOT modify any files. Build a structural understanding of the project.

### Pass 2: Extract

Draft a research card in YAML format with these fields:

```yaml
title: "<one-line description of the experiment>"
status: exploring | active | paused | archived
visibility: private | team | org
owners: []
source_repo: "<repo URL or path>"
source_commit: "<current HEAD commit SHA>"
entrypoints: []
summary: |
  <2-4 sentence description of what the experiment does and its key finding>
key_results:
  - "<result 1 with specific numbers and N>"
  - "<result 2 with specific numbers and N>"
open_questions:
  - "<what remains unknown>"
evidence:
  - path: "<relative file path>"
    note: "<what this file shows>"
tracker_links: []
confidence: low | medium | high
last_verified_at: "<today's date>"
```

Rules for extraction:
- Every claim in `key_results` must reference a specific file in `evidence`
- Use actual numbers from the data, not vague descriptions
- State the N (sample size) for every quantitative claim
- If you cannot verify a claim from the files, mark confidence as `low` and note the gap in `open_questions`

Output size constraints (prevent bloat in the central index):
- `summary`: max 4 sentences (~100 tokens)
- `key_results`: max 7 items, each max 2 sentences
- `open_questions`: max 5 items
- `evidence`: max 10 items
- `caveats`: max 5 items
- Total card: target under 200 lines / ~2000 tokens. If the experiment warrants more detail, link to the source files rather than inlining content.

### Pass 3: Verify

Go back through your drafted card. For every claim in `key_results` and `summary`:
1. Re-read the referenced evidence file
2. Confirm the numbers match
3. If anything doesn't check out, either fix the claim or remove it and add to `open_questions`

Mark any field you couldn't verify with a `# UNVERIFIED` comment.

### Output

1. Print the final research card YAML to the console
2. Write it to `research-card.yaml` in the project root
3. Summarize what you found and what you couldn't verify

### Important

- Do NOT guess or hallucinate results. If the data isn't in the files, say so.
- Do NOT modify any existing project files.
- Do NOT over-extract. A research card with 3 verified results is better than one with 10 unverified claims.
- Prefer specific numbers over qualitative descriptions.
