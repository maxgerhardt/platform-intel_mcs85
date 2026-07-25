/*
 * OMEN ALPHA baremetal blink + UART demo.
 *
 * Blinks the LEDs on the on-board 8255 PPI (Programmable Peripheral Interface,
 * port A) and prints a status line over the console ACIA (a Motorola MC6850 at
 * I/O ports 0xDE/0xDF) on every toggle. That ACIA is the same serial link the
 * monitor and the Hexload uploader use, so the output shows up in your serial
 * monitor at 115200 baud.
 *
 * The monitor has already initialised the console ACIA, so we only transmit;
 * we do not reset or reconfigure it.
 */

#include <stdint.h>

/* --- 8085 I/O port access ------------------------------------------------- */
static inline uint8_t IN(uint8_t port) {
    uint8_t result;
    /* The 8085 IN instruction loads the accumulator (A). Move A into the
       compiler-chosen result register so we use the value read, not whatever
       register the compiler assumed the result was in. */
    __asm__ volatile("in %1\n\tMOV %0, A" : "=r"(result) : "i"(port));
    return result;
}

static inline void OUT(uint8_t port, uint8_t value) {
    /* The 8085 OUT instruction transmits the accumulator (A). Move the value
       into A first, so we output it rather than whatever A happened to hold. */
    __asm__ volatile("MOV A, %0\n\tout %1" : : "r"(value), "i"(port));
}

/* --- 8255 PPI (parallel I/O chip) ---------------------------------------- */
#define PPI_PORTA 0x00   /* port A -> LEDs */
#define PPI_CTRL  0x03   /* control word register */

/* --- Console ACIA (MC6850), shared with the monitor / hexload ------------ */
#define ACIA_CTRL 0xDE   /* control (W) / status (R) */
#define ACIA_DATA 0xDF   /* data */
#define ACIA_TDRE 0x02   /* status bit: transmit data register empty */

static void uart_putc(char c) {
    while ((IN(ACIA_CTRL) & ACIA_TDRE) == 0) {
        /* wait for the transmitter to be ready */
    }
    OUT(ACIA_DATA, (uint8_t)c);
}

static void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

/* crude busy-wait so the blink is visible; volatile keeps the loop alive */
static void delay(void) {
    for (volatile uint16_t i = 0; i < 20000; i++) {
        __asm__ volatile("");
    }
}

int main(void) {
    /* 8255 control word 0x80: mode 0, every port an OUTPUT. */
    OUT(PPI_CTRL, 0x80);

    uart_puts("OMEN ALPHA blink demo\r\n");

    uint8_t on = 0;
    while (1) {
        on = !on;
        OUT(PPI_PORTA, on ? 0xFF : 0x00);
        uart_puts(on ? "LED on\r\n" : "LED off\r\n");
        delay();
    }

    return 0;
}
