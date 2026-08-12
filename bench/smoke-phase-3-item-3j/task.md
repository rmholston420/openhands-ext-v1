Please do exactly the following three steps and then finish:

1. Create the file `/workspace/router-ok.txt` with the exact single-line
   contents `router-ok-3j`.
2. Read the file back with `cat /workspace/router-ok.txt` and confirm the
   contents.
3. Call the `finish` tool.

Do not do anything else. No preamble, no additional files, no additional
explanations. Trivial task; the point is to prove the router survives the
DockerWorkspace serialization boundary and lands on the local vLLM coder
endpoint, not `api.openai.com`.
