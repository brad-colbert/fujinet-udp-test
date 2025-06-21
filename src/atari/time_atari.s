; (C) 2025 Brad Colbert

.include "memory.inc"

; imports
.import     popa

; Constants
RTCLOK = 18  ; 19, 20
PALNTS = $62 ; 0 == NTSC, 1 == PAL

; Exports
.export _get_time_millis
.export _set_time_millis

; Macros

; Imports

; Data
.zeropage
_time_millis: .dword $00000000

.data
; This is a 32-bit value to hold the time in milliseconds.
_time_millis_pal: .DWORD $00000000 ; 4 bytes for 32-bit value

; Code
.code

; Get the current time in milliseconds
.proc _get_time_millis
    ; Copy the current JIFFY counter to our work/destination memory
    lda RTCLOK+2
    sta _time_millis+0
    lda RTCLOK+1
    sta _time_millis+1
    lda RTCLOK+0
    sta _time_millis+2


    ; Shift by 4 bits (x16) to convert JIFFY to milliseconds.  One Jiffy is 16 milliseconds.
    clc
    lda PALNTS
    beq @ntsc

@pal:
    cpy32 _time_millis, _time_millis_pal  ; make a copy so we can add the shift left twice
    asl32 _time_millis_pal
    asl32 _time_millis_pal

@ntsc:                   ; add pal
    asl32 _time_millis
    asl32 _time_millis
    asl32 _time_millis
    asl32 _time_millis

    lda PALNTS
    beq @done

    ; Add the PAL/NTSC factor
    add32 _time_millis_pal, _time_millis

@done:
    rts
.endproc

.proc _set_time_millis
    ; Get the command line arguments
    jsr popa
    sta _time_millis
    jsr popa
    sta _time_millis+1
    jsr popa
    sta _time_millis+2
    jsr popa
    sta _time_millis+3

    ; Divide the time by 16 to convert milliseconds to JIFFY
    ; This is done by shifting right by 4 bits
    lsr32 _time_millis
    lsr32 _time_millis
    lsr32 _time_millis
    lsr32 _time_millis

    ; Copy the provided time in milliseconds to the JIFFY counter
    ; This will drop the upper byte but all in all we lose 4 bits.
    lda _time_millis+2
    sta RTCLOK+0
    lda _time_millis+1
    sta RTCLOK+1
    lda _time_millis+0
    sta RTCLOK+2    

    ; Now we have to get it back to milliseconds
    jsr _get_time_millis

    rts
.endproc

