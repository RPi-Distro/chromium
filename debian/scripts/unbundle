#!/usr/bin/python3 -B

import os
import sys
import shutil

sys.path.append("build/linux/unbundle")

import replace_gn_files

keepers = (
    'ffmpeg',
    'icu',          # previously bundled due to bullseye. TODO: test w/ bookworm.
    'libvpx',       # currently broken with no easy fix; https://crbug.com/1307941
    'absl_algorithm',
    'absl_base',    # all absl bundled due to bullseye. TODO: test w/ bookworm.
    'absl_cleanup',
    'absl_crc',
    'absl_container',
    'absl_debugging',
    'absl_flags',
    'absl_functional',
    'absl_hash',
    'absl_log',
    'absl_log_internal',
    'absl_memory',
    'absl_meta',
    'absl_numeric',
    'absl_random',
    'absl_status',
    'absl_strings',
    'absl_synchronization',
    'absl_time',
    'absl_types',
    'absl_utility',
    'brotli',       # requires brotli >= 1.1 (trixie)
    'crc32c',
    'flatbuffers',  # "So third_party/tflite uses a specific version of flatbuffers
                    # (currently only available in experimental; not even in sid).
                    # I'm not comfortable changing the version check and potentially
                    # having different schemas specifically for a serialization library"
                    # from Dec 2023

    'libaom',       # broken - media/gpu/vaapi/BUILD.gn depends on libaomrc, but the
                    # shim doesn't provide it. Needs an upstream bug.

    'libavif',
    'libyuv' ,
    'libwebp',      # libavif depends on libsharpyuv-dev; only in libwebp 1.3 (trixie)
    're2',          # experienced crashes Aug 2023 w/ 20230301-3; try >= 20240401.
    'snappy',
    'jsoncpp',
    'woff2',
    'swiftshader-SPIRV-Headers' ,
    'swiftshader-SPIRV-Tools' ,
    'vulkan-SPIRV-Headers' ,
    'vulkan-SPIRV-Tools' ,
    'vulkan_memory_allocator',
    )

for lib,rule in replace_gn_files.REPLACEMENTS.items():
    if lib not in keepers:
        # create a symlink to the unbundle gn file
        symlink = "ln -sf "
        path = os.path.split(rule)
        if not os.path.exists(path[0]):
            os.mkdir(path[0])
        while path[0] != '':
            path = os.path.split(path[0])
            symlink += '../'
        symlink += "build/linux/unbundle/%s.gn %s"%(lib,rule)
        if os.system(symlink):
            raise RuntimeError("error creating symlink",symlink)
