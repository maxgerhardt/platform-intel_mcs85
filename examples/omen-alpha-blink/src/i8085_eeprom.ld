/* EEPROM-resident image for the Omen Alpha (Monitor v4).
 *
 * Code + rodata + the .data initializer live in EEPROM (0x2000..0x7FFF, the
 * free user area above the resident monitor/loader). .data and .bss live in
 * RAM (0x8000+); crt0_for_eeprom.S copies .data from EEPROM to RAM and zeroes
 * .bss at startup. Launch with the monitor at the ROM origin (G2000), or upload
 * with hexload_uploader.py --run (auto-jumps to the lowest = entry address).
 */
OUTPUT_FORMAT(elf32-i8085)
ENTRY(_start)

MEMORY
{
  /* EEPROM user area: above the resident image (ends ~0x13DA) with a growth
     margin. Keep in sync with the loader's user base if you enforce one. */
  ROM (rx)  : ORIGIN = 0x2000, LENGTH = 0x6000   /* 0x2000..0x7FFF (24 KB) */
  /* RAM for .data/.bss/heap; stack is placed at _estack below (0xFE00). */
  RAM (rwx) : ORIGIN = 0x8000, LENGTH = 0x7E00   /* 0x8000..0xFDFF */
}

SECTIONS
{
  /* Startup (crt0 _start) first, so the ROM origin is the entry point. */
  .vectors : {
    KEEP(*(.vectors))
  } > ROM

  .text : {
    *(.text .text.* .init .fini)
  } > ROM

  .rodata : {
    *(.rodata .rodata.*)
  } > ROM

  /* C++ global constructors/destructors */
  .init_array : {
    . = ALIGN(2);
    PROVIDE_HIDDEN(__init_array_start = .);
    KEEP(*(SORT_BY_INIT_PRIORITY(.init_array.*) SORT_BY_INIT_PRIORITY(.ctors.*)))
    KEEP(*(.init_array .ctors))
    PROVIDE_HIDDEN(__init_array_end = .);
  } > ROM

  .fini_array : {
    . = ALIGN(2);
    PROVIDE_HIDDEN(__fini_array_start = .);
    KEEP(*(SORT_BY_INIT_PRIORITY(.fini_array.*) SORT_BY_INIT_PRIORITY(.dtors.*)))
    KEEP(*(.fini_array .dtors))
    PROVIDE_HIDDEN(__fini_array_end = .);
  } > ROM

  . = ALIGN(2);
  _etext = .;

  /* .data: runs in RAM (VMA) but is stored in EEPROM (LMA), copied by crt0. */
  .data : {
    . = ALIGN(2);
    _sdata = .;
    *(.data .data.*)
    . = ALIGN(2);
    _edata = .;
  } > RAM AT > ROM

  /* Load address of the .data initializer image, i.e. where it sits in EEPROM. */
  _sidata = LOADADDR(.data);

  .bss (NOLOAD) : {
    . = ALIGN(2);
    _sbss = .;
    *(.bss .bss.*)
    *(COMMON)
    . = ALIGN(2);
    _ebss = .;
  } > RAM

  _end = .;
}

PROVIDE(_data_size = _edata - _sdata);
PROVIDE(_bss_size  = _ebss - _sbss);

PROVIDE(_estack = 0xFE00);
PROVIDE(_stack  = _estack);

PROVIDE(__heap_start = _end);
PROVIDE(__heap_end   = _stack - 0x0200);

