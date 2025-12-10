## Project Update

<!-- 
This PR adds or updates a Rocq/Coq project in Rocq Stats.
Please fill in the information below.
-->

**Action:** <!-- Check one -->
- [ ] Add new project
- [ ] Update existing project

**Project Name:** <!-- e.g., dsdp -->

**Repository:** <!-- e.g., https://github.com/user/repo.git -->

**Branch:** <!-- e.g., main -->

**Commit Hash:** <!-- Full 40-character SHA, e.g., abc123... -->

---

### YAML Configuration

<!-- 
Your PR should include a YAML file in the `projects/` directory.
Example configuration:

```yaml
name: myproject
title: "My Project Title"
description: "Brief description of the project"

source:
  repo: "https://github.com/user/repo.git"
  branch: "main"
  commit: "full-40-char-commit-hash"
  directories:
    - "src"

index: "path/to/README.md"  # Optional: Markdown file for overview page
```
-->

### Checklist

- [ ] YAML file is valid and placed in `projects/` directory
- [ ] Commit hash is a full 40-character SHA
- [ ] Commit exists in the specified repository and branch
- [ ] Repository is publicly accessible

---

*This PR will be automatically built and merged once the build succeeds.*

