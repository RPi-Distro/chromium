# deb_pre_gen.py

import os
import re
import shutil
import sys

mode = os.environ.get("DEB_CR_PRE_GEN")
arch = os.environ.get("DEB_CR_PRE_GEN_ARCH")

if not mode:
  #mode = "prefer"
  mode = "require"  # more strict
if mode not in ("disable", "generate", "prefer", "require"):
  sys.exit("error: DEB_CR_PRE_GEN has invalid value \"{mode}\"")
if not arch:
  arch = "arch"

debug = True
pre_gen_dir = "pre-gen"
record_outputs_always = False

################################################################

prev_output_key, prev_indep = None, None

def xform_path(path, section=None, prefix="../../"):
  assert ".." not in path, f"path = \"{path}\""
  assert "//" not in path, f"path = \"{path}\""
  assert "/./" not in path, f"path = \"{path}\""
  assert not path.startswith("/"), f"path = \"{path}\""
  if path.startswith("host_for_rust_host_build_tools/"):
    # This one comes up in cross builds, redirect to the usual location
    path = "default" + path[4:]
  if not section:
    section = arch
  return f"{prefix}{pre_gen_dir}/{section}/{path}"

# Gets a list of the output files, not the file contents
def get_output_files(output_key):
  meta_file = xform_path(output_key, "meta") + ".OUTPUTS"
  try:
    with open(meta_file, "r") as f:
      return f.read().split()
  except FileNotFoundError:
    if record_outputs_always:
      sys.exit(f"error: cannot find {meta_file}")
    return [output_key]

# Records a list of the output files, not the file contents
def record_output_files(output_files):
  if len(output_files) == 1 and not record_outputs_always:
    return
  output_key = output_files[0]
  meta_file = xform_path(output_key, "meta", "") + ".OUTPUTS"
  os.makedirs(os.path.dirname(meta_file), exist_ok=True)
  with open(meta_file, "w") as f:
    print("\n".join(output_files), file=f)

# Called at the beginning of the generation script, after the arguments
# have been parsed but before any files are generated
def before(output_key, indep=False):
  global prev_output_key, prev_indep
  prev_output_key, prev_indep = output_key, indep
  if not output_key:
    return False
  if mode in ("disable", "generate"):
    return False
  if not os.path.exists(f"../../{pre_gen_dir}"):
    return False
  if os.path.exists(f"../../{pre_gen_dir}/DISABLED"):
    return False
  if arch == "arch":
    assert os.path.exists(f"../../{pre_gen_dir}/arch"), "Need symlink to actual arch"
  section = "indep" if indep else None
  output_files = get_output_files(output_key)
  if not all([os.path.exists(xform_path(out, section)) for out in output_files]):
    if mode == "require":
      sys.exit("error: missing pre-generated output")
    else:
      print("warning: missing pre-generated output", file=sys.stderr)
    return False
  print("note: using pre-generated output", file=sys.stderr)
  for out in output_files:
    saved = xform_path(out, section)
    shutil.copyfile(saved, out)
    if debug: print(f"  <- {saved[6:]}", file=sys.stderr)
  return True

def is_system_dep(dep):
  return "/usr/include/"   in dep \
    or   "/usr/lib/llvm-"  in dep \
    or   "/lib/gcc-cross/" in dep

# Called at the end of the generation script, after the output files
# have been successfully generated
def after():
  output_key, indep = prev_output_key, prev_indep
  if not output_key:
    return
  if mode != "generate":
    return
  if not os.path.exists(f"../../{pre_gen_dir}"):
    return
  if os.path.exists(f"../../{pre_gen_dir}/DISABLE"):
    return
  print("note: saving generated output", file=sys.stderr)
  section = "indep" if indep else None
  for out in get_output_files(output_key):
    saved = xform_path(out, section)
    os.makedirs(os.path.dirname(saved), exist_ok=True)
    shutil.copyfile(out, saved)
    if debug: print(f"  -> {saved[6:]}", file=sys.stderr)
    if out.endswith(".d"):
      # Ninja dependency file -- filter out system paths from saved copy
      with open(saved, "r") as f:
        dep_line = f.read().strip()
      assert "\n" not in dep_line  # assuming only one line
      deps = dep_line.split()
      assert deps[0].endswith(":")
      deps_filt = [d for d in deps if not is_system_dep(d)]
      with open(saved, "w") as f:
        f.write(" ".join(deps_filt))

################################################################

# Called from third_party/node/node.py
def node_wrap(cmd_parts, run_node_fn, check_only=False):
  output_key = None
  src = "../../third_party/devtools-frontend/src"

  if cmd_parts[0] == f"{src}/front_end/Images/generate-css-vars.js":
    out_dir = cmd_parts[2]
    output_key = f"{out_dir}/Images.prebundle.js"
  elif cmd_parts[0] == f"{src}/front_end/core/i18n/collect-ui-strings.js":
    if check_only: return True
    out_pos = cmd_parts.index("--output-directory") + 1
    out_dir = cmd_parts[out_pos]
    output_key = f"{out_dir}/en-US.json"
  elif cmd_parts[0] == f"{src}/front_end/core/i18n/generate-locales-js.js":
    if check_only: return True
    out_pos = cmd_parts.index("--target-gen-dir") + 1
    out_dir = cmd_parts[out_pos]
    output_key = f"{out_dir}/locales.js"
  elif cmd_parts[0] == f"{src}/front_end/panels/timeline/enable-easter-egg.js":
    out_dir = cmd_parts[1]
    output_key = f"{out_dir}/EasterEgg.js"
  elif cmd_parts[0] == f"{src}/node_modules/rollup3/dist/bin/rollup":
    if check_only: return True
    out_pos = cmd_parts.index("--file") + 1
    output_key = cmd_parts[out_pos]
  elif cmd_parts[0] == f"{src}/scripts/build/esbuild.js":
    output_key = cmd_parts[2]
  elif cmd_parts[0] == f"{src}/scripts/build/generate_css_js_files.js":
    out_dir = cmd_parts[5]
    file_list = cmd_parts[6].split(",")
    first_file = file_list[0]
    if first_file.startswith("./"):
      first_file = first_file[2:]
    output_key = f"{out_dir}/{first_file}.js"
  elif cmd_parts[0] == f"{src}/scripts/build/generate_devtools_json.mjs":
    output_key = cmd_parts[1]
  elif cmd_parts[0] == f"{src}/scripts/build/ninja/generate-declaration.js":
    if check_only: return True
    out_dir, entry_name = cmd_parts[1:3]
    assert entry_name.endswith(".js") or entry_name.endswith(".ts")
    output_key = f"{out_dir}/{entry_name[:-3]}.d.ts"
  elif cmd_parts[0] == f"{src}/scripts/build/ninja/generate-tsconfig.js":
    output_key = cmd_parts[1]
  elif not check_only:
    print(f"note: unhandled script: {cmd_parts[0]}", file=sys.stderr)

  if check_only:
    return bool(output_key)
  if before(output_key, indep=True):
    return
  run_node_fn(cmd_parts)
  after()

def is_handled_node_script(script_path):
  fake_cmd_parts = [script_path] + ["x"] * 10
  return node_wrap(fake_cmd_parts, None, True)

################################################################

handled_python_arch_scripts = set([
  "../../build/rust/gni_impl/run_bindgen.py",
])

handled_python_indep_scripts = set([
  "../../third_party/dawn/tools/generate-sources-gn.py",  # golang
  "../../third_party/devtools-frontend/src/scripts/build/build_inspector_overlay.py",
  "../../third_party/devtools-frontend/src/scripts/build/typescript/ts_library.py",
  "../../tools/typescript/ts_library.py",  # fails with Node.js v12
  "../../ui/webui/resources/tools/bundle_js.py",  # fails with Node.js v12
  "../../ui/webui/resources/tools/minify_js.py",  # fails with Node.js v12
])

# Don't make these, as they depend on files we've excluded
bad_outputs = set([
  "gen/third_party/devtools-frontend/src/front_end/models/trace/lantern/core/unittests-tsconfig.json",
  "gen/third_party/devtools-frontend/src/front_end/models/trace/lantern/metrics/unittests-tsconfig.json",
  "gen/third_party/devtools-frontend/src/front_end/models/trace/lantern/simulation/unittests-tsconfig.json",
  "gen/third_party/devtools-frontend/src/frontend_indexer_tsconfig-tsconfig.json",
])

# Parses toolchain.ninja files to determine the set of output files that
# are generated by the scripts we want to handle
def find_generated_files(indep=False):
  relevant_rules = set()
  generated_files = set()
  for root, _, files in os.walk("out/Release"):
    for fname in files:
      if fname != "toolchain.ninja":
        continue
      current_rule = None
      with open(f"{root}/{fname}", "r") as f:
        for line in f:
          # Rule definitions
          m = re.match(r"^rule (\S+)", line)
          if m:
            current_rule = m.group(1)
            continue
          elif not line.startswith("  "):
            current_rule = None
          if current_rule:
            m = re.match(r"^  command = python3? \.\./\.\./third_party/node/node\.py (\S+)", line)
            if m and indep:
              script = m.group(1)
              if is_handled_node_script(script):
                relevant_rules.add(current_rule)
              continue
            m = re.match(r"^  command = python3? \.\./\.\./tools/protoc_wrapper/protoc_wrapper\.py ", line)
            if m and indep and "--protoc-gen-ts" in line:
              relevant_rules.add(current_rule)
              continue
            m = re.match(r"^  command = python3? (\S+) ", line)
            if m:
              script = m.group(1)
              if (not indep and script in handled_python_arch_scripts) or \
                     (indep and script in handled_python_indep_scripts):
                relevant_rules.add(current_rule)
              continue
          # Target definitions
          m = re.match(r"^build (.+): (__[-\w]+__rule)\b", line)
          if m:
            outputs_flat = m.group(1)
            rule = m.group(2)
            if rule in relevant_rules:
              outputs_flat = outputs_flat.replace("$:", ":")
              assert "$" not in outputs_flat, "Drat, need to process more escape sequences"
              outputs = outputs_flat.split()
              if "/chrome/test/data/" in outputs[0]:
                continue
              if bad_outputs.intersection(outputs):
                continue
              record_output_files(outputs)
              generated_files.add(outputs[0])
  return sorted(generated_files), sorted(relevant_rules)

if __name__ == "__main__":
  # Note: This script is invoked directly only from
  # debian/scripts/init-pre-gen.sh
  op = sys.argv[1]
  if op == "make-lists":
    files_arch, rules_arch = find_generated_files()
    print(f"Found {len(files_arch)} generated arch file targets.")
    files_indep, rules_indep = find_generated_files(True)
    print(f"Found {len(files_indep)} generated indep file targets.")
    with open(f"{pre_gen_dir}/FILES_ARCH", "w") as f:
      print("\n".join(files_arch), file=f)
    with open(f"{pre_gen_dir}/RULES_ARCH.tmp", "w") as f:
      print("\n".join(rules_arch), file=f)
    with open(f"{pre_gen_dir}/FILES_INDEP", "w") as f:
      print("\n".join(files_indep), file=f)

# end deb_pre_gen.py
