# QA successor candidate after S10/C-02

Inputs pinned: backend ff8571720ae1940034832bfbb69ddf9503f94c0e; applicant fcce7c1dad899e090fba17809ac904ed65833a97; council 87f094f42056a72eb92b102bf009577734686945; UI 554dcf68bba63695bf8657c7579508e2a24379dc.

Merged serially into governance/integration-20261021. Council-media conflict resolved to the council's updated full implementation (includes expected_version, S10 and C-02). Shell conflict retains all applicant scripts and the single existing shell-layout load. Applied applicant linked-petition-integration.patch with distinct case-qualified React keys. No newer unpublished UI/account files adopted.

Validation:208 frontend passed;604 PostgreSQL passed,2 skipped. Exact candidate still needs independent QA run3, hosted checks and combined browser acceptance. No main merge/deployment or production migrations.

## Disposable container recovery

Verified container ownership label a9460e5e2058447397206449a603a027 and full ID8b6398c3961cf0996b9ca187743df3ed5a5294197a87354043aa4bdf39629838. Normal Docker exec/remove failed. Inspected actual Docker Linux namespace, verified cgroup ownership before targeted INT/KILL and cgroup.kill. PostgreSQL child processes1975/2039/2059 remain uninterruptible D state with wait channel __vma_start_write. Root cause beyond that observed kernel wait is unproven. Shared Docker engine and WordPress/governance services were not restarted. Disposable container remains blocked; needs coordinated Docker Linux VM restart. Do not claim recovery completed or reuse this database for acceptance.
