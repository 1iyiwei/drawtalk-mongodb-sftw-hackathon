# Coreweave Forge <noreply@coreweave.com>

Serverless Sandboxes are now on your account. A sandbox is an isolated environment for running untrusted code: agent tool calls, RL environments, eval harnesses. There's no cluster to provision, and you're billed only while a sandbox runs.

You get **$30 in credits each month for your first six months**, covering CPU, GPU, and memory. Credits reset monthly and don't roll over. Sandboxes pause once a month's credits run out; turning on pay-as-you-go resumes them and charges only for usage beyond your credits.

Run your first sandbox in under a minute:

```
pip install "cwsandbox[wandb]"
wandb login
```

```
from cwsandbox import AuthStrategy, Sandbox
with Sandbox.run(auth=AuthStrategy.WANDB, resources={"cpu": "1", "memory": "1Gi"}) as sandbox:
    print(sandbox.exec(["echo", "Hello from a sandbox!"]).result().stdout)
```

For the TypeScript SDK, REST API, GPUs, and snapshots, see the [getting started guide](https://docs.coreweave.com/products/sandboxes/get-started).

Happy building,
The Coreweave Forge Team