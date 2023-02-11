import sys
import ast
from typing import Union, Tuple
import logging
from isa import Opcode, Register, InstructionType, read_program
from exceptions import OutOfBufferException, AluOpcodeException, ZeroRegisterModificationException
from enum import Enum


class AluOperation(str, Enum):
    ADD = "add",
    SUB = "sub",
    MUL = "mul",
    DIV = "div",
    REM = "rem",


class Alu:
    def __init__(self):
        self.op1: int = 0
        self.op2: int = 0
        self.result: int = 0
        self.opcode: AluOperation = AluOperation.ADD
        self.ZF = 0

    def execute(self):
        self.ZF = 0

        if self.opcode == AluOperation.ADD:
            self.result = self.op1 + self.op2
        elif self.opcode == AluOperation.SUB:
            self.result = self.op1 - self.op2
        elif self.opcode == AluOperation.MUL:
            self.result = self.op1 * self.op2
        elif self.opcode == AluOperation.DIV:
            self.result = self.op1 // self.op2
        elif self.opcode == AluOperation.REM:
            self.result = self.op1 % self.op2
        else:
            raise AluOpcodeException("There is not such ALU's instruction")

        if self.result == 0:
            self.ZF = 1


class DataPath:
    """
    Memory:
    ____________________
    | IRQ_HANDLER_ADDR |
    | ...              |
    | ...              |
    | STACK BEGINNING  |
    | INPUT            |
    | OUTPUT           |
    |__________________|
    """

    def __init__(self, memory):
        self.registers: dict[Register, int] = {
            Register.R0: 0,
            Register.R1: 0,
            Register.R2: 0,
            Register.R3: 0,
            Register.R4: 0,
            Register.R5: 0,
            Register.R6: 0,
            Register.R7: 0,
            Register.PC: 0,
            Register.SP: len(memory) - 3,
        }
        self.memory: list[Union[dict[str, str], int]] = memory
        self.alu = Alu()
        self.input_buf: int = -1
        self.output_buf: list[str] = []
        self.mem_addr_bus: int = 0
        self.input_map_addr: int = len(memory) - 2
        self.output_map_addr: int = len(memory) - 1

    def io_get(self, rd: Register):
        if self.input_buf == -1:
            raise OutOfBufferException()
        self.registers[rd] = self.input_buf

    def io_put(self, rs: Register):
        self.output_buf.append(chr(self.registers[rs]))

    def latch_alu(self, op1: int, op2: int, opcode: AluOperation):
        self.alu.op1 = op1
        self.alu.op2 = op2
        self.alu.opcode = opcode
        self.alu.execute()

    def latch_calc_on_register(self, rd: Register):
        self.registers[rd] = self.alu.result

    def latch_calc_on_memory(self):
        self.mem_addr_bus = self.alu.result

    def mem_read(self, rd: Register):
        tmp = self.memory[self.mem_addr_bus]
        if not isinstance(tmp, int):
            raise ValueError("Attempt to write an instruction to a register")
        self.registers[rd] = tmp

    def mem_write(self, rs: Register):
        self.memory[self.mem_addr_bus] = self.registers[rs]


class ControlUnit:
    def __init__(self, data_path, input_irq, limit):
        self.data_path = data_path
        self.input_irq: dict[int, str] = input_irq
        self.input_irq_handler = 0
        self.limit: int = limit
        self.is_interrupted: bool = False
        self.last_instr = {}
        self.instr_counter = 0
        self._tick: int = 0

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def bound(self, num: int):
        if num > 2147483647:
            return -2147483648 + (num - 2147483647)
        if num < -2147483648:
            return 2147483647 - (num + 2147483648)
        return num

    def inc_program_counter(self):
        pc_current = self.data_path.registers[Register.PC]
        self.data_path.latch_alu(pc_current, 1, AluOperation.ADD)
        self.data_path.latch_calc_on_register(Register.PC)
        self.tick()

    def push_program_counter(self):
        sp_current = self.data_path.registers[Register.SP]
        self.data_path.latch_alu(sp_current, 1, AluOperation.SUB)
        self.data_path.latch_calc_on_register(Register.SP)
        self.tick()
        sp_current = self.data_path.registers[Register.SP]
        self.data_path.latch_alu(sp_current, 0, AluOperation.ADD)
        self.data_path.latch_calc_on_memory()
        self.data_path.mem_write(Register.PC)
        self.tick()

    def pop_program_counter(self):
        sp_current = self.data_path.registers[Register.SP]
        self.data_path.latch_alu(sp_current, 0, AluOperation.ADD)
        self.data_path.latch_calc_on_memory()
        self.data_path.mem_read(Register.PC)
        self.tick()
        self.data_path.latch_alu(sp_current, 1, AluOperation.SUB)
        self.data_path.latch_calc_on_register(Register.SP)
        self.tick()

    def decode_and_execute_instruction(self):
        op1 = self.data_path.registers[Register.PC]
        op2 = 0
        alu_op = AluOperation.ADD
        self.data_path.latch_alu(op1, op2, alu_op)
        self.data_path.latch_calc_on_memory()
        self.tick()
        instr = self.data_path.memory[self.data_path.mem_addr_bus]

        self.last_instr = instr
        self.instr_counter += 1

        past_irq = list(filter(lambda x: x <= self.current_tick(), self.input_irq.keys()))

        if not self.is_interrupted and len(past_irq) > 0:
            current_char = self.input_irq[max(past_irq)]
            self.input_irq = {k: v for k, v in self.input_irq.items() if k > self.current_tick()}
            self.is_interrupted = True
            self.push_program_counter()
            self.data_path.registers[Register.PC] = self.data_path.memory[0]
            self.data_path.input_buf = ord(current_char)
            self.tick()
            return

        if instr['opcode'] == Opcode.HLT:
            raise StopIteration()

        if instr['opcode'] == Opcode.IRET:
            self.is_interrupted = False
            self.pop_program_counter()
            return

        if ('rd' in instr) and (instr['rd'] == 'r0'):
            raise ZeroRegisterModificationException(
                "It's not allowed to modify R0")

        if instr["type"] == InstructionType.A or instr["type"] == InstructionType.E:
            op1 = self.data_path.registers[Register(instr['rs1'])]
            op2 = self.data_path.registers[Register(instr['rs2'])]
        elif instr["type"] == InstructionType.B:
            op1 = self.data_path.registers[Register(instr['rs'])]
            op2 = self.bound(int(instr['imm']))
        elif instr["type"] == InstructionType.C:
            op1 = self.data_path.registers[Register(instr['rs'])]
            op2 = 0
        elif instr["type"] == InstructionType.D:
            op1 = self.bound(int(instr['imm']))
            op2 = self.data_path.registers[Register.PC]

        if instr['opcode'] in [
                Opcode.ADD,
                Opcode.SUB,
                Opcode.MUL,
                Opcode.DIV,
                Opcode.REM]:
            alu_op = AluOperation(instr['opcode'].value)
        elif instr['opcode'] == Opcode.ADDI:
            alu_op = AluOperation.ADD
        elif instr['opcode'] == Opcode.SUBI:
            alu_op = AluOperation.SUB
        elif instr['opcode'] == Opcode.LD:
            alu_op = AluOperation.ADD
        elif instr['opcode'] == Opcode.ST:
            alu_op = AluOperation.ADD
        elif instr['opcode'] == Opcode.JMP:
            alu_op = AluOperation.ADD
        elif instr['opcode'] == Opcode.BEQ:
            alu_op = AluOperation.SUB

        self.data_path.latch_alu(op1, op2, alu_op)
        if instr['opcode'] not in [
                Opcode.JMP,
                Opcode.BEQ,
                Opcode.ST,
                Opcode.LD]:
            self.data_path.latch_calc_on_register(Register(instr['rd']))
            self.tick()
            self.inc_program_counter()
        if instr['opcode'] == Opcode.LD:
            self.data_path.latch_calc_on_memory()
            if self.data_path.mem_addr_bus == self.data_path.input_map_addr:
                self.data_path.io_get(Register(instr['rd']))
            else:
                self.data_path.mem_read(Register(instr['rd']))
            self.tick()
            self.inc_program_counter()
        if instr['opcode'] == Opcode.ST:
            self.data_path.latch_calc_on_memory()
            if self.data_path.mem_addr_bus == self.data_path.output_map_addr:
                self.data_path.io_put(Register(instr['rd']))
            else:
                self.data_path.mem_write(Register(instr['rd']))
            self.tick()
            self.inc_program_counter()
        if instr['opcode'] == Opcode.JMP:
            self.data_path.latch_calc_on_register(Register.PC)
            self.tick()
        if instr['opcode'] == Opcode.BEQ:
            if self.data_path.alu.ZF:
                self.tick()
                op1 = self.data_path.registers[Register.PC]
                op2 = self.bound(int(instr['imm']))
                alu_op = AluOperation.ADD
                self.data_path.latch_alu(op1, op2, alu_op)
                self.data_path.latch_calc_on_register(Register.PC)
                self.tick()
            else:
                self.inc_program_counter()

    def __repr__(self):
        return f'is_interrupted: {self.is_interrupted} | ' \
               f'PC: {self.data_path.registers[Register.PC]} | ' \
               f'instr_counter: {self.instr_counter} | ' \
               f'tick: {self.current_tick()} | ' \
               f'last_instr: {self.last_instr}'


def initialize_vectors(memory, handler_addr):
    memory[0] = handler_addr


def load_program(memory, code, start):
    for i in range(len(code)):
        memory[start + i] = code[i]


def simulation(program, input_schedule, data_memory_size: int,
               limit: int) -> Tuple[str, int, int]:
    assert data_memory_size >= 100, "Memory size have to be >= 100"

    memory = [0] * data_memory_size
    program_addr = 20

    initialize_vectors(memory, program_addr)
    load_program(memory, program["code"], program_addr)

    data_path = DataPath(memory)
    data_path.registers[Register.PC] = program_addr + int(program["start"])
    input_irq = dict(input_schedule)
    control_unit = ControlUnit(data_path, input_irq, limit)
    instr_counter = 0

    try:
        while True:
            assert instr_counter <= limit, "too long execution, increase limit!"
            control_unit.decode_and_execute_instruction()
            instr_counter += 1
            logging.debug(repr(control_unit))
    except StopIteration:
        instr_counter += 1
        pass
    except Exception as e:
        logging.error("Error message:", e)
        logging.error(data_path.memory)

    logging.debug(data_path.registers)
    return ''.join(
        data_path.output_buf), instr_counter, control_unit.current_tick()


def main(args):
    assert len(args) == 2, "2 arguments required <program_file> <input_file>"
    program_file, input_file = args

    program = read_program(program_file)
    with open(input_file, encoding='utf-8') as file:
        input_schedule = ast.literal_eval(file.read())

    output, instr_counter, ticks = simulation(
        program, input_schedule=input_schedule, data_memory_size=100, limit=10000)

    print(f'output: {output}\ninstr: {instr_counter}  ticks: {ticks}')


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    main(sys.argv[1:])
