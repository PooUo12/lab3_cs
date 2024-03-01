from enum import Enum


class Opcode(Enum):
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    JUMP = "jump"
    JMPZ = "jump_if_zero"
    JMPNZ = "jump_if_not_zero"
    JMPS = "jump_if_signed"
    JMPNS = "jump_if_not_signed"
    JMPSZ = "jump_if_signed_or_zero"
    JMPNSNZ = "jump_if_not_signed_and_not_zero"
    READ = "read_to_acc"
    WRITE = "write_to_mem"
    READADR = "read_address_to_acc"
    WRITEADR = "write_address_from_acc"
    INPUT = "input"
    OUTPUT = "output"
    BREAK = "stop_program"
