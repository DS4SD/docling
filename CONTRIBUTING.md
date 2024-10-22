## Contributing In General
Our project welcomes external contributions. If you have an itch, please feel
free to scratch it.

To contribute code or documentation, please submit a [pull request](https://github.com/DS4SD/docling/pulls).

A good way to familiarize yourself with the codebase and contribution process is
to look for and tackle low-hanging fruit in the [issue tracker](https://github.com/DS4SD/docling/issues).
Before embarking on a more ambitious contribution, please quickly [get in touch](#communication) with us.

For general questions or support requests, please refer to the [discussion section](https://github.com/DS4SD/docling/discussions).

**Note: We appreciate your effort and want to avoid situations where a contribution
requires extensive rework (by you or by us), sits in the backlog for a long time, or
cannot be accepted at all!**

### Proposing New Features

If you would like to implement a new feature, please [raise an issue](https://github.com/DS4SD/docling/issues)
before sending a pull request so the feature can be discussed. This is to avoid
you spending valuable time working on a feature that the project developers
are not interested in accepting into the codebase.

### Fixing Bugs

If you would like to fix a bug, please [raise an issue](https://github.com/DS4SD/docling/issues) before sending a
pull request so it can be tracked.

### Merge Approval

The project maintainers use LGTM (Looks Good To Me) in comments on the code
review to indicate acceptance. A change requires LGTMs from two of the
maintainers of each component affected.

For a list of the maintainers, see the [MAINTAINERS.md](MAINTAINERS.md) page.


## Legal

Each source file must include a license header for the MIT
Software. Using the SPDX format is the simplest approach,
e.g.

```
/*
Copyright IBM Inc. All rights reserved.

SPDX-License-Identifier: MIT
*/
```

We have tried to make it as easy as possible to make contributions. This
applies to how we handle the legal aspects of contribution. We use the
same approach - the [Developer's Certificate of Origin 1.1 (DCO)](https://github.com/hyperledger/fabric/blob/master/docs/source/DCO1.1.txt) - that the Linux® Kernel [community](https://elinux.org/Developer_Certificate_Of_Origin)
uses to manage code contributions.

We simply ask that when submitting a patch for review, the developer
must include a sign-off statement in the commit message.

Here is an example Signed-off-by line, which indicates that the
submitter accepts the DCO:

```
Signed-off-by: John Doe <john.doe@example.com>
```

You can include this automatically when you commit a change to your
local git repository using the following command:

```
git commit -s
```


## Communication

Please feel free to connect with us using the [discussion section](https://github.com/DS4SD/docling/discussions).



## Developing

### Usage of Poetry

We use Poetry to manage dependencies.

#### Installation

To install Poetry, follow the documentation here: https://python-poetry.org/docs/master/#installing-with-the-official-installer

1. Install Poetry globally on your machine:
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```
    The installation script will print the installation bin folder `POETRY_BIN` which you need in the next steps.

2. Make sure Poetry is in your `$PATH`:
    - for `zsh`:
        ```sh
        echo 'export PATH="POETRY_BIN:$PATH"' >> ~/.zshrc
        ```
    - for `bash`:
        ```sh
        echo 'export PATH="POETRY_BIN:$PATH"' >> ~/.bashrc
        ```

3. The official guidelines linked above include useful details on configuring autocomplete for most shell environments, e.g., Bash and Zsh.

#### Create a Virtual Environment and Install Dependencies

To activate the Virtual Environment, run:

```bash
poetry shell
```

This will spawn a shell with the Virtual Environment activated. If the Virtual Environment doesn't exist, Poetry will create one for you. Then, to install dependencies, run:

```bash
poetry install
```

**(Advanced) Use a Specific Python Version**

If you need to work with a specific (older) version of Python, run:

```bash
poetry env use $(which python3.8)
```

This creates a Virtual Environment with Python 3.8. For other versions, replace `$(which python3.8)` with the path to the interpreter (e.g., `/usr/bin/python3.8`) or use `$(which pythonX.Y)`.

#### Add a New Dependency

```bash
poetry add NAME
```

## Coding Style Guidelines

We use the following tools to enforce code style:

- iSort, to sort imports
- Black, to format code

We run a series of checks on the codebase on every commit using `pre-commit`. To install the hooks, run:

```bash
pre-commit install
```

To run the checks on-demand, run:

```bash
pre-commit run --all-files
```

Note: Checks like `Black` and `isort` will "fail" if they modify files. This is because `pre-commit` doesn't like to see files modified by its hooks. In these cases, `git add` the modified files and `git commit` again.

## Documentation

We use [MkDocs](https://www.mkdocs.org/) to write documentation.

To run the documentation server, run:

```bash
mkdocs serve
```

The server will be available at [http://localhost:8000](http://localhost:8000).

### Pushing Documentation to GitHub Pages

Run the following:

```bash
mkdocs gh-deploy
```