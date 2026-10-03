# Documentation format

Integration READMEs are the source of truth for the corresponding Lens integration pages in litellm-docs. Update the guide alongside its runnable example. The docs repository will import a reviewed snapshot from a specific source commit.

## README structure

Use one H1 matching the page title in [docs.json](docs.json), followed by a short description. Runnable integration guides use these H2 sections in order: Prerequisites, Configuration, Run an example, Verify the trace, How tracing works, and Troubleshooting. Under Run an example, use Simple agent and Agent swarm H3 sections; add Streaming only when supported. Additional adapter, validation, and reference sections may follow.

Coding agent pointer guides use Prerequisites, Setup, Verify the trace, and Troubleshooting. Keep installation details in the linked maintained guide.

Use plain Markdown with fenced code blocks and explicit language names. Keep Docusaurus imports, JSX, components, and front matter out of these READMEs. Use relative links to repository files so they work on GitHub. Document the working directory for every command and explain how to configure the environment. Leave gateway and model values configurable.

## Publication manifest

The manifest has `schema_version: 1` and an ordered `pages` array. Each entry contains:

| Field | Meaning |
| --- | --- |
| `source` | Repository-relative path to the authoritative README |
| `slug` | Stable path relative to the Lens docs instance, beginning with `/` |
| `title` | Page title matching the README’s H1 |
| `description` | Plain-text description for the published page |
| `category` | Sidebar group: `integrations` or `coding-agents` |

The array order controls publication order within each category. Sources and slugs must be unique. Add a manifest entry when adding a published integration. Shared libraries, the recorder, and contributor documentation are outside this manifest.

For example, `deepagents/README.md` with slug `/integrations/deepagents` is intended to publish at `https://docs.litellm.ai/lens/integrations/deepagents`. A source folder rename does not require changing its slug.

## Importer contract

The upcoming litellm-docs importer should read this manifest and all source files from the same pinned commit. Generate each complete page body from its README, then add Docusaurus metadata for the title, description, slug, sidebar label, source edit URL, and standard Markdown parsing (`mdx.format: md`). Record the imported commit in generated provenance. The edit URL should open the authoritative README on the source repository’s main branch.

Resolve links with a Markdown parser, including reference links and images. Links to other published READMEs should point to their Lens routes. Links to code, configuration, shared documentation, and other unpublished files should point to GitHub at the imported commit. Preserve query strings and fragments. Copy relative image assets into the docs output and rewrite their URLs. Current published LiteLLM docs URLs should remain usable until the docs migration maps them to the new routes.

Preserve code blocks and tested version requirements. Apply any site-only metadata or compatibility transformations in the importer. The source guides must remain readable and runnable from GitHub.

Fail the sync on missing sources, duplicate slugs, unresolved repository links, or failed Markdown conversion. Generate and validate all outputs before replacing the previous snapshot. Commit generated pages through a docs PR; the normal website build should read that snapshot without fetching this repository.
