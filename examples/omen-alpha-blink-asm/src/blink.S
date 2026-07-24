//----------------------------------------------------------------------------
// OMEN ALPHA baremetal assembly blink.
//
// Pure 8085 assembly, no C runtime: this file is its own startup. It defines
// _start in the .vectors section (placed at the ROM origin = the entry point by
// the linker script), sets up the stack, configures the on-board 8255 PPI for
// output, and toggles the LEDs on port A forever with a busy-wait delay.
//
// PPI port A  = I/O port 0x00  (LEDs)
// PPI control = I/O port 0x03
//----------------------------------------------------------------------------

  .section .vectors, "ax"
  .globl _start
_start:
  LXI SP, _stack        // set up the stack (provided by the linker script)

  MVI A, 0x80           // 8255 control word 0x80: mode 0, all ports OUTPUT
  OUT 0x03              // -> PPI control register

  JMP blink             // enter the main loop (in .text)

  .section .text
blink:
  MVI A, 0xFF           // all LEDs on
  OUT 0x00              // -> PPI port A
  CALL delay

  MVI A, 0x00           // all LEDs off
  OUT 0x00              // -> PPI port A
  CALL delay

  JMP blink

//----------------------------------------------------------------------------
// Busy-wait delay. Outer count in DE, inner count in BC (a full 16-bit wrap =
// 65536). Increase the outer count (LXI D) to slow the blink down.
//----------------------------------------------------------------------------
delay:
  LXI D, 0x0002         // outer count
delay_outer:
  LXI B, 0x0000         // inner count = 65536
delay_inner:
  DCX B
  MOV A, B
  ORA C
  JNZ delay_inner
  DCX D
  MOV A, D
  ORA E
  JNZ delay_outer
  RET
