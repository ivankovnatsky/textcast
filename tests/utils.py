import asyncio
from click.testing import CliRunner

class AsyncCliRunner(CliRunner):
    def __init__(self):
        super().__init__()
        
    async def invoke(self, cli, args=None, **kwargs):
        def invoke_sync():
            return CliRunner.invoke(self, cli, args, **kwargs)
        return await asyncio.get_event_loop().run_in_executor(None, invoke_sync)
