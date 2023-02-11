_int:
    addi r7, r0, 98
    ld r6, r7
    beq r6, r0, end
    addi r7, r0, 99
    st r6, r7
    iret
_start:
    jmp _start
end:
    hlt
