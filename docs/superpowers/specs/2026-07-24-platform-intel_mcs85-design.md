# Design: `platform-intel_mcs85`

A PlatformIO development platform for the Intel MCS-85 (8085) family, targeting
the OMEN ALPHA homebrew computer.

## Goal

Let users compile C applications for the OMEN ALPHA with PlatformIO, using the
existing LLVM 8085 toolchain, and upload them over serial with the Hexload
module. Package everything as publishable, self-contained repositories.

## Three repositories

| Repo | Type | Contents |
| --- | --- | --- |
| `platform-intel_mcs85` | dev-platform | `platform.json`, `platform.py`, `builder/`, `boards/omen_alpha.json`, `examples/omen-alpha-blink/`, CI, README, LICENSE |
| `toolchain-llvm-i8085` | toolchain | Trimmed LLVM (clang, ld.lld, llvm-*), clang resource headers, bundled i8085 sysroot; `package.json` |
| `tool-hexload` | uploader | `hexload_uploader.py`, `requirements.txt`, `package.json` |

`platform.json` references the toolchain (required) and tool (optional).
`platform.py` selects the per-host toolchain package (currently `windows_amd64`
only), and yields to a local `symlink://` override for development.

## Build flow (`baremetal` framework)

Mirrors the known-good `first_c` recipe:

- **Compile** `clang --target=i8085-unknown-elf[+undoc] -std=c23 -O2
  -ffreestanding -fno-builtin -fdata-sections -ffunction-sections`
- **Assemble** `.S` startup files with the same clang driver/target.
- **Link** `ld.lld -T <board_build.ldscript> --gc-sections ... libc.a
  libgcc[-undoc].a` (libs grouped, after the project objects).
- **Post** `llvm-objcopy -O ihex` / `-O binary`, `llvm-objdump -d` listing,
  `llvm-size`.
- **Upload** `hexload_uploader.py <hex> [-p PORT] -b <speed> --run`.

The undocumented instruction set is opt-in per project via
`board_build.undocumented_insns = yes`, which appends `+undoc` to the target
triple and links `libgcc-undoc.a`.

## Board

`omen_alpha`: `mcu=i8085`, `f_cpu=2 MHz`, RAM 32 KB, EEPROM user area 24 KB,
`upload.protocol=hexload`, `speed=115200`.

## Example: `omen-alpha-blink`

The linker scripts and `crt0` startup files come from the `first_c` project
(example-owned, per the request). One `src/main.c` blinks the LEDs on the 8255
PPI (`OUT 0x03,0x80` then toggling `OUT 0x00`) and prints over the console ACIA
(MC6850 at `0xDE/0xDF`, the port the monitor/hexload use, so output reaches the
serial monitor). Two environments:

- `omen_alpha_ram` — `i8085_32k_ram_flat.ld` + `crt0_for_ram.S`, entry `0x8000`.
- `omen_alpha_eeprom` — `i8085_eeprom.ld` + `crt0_for_eeprom.S`, entry `0x2000`.

Each env selects its startup via `build_src_filter`. A commented, explained
`board_build.undocumented_insns = yes` opt-in is present.

## Verification

`pio run` builds both environments against a local symlinked platform +
packages. Confirmed: entry points (`0x8000` / `0x2000`), the four I/O ports
(`OUT 0x3`, `OUT 0x0`, `IN 0xde`, `OUT 0xdf`), valid Intel HEX (stack init
`LXI SP,0xFE00`), the undoc toggle flips target + libgcc, and the uploader runs
from its packaged path with its deps present. Live hardware upload is a manual
follow-up. CI builds the example on `windows-latest` only.
