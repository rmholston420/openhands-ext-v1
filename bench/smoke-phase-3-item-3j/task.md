Please do exactly the following three steps and then finish:

1. Create the file `/workspace/router-ok.txt` with the exact single-line
   contents `router-ok-3j`.
2. Read the file back with `cat /workspace/router-ok.txt` and confirm the
   contents.
3. Call the `finish` tool.

Do not do anything else. No preamble, no additional files, no additional
explanations. Trivial task; the point is to prove the router survives the
ADR-0034 serialization boundary (`agent.model_dump → LLM.model_validate`)
and lands on the local vLLM coder endpoint, not `api.openai.com`. Per
ADR-0036, this smoke runs under LocalWorkspace; container-side ADR-0034
verification is deferred to sign-off item 3.k. The `run.sh` harness rewrites
the `/workspace/router-ok.txt` path above to the per-run temp workspace dir
before sending the task; the router-lands-on-vLLM assertion is the load-
bearing verdict criterion here, not the workspace transport.
