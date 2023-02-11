# pylint: disable=missing-class-docstring     # чтобы не быть Капитаном Очевидностью
# pylint: disable=missing-function-docstring  # чтобы не быть Капитаном Очевидностью
# pylint: disable=line-too-long               # строки с ожидаемым выводом

"""Интеграционные тесты транслятора и машины
"""

import contextlib
import io
import logging
import os
import tempfile
import unittest

import pytest

import machine
import translator


@pytest.mark.golden_test("golden/*.yml")
def test_whole_by_golden(golden, caplog):
    # Установим уровень отладочного вывода на DEBUG
    caplog.set_level(logging.DEBUG)

    # Создаём временную папку для тестирования приложения.
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Готовим имена файлов для входных и выходных данных.
        source = os.path.join(tmpdirname, "source.asm")
        input_stream = os.path.join(tmpdirname, "input.txt")
        target = os.path.join(tmpdirname, "target")

        # Записываем входные данные в файлы. Данные берутся из теста.
        with open(source, "w", encoding="utf-8") as file:
            file.write(golden["source"])
        with open(input_stream, "w", encoding="utf-8") as file:
            file.write(golden["input"])

        # Запускаем транлятор и собираем весь стандартный вывод в переменную
        # stdout
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            translator.main([source, target])
            print("============================================================")
            machine.main([target, input_stream])

        # Выходные данные также считываем в переменные.
        with open(target, encoding="utf-8") as file:
            code = file.read()

        # Проверяем что ожидания соответствуют реальности.
        assert code == golden.out["code"]
        assert stdout.getvalue() == golden.out["output"]
        assert caplog.text == golden.out["log"]


class TestTranslator(unittest.TestCase):

    def test_hello(self):
        # Создаём временную папку для скомпилированного файла. Удаляется автоматически.
        with tempfile.TemporaryDirectory() as tmpdirname:
            source = "tests/hello.asm"
            target = os.path.join(tmpdirname, "hello")
            input_stream = "tests/hello_input"

            # Собираем весь стандартный вывод в переменную stdout.
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                translator.main([source, target])
                machine.main([target, input_stream])

            # Проверяем, что было напечатано то, что мы ожидали.
            self.assertEqual(stdout.getvalue(),
                             'output: hello\ninstr: 12  ticks: 34\n')

    def test_cat(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            source = "tests/cat.asm"
            target = os.path.join(tmpdirname, "cat")
            input_stream = "tests/cat_input"

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                translator.main([source, target])
                machine.main([target, input_stream])

            self.assertEqual(stdout.getvalue(),
                             'output: Hello, world!\ninstr: 154  ticks: 403\n')

    def test_prob1(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            source = "tests/prob1.asm"
            target = os.path.join(tmpdirname, "prob1")
            input_stream = "tests/prob1_input"

            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                translator.main([source, target])
                machine.main([target, input_stream])

            self.assertEqual(stdout.getvalue(),
                             'output: 233168\ninstr: 7899  ticks: 20473\n')
