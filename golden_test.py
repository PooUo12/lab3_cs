import logging
import tempfile
from pathlib import Path
from typing import Any

import pytest

import proc
import translator


@pytest.mark.golden_test("golden_tests/*.yml")
def test(golden: Any, caplog: Any) -> None:
    caplog.set_level(logging.DEBUG)
    with tempfile.TemporaryDirectory() as directory:
        code = Path(directory) / "code.txt"
        input_file = Path(directory) / "input.txt"
        mem = Path(directory) / "mem.txt"
        output_file = Path(directory) / "output.txt"
        with Path(code).open("w") as file:
            file.write(golden["in_code"])
        with Path(input_file).open("w") as file:
            file.write(str(golden["input"]))
        translator.main(code, mem)
        proc.main(mem, input_file, output_file)
        with Path(mem).open() as file:
            out_code = file.read()
        with Path(output_file).open() as file:
            output = file.read()
        assert (out_code == golden.out["out_code"])
        assert (output == golden.out["output"])
        assert (caplog.text == golden.out["proc_log"])
