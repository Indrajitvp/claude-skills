# 02 selftest: add a second hello module
tag: TEST
check: --backend
allow: automation/hello_selftest2.py
verify: python automation/hello_selftest2.py
expect: hello selftest2
---
Create automation/hello_selftest2.py. It must print exactly: hello selftest2
