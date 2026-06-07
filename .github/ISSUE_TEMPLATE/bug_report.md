---
name: Bug report
about: Something is broken or behaving unexpectedly
title: "[bug] "
labels: bug
assignees: satyamsoni2211
---
 
**Describe the bug**
A clear, concise description of what is wrong.
 
**Minimal reproducible example**
```python
import asyncio
import async_patcher
 
# smallest code that shows the problem
async def main():
    ...
 
asyncio.run(main())
```
 
**Expected behaviour**
What you expected to happen.
 
**Actual behaviour**
What actually happened. Include the full traceback if applicable.
 
**Environment**
- async-patcher version: <!-- e.g. 0.2.0 — run: python -c "import async_patcher; print(async_patcher.__version__)" -->
- Python version: <!-- e.g. 3.11.9 — run: python --version -->
- OS and version: <!-- e.g. Ubuntu 22.04, macOS 14.4, Windows 11 -->
**Additional context**
Any other information that might be relevant (executor config, pool size, signal handling overrides, etc.).