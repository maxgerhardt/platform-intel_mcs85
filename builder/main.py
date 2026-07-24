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

# The toolchain package's bin/ directory is prepended to $PATH by PlatformIO
# (pioplatform.py) when the package is installed, so the tools resolve by bare
# name -- no need to join absolute paths here. Sysroot include/lib paths, which
# are not on $PATH, are still referenced explicitly in frameworks/_bare.py.
env.Replace(
    AR="llvm-ar",
    AS="clang",
    CC="clang",
    CXX="clang",
    # Link through the clang driver (it invokes ld.lld via -fuse-ld=lld). This
    # keeps the standard PlatformIO link command; linker options are passed with
    # the -Wl, prefix from the framework script.
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
# Target: Upload firmware via the HEX Loader (Hexload) module
#
upload_protocol = env.subst("$UPLOAD_PROTOCOL")
upload_actions = []

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
elif upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]
else:
    import sys

    sys.stderr.write("Warning! Unknown upload protocol %s\n" % upload_protocol)

# The Hexload uploader consumes the Intel HEX image.
AlwaysBuild(env.Alias("upload", target_hex, upload_actions))

#
# Default targets
#
Default([target_buildprog, target_size])
