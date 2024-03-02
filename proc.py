from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from opc import Opcode


class DataPath:
    memory: list[dict[str, object]] = []
    memory_address = 0
    acc = 0
    instruction: Any = {}
    program_counter = 0
    input_tokens: list[str] = []
    calc_type: Any = None
    zero_flag = 0
    signed_flag = 0
    input_flag = 0
    output_tokens: list[str] = []

    def __init__(self, memory: list[dict[str, object]], input_tokens: list[str]) -> None:
        self.memory = memory
        self.input_tokens = input_tokens
        self.program_counter = 0
        self.acc = 0
        self.memory_address = 0
        self.zero_flag = 0
        self.signed_flag = 0
        self.input_flag = 0
        self.output_tokens = []

    def get_zero_flag(self) -> int:
        return self.zero_flag

    def get_acc(self) -> int:
        return self.acc

    def get_memory_address(self) -> int:
        return self.memory_address

    def get_pc(self) -> int:
        return self.program_counter

    def get_input_flag(self) -> int:
        return self.input_flag

    def get_signed_flag(self) -> int:
        return self.signed_flag

    def get_instruction(self) -> Any:
        return self.instruction

    def set_calc_type(self, calc_type: str) -> None:
        match calc_type:
            case "read":
                self.calc_type = lambda x, y: int(y)
            case "add":
                self.calc_type = lambda x, y: int(x) + int(y)
            case "sub":
                self.calc_type = lambda x, y: int(x) - int(y)
            case "mul":
                self.calc_type = lambda x, y: int(x) * int(y)
            case "div":
                self.calc_type = lambda x, y: int(x) // int(y)

    def mem_read(self) -> object:
        for i in self.memory:
            if i["address"] == self.memory_address:
                return i["value"]
        return None

    def latch_acc(self, sel_acc: str) -> None:
        if sel_acc == "input":
            if self.instruction["address"] == 0:
                self.acc = int("".join(self.input_tokens))
            elif len(self.input_tokens) == 0:
                self.input_flag = 1
            else:
                self.acc = ord(self.input_tokens.pop(0))
        elif sel_acc == "count":
            self.acc = self.calc_type(self.acc, self.mem_read())
        elif sel_acc == "address":
            self.acc = self.memory_address

        if self.acc == 0:
            self.zero_flag = 1
        else:
            self.zero_flag = 0
        if self.acc < 0:
            self.signed_flag = 1
        else:
            self.signed_flag = 0

    def output(self) -> None:
        if self.instruction["address"] == 1:
            self.output_tokens.append(chr(self.acc))
        else:
            self.output_tokens.append(str(self.acc))

    def mem_write(self) -> None:
        for i in self.memory:
            if i["address"] == self.memory_address:
                i["value"] = self.acc
                return
        self.memory.append({"value": self.acc, "address": self.memory_address})

    def latch_inst(self) -> None:
        self.instruction = self.mem_read()

    def latch_pc(self, sel_pc: str) -> None:
        if sel_pc == "jump":
            self.program_counter += self.instruction["address"]
        elif sel_pc == "skip_jump":
            self.program_counter += 2
        elif sel_pc == "next":
            self.program_counter += 1

    def latch_address(self, sel_address: str) -> None:
        if sel_address == "instr":
            self.memory_address = self.program_counter
        elif sel_address == "var":
            self.memory_address = self.instruction["address"]
        elif sel_address == "acc":
            self.memory_address = self.acc


class ControlUnit:
    tick = 0
    data_path: Any = None

    def __init__(self, data_path: DataPath) -> None:
        self.tick = 1
        self.data_path = data_path
        self.read_instruction()

    def new_tick(self) -> None:
        logging.info(
            " tact: {tick} acc: {acc} memory_address: {mem} PC: {PC} inst: {inst}".format(
                tick=self.tick, acc=self.data_path.get_acc(),
                PC=self.data_path.get_pc(), mem=self.data_path.get_memory_address(),
                inst=self.data_path.get_instruction(),
            ))
        self.tick += 1

    def read_instruction(self) -> None:
        self.data_path.latch_address("instr")
        self.data_path.latch_inst()
        self.new_tick()
        self.execute_instruction()

    def execute_instruction(self) -> None:
        if self.data_path.get_instruction() is None:
            raise StopIteration()  # Instructions finished
        match self.data_path.get_instruction()["opcode"]:
            case Opcode.ADD.name:
                self.data_path.set_calc_type("add")
                self.data_path.latch_address("var")
                self.data_path.latch_acc("count")
                self.data_path.latch_pc("next")  # Инструкция выполнилась, увеличиваем PC
                self.new_tick()
            case Opcode.SUB.name:
                self.data_path.set_calc_type("sub")
                self.data_path.latch_address("var")
                self.data_path.latch_acc("count")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.MUL.name:
                self.data_path.set_calc_type("mul")
                self.data_path.latch_address("var")
                self.data_path.latch_acc("count")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.DIV.name:
                self.data_path.set_calc_type("div")
                self.data_path.latch_address("var")
                self.data_path.latch_acc("count")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.JUMP.name:
                self.data_path.latch_pc("jump")
                self.new_tick()
            case Opcode.JMPZ.name:
                if self.data_path.get_zero_flag() == 1:
                    self.data_path.latch_pc("skip_jump")
                else:
                    self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.JMPNZ.name:
                if self.data_path.get_zero_flag() == 0:
                    self.data_path.latch_pc("skip_jump")
                else:
                    self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.JMPS.name:
                if self.data_path.get_signed_flag() == 1:
                    self.data_path.latch_pc("skip_jump")
                else:
                    self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.JMPNS.name:
                if self.data_path.get_signed_flag() == 0:
                    self.data_path.latch_pc("skip_jump")
                else:
                    self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.JMPSZ.name:
                if (self.data_path.get_signed_flag() == 1) or (self.data_path.get_zero_flag() == 1):
                    self.data_path.latch_pc("skip_jump")
                else:
                    self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.JMPNSNZ.name:
                if (self.data_path.get_signed_flag() == 0) and (self.data_path.get_zero_flag() == 0):
                    self.data_path.latch_pc("skip_jump")
                else:
                    self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.READ.name:
                self.data_path.set_calc_type("read")
                self.data_path.latch_address("var")
                self.data_path.latch_acc("count")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.WRITE.name:
                self.data_path.latch_address("var")
                self.data_path.mem_write()
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.READADR.name:
                self.data_path.latch_address("var")
                self.new_tick()
                self.data_path.latch_acc("address")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.WRITEADR.name:
                self.data_path.set_calc_type("read")
                self.data_path.latch_address("acc")
                self.new_tick()
                self.data_path.latch_acc("count")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.INPUT.name:
                self.data_path.latch_acc("input")
                if self.data_path.get_input_flag() == 1:
                    self.data_path.latch_pc("jump")
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.OUTPUT.name:
                self.data_path.output()
                self.data_path.latch_pc("next")
                self.new_tick()
            case Opcode.BREAK.name:
                raise StopIteration()  # Impossible Instruction


def main(mem_file: Path, input_file: Path, output_file: Path) -> None:
    logging.basicConfig(level=logging.DEBUG, filename="files/journal.log", filemode="w")
    with Path(mem_file).open() as f:
        mem = []
        for line in f.readlines():
            mem.append(json.loads(line))
    with Path(input_file).open() as inp_file:
        input_tokens = []
        for char in inp_file.read():
            input_tokens.append(char)
    data_path = DataPath(mem, input_tokens)
    try:
        control_unit = ControlUnit(data_path)
        while True:
            control_unit.read_instruction()
    except StopIteration:
        with Path(output_file).open("w") as out_file:
            out_file.write("".join(data_path.output_tokens))


if __name__ == "__main__":
    main(Path("files/mem.txt"), Path("files/input.txt"), Path("files/output.txt"))
