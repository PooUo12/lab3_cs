from __future__ import annotations

import json
from pathlib import Path

from opc import Opcode

NO_ADDRESS = 0
INT_FLAG = 0
STR_FLAG = 1
IO_STRING_RESERVE = 1001
INPUT_END_RESERVE = 1002

mach_code = []
new_vars = []
current_var_mem = 1000
current_inst_mem = 0
mapping = {}


def create_inst(opcode: str, var_addr: int) -> None:
    global current_inst_mem
    mach_code.append({"value": {"opcode": opcode, "address": var_addr}, "address": current_inst_mem})
    current_inst_mem += 1


def create_var(val: int, addr: int) -> dict[str, object]:
    return {"value": val, "address": addr}


def new_var(flag: int, val: str, name: str) -> None:
    global current_var_mem
    if flag == 0:
        new_vars.append(create_var(int(val), current_var_mem))
        mapping[name] = current_var_mem
        current_var_mem -= 1
    else:
        new_vars.append(create_var(len(val), current_var_mem))
        mapping[name] = current_var_mem
        current_var_mem -= 1
        for i in val:
            new_vars.append(create_var(ord(i), current_var_mem))
            current_var_mem -= 1


def parse_math(tokens: list[str]) -> int:
    variables: list[int] = []
    operands = []
    for i in range(len(tokens)):
        if tokens[i] == "(":
            operands.append(tokens[i])
        elif tokens[i] == ")":
            while operands[-1] != "(":
                update_var = apply_operand(operands.pop(), variables.pop(), variables.pop())
                variables.append(update_var)
            operands.pop()
        elif tokens[i] in ("+", "-", "*", "/"):
            while len(operands) > 0 and has_priority(tokens[i], operands[-1]):
                update_var = apply_operand(operands.pop(), variables.pop(), variables.pop())
                variables.append(update_var)
            operands.append(tokens[i])
        else:
            if tokens[i] not in mapping:
                new_var(0, tokens[i], tokens[i])
            variables.append(mapping[tokens[i]])
    while len(operands) > 0:
        variables.append(apply_operand(operands.pop(), variables.pop(), variables.pop()))
    return variables[0]


def apply_operand(op: str, var2: int, var1: int) -> int:
    create_inst(Opcode.READ.name, var1)
    if op == "+":
        create_inst(Opcode.ADD.name, var2)
    elif op == "-":
        create_inst(Opcode.SUB.name, var2)
    elif op == "*":
        create_inst(Opcode.MUL.name, var2)
    elif op == "/":
        create_inst(Opcode.DIV.name, var2)
    create_inst(Opcode.WRITE.name, var1)
    return var1


def has_priority(op1: str, op2: str) -> bool:
    if op2 == "(" or op2 == ")":
        return False
    if (op1 == "*" or op1 == "/") and (op2 == "+" or op2 == "-"):
        return False
    return True


def inequality_sign_parse(sign: str) -> None:
    match sign:
        case ">":
            create_inst(Opcode.JMPNSNZ.name, current_var_mem)
        case ">=":
            create_inst(Opcode.JMPNS.name, current_var_mem)
        case "<":
            create_inst(Opcode.JMPS.name, current_var_mem)
        case "<=":
            create_inst(Opcode.JMPSZ.name, current_var_mem)
        case "==":
            create_inst(Opcode.JMPZ.name, current_var_mem)
        case "!=":
            create_inst(Opcode.JMPNZ.name, current_var_mem)


def start_while(op_1: int, op_2: int, sign: str) -> None:
    create_inst(Opcode.READ.name, op_1)
    create_inst(Opcode.SUB.name, op_2)
    inequality_sign_parse(sign)


def check_if_new_numbers_in_mapping(num1: str, num2: str) -> None:
    if num1 not in mapping:
        new_var(0, num1, num1)
    if num2 not in mapping:
        new_var(0, num2, num2)


def translate(prog: list[str]) -> None:
    count = 0
    global current_var_mem
    for i in range(len(prog)):
        line = prog[i].split(" ")
        match line[0].split("(")[0]:
            case "int":
                new_var(0, line[2], line[1])
            case "string":
                new_var(1, " ".join(line[2:]), line[1])
            case "while":
                check_if_new_numbers_in_mapping(str(line[1]), str(line[3]))
                start_while(mapping[line[1]], mapping[line[3]], line[2])
                count = 0
                for j in range(i, len(prog)):
                    count += 1
                    if prog[j] == "endWhile":
                        create_inst(Opcode.JUMP.name, count + 4)
                        break
            case "endWhile":
                create_inst(Opcode.JUMP.name, -(count + 6))
            case "new":
                mapping[line[1]] = parse_math(line[3:])
            case "input_str":
                check_if_new_numbers_in_mapping(str(0), str(1))
                create_inst(Opcode.READ.name, mapping[str(0)])
                create_inst(Opcode.WRITE.name, IO_STRING_RESERVE)
                start_while(IO_STRING_RESERVE, mapping[str(0)], "==")
                create_inst(Opcode.JUMP.name, 4)
                create_inst(Opcode.INPUT.name, STR_FLAG + 2)  # Если ввод кончился джампим из вайла
                create_inst(Opcode.OUTPUT.name, STR_FLAG)
                create_inst(Opcode.JUMP.name, -6)
            case "input_int":
                var = line[0].split("(")[1].split(")")[0]
                create_inst(Opcode.INPUT.name, INT_FLAG)
                mapping[var] = current_var_mem
                create_inst(Opcode.WRITE.name, mapping[var])
                current_var_mem -= 1
            case "output_int":
                var = line[0].split("(")[1].split(")")[0]
                create_inst(Opcode.READ.name, mapping[var])
                create_inst(Opcode.OUTPUT.name, INT_FLAG)
            case "output_str":
                check_if_new_numbers_in_mapping(str(0), str(1))
                var = line[0].split("(")[1].split(")")[0]
                create_inst(Opcode.READ.name, mapping[str(0)])
                create_inst(Opcode.WRITE.name, IO_STRING_RESERVE)
                start_while(IO_STRING_RESERVE, mapping[var], "<")
                create_inst(Opcode.JUMP.name, 9)
                create_inst(Opcode.READ.name, IO_STRING_RESERVE)
                create_inst(Opcode.ADD.name, mapping[str(1)])
                create_inst(Opcode.WRITE.name, IO_STRING_RESERVE)
                create_inst(Opcode.READADR.name, mapping[var])
                create_inst(Opcode.SUB.name, IO_STRING_RESERVE)
                create_inst(Opcode.WRITEADR.name, NO_ADDRESS)
                create_inst(Opcode.OUTPUT.name, STR_FLAG)
                create_inst(Opcode.JUMP.name, -11)


def main(code_file: Path, mem_file: Path) -> None:
    global mach_code, new_vars, current_var_mem, current_inst_mem, mapping
    mach_code = []
    new_vars = []
    current_var_mem = 1000
    current_inst_mem = 0
    mapping = {}
    # try:
    with Path(code_file).open() as f:
        prog = list(filter(None, f.read().replace("\n", "").split(";")))
    translate(prog)
    with Path(mem_file).open("w") as f:
        for i in mach_code:
            f.write(json.dumps(i) + "\n")
        for i in new_vars:
            f.write(json.dumps(i) + "\n")
    # except Exception:
    #     pass


if __name__ == "__main__":
    main(Path("files/code.txt"), Path("files/mem.txt"))
