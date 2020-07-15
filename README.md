# Longhorn Test cases
Various test cases for longhorn

## Manual Test Cases
Some scenarios are hard to test using the automation tests and are documented as manual test cases that need to be verified before release.
The manual test cases are accessible [here](https://longhorn.github.io/longhorn-tests/manual/).

The manual test case pages can be edited under `website/content/manual/`.

To categorize tests, place them in sub-directories under `website/content/manual/`.
These sub-directories must contain a file named `_index.md` with the following:
```markdown
---
title: Name of Test Category
---
Optional description regarding the test category.
```

Each test page should be structured as such:
```markdown
---
title: Name of Test Case
---
Description of the test case.
```

Both of these files can contain Markdown in the title and page body.

To preview the website changes, you will need to [install Hugo](http://localhost:1313/).
Once Hugo is installed, run the following:
```shell
hugo server --buildDrafts --buildFuture
```
The site will be accessible at http://localhost:1313.
