# Contributing

Report the result you expected and the result you got. Include the agent, OS, Python version and runtime doctor output with personal paths removed. Do not attach private footage, credentials or customer screens. A small synthetic reproduction is best.

For code changes, install the pinned requirements, run `python -m unittest discover -s tests -v`, and describe the visible output and any changed limitations. Shared workflow rules belong in SKILL.md; conditional guidance belongs in references; deterministic media operations belong in scripts.

Keep Persian and English guidance consistent. New behavior needs an appropriate behavioral check, using generated media when possible. Do not mark a host workflow or OS as supported solely because its files install.

Submit a pull request. MIT covers original contributions; identify any third-party material and its license.
