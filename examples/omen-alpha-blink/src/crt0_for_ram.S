//----------------------------------------------------------------------------
// Minimal i8085 CRT0 with vector table and C runtime init
//----------------------------------------------------------------------------
  .section .vectors, "ax"
  .globl _start
_start:
  LXI SP, _stack

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
  // Call global constructors (.init_array) — needed for C++
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
  MOV C, M      // low byte of function pointer
  INX H
  MOV B, M      // high byte
  INX H
  PUSH H        // save iterator
  PUSH D        // save end pointer
  MOV H, B
  MOV L, C      // HL = function pointer
  CALL __call_hl
  POP D         // restore end pointer
  POP H         // restore iterator
  JMP init_loop

init_done:
  CALL main

halt_loop:
  HLT
  JMP halt_loop

.section .text
  // Indirect call trampoline: CALL __call_hl jumps to address in HL.
  // The CALL pushes the return address, then PCHL jumps to the function.
  // When the function RETurns, it returns to after the CALL.
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
