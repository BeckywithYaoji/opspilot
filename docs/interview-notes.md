# Interview notes

1. **Why OpsPilot?** It makes the gap between model recommendations and observable tool execution concrete in a bounded IT demo.
2. **Agent or workflow?** The model selects tools dynamically from observations; Python enforces loop limits and permission boundaries.
3. **Why MCP?** It isolates tool implementation in a discoverable process boundary and exercises structured schemas and failure handling.
4. **Agentic versus traditional RAG?** Retrieval is a tool choice, not a mandatory first step. The benchmark has positive and negative retrieval cases.
5. **Session versus incident memory?** Redis resolves conversational references; Qdrant incidents supply historical evidence across sessions. Current observations still matter.
6. **Goal verifier?** It creates an explicit stopping decision from task evidence, helping limit over-execution but not guaranteeing semantic correctness.
7. **How was over-execution studied?** Trajectories reveal calls after the first goal-satisfied step. Historical iterations added snapshot/completion checks; V6 reports the frozen implementation without retuning.
8. **Why deterministic guardrails?** Execution permission should be inspectable and independent of persuasive model text. Current policy requires approval for restart.
9. **Cross-HTTP resume?** Redis persists approval ID, frozen arguments and trace ID. The current endpoint runs the frozen tool in a new MCP process, not the suspended LangGraph checkpoint. This limitation matters.
10. **Replay prevention?** Resolved status rejects sequential repeats. Atomic concurrent claiming is not implemented; do not claim exactly-once production safety.
11. **Observability design?** Separate trajectory and local component spans. V6 uses independent wall-clock request timing because legacy span sums are not E2E duration. Langfuse is not actually integrated.
12. **Avoid cherry-picking?** Fixed 36-case dataset, one saved attempt per case, separate deterministic safety layer, raw failures retained. No prompt tuning.
13. **Largest limitations?** Mock operations, coarse task-success rubric, incomplete provider-call tracing and incomplete approval continuation. The four incident-query tasks failed to verify current state.
14. **What would production require?** Authentication, scoped authorization, atomic/durable approval consumption, real checkpoint continuation, production tool isolation, audit storage and concurrent trace safety. These are not implemented in v1.0.

Use only the V6 final report for numerical claims. Explain the safety test scope and the failure cases before suggesting production applicability.
