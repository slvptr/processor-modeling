## Язык программирования 
### EBNF

``` ebnf
program ::= {[label] [instruction] {newline | space}}
label ::= {symbol}':'
word ::= {symbol}
instruction ::= command [(register, register, register) | (register, register, number) |
                        (register, register, word) | (register, register) | number]

register ::= 'r0' | 'r1' | 'r2' | 'r3' | 'r4' | 'r5' | 'r6' | 'r7' | 'pc' | 'sp'

newline ::= \n
space :== \s
symbol ::= [a-zA-Z0-9_]
number ::= [0-9]+
command ::= 'ld' | 'st' | 'jmp' | 'beq' | 'add' | 'addi' | 'sub' | 'subi' |
            'mul' | 'div' | 'rem' | 'iret' | 'hlt'
```


Типы инструкций:

    A            # rd, rs1, rs2
    B            # rd, rs, imm
    C            # rd, rs
    D            # imm
    E            # rs1, rs2, imm
    F            # no args

Инструкции:

    ld rd, rs                # type C        rd <- mem[rs]
    st rd, rs                # type C        rd -> mem[rs]

    jmp imm                  # type D        pc <- pc + imm
    beq rs1, rs2, imm        # type E        if rs1 == rs2:    pc <- pc + imm   

    add rd, rs1, rs2         # type A        rd <- rs1 + rs2   
    addi rd, rs, imm         # type B        rd <- rs + imm
    sub rd, rs1, rs2         # type A        rd <- rs1 - rs2
    subi rd, rs, imm         # type B        rd <- rs - imm
    mul rd, rs1, rs2         # type A        rd <- rs1 * rs2
    div rd, rs1, rs2         # type A        rd <- rs1 // rs2
    rem rd, rs1, rs2         # type A        rd <- rs1 % rs2

    iret                     # type F
    hlt                      # type F


Код выполняется последовательно, начиная с метки _start.

Специальные метки:

    _start  точка входа
    _int    обработчик прерывания (ввод)

## Организация памяти

    ____________________ 
    | IRQ_HANDLER_ADDR |
    | ...              |
    | ...              |
    | STACK BEGINNING  |
    | INPUT            |
    | OUTPUT           |
    |__________________| 

Модель памяти процессора:

- Память общая для команд и данных. Каждая ячейка является либо словарем, описывающим инструкцию, либо числом. В начале находится адрес обработчика прерывания input. Предпоследний адрес соответствует устройству ввода, последний устройству вывода.

Типы адресации:

- Прямая регистровая: операндом инструкции является регистр.
- Непосредственная загрузка: одним из операндов является константа, подаваемая как один из аргументов.

## Особенности процессора

Интерфейс командной строки: `machine.py <file_code> <file_input>"`

- Машинное слово -- знаковое, 32 бита

- АЛУ:
    - на левый вход АЛУ вместо регистра может быть подана константа из инструкции;
    - АЛУ поддерживает операции: `ADD`, `SUB`, `MUL`, `DIV`, `REM`
- Регистры:
    - 7 регистров общего назначения (`R1`, `R2`, `R3`, `R4`, `R5`, `R6`, `R7`)
    - регистр `R0` всегда содержит значение 0
    - регистр, хранящий program counter, `PC`
    - регистр, указатель на вершину стека, `SP`
- Ввод-вывод:
    - memory-mapped через систему прерываний.
- program_counter -- счётчик команд:
    - инкрементируется после каждой инструкции или перезаписывается инструкцией перехода.


### Кодирование инструкций

- Код ассемблера сериализуется в инструкции в формате JSON
```
{
    "start: 0,
    "code": [{"opcode": "add", "rd": "r1", "rs1: "r5", "rs2: "r6" }, ...]
}
```

где:
- start: точка входа
- code: инструкции

Типы данных в модуле isa, где:
- Opcode -- перечисление кодов операций;
- InstructionType -- типы инструкции;
- Register -- перечисление регистров процессора;

## Транслятор

Интерфейс командной строки: `translator.py <program.asm> <target>"`

Этапы трансляции (функция `translate`):

1. Разбиение текста на токены -- (label, [instr1, instr2, ...])
2. Установка токена _int в начало программы
2. Преобразование меток в адреса
3. Генерация машинного кода


### Схема DataPath и ControlUnit

![https://drive.google.com/file/d/1eVrgHuvZY1H4tJJuMHTfdRYEOCf-4IDP/view](/images/image.png "Схема DataPath и ControlUnit") 

## DataPath

Реализован в классе `DataPath`.

- `memory` -- смешанная память
- `registers` -- регистры процессора
- `alu` -- АЛУ, выполняющее арифметические операции
- - `alu.op1` -- данные с левого входа АЛУ
- - `alu.op2` -- данные с правого входа АЛУ
- - `alu.opcode` -- установленный код операции
- - `alu.result` -- результат вычисления
- - `alu.ZF` -- zero флаг АЛУ, передается на CU по сигналу, используется для условных переходов
- `input_buf` -- буфер с входными данными от внешнего устройства
- `output_buf` -- буфер вывода.
- `mem_addr_bus` -- шина адреса в памяти, соединяется с выходом АЛУ
- `input_map_addr` -- адрес устройства ввода в памяти
- `output_map_addr` -- адрес устройства вывода в памяти

Сигналы:

- `io_get` -- подать сигнал на запись символа из буфера ввода в регистр
- `io_put` -- подать сигнал на добавление в буфер вывода значения из регистра
- `latch_alu` -- рассчитать выходное значение АЛУ
- `latch_calc_on_register` -- защелкнуть результат вычисления АЛУ на регистр
- `latch_calc_on_memory` -- защелкнуть результат вычисления АЛУ на шину адреса
- `mem_read` -- прочитать значение из памяти (по адресу mem_addr_bus) в регистр
- `mem_write` -- заисать значение из регистра в пямять (по адресу mem_addr_bus)

Флаги:
- `ZF` -- отражает наличие нулевого значения на выходе АЛУ. Используется для условных переходов.

## ControlUnit
Реализован в классе `ControlUnit`.

- Hardwired (реализовано полностью на python).
- Моделирование на уровне инструкций.
- Трансляция инструкции в последовательность сигналов: `decode_and_execute_instruction`.

Функции (наборы сигналов):

- `inc_program_counter` -- инкрементировать PC
- `pop_program_counter` -- записать в PC значение с вершины стека и инкрементировать SP
- `push_program_counter` -- декрементировать SP и записать значение PC на вершнину стека


Особенности работы модели:

- Для журнала состояний процессора используется стандартный модуль logging.
- Количество инструкций для моделирования ограничено параметром `limit`.
- Управление симуляцией реализовано в функции `simulation`.

#### Прерывания
- Система прерываний реализована через проверку наличия сигнала от ВУ в начале цикла выборки инструкции.
- Прерывания обслуживаются относительно: при поступлении сигнала прерывания во время нахождения в прерывании сигнал будет проигнорирован.
- В CU хранится адрес вектора прерывания.
- При прерывании по адресу `SP` сохраняется счетчик команд `PC`, `SP` декрементируется.
 Далее новое значение `PC` берется из памяти данных по адресу из вектора прерываний.

## Апробация

В качестве тестов использовано три алгоритма:

1. [hello world](tests/hello.asm).
2. [cat](tests/cat.asm) -- программа `cat`, повторяем ввод на выводе.
3. [prob1](tests/prob1.asm) -- рассчитать сумму делителей 3 или 5, меньших 1000
```

Пример использования и журнал работы процессора на примере `cat`:

``` commandline
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 1 | tick: 4 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 2 | tick: 7 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 3 | tick: 10 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 4 | tick: 12 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 5 | tick: 15 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 6 | tick: 18 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 7 | tick: 21 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 8 | tick: 25 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 9 | tick: 28 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 10 | tick: 31 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 11 | tick: 33 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 12 | tick: 36 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 13 | tick: 39 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 14 | tick: 42 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 15 | tick: 46 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 16 | tick: 49 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 17 | tick: 52 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 18 | tick: 54 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 19 | tick: 57 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 20 | tick: 60 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 21 | tick: 63 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 22 | tick: 65 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 23 | tick: 67 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 24 | tick: 69 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 25 | tick: 73 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 26 | tick: 76 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 27 | tick: 79 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 28 | tick: 81 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 29 | tick: 84 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 30 | tick: 87 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 31 | tick: 90 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 32 | tick: 92 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 33 | tick: 94 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 34 | tick: 96 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 35 | tick: 98 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 36 | tick: 100 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 37 | tick: 104 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 38 | tick: 107 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 39 | tick: 110 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 40 | tick: 112 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 41 | tick: 115 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 42 | tick: 118 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 43 | tick: 121 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 44 | tick: 125 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 45 | tick: 128 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 46 | tick: 131 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 47 | tick: 133 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 48 | tick: 136 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 49 | tick: 139 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 50 | tick: 142 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 51 | tick: 146 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 52 | tick: 149 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 53 | tick: 152 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 54 | tick: 154 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 55 | tick: 157 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 56 | tick: 160 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 57 | tick: 163 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 58 | tick: 165 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 59 | tick: 167 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 60 | tick: 169 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 61 | tick: 171 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 62 | tick: 173 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 63 | tick: 175 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 64 | tick: 177 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 65 | tick: 179 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 66 | tick: 183 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 67 | tick: 186 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 68 | tick: 189 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 69 | tick: 191 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 70 | tick: 194 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 71 | tick: 197 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 72 | tick: 200 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 73 | tick: 204 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 74 | tick: 207 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 75 | tick: 210 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 76 | tick: 212 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 77 | tick: 215 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 78 | tick: 218 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 79 | tick: 221 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 80 | tick: 225 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 81 | tick: 228 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 82 | tick: 231 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 83 | tick: 233 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 84 | tick: 236 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 85 | tick: 239 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 86 | tick: 242 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 87 | tick: 244 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 88 | tick: 246 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 89 | tick: 250 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 90 | tick: 253 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 91 | tick: 256 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 92 | tick: 258 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 93 | tick: 261 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 94 | tick: 264 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 95 | tick: 267 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 96 | tick: 269 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 97 | tick: 271 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 98 | tick: 273 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 99 | tick: 275 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 100 | tick: 277 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 101 | tick: 279 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 102 | tick: 281 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 103 | tick: 283 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 104 | tick: 285 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 105 | tick: 287 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 106 | tick: 289 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 107 | tick: 291 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 108 | tick: 295 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 109 | tick: 298 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 110 | tick: 301 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 111 | tick: 303 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 112 | tick: 306 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 113 | tick: 309 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 114 | tick: 312 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 115 | tick: 314 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 116 | tick: 316 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 117 | tick: 318 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 118 | tick: 320 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 119 | tick: 322 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 120 | tick: 324 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 121 | tick: 326 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 122 | tick: 328 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 123 | tick: 330 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 124 | tick: 332 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 125 | tick: 334 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 126 | tick: 336 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 127 | tick: 338 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 128 | tick: 340 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 129 | tick: 342 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 130 | tick: 346 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 131 | tick: 349 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 132 | tick: 352 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 23 | instr_counter: 133 | tick: 354 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:is_interrupted: True | PC: 24 | instr_counter: 134 | tick: 357 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '99', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 25 | instr_counter: 135 | tick: 360 | last_instr: {'opcode': <Opcode.ST: 'st'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 136 | tick: 363 | last_instr: {'opcode': <Opcode.IRET: 'iret'>, 'type': <InstructionType.F: 'f'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 137 | tick: 365 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 138 | tick: 367 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 139 | tick: 369 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 140 | tick: 371 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 141 | tick: 373 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 142 | tick: 375 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 143 | tick: 377 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 144 | tick: 379 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 145 | tick: 381 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 146 | tick: 383 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 147 | tick: 385 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 148 | tick: 387 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: False | PC: 26 | instr_counter: 149 | tick: 389 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 20 | instr_counter: 150 | tick: 393 | last_instr: {'opcode': <Opcode.JMP: 'jmp'>, 'imm': 0, 'type': <InstructionType.D: 'd'>}
DEBUG:root:is_interrupted: True | PC: 21 | instr_counter: 151 | tick: 396 | last_instr: {'opcode': <Opcode.ADDI: 'addi'>, 'rd': 'r7', 'rs': 'r0', 'imm': '98', 'type': <InstructionType.B: 'b'>}
DEBUG:root:is_interrupted: True | PC: 22 | instr_counter: 152 | tick: 399 | last_instr: {'opcode': <Opcode.LD: 'ld'>, 'rd': 'r6', 'rs': 'r7', 'type': <InstructionType.C: 'c'>}
DEBUG:root:is_interrupted: True | PC: 27 | instr_counter: 153 | tick: 402 | last_instr: {'opcode': <Opcode.BEQ: 'beq'>, 'rs1': 'r6', 'rs2': 'r0', 'imm': 5, 'type': <InstructionType.E: 'e'>}
DEBUG:root:{<Register.R0: 'r0'>: 0, <Register.R1: 'r1'>: 0, <Register.R2: 'r2'>: 0, <Register.R3: 'r3'>: 0, <Register.R4: 'r4'>: 0, <Register.R5: 'r5'>: 0, <Register.R6: 'r6'>: 0, <Register.R7: 'r7'>: 98, <Register.PC: 'pc'>: 27, <Register.SP: 'sp'>: 70}
output: Hello, world!
instr: 154  ticks: 403
```
