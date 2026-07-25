"""
    Builder for the Intel MCS-85 (8085) platform.

    Wires up the LLVM/Clang toolchain (clang, ld.lld, llvm-* utilities) and the
    build/upload targets. The actual compiler/linker flags live in the
    baremetal framework script (frameworks/_bare.py), which is also used as the
    default when no framework is selected.
"""

from os.path import join

from SCons.Script import (
    COMMAND_LINE_TARGETS,
    AlwaysBuild,
    Builder,
    Default,
    DefaultEnvironment,
)

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

env.Replace(
    AR="llvm-ar",
    AS="clang",
    CC="clang",
    CXX="clang",
    LINK="$CC",
    OBJCOPY="llvm-objcopy",
    OBJDUMP="llvm-objdump",
    RANLIB="llvm-ranlib",
    SIZETOOL="llvm-size",
    ARFLAGS=["rc"],
    # llvm-size -A (sysv) prints one line per section: "<name> <size> <addr>".
    # Program (EEPROM/flash) = code + read-only + the .data load image.
    # Data (RAM) = .data (runtime copy) + .bss.
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD="$SIZETOOL -B -d $SOURCES",
    SIZEPROGREGEXP=r"^(?:\.vectors|\.text|\.rodata|\.init_array|\.fini_array|\.data)\s+(\d+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss)\s+(\d+).*",
    PROGSUFFIX=".elf",
)

env.Append(
    BUILDERS=dict(
        ElfToHex=Builder(
            action=env.VerboseAction(
                " ".join(["$OBJCOPY", "-O", "ihex", "$SOURCES", "$TARGET"]),
                "Building $TARGET",
            ),
            suffix=".hex",
        ),
        ElfToBin=Builder(
            action=env.VerboseAction(
                " ".join(["$OBJCOPY", "-O", "binary", "$SOURCES", "$TARGET"]),
                "Building $TARGET",
            ),
            suffix=".bin",
        ),
        Disassemble=Builder(
            action=env.VerboseAction(
                " ".join(["$OBJDUMP", "-d", "$SOURCES", ">", "$TARGET"]),
                "Building disassembly $TARGET",
            ),
            suffix=".lst",
        ),
    )
)

# Apply the baremetal build flags when the project does not select a framework.
# (When `framework = baremetal` is set, PlatformIO runs the same script as the
# framework, so this fallback is skipped to avoid applying the flags twice.)
if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py", exports="env")

#
# Target: Build executable and linkable firmware, plus HEX/BIN/listing
#
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_hex = join("$BUILD_DIR", "${PROGNAME}.hex")
    target_bin = join("$BUILD_DIR", "${PROGNAME}.bin")
else:
    target_elf = env.BuildProgram()
    target_hex = env.ElfToHex(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_bin = env.ElfToBin(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    target_lst = env.Disassemble(join("$BUILD_DIR", "${PROGNAME}"), target_elf)
    env.Depends(target_hex, target_lst)

AlwaysBuild(env.Alias("nobuild", [target_hex, target_bin]))
target_buildprog = env.Alias("buildprog", [target_hex, target_bin])

#
# Target: Print binary size
#
target_size = env.AddPlatformTarget(
    "size",
    target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"),
    "Program Size",
    "Calculate program size",
)

#
# Helpers for the i8085-trace simulator "upload"
#
def _elf_load_and_entry(elf_path):
    """Return (load_address, entry_point) from an ELF32 little-endian file.

    load = lowest physical address (LMA) of a loadable segment with content;
    entry = e_entry. For this platform's linker scripts they coincide, but the
    simulator wants both a load address for the flat .bin and an entry point.
    """
    import struct

    with open(elf_path, "rb") as fh:
        data = fh.read()
    e_entry = struct.unpack_from("<I", data, 24)[0]
    e_phoff = struct.unpack_from("<I", data, 28)[0]
    e_phentsize = struct.unpack_from("<H", data, 42)[0]
    e_phnum = struct.unpack_from("<H", data, 44)[0]
    load = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        p_paddr = struct.unpack_from("<I", data, off + 12)[0]
        p_filesz = struct.unpack_from("<I", data, off + 16)[0]
        if p_type == 1 and p_filesz > 0:  # PT_LOAD with content
            load = p_paddr if load is None else min(load, p_paddr)
    return (e_entry if load is None else load), e_entry


def _run_in_simulator(source, target, env):
    """Run the built flat binary in the i8085-trace simulator. The MC6850 ACIA
    plugin (ports 0xDE/0xDF) streams the firmware's console-UART output live to
    stdout (txlog=-)."""
    import os
    import subprocess
    import sys

    binimg = str(source[0])
    elf = env.subst(join("$BUILD_DIR", "${PROGNAME}.elf"))
    load, entry = _elf_load_and_entry(elf)
    max_steps = str(board.get("upload.sim_max_steps", 8000000))

    sim_pkg = platform.get_package_dir("tool-i8085-trace") or ""
    plugin = join(sim_pkg, "plugins", "mc6850_28c256.dll")

    cmd = [
        "i8085-trace", "-q", "-S", "-n", max_steps,
        "-l", "0x%X" % load, "-e", "0x%X" % entry,
    ]
    if os.path.isfile(plugin):
        # Live-stream any console-UART (0xDE/0xDF) output to stdout.
        cmd += ["--io-plugin=%s" % plugin, "--io-plugin-config=txlog=-"]
    cmd += [binimg]

    print(
        "Running %s in i8085-trace (load 0x%X, entry 0x%X, max %s steps)..."
        % (os.path.basename(binimg), load, entry, max_steps)
    )
    sys.stdout.flush()
    return subprocess.call(cmd)


#
# Target: Upload firmware -- to hardware via Hexload, or into the simulator
#
upload_protocol = env.subst("$UPLOAD_PROTOCOL")
upload_actions = []
upload_source = target_hex

if upload_protocol == "hexload":
    # The Hexload uploader needs pyserial + intelhex. Ensure they are available
    # in PlatformIO's Python environment, but only when actually uploading.
    if "upload" in COMMAND_LINE_TARGETS:
        import importlib
        import subprocess
        import sys

        for _mod, _pkg in (("serial", "pyserial"), ("intelhex", "intelhex")):
            try:
                importlib.import_module(_mod)
            except ImportError:
                print("Installing '%s' into the PlatformIO Python environment..." % _pkg)
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", _pkg, "--no-input"]
                )

    uploader = join(platform.get_package_dir("tool-hexload") or "", "hexload_uploader.py")
    uploader_flags = ["-b", "$UPLOAD_SPEED", "--run"]
    # If a port is configured we pass it explicitly; otherwise the uploader
    # autodetects the USB serial port itself.
    if env.subst("$UPLOAD_PORT"):
        uploader_flags = ["-p", "$UPLOAD_PORT"] + uploader_flags

    env.Replace(
        UPLOADER=uploader,
        UPLOADERFLAGS=uploader_flags,
        UPLOADCMD='"$PYTHONEXE" "$UPLOADER" $UPLOADERFLAGS "$SOURCE"',
    )
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]
elif upload_protocol == "i8085-trace":
    # Run the firmware in the i8085-trace simulator instead of flashing hardware.
    upload_source = target_bin
    upload_actions = [
        env.VerboseAction(_run_in_simulator, "Running $SOURCE in i8085-trace")
    ]
elif upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]
else:
    import sys

    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)

AlwaysBuild(env.Alias("upload", upload_source, upload_actions))

#
# Default targets
#
Default([target_buildprog, target_size])
