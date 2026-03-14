# Headmaster Deployment Protocol (Resuscitation Health App)

At cycle close:
1. rerun verification from a clean local runtime state
2. stop any project-local listeners started during the cycle
3. push only after the local cycle is accepted
4. check remote CI/deploy health before reporting completion
5. refresh continuity state if the project uses Exit

Generated: 2026-03-13
