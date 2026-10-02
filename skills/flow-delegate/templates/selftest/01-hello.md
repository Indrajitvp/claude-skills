# 01 selftest: add a hello module
tag: TEST
check: --backend
allow: automation/hello_selftest.py
verify: python automation/hello_selftest.py
expect: hello selftest
---
Create automation/hello_selftest.py. It must print exactly: hello selftest
