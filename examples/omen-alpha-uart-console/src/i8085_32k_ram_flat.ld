/* 32K flat map with heap, init_array, etc. */
OUTPUT_FORMAT(elf32-i8085)
ENTRY(_start)

MEMORY
{
  VECTORS (rx)  : ORIGIN = 0x8000, LENGTH = 0x0050
  PROG    (rwx) : ORIGIN = 0x8050, LENGTH = 0xFDB0
}

SECTIONS
{
  .vectors : {
    KEEP(*(.vectors))
  } > VECTORS

  .text : {
    *(.text .text.* .init .fini)
  } > PROG

  .rodata : {
    *(.rodata .rodata.*)
  } > PROG

  /* C++ global constructors/destructors */
  .init_array : {
    . = ALIGN(2);
    PROVIDE_HIDDEN(__init_array_start = .);
    KEEP(*(SORT_BY_INIT_PRIORITY(.init_array.*) SORT_BY_INIT_PRIORITY(.ctors.*)))
    KEEP(*(.init_array .ctors))
    PROVIDE_HIDDEN(__init_array_end = .);
  } > PROG

  .fini_array : {
    . = ALIGN(2);
    PROVIDE_HIDDEN(__fini_array_start = .);
    KEEP(*(SORT_BY_INIT_PRIORITY(.fini_array.*) SORT_BY_INIT_PRIORITY(.dtors.*)))
    KEEP(*(.fini_array .dtors))
    PROVIDE_HIDDEN(__fini_array_end = .);
  } > PROG

  . = ALIGN(2);
  _etext = .;

  .data : {
    . = ALIGN(2);
    _sdata = .;
    *(.data .data.*)
    . = ALIGN(2);
    _edata = .;
  } > PROG

  _sidata = LOADADDR(.data);

  .bss (NOLOAD) : {
    . = ALIGN(2);
    _sbss = .;
    *(.bss .bss.*)
    *(COMMON)
    . = ALIGN(2);
    _ebss = .;
  } > PROG

  _end = .;
}

PROVIDE(_data_size = _edata - _sdata);
PROVIDE(_bss_size = _ebss - _sbss);

PROVIDE(_estack = 0xFE00);
PROVIDE(_stack = _estack);

PROVIDE(__heap_start = _end);
PROVIDE(__heap_end = _stack - 0x0200);

