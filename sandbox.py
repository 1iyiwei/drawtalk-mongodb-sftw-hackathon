from cwsandbox import AuthStrategy, Sandbox
with Sandbox.run(auth=AuthStrategy.WANDB, resources={"cpu": "1", "memory": "1Gi"}) as sandbox:
    print(sandbox.exec(["echo", "Hello from a sandbox!"]).result().stdout)