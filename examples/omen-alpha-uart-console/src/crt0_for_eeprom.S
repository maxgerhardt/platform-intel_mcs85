//----------------------------------------------------------------------------
// i8085 CRT0 for EEPROM-resident images (Omen Alpha, Monitor v4)
//
// Unlike the RAM-flat crt0, the code, rodata and the .data INITIALIZER image
// live in EEPROM (their load address / LMA), while .data and .bss live in RAM
// (their run address / VMA). So before running C we must:
//   1. copy .data from EEPROM (_sidata) into RAM (_sdata.._edata), and
//   2. zero .bss.
// The monitor launches this image at _start (= the ROM origin, e.g. G2000).
//----------------------------------------------------------------------------
  .section .vectors, "ax"
  .globl _start
_start:
  LXI SP, _stack

  // --- copy .data initializer image: EEPROM(_sidata) -> RAM(_sdata) ---
  // HL = source in EEPROM (LMA), DE = destination in RAM (VMA), BC = byte count
  LXI H, _sidata
  LXI D, _sdata
  LXI B, _data_size
data_loop:
  MOV A, B
  ORA C
  JZ data_done          // count == 0 -> done (also handles empty .data)
  MOV A, M              // read a byte from EEPROM
  STAX D                // store it into RAM
  INX H
  INX D
  DCX B
  JMP data_loop
data_done:

  // --- zero .bss (RAM) ---
  LXI H, _sbss
  LXI D, _ebss
  MVI B, 0

  MOV A, H
  CMP D
  JNZ bss_loop
  MOV A, L
  CMP E
  JZ bss_done

bss_loop:
  MOV M, B
  INX H
  MOV A, H
  CMP D
  JNZ bss_loop
  MOV A, L
  CMP E
  JNZ bss_loop

bss_done:
  // --- call global constructors (.init_array) - needed for C++ ---
  LXI H, __init_array_start
  LXI D, __init_array_end

init_loop:
  MOV A, H
  CMP D
  JNZ init_call
  MOV A, L
  CMP E
  JZ init_done

init_call:
  MOV C, M              // low byte of function pointer
  INX H
  MOV B, M              // high byte
  INX H
  PUSH H                // save iterator
  PUSH D                // save end pointer
  MOV H, B
  MOV L, C              // HL = function pointer
  CALL __call_hl
  POP D                 // restore end pointer
  POP H                 // restore iterator
  JMP init_loop

init_done:
  CALL main

halt_loop:
  HLT
  JMP halt_loop

.section .text
  // Indirect call trampoline: CALL __call_hl jumps to the address in HL.
  .globl __call_hl
__call_hl:
  PCHL

  // _exit stub: halt the CPU
  .globl _exit
  .globl _Exit
_exit:
_Exit:
  HLT
  JMP _exit
