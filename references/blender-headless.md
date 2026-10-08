# Blender setup and headless execution

## Contents

- Install Blender
- Locate the executable
- Verify the runtime
- Run a script headlessly
- Pass script arguments
- Reproducible command pattern
- Troubleshooting

## Install Blender

Download a stable or Long-Term Support build from the official [Blender download page](https://www.blender.org/download/). Pin one tested Blender version for the project and record it in the art contract or build report; different Blender releases can change Python APIs, modifiers, import/export behavior, and triangulation.

Blender includes its own Python runtime and the `bpy`, `bmesh`, and `mathutils` modules used by this skill. Run modeling scripts through the Blender executable, not through the system `python` command.

Platform options:

- **Windows:** use the installer or portable ZIP. A portable folder is convenient for pinning a project version and does not require administrator rights.
- **macOS:** install the official application bundle. Keep separately named application bundles when a project must retain an older tested version.
- **Linux:** use the official archive or a distribution package when its version matches the project contract.

Do not commit the Blender application into the skill repository. If a project keeps a portable toolchain locally, place it under an ignored directory such as `tools/blender/` and document how contributors obtain the matching build.

## Locate the executable

Prefer this resolution order:

1. an explicit command-line option or project configuration value;
2. a project-local portable executable in an ignored tools directory;
3. `blender` found on `PATH`;
4. a known system installation selected by the user.

Typical executable forms are:

```text
Windows: tools/blender/blender.exe
macOS:   /Applications/Blender.app/Contents/MacOS/Blender
Linux:   blender
```

Paths vary by version and install choice. Do not hardcode a developer-specific home directory in reusable scripts.

## Verify the runtime

From the repository root, run the executable with `--version`:

```bash
blender --version
```

If Blender is not on `PATH`, use its explicit path. PowerShell example:

```powershell
$blender = "tools/blender/blender.exe"
& $blender --version
```

Stop if the executable is missing or the version differs from the project's pinned major/minor release. Do not silently fall back to another Blender installation.

## Run a script headlessly

Use background mode for reproducible UI-free builds:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python examples/stylized-crate.py -- \
  --out build/stylized-crate.glb
```

PowerShell, using an explicit executable:

```powershell
$blender = "tools/blender/blender.exe"
& $blender --background --factory-startup --python-exit-code 1 `
  --python examples/stylized-crate.py -- `
  --out build/stylized-crate.glb
```

The important flags are:

- `--background`: run without the interactive UI;
- `--factory-startup`: ignore the user's startup scene and settings that could change a build;
- `--python-exit-code 1`: return a failing process code when the Python script raises an exception;
- `--python <file>`: execute the builder script;
- `--`: stop Blender argument parsing and pass the remaining values to the script through `sys.argv`.

Blender processes command-line arguments in order. Keep the script and its own arguments in the shown order.

## Pass script arguments

A Blender script can parse only the values after `--`:

```python
import sys

script_args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
```

Use `argparse` on `script_args` so commands are self-documenting and invalid options fail clearly.

## Reproducible command pattern

For every pipeline command:

1. run from a documented working directory;
2. start from `--factory-startup` or call `bpy.ops.wm.read_factory_settings(use_empty=True)`;
3. accept explicit input and output paths;
4. create output directories intentionally;
5. print a concise machine-readable report;
6. fail with a nonzero exit code on validation or export errors;
7. record the Blender version in the build report.

Do not rely on whichever `.blend` file, render engine, object selection, mode, or active collection a user happened to leave open.

## Troubleshooting

- **`blender` is not recognized / command not found:** use the full executable path or add its folder to `PATH`.
- **`ModuleNotFoundError: bpy`:** the script was launched with system Python; launch it through Blender.
- **Script errors but the command reports success:** include `--python-exit-code 1`.
- **Arguments are ignored:** place the script's arguments after the standalone `--`.
- **Unexpected default cube, camera, or light:** use `--factory-startup` and clear the scene in the script.
- **Works in the UI but not headlessly:** remove UI-context-dependent operators where possible, set the active object and mode explicitly, and test with the exact background command used by automation.
- **Wrong Blender version runs:** resolve and print the executable path and `--version`; do not depend on an ambiguous `PATH` entry.
- **Render or bake differs across machines:** pin Blender, render engine, device choice, color management, samples, and relevant add-ons in project configuration.

Blender's official documentation covers [downloads](https://www.blender.org/download/) and [command-line arguments](https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html).
