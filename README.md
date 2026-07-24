# Intel MCS-85 (8085): development platform for [PlatformIO](https://platformio.org)

[![Examples](https://github.com/maxgerhardt/platform-intel_mcs85/actions/workflows/examples.yml/badge.svg)](https://github.com/maxgerhardt/platform-intel_mcs85/actions/workflows/examples.yml)

The Intel MCS-85 is the microprocessor family built around the **Intel 8085**,
an 8-bit CISC CPU introduced in 1976. This platform compiles C (and assembly)
for the 8085 using an **LLVM/Clang** toolchain with a native 8085 backend, and
targets the **OMEN ALPHA** homebrew computer.

* Baremetal (no-framework) development
* C23 via Clang, `ld.lld`, and the `llvm-*` binary utilities
* Optional **undocumented 8085 instructions** (`LDSI`/`LHLX`/`SHLX`, ...)
* Upload over USB serial via the **Hexload** monitor module

## Usage

```ini
[env:omen_alpha]
platform = https://github.com/maxgerhardt/platform-intel_mcs85.git
board = omen_alpha
framework = baremetal
```

## Examples

* [`examples/omen-alpha-blink`](examples/omen-alpha-blink) — blinks the LEDs on
  the on-board 8255 PPI and prints over the console ACIA (UART), in two firmware
  layouts:
  * `omen_alpha_ram` — the whole image runs from RAM at `0x8000` (volatile).
  * `omen_alpha_eeprom` — code/rodata in EEPROM (`0x2000+`), data/bss in RAM.

## Boards

| ID | Name | MCU | RAM | EEPROM (user) |
| --- | --- | --- | --- | --- |
| `omen_alpha` | OMEN ALPHA | Intel 8085 | 32 KB | 24 KB |

## Configuration

Set in `platformio.ini`:

| Option | Default | Meaning |
| --- | --- | --- |
| `board_build.undocumented_insns` | `no` | `yes` allows the undocumented 8085 opcodes and links the matching `libgcc`. |
| `board_build.ldscript` | *(per-env)* | Linker script; the example ships a RAM and an EEPROM script under `src/`. |
| `upload_port` | *(autodetect)* | Serial port for the Hexload uploader. |
| `upload_speed` | `115200` | Upload/monitor baud. |

## The baremetal model

No runtime is imposed: your project supplies its own startup (`crt0`) and linker
script. The `baremetal` framework only sets the compiler/linker flags and links
the bundled `libc`/`libgcc`. See the example's `src/crt0_for_ram.S` /
`src/crt0_for_eeprom.S` and the two linker scripts for a working template.

## Uploading

`pio run -t upload` invokes the [Hexload uploader](https://github.com/maxgerhardt/tool-hexload),
which streams the Intel HEX image to the board's resident Hexload monitor module
over serial, then runs it and streams the board's UART output back to the
console (Ctrl+C to stop).

## Packages

| Package | Role |
| --- | --- |
| [`toolchain-llvm-i8085`](https://github.com/maxgerhardt/toolchain-llvm-i8085) | LLVM/Clang 8085 toolchain + sysroot |
| [`tool-hexload`](https://github.com/maxgerhardt/tool-hexload) | Hexload serial uploader |

## License

Apache-2.0.
