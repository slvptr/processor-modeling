import sys
from typing import Tuple, Union

from isa import InstructionType
import json


def parse_symbol(text: str) -> Tuple[str, int]:
    it = text[0]
    if (ord('a') <= ord(it) <= ord('z')) or \
            (ord('A') <= ord(it) <= ord('Z')) or \
            (ord('0') <= ord(it) <= ord('9')) or \
            it == '_':
        return it, 1
    return '', 0


def parse_digit(text: str) -> Tuple[str, int]:
    it = text[0]
    if ord('0') <= ord(it) <= ord('9'):
        return it, 1
    return '', 0


def parse_comma(text: str) -> Tuple[str, int]:
    if text[0] == ',':
        return ',', 1
    return '', 0


def parse_delimiter(text: str) -> Tuple[str, int]:
    if text[0] == ',' and text[1] == ' ':
        return ', ', 2
    return '', 0


def parse_word(text: str) -> Tuple[str, int]:
    word, ll = '', 0
    while True:
        ch, cnt = parse_symbol(text[ll:])
        if cnt == 0:
            break
        word += ch
        ll += cnt
    return word, ll


def parse_label(text: str) -> Tuple[str, int]:
    label, ll = parse_word(text)
    if text[ll] == ':':
        label, ll = label + ':', ll + 1
        return label, ll
    return '', 0


def parse_spaces(text: str) -> Tuple[str, int]:
    spaces, ll = "", 0
    while True:
        if text[ll] == ' ':
            spaces += ' '
            ll += 1
        else:
            break
    return spaces, ll


def parse_gap(text: str) -> Tuple[str, int]:
    gap, ll = '', 0
    while True:
        if ll < len(text) and (text[ll] in [' ', '\n', '\r', '\t']):
            gap += text[ll]
            ll += 1
        else:
            break
    return gap, ll


def parse_command(text: str) -> Tuple[str, int]:
    label, ll = '', 0
    while True:
        ch, cnt = parse_symbol(text[ll:])
        if cnt == 0:
            break
        label += ch
        ll += cnt
    if label in [
        'ld',
        'st',
        'jmp',
        'beq',
        'add',
        'addi',
        'sub',
        'subi',
        'mul',
        'div',
        'rem',
        'iret',
            'hlt']:
        return label, ll
    return '', 0


def parse_register(text: str) -> Tuple[str, int]:
    register, ll = '', 0
    for i in range(2):
        ch, cnt = parse_symbol(text[ll:])
        register += ch
        ll += cnt
    if register in [
        'r0',
        'r1',
        'r2',
        'r3',
        'r4',
        'r5',
        'r6',
        'r7',
        'pc',
            'sp']:
        return register, ll
    return '', 0


def parse_number(text: str) -> Tuple[str, int]:
    number, ll = "", 0
    while True:
        ch, cnt = parse_digit(text[ll:])
        if cnt == 0:
            break
        number += ch
        ll += cnt
    return number, ll


def parse_instruction(text) -> Tuple[dict, int]:
    instr: dict[str, Union[str, InstructionType]] = dict()
    ll: int = 0

    command, llt = parse_command(text[ll:])
    if llt == 0:
        return {}, 0
    ll += llt

    spaces, llt = parse_spaces(text[ll:])
    ll += llt

    register1, llt = parse_register(text[ll:])
    ll += llt
    if llt > 0:
        delimiter, llt = parse_delimiter(text[ll:])
        if llt == 0:
            return {}, 0
        ll += llt

        register2, llt = parse_register(text[ll:])
        if llt == 0:
            return {}, 0
        ll += llt

        delimiter, llt = parse_delimiter(text[ll:])
        ll += llt
        if llt == 0:
            return {"opcode": command, "rd": register1,
                    "rs": register2, "type": InstructionType.C}, ll

        register3, llt = parse_register(text[ll:])
        ll += llt
        if llt > 0:
            return {"opcode": command, "rd": register1, "rs1": register2,
                    "rs2": register3, "type": InstructionType.A}, ll

        word, llt = parse_word(text[ll:])
        if llt > 0 and command in ['beq', 'jmp']:
            ll += llt
            return {"opcode": command, "rs1": register1, "rs2": register2,
                    "label": word, "type": InstructionType.E}, ll

        number, llt = parse_number(text[ll:])
        ll += llt
        if llt > 0:
            return {"opcode": command, "rd": register1, "rs": register2,
                    "imm": word, "type": InstructionType.B}, ll

        return {}, 0

    word, llt = parse_word(text[ll:])
    ll += llt
    if llt > 0:
        return {"opcode": command, "label": word,
                "type": InstructionType.D}, ll

    return {"opcode": command, "type": InstructionType.F}, ll


def tokenize(text):
    tokens: list[Tuple[str, list]] = []
    cursor = 0
    while cursor < len(text) - 1:
        label, it = parse_label(text[cursor:])
        if it > 0:
            tokens.append((label, []))
            cursor += it
            continue

        instr, it = parse_instruction(text[cursor:])
        if it > 0:
            if len(tokens) > 0 and isinstance(tokens[-1], tuple):
                tokens[-1][1].append(instr)
            else:
                raise ValueError("Invalid token")
            cursor += it
            continue

        gap, it = parse_gap(text[cursor:])
        if it == 0:
            break
        cursor += it
    return tokens


def get_start_token_idx(tokens):
    start_token_idx = None
    for i in range(len(tokens)):
        if tokens[i][0] == "_start:":
            start_token_idx = i
            break
    return start_token_idx


def get_int_token_idx(tokens):
    int_token_idx = None
    for i in range(len(tokens)):
        if tokens[i][0] == "_int:":
            int_token_idx = i
            break
    return int_token_idx


def translate(text):
    tokens = tokenize(text + '\n')
    int_token_idx = get_int_token_idx(tokens)
    start_token_idx = get_start_token_idx(tokens)

    if start_token_idx is None:
        raise ValueError("There is no _start label")
    if int_token_idx is not None:
        tokens[0], tokens[int_token_idx] = tokens[int_token_idx], tokens[0]

    label_positions: dict[str, int] = {}
    cur_pos = 0
    for token in tokens:
        label_positions[token[0][:-1]] = cur_pos
        cur_pos += len(token[1])

    cur_pos = 0
    for token in tokens:
        for instr in token[1]:
            if 'label' in instr:
                instr['imm'] = label_positions[instr['label']] - cur_pos
            cur_pos += 1

    code = []
    for token in tokens:
        for instr in token[1]:
            if instr["type"] == InstructionType.A:
                code.append({"opcode": instr["opcode"],
                             "rd": instr["rd"],
                             "rs1": instr["rs1"],
                             "rs2": instr["rs2"]})

            elif instr["type"] == InstructionType.B:
                code.append({"opcode": instr["opcode"],
                             "rd": instr["rd"],
                             "rs": instr["rs"],
                             "imm": instr["imm"]})

            elif instr["type"] == InstructionType.C:
                code.append({"opcode": instr["opcode"], "rd": instr["rd"], "rs": instr["rs"]})

            elif instr["type"] == InstructionType.D:
                code.append({"opcode": instr["opcode"], "imm": instr["imm"]})

            elif instr["type"] == InstructionType.E:
                code.append({"opcode": instr["opcode"],
                             "rs1": instr["rs1"],
                             "rs2": instr["rs2"],
                             "imm": instr["imm"]})

            elif instr["type"] == InstructionType.F:
                code.append({"opcode": instr["opcode"]})

    target = {
        "start": label_positions["_start"],
        "code": code
    }
    return target


def main(args):
    assert len(args) == 2, \
        "2 argument required <input_file> <target_file>"
    source, target = args

    with open(source, "rt", encoding="utf-8") as f:
        source = f.read()

    program = translate(source)
    with open(target, "w", encoding="utf-8") as f:
        f.write(json.dumps(program))


if __name__ == '__main__':
    main(sys.argv[1:])
