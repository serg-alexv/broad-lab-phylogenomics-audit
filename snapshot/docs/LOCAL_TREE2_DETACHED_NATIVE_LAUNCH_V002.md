# Nested-job persistence correction

All V001 source, claims and observations remain unchanged. The actual benign V001 child24220 lived for60 seconds and recorded its original launcher8972 absent. Its self-deadline receipt is not an externally observed process exit. The launcher held because the child remained in some job; that condition does not by itself show membership in the caller's kill-on-close job.

Microsoft documents that breakaway proceeds up a nested job chain until an ancestor forbids it. `QueryInformationJobObject(NULL,...)` describes the immediate current job. Its BasicProcessIdList includes that job and its descendant jobs. V002 therefore captures a complete caller-job census while retaining the child's real handle, observes the child still live, and accepts escape from that current job only when the child's PID is absent. Incomplete lists, missing caller PID, live-state uncertainty or retained membership remain held. This does not enumerate all ancestor jobs or prove their lifetime.

The V002 benign self-expiring fixture reports its own immediate job flags and complete PID census at startup and each heartbeat. Root must separately review those actual flags and later observations before approving a persistent controller. No fixture, AI or scientific worker was started by the source author. No job limits, process memberships, global settings or scheduler were modified.

The Root-admitted invocation and source/argv/role/executable/config gates remain as V001, with new immutable templates in `metadata/local_tree2_detached_launch_v002`. The fixture contract additionally binds its launcher-module dependency. Registration keeps exact birth identities and UNKNOWN child exit; subsequent owned exit observation or an ACK protocol remains required for fast workers. Existing scientific entry admissions, once claims, resource gates and ordinary closure requirements still apply.

The seven source-only fixtures execute pure extracted functions and mock handle cleanup, including nested-job exclusion and incomplete/retained census rejection. They start no processes.

Sources: [Nested Jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs), [QueryInformationJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-queryinformationjobobject), [BasicProcessIdList](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list).
