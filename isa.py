import json
from enum import Enum


class InstructionType(str, Enum):
    A = "a",            # rd, rs1, rs2
    B = "b",            # rd, rs, imm
    C = "c",            # rd, rs
    D = "d",            # imm
    E = "e",             # rs1, rs2, imm
    F = "f"


class Opcode(str, Enum):
    LD = "ld",          # type C        rd <- mem[rs]
    ST = "st",          # type C        rd -> mem[rs]

    JMP = "jmp",        # type D        pc <- pc + imm
    BEQ = "beq",        # type E        if rs1 == rs2:    pc <- pc + imm

    ADD = "add",        # type A        rd <- rs1 + rs2
    ADDI = "addi",      # type B        rd <- rs + imm
    SUB = "sub",        # type A        rd <- rs1 - rs2
    SUBI = "subi",      # type B        rd <- rs - imm
    MUL = "mul",        # type A        rd <- rs1 * rs2
    DIV = "div",        # type A        rd <- rs1 // rs2
    REM = "rem",        # type A        rd <- rs1 % rs2

    IRET = "iret",      # type F
    HLT = "hlt",        # type F


class Register(str, Enum):
    R0 = "r0",
    R1 = "r1",
    R2 = "r2",
    R3 = "r3",
    R4 = "r4",
    R5 = "r5",
    R6 = "r6",
    R7 = "r7",
    PC = "pc",
    SP = "sp",


def read_program(filename: str):
    with open(filename, encoding='utf-8') as file:
        program = json.load(file)
        for instr in program["code"]:
            instr["opcode"] = Opcode(instr["opcode"])
            if len(instr) == 4:
                if ('imm' in instr) and ('rs' in instr):
                    instr["type"] = InstructionType.B
                elif 'imm' in instr:
                    instr["type"] = InstructionType.E
                else:
                    instr["type"] = InstructionType.A
            elif len(instr) == 3:
                instr["type"] = InstructionType.C
            elif len(instr) == 2:
                instr["type"] = InstructionType.D
            elif len(instr) == 1:
                instr["type"] = InstructionType.F

    return program
