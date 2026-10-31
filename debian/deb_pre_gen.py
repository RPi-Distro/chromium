# deb_pre_gen.py
#
# Main implementation of the pre-gen source framework, which allows Debian
# stable builds of Chromium to obtain generated source files where the
# generation process requires build-dependency versions that are only
# available in unstable
#

import argparse
import filecmp
import fileinput
import hashlib
import os
import re
import shutil
import subprocess
import sys

# Mode values:
#  * check: Check to see if the handled command runs correctly,
#      otherwise do the same as "enable".
#  * disable: Just run the handled command, nothing more.
#  * enable: Use the output file(s) in the pre-gen directory instead of
#      running the handled command; if files are missing, then error out.
#  * generate: Run the handled command, and populate the pre-gen directory
#      with its outputs. Used only from d/scripts/init-pre-gen.sh .

mode = os.environ.get("DEB_CR_PRE_GEN")
arch = os.environ.get("DEB_CR_PRE_GEN_ARCH")

if not mode:
  mode = "enable"
if mode not in ("check", "disable", "enable", "generate"):
  sys.exit("error: DEB_CR_PRE_GEN has invalid value \"{mode}\"")
if not arch:
  arch = "arch"

debug = False
pre_gen_dir = "pre-gen"

################################################################

src = "third_party/devtools-frontend/src"

handled_node_scripts = set([
  "third_party/blink/public/devtools_protocol/scripts/protocol_dts_generator.ts",
  f"{src}/front_end/core/i18n/collect-ui-strings.js",
  f"{src}/front_end/core/i18n/generate-locales-js.js",
  f"{src}/node_modules/rollup3/dist/bin/rollup",
  f"{src}/scripts/build/build_ai_skills.mjs",
  f"{src}/scripts/build/esbuild.js",
  f"{src}/scripts/build/generate_css_js_files.js",
  f"{src}/scripts/build/generate_devtools_json.mjs",
  f"{src}/scripts/build/generate_html_entrypoint.js",
  f"{src}/scripts/build/optimize_images.js",
])

handled_python_arch_scripts = set([
  "build/rust/gni_impl/run_bindgen.py",
])

handled_python_indep_scripts = set([
  "third_party/chromium-bidi/tools/build/scripts/rollup.py",  # needs rollup >= 2.78
  "third_party/dawn/tools/generate-sources-gn.py",  # golang
  "third_party/devtools-frontend/src/scripts/build/run_with_restat.py",  # tsc
  "third_party/devtools-frontend/src/scripts/build/run_with_stamp.py",  # tsc
  "tools/polymer/css_to_wrapper.py",  # fails with Node.js v12
  "tools/protoc_wrapper/protoc_wrapper.py",  # --protoc-gen-ts -> tsc
  "tools/typescript/ts_library.py",  # fails with Node.js v12
  "ui/webui/resources/tools/bundle_js.py",  # fails with Node.js v12
  "ui/webui/resources/tools/minify_js.py",  # fails with Node.js v12
])

# Brute-force measure to find outputs that can't be made due to missing
# prerequisites in the source tree:
#
#  $ cat pre-gen/FILES_INDEP | xargs -n 1 -P $(nproc) sh -c 'ninja -C out/Release -n $1 >/dev/null 2>&1 || echo bad: $1' --
#
# (Reducing the size of the input list helps)

bad_outputs = set([
  # Don't make these, as they depend on files we've excluded
  "gen/third_party/devtools-frontend/src/front_end/models/trace/lantern/core/foundation_unittests_node_typecheck.stamp",
  "gen/third_party/devtools-frontend/src/front_end/models/trace/lantern/metrics/foundation_unittests_node_typecheck.stamp",
  "gen/third_party/devtools-frontend/src/front_end/models/trace/lantern/simulation/foundation_unittests_node_typecheck.stamp",
])

# Return True iff the command should be handled by pre-gen
# (can also do other checks/assertions here)
def examine_command(command, outputs):
  assert command[0].endswith(".py"), "Expecting a Python script"
  script = os.path.basename(command[0])

  # Expand any response-file args
  command_expanded = command[:1]
  for arg in command[1:]:
    if arg.startswith("@") and arg.endswith(".rsp"):
      with open(arg[1:], "r") as f:
        rsp_args = f.read().split()
      command_expanded.extend(rsp_args)
    else:
      command_expanded.append(arg)
  command = command_expanded

  if script == "css_to_wrapper.py":
    # "Invalid regular expression flags" in css_minifier.js (Node.js v12)
    return "--minify" in command

  if script == "protoc_wrapper.py":
    # Only the TypeScript piece is a problem
    return "--protoc-gen-ts" in command

  if script in ("run_with_restat.py", "run_with_stamp.py"):
    dash_pos = command.index("--")
    assert command[dash_pos + 1].endswith("tsc"), "Not being used with tsc: " + " ".join(command)

  return True

################################################################

# Rewrite a path under e.g. out/Release/ into the corresponding one
# under the pre-gen/ directory
def xform_path(path, section=None):
  assert ".." not in path, f"path = \"{path}\""
  assert "//" not in path, f"path = \"{path}\""
  assert "/./" not in path, f"path = \"{path}\""
  assert not path.startswith("-"), f"path = \"{path}\""
  assert not path.startswith("/"), f"path = \"{path}\""
  if path.startswith("host_for_rust_host_build_tools/"):
    # This one comes up in cross builds, redirect to the usual location
    path = "default" + path[4:]
  if not section:
    section = arch
  return f"../../{pre_gen_dir}/{section}/{path}"

def is_system_dep(dep):
  return dep.startswith("/") or "../usr/lib/" in dep

def rule_command(command, outputs_orig, depfile, indep):
  global mode

  if type(outputs_orig) is str:
    out_id = outputs_orig
    with open(f"../../{pre_gen_dir}/meta/{out_id}.out", "r") as f:
      outputs_orig = f.read().split()

  outputs = outputs_orig.copy()
  if depfile:
    outputs.append(depfile)
  section = "indep" if indep else None

  n = len(outputs)
  n_files = f"({n} file" + ("s" if n >= 2 else "") + ")"

  if not os.path.exists(f"../../{pre_gen_dir}"):
    mode = "disable"
  if os.path.exists(f"../../{pre_gen_dir}/DISABLE"):
    mode = "disable"
  if not examine_command(command, outputs):
    mode = "disable"
  if mode not in ("disable", "generate") and arch == "arch":
    assert os.path.exists(f"../../{pre_gen_dir}/arch"), "Need symlink to actual arch"

  if mode in ("check", "enable"):
    missing_outputs = [out for out in outputs if not os.path.exists(xform_path(out, section))]
    if missing_outputs:
      for out in missing_outputs:
        print(f"  ?? {out}", file=sys.stderr)
      sys.exit("error: missing pre-generated output")

  if mode == "check":
    print("note: check-pre-gen: attempting command:", file=sys.stderr)
    print(" ".join([sys.executable] + command), file=sys.stderr)
    proc = subprocess.run([sys.executable] + command)
    if proc.returncode == 0:
      missing_outputs = [out for out in outputs if not os.path.exists(out)]
      if missing_outputs:
        for out in missing_outputs:
          print(f"  missing: {out}", file=sys.stderr)
        print("note: check-pre-gen: command did not produce all expected outputs", file=sys.stderr)
      else:
        diffing_outputs = [out for out in outputs if not filecmp.cmp(out, xform_path(out, section), False)]
        if diffing_outputs:
          for out in diffing_outputs:
            print(f"  diff: {out}", file=sys.stderr)
          print("note: check-pre-gen: command did not produce identical outputs", file=sys.stderr)
        else:
          sys.exit("error: check-pre-gen: command was successful")
    else:
      print("note: check-pre-gen: command failed as expected", file=sys.stderr)
    mode = "enable"

  if mode == "enable":
    print(f"note: using pre-generated output {n_files}", file=sys.stderr)
    for out in outputs:
      saved = xform_path(out, section)
      shutil.copyfile(saved, out)
      if debug: print(f"  <- {saved[6:]}", file=sys.stderr)
    sys.exit(0)

  if mode in ("disable", "generate"):
    proc = subprocess.run([sys.executable] + command)
    if proc.returncode != 0:
      sys.exit(proc.returncode)

  if mode == "generate":
    missing_outputs = [out for out in outputs if not os.path.exists(out)]
    if missing_outputs:
      for out in missing_outputs:
        print(f"  ?? {out}", file=sys.stderr)
      sys.exit("error: missing expected output")
    print(f"note: saving generated output {n_files}", file=sys.stderr)
    for out in outputs:
      saved = xform_path(out, section)
      os.makedirs(os.path.dirname(saved), exist_ok=True)
      shutil.copyfile(out, saved)
      if debug: print(f"  -> {saved[6:]}", file=sys.stderr)
      if out.endswith(".d"):
        # Ninja dependency file -- filter out system paths from saved copy
        with open(saved, "r") as f:
          dep_line = f.read().strip()
        assert "\n" not in dep_line, "Expected a single line"
        deps = dep_line.split()
        assert deps[0].endswith(":")
        deps_filt = [d for d in deps if not is_system_dep(d)]
        with open(saved, "w") as f:
          f.write(" ".join(deps_filt))

  sys.exit(0)

################################################################

class NinjaRule():
  def __init__(self, name):
    self.name = name
    self.indep = True
    self.script = None
    self.output_groups = {}
    self.large_groups = set()

# Return the same result as "echo $s | md5sum | cut -c1-8"
def hash_string(s):
  h = hashlib.md5()
  h.update(s.encode("ASCII") + b"\n")
  return h.hexdigest()[:8]

def add_ninja_hooks():

  # Ensure that all listed scripts are present
  missing_scripts = [script for script in
    (handled_node_scripts |
     handled_python_arch_scripts |
     handled_python_indep_scripts
    ) if not os.path.exists(f"../../{script}")
  ]
  if missing_scripts:
    for script in sorted(missing_scripts):
      print(f"  not found: {script}", file=sys.stderr)
    sys.exit("error: found references to scripts not in the source tree")

  with open("toolchain.ninja", "r") as f:
    line = f.readline()
    if "deb_pre_gen" in line:
      print("Already added the ninja hooks.", file=sys.stderr)
      sys.exit(0)

  def toolchain_ninja_files():
    for root, _, files in os.walk("."):
      for fname in files:
        if fname == "toolchain.ninja":
          yield f"{root}/{fname}"

  current_rule_name = None
  rspfile_content = None
  relevant_rules = {}
  all_outputs = set()
  all_out_ids = set()
  unseen_bad_outputs = bad_outputs.copy()

  with fileinput.input(
      files=toolchain_ninja_files(),
      inplace=True,
      backup=".orig-pre-gen",
      encoding="UTF-8"
  ) as f:
    for line in f:
      if fileinput.filelineno() == 1:
        print(f"Adding ninja hooks to {fileinput.filename()} ...", file=sys.stderr)
        print("# deb_pre_gen.py hooks added to this file")

      # Rule definition
      if line.startswith("rule "):
        current_rule_name = line[5:].rstrip()
      elif not current_rule_name:
        pass  # Not in a rule body
      elif not line.startswith("  "):
        # At the end of the rule body
        current_rule_name = None
        rspfile_content = None
      elif line.startswith("  rspfile_content = "):
        rspfile_content = line[20:].rstrip()
      elif line.startswith("  command = "):
        command_flat = line[12:].rstrip()
        if rspfile_content:
          command_flat = command_flat.replace("@${rspfile}", rspfile_content)
          if " @" in command_flat and not ' @"${output_dir}/' in command_flat:
            print(f"warning: apparent unhandled rspfile in rule \"{current_rule_name}\"", file=sys.stderr)
        command = command_flat.split()
        if "python" in command[0] and command[1].endswith(".py"):
          script = command[1]
          if script.startswith("../../"):
            script = script[6:]
          rule_is_relevant = False
          rule_is_indep = True
          if not examine_command(command[1:], None):
            pass
          elif script == "third_party/node/node.py":
            node_script = command[2]
            if node_script.startswith("../../"):
              node_script = node_script[6:]
            if node_script in handled_node_scripts:
              rule_is_relevant = True
          elif script in handled_python_arch_scripts:
            rule_is_relevant = True
            rule_is_indep = False
          elif script in handled_python_indep_scripts:
            rule_is_relevant = True
          if rule_is_relevant:
            nrule = NinjaRule(current_rule_name)
            nrule.indep = rule_is_indep
            nrule.script = script
            relevant_rules[current_rule_name] = nrule
            arch_arg = "" if rule_is_indep else " --arch"
            line = re.sub(r"^(  command) = (\S+)",
                r"\1 = \2 ../../debian/deb_pre_gen.py ${deb_out} --depfile ${depfile} --end" + arch_arg + " rule-command --", line)
            assert "deb_pre_gen" in line, f"Command edit failed for rule \"{current_rule_name}\""

      # Target definition
      m = re.match(r"build (.+): (__[-\w]+__rule)\b", line)
      if m:
        outputs_flat = m.group(1)
        rule_name = m.group(2)
        nrule = relevant_rules.get(rule_name)
        if nrule:
          outputs_flat = outputs_flat.replace("$:", ":")
          assert "$" not in outputs_flat, "Drat, need to process more escape sequences"
          outputs = outputs_flat.split()
          assert not all_outputs.intersection(outputs), "Found non-unique output file(s)"
          all_outputs.update(outputs)
          unseen_bad_outputs.difference_update(outputs)
          if "/chrome/test/data/" in outputs[0]:
            pass  # bad output
          elif bad_outputs.intersection(outputs):
            pass  # bad output
          else:
            if nrule.script.endswith("/run_bindgen.py"):
              # Remove the static-library dependency from the bindgen
              # targets; the library is not needed, and removing it
              # speeds up the generation process considerably
              line = re.sub(r" obj/\S+/lib\w+\.a( |$)", r"", line)
            print(line, end="")
            out_id = hash_string(outputs_flat)
            assert out_id not in all_out_ids, "Hash collision!"
            all_out_ids.add(out_id)
            nrule.output_groups[out_id] = outputs
            if len(outputs_flat) >= 2**12:
              nrule.large_groups.add(out_id)
              line = f"  deb_out = --out-id {out_id}\n"
            else:
              # Short enough to avoid E2BIG ("Argument list too long")
              line = f"  deb_out = --out {outputs_flat}\n"

      print(line, end="")

  # Check for stale entries in bad_outputs
  if mode == "generate" and unseen_bad_outputs:
    print(file=sys.stderr)
    for out in sorted(unseen_bad_outputs):
      print(f"  ?? {out}", file=sys.stderr)
    sys.exit("error: please remove the above from bad_outputs")

  # Sort the list of rules, and filter out rules with no outputs
  # (resulting from "bad output" filtering above)
  nrule_list = sorted(relevant_rules.values(), key=lambda r: r.name)
  nrule_list = [r for r in nrule_list if r.output_groups]
  return nrule_list

################################################################

if __name__ == "__main__":

  parser = argparse.ArgumentParser()
  parser.add_argument("-C", metavar="DIR", dest="dir")
  parser.add_argument("--out", metavar="FILE", nargs="+")
  parser.add_argument("--out-id", metavar="ID", action="store")
  parser.add_argument("--depfile", metavar="FILE", nargs="?")
  parser.add_argument("--end", action="store_true")  # dummy
  parser.add_argument("--arch", action="store_true")
  parser.add_argument("op", choices=("add-ninja-hooks", "rule-command"))
  parser.add_argument("op_args", metavar="ARG", nargs="*")
  args = parser.parse_args()

  if args.dir:
    os.chdir(args.dir)

  if args.op == "rule-command":
    rule_command(args.op_args, args.out or args.out_id, args.depfile, not args.arch)
  elif args.op == "add-ninja-hooks":
    nrule_list = add_ninja_hooks()
    if mode == "generate":
      files_arch = []
      files_indep = []
      for nrule in nrule_list:
        for out_id, outputs in nrule.output_groups.items():
          (files_indep if nrule.indep else files_arch).append(outputs[0])
          if out_id in nrule.large_groups:
            with open(f"../../{pre_gen_dir}/meta/{out_id}.out", "x") as f:
              print("\n".join(outputs), file=f)
      with open(f"../../{pre_gen_dir}/FILES_ARCH", "w") as f:
        print("\n".join(sorted(files_arch)), file=f)
      with open(f"../../{pre_gen_dir}/FILES_INDEP", "w") as f:
        print("\n".join(sorted(files_indep)), file=f)

# end deb_pre_gen.py
