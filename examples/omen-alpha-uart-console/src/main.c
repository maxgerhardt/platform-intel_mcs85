/*
 * OMEN ALPHA interactive UART console.
 *
 * Reads command lines from the console ACIA (MC6850 at 0xDE/0xDF) and responds:
 *
 *   ping        -> pong
 *   blink N     -> blink the LEDs on the 8255 PPI (port A) N times
 *   help        -> list commands
 *
 * Run it interactively in the simulator with:  pio run -t sim
 * (the i8085-trace simulator bridges the ACIA to a terminal). On real hardware,
 * open a serial monitor at 115200 after uploading.
 */

#include <stdint.h>

/* --- 8085 I/O ------------------------------------------------------------- */
static inline uint8_t IN(uint8_t port) {
    uint8_t r;
    __asm__ volatile("in %1\n\tMOV %0, A" : "=r"(r) : "i"(port));
    return r;
}
static inline void OUT(uint8_t port, uint8_t value) {
    __asm__ volatile("MOV A, %0\n\tout %1" : : "r"(value), "i"(port));
}

/* --- Peripherals ---------------------------------------------------------- */
#define PPI_PORTA 0x00 /* LEDs */
#define PPI_CTRL  0x03
#define ACIA_CTRL 0xDE /* status (R) / control (W) */
#define ACIA_DATA 0xDF /* rx (R) / tx (W) */
#define ACIA_TDRE 0x02 /* transmit register empty */
#define ACIA_RDRF 0x01 /* receive register full */

static void put_c(char c) {
    while ((IN(ACIA_CTRL) & ACIA_TDRE) == 0) {
    }
    OUT(ACIA_DATA, (uint8_t)c);
}
static void put_s(const char *s) {
    while (*s)
        put_c(*s++);
}
static char get_c(void) {
    while ((IN(ACIA_CTRL) & ACIA_RDRF) == 0) {
    }
    return (char)IN(ACIA_DATA);
}

static void set_leds(uint8_t v) { OUT(PPI_PORTA, v); }
static void delay(void) {
    for (volatile uint16_t i = 0; i < 20000; i++)
        __asm__ volatile("");
}

/* read a line (until CR/LF), with echo and backspace; returns its length */
static uint8_t readline(char *buf, uint8_t max) {
    uint8_t n = 0;
    for (;;) {
        char c = get_c();
        if (c == '\r' || c == '\n') {
            put_s("\r\n");
            buf[n] = 0;
            return n;
        }
        if ((c == 8 || c == 127) && n > 0) { /* backspace */
            n--;
            put_s("\b \b");
        } else if (c >= 32 && n < max - 1) {
            buf[n++] = c;
            put_c(c); /* echo */
        }
    }
}

static uint8_t streq(const char *a, const char *b) {
    while (*a && *b) {
        if (*a++ != *b++)
            return 0;
    }
    return *a == *b;
}

int main(void) {
    OUT(PPI_CTRL, 0x80); /* 8255: all ports output */
    set_leds(0x00);

    put_s("\r\nOMEN ALPHA UART console\r\n"
          "commands: ping | blink N | help\r\n> ");

    char line[32];
    for (;;) {
        uint8_t n = readline(line, sizeof line);
        if (n == 0) {
            put_s("> ");
            continue;
        }

        if (streq(line, "ping")) {
            put_s("pong\r\n");
        } else if (streq(line, "help")) {
            put_s("commands: ping, blink N, help\r\n");
        } else if (line[0] == 'b' && line[1] == 'l' && line[2] == 'i' && line[3] == 'n' &&
                   line[4] == 'k') {
            uint8_t i = 5;
            while (line[i] == ' ')
                i++;
            uint8_t cnt = 0;
            while (line[i] >= '0' && line[i] <= '9')
                cnt = (uint8_t)(cnt * 10 + (line[i++] - '0'));
            if (cnt == 0)
                cnt = 1;
            put_s("blinking\r\n");
            for (uint8_t k = 0; k < cnt; k++) {
                set_leds(0xFF);
                delay();
                set_leds(0x00);
                delay();
            }
        } else {
            put_s("unknown command: ");
            put_s(line);
            put_s("\r\n");
        }
        put_s("> ");
    }
    return 0;
}
