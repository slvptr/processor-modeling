_start:
    addi r1, r0, 3
    addi r2, r0, 5
    addi r3, r0, 1000
    jmp inc
inc:
    addi r4, r4, 1
    sub r5, r3, r4
    beq r5, r0, push_digits
    rem r5, r4, r1
    beq r5, r0, add
    rem r5, r4, r2
    beq r5, r0, add
    jmp inc
add:
    addi r7, r7, r4
    jmp inc
print:
    beq r5, r0, exit
    addi r2, r0, 99
    ld r3, sp
    addi r3, r3, 48
    st r3, r2
    addi sp, sp, 1
    subi r5, r5, 1
    jmp print
push_digits:
    addi r1, r0, 10
    beq r7, r0, print
    rem r6, r7, r1
    subi sp, sp, 1
    st r6, sp
    addi r5, r5, 1
    div r7, r7, r1
    jmp push_digits
exit:
    hlt





