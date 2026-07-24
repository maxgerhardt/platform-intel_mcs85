"""
Baremetal framework for the Intel 8085 (MCS-85).

No runtime/framework code is provided: the project supplies its own startup
(crt0) and linker script. This script only sets the compiler/assembler/linker
flags for the LLVM 8085 toolchain, following the known-good recipe:

    clang --target=i8085-unknown-elf[+undoc] -std=c23 -O2 -ffreestanding \
          -fno-builtin -fdata-sections -ffunction-sections -c ...
    ld.lld -T <ldscript> --gc-sections ... libc.a libgcc[-undoc].a

The undocumented 8085 instructions are opt-in per project via
`board_build.undocumented_insns = yes`, which appends `+undoc` to the target
triple and links the matching libgcc variant.
"""

from os.path import join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()

toolchain_dir = platform.get_package_dir("toolchain-llvm-i8085") or ""
sysroot_inc = join(toolchain_dir, "sysroot", "include")
sysroot_lib = join(toolchain_dir, "sysroot", "lib")

# --- Undocumented-instruction opt-in --------------------------------------- #
undoc = str(board.get("build.undocumented_insns", "no")).lower() in (
    "1",
    "yes",
    "true",
    "on",
)
target = "i8085-unknown-elf" + ("+undoc" if undoc else "")
# -l name of the compiler-support library (libgcc-undoc.a -> -lgcc-undoc).
libgcc = "gcc-undoc" if undoc else "gcc"

# The target selection must reach both the compiler and the (clang-driven)
# assembler used for .S startup files. It must NOT be passed to ld.lld.
machine_flags = ["--target=%s" % target]

env.Append(
    ASFLAGS=machine_flags,
    ASPPFLAGS=machine_flags,
    CCFLAGS=machine_flags
    + [
        "-O2",
        "-ffreestanding",
        "-fno-builtin",
        "-fdata-sections",
        "-ffunction-sections",
        "-Wall",
    ],
    CFLAGS=["-std=c23"],
    CXXFLAGS=[
        "-std=gnu++17",
        "-fno-exceptions",
        "-fno-rtti",
        "-fno-threadsafe-statics",
    ],
    CPPPATH=[sysroot_inc],
    CPPDEFINES=[("F_CPU", "$BOARD_F_CPU")],
    # The C runtime and compiler-support libraries. PlatformIO prepends
    # `-T <ldscript>` (from board_build.ldscript) to LINKFLAGS, and the clang
    # driver forwards it to the linker.
    LIBPATH=[sysroot_lib],
    LIBS=["c", libgcc],
    LINKFLAGS=machine_flags
    + [
        "-nostdlib",  # we supply our own startup (crt0) and libraries
        "-fuse-ld=lld",  # use the bundled ld.lld
        "-Wl,--gc-sections",
        "-Wl,-Map=" + join("$BUILD_DIR", "${PROGNAME}.map"),
    ],
)

# Group libc/libgcc so their mutual references resolve regardless of order.
env.Prepend(_LIBFLAGS="-Wl,--start-group ")
env.Append(_LIBFLAGS=" -Wl,--end-group")
